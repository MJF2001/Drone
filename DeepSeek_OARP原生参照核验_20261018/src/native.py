"""Native OARP plan / execution / event structures.

The point of this module is that a strip's identity comes from the rank solver and
the tour order, **not** from re-deriving strips out of a cell-by-cell route.  The
old adapter did the latter (`old_services`), and the earlier review showed it
loses native identity in three of four probe constructions.

Three kinds of fact are kept apart and never inferred from one another:

``NativePlan``     what was planned: rank id, axis, canonical cells, visit order
                   and direction, connector spans, service spans, the full route.
``Execution``      what was actually flown: the executed prefix, the current route
                   index and cell, first-coverage indices, steps used.
``EventState``     what changed afterwards: obstacles added, targets published,
                   and the resulting P / F / Q / D.

Everything is JSON round-trip stable, and every derived remnant carries the reason
it exists (`completed`, `partially_executed`, `split_by_coverage`, `blocked`,
`deferred`).

Determinism rules (fixed once, used everywhere):

* ranks are ordered by ``(axis, cells)`` key;
* tour ties are broken by the solver's own order and, when equal, by state index;
* canonical cell order inside a horizontal rank is left-to-right, inside a
  vertical rank bottom-to-top, matching the frozen ``Rank`` convention;
* serialisation sorts keys so a round trip is byte-identical.
"""
import json
from dataclasses import dataclass, field, replace

AXIS = ("H", "V")


def canon_cells(axis, cells):
    if axis == "H":
        return tuple(sorted(cells, key=lambda p: (p[1], p[0])))
    return tuple(sorted(cells, key=lambda p: (p[0], p[1])))


@dataclass(frozen=True)
class Strip:
    rank_id: str
    axis: str
    cells: tuple
    visit_order: int
    reversed_direction: bool
    service_start: int
    service_end: int
    connector_start: int

    def ordered_cells(self):
        return tuple(reversed(self.cells)) if self.reversed_direction else tuple(self.cells)

    def as_dict(self):
        return {"rank_id": self.rank_id, "axis": self.axis,
                "cells": [list(p) for p in self.cells],
                "visit_order": self.visit_order,
                "reversed_direction": self.reversed_direction,
                "service_start": self.service_start,
                "service_end": self.service_end,
                "connector_start": self.connector_start}


@dataclass
class NativePlan:
    plan_id: str
    method_id: str
    seed: int
    start: tuple
    end: tuple
    route: tuple
    strips: tuple
    rank_status: str = ""
    rank_objective: float = None
    tour_status: str = ""
    tour_seconds: float = None
    note: str = ""
    source: str = "rank_solver_and_tour"

    def strip_of(self, rank_id):
        for strip in self.strips:
            if strip.rank_id == rank_id:
                return strip
        return None

    def as_dict(self):
        return {"plan_id": self.plan_id, "method_id": self.method_id, "seed": self.seed,
                "start": list(self.start), "end": list(self.end),
                "route": [list(p) for p in self.route],
                "strips": [s.as_dict() for s in self.strips],
                "rank_status": self.rank_status,
                "rank_objective": self.rank_objective,
                "tour_status": self.tour_status, "tour_seconds": self.tour_seconds,
                "note": self.note, "source": self.source,
                "route_steps": len(self.route) - 1}

    @staticmethod
    def from_dict(payload):
        return NativePlan(
            plan_id=payload["plan_id"], method_id=payload["method_id"],
            seed=payload["seed"], start=tuple(payload["start"]),
            end=tuple(payload["end"]),
            route=tuple(tuple(p) for p in payload["route"]),
            strips=tuple(Strip(rank_id=s["rank_id"], axis=s["axis"],
                               cells=tuple(tuple(p) for p in s["cells"]),
                               visit_order=s["visit_order"],
                               reversed_direction=s["reversed_direction"],
                               service_start=s["service_start"],
                               service_end=s["service_end"],
                               connector_start=s["connector_start"])
                         for s in payload["strips"]),
            rank_status=payload.get("rank_status", ""),
            rank_objective=payload.get("rank_objective"),
            tour_status=payload.get("tour_status", ""),
            tour_seconds=payload.get("tour_seconds"),
            note=payload.get("note", ""),
            source=payload.get("source", ""))


def build_plan(plan_id, method_id, seed, start, end, ordered_strips, metric,
               rank_status="", rank_objective=None, tour_status="", note=""):
    """Lay the ordered strips onto a route and record every index as it happens.

    `ordered_strips` is a sequence of `(rank_id, axis, cells, reversed_direction)`
    in visit order.  A strip's service span is exactly its cells in visit order; the
    connector before it is the metric's canonical shortest path from the previous
    position.  Indices are written while the route is built, never recovered later.
    """
    route = [tuple(start)]
    strips = []
    for order, (rank_id, axis, cells, reversed_direction) in enumerate(ordered_strips):
        ordered = tuple(reversed(tuple(cells))) if reversed_direction else tuple(cells)
        connector_start = len(route) - 1
        connector = metric.path(route[-1], ordered[0])
        route.extend(connector[1:])
        service_start = len(route) - 1
        for a, b in zip(ordered, ordered[1:]):
            route.extend(metric.path(a, b)[1:])
        service_end = len(route) - 1
        strips.append(Strip(rank_id=rank_id, axis=axis, cells=tuple(cells),
                            visit_order=order,
                            reversed_direction=bool(reversed_direction),
                            service_start=service_start, service_end=service_end,
                            connector_start=connector_start))
    route.extend(metric.path(route[-1], tuple(end))[1:])
    return NativePlan(plan_id=plan_id, method_id=method_id, seed=seed,
                      start=tuple(start), end=tuple(end), route=tuple(route),
                      strips=tuple(strips), rank_status=rank_status,
                      rank_objective=rank_objective, tour_status=tour_status,
                      note=note)


@dataclass
class Execution:
    executed_route: tuple
    current_index: int
    current: tuple
    steps_used: int
    first_visit_index: dict
    covered_physical: tuple
    note: str = ""

    def as_dict(self):
        return {"executed_route": [list(p) for p in self.executed_route],
                "current_index": self.current_index,
                "current": list(self.current), "steps_used": self.steps_used,
                "first_visit_index": [[list(k), v] for k, v in
                                      sorted(self.first_visit_index.items())],
                "covered_physical": [list(p) for p in self.covered_physical],
                "note": self.note}


def execute_prefix(plan, length, covered_before=()):
    """Fly ``length`` steps of the plan and record first-visit indices."""
    length = max(0, min(int(length), len(plan.route) - 1))
    executed = plan.route[: length + 1]
    first = {}
    for index, cell in enumerate(executed):
        first.setdefault(cell, index)
    covered = set(covered_before) | set(executed)
    return Execution(executed_route=tuple(executed), current_index=length,
                     current=tuple(executed[-1]), steps_used=length,
                     first_visit_index=first, covered_physical=tuple(sorted(covered)))


@dataclass
class Remnant:
    rank_id: str
    axis: str
    cells: tuple
    original_indices: tuple
    reason: str
    source_axis_preserved: bool = True

    def as_dict(self):
        return {"rank_id": self.rank_id, "axis": self.axis,
                "cells": [list(p) for p in self.cells],
                "original_indices": list(self.original_indices),
                "reason": self.reason,
                "source_axis_preserved": self.source_axis_preserved}


def normalize(plan, execution, covered_physical, free, targets_after=None):
    """Turn the native plan into the remaining service fragments.

    ``covered_physical`` is the physical ledger (real coverage, transit included).
    A cell that the plan wanted but that is already physically covered is removed
    from the fragment; if that splits the fragment, each piece keeps the original
    ``rank_id`` and the exact original indices — the axis is never re-guessed.
    """
    covered = set(covered_physical)
    targets_after = set(targets_after) if targets_after is not None else None
    out = []
    for strip in plan.strips:
        remaining = []
        for offset, cell in enumerate(strip.cells):
            index = (strip.service_start + offset
                     if not strip.reversed_direction
                     else strip.service_end - offset)
            if cell in covered:
                continue
            if cell not in free:
                continue
            if targets_after is not None and cell not in targets_after:
                continue
            remaining.append((index, cell))
        if not remaining:
            out.append(Remnant(strip.rank_id, strip.axis, (), (), "completed"))
            continue
        if len(remaining) == len(strip.cells):
            reason = "unchanged"
        elif len(remaining) == 1:
            reason = "partially_executed"
        else:
            reason = "split_by_coverage"
        runs, current = [], [remaining[0]]
        for previous, item in zip(remaining, remaining[1:]):
            if abs(previous[1][0] - item[1][0]) + abs(previous[1][1] - item[1][1]) == 1:
                current.append(item)
            else:
                runs.append(current)
                current = [item]
        runs.append(current)
        for index, run in enumerate(runs):
            cells = tuple(cell for _, cell in run)
            indices = tuple(i for i, _ in run)
            out.append(Remnant(strip.rank_id + ("" if index == 0 else f"#{index}"),
                               strip.axis, cells, indices,
                               reason if len(runs) == 1 else "split_by_coverage"))
    return out


@dataclass
class EventState:
    name: str
    published: tuple
    free: tuple
    covered: tuple
    pending: tuple
    deferred: tuple
    new_obstacles: tuple = ()
    new_targets: tuple = ()
    note: str = ""

    def as_dict(self):
        return {"name": self.name,
                "published": [list(p) for p in self.published],
                "free": [list(p) for p in self.free],
                "covered": [list(p) for p in self.covered],
                "pending": [list(p) for p in self.pending],
                "deferred": [list(p) for p in self.deferred],
                "new_obstacles": [list(p) for p in self.new_obstacles],
                "new_targets": [list(p) for p in self.new_targets],
                "note": self.note}


def _pts(values):
    return frozenset(tuple(v) for v in values)


def event_state(name, published, free, covered, new_obstacles=(), new_targets=()):
    published = _pts(published) | _pts(new_targets)
    free = (_pts(free) | _pts(new_targets)) - _pts(new_obstacles)
    covered = _pts(covered)
    pending = frozenset((p for p in published - covered if p in free))
    deferred = frozenset(p for p in published - covered if p not in free)
    return EventState(name=name, published=tuple(sorted(published)),
                      free=tuple(sorted(free)), covered=tuple(sorted(covered)),
                      pending=tuple(sorted(pending)), deferred=tuple(sorted(deferred)),
                      new_obstacles=tuple(sorted(new_obstacles)),
                      new_targets=tuple(sorted(new_targets)))


def dumps(obj):
    if hasattr(obj, "as_dict"):
        obj = obj.as_dict()
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def roundtrip(value):
    """Serialise and read back, so a saved plan is provably the same object."""
    payload = json.loads(dumps(value))
    return payload
