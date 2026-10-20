"""The two references required by this round, plus the shared fallback.

``OARP_RANK0_FULLTOUR_SCENE``
    Rank minimisation over the **current** Q with no change budget (variant 0),
    then every rank enters one full GTSP with both directions and fixed
    start/end.  No old service is passed to ``path_sets``, so no old block keeps
    its internal order -- that is what makes it a whole-strip re-plan rather than
    a larger cap.

``OARP_REPLAN2_NATIVE_SCENE``
    Model 2 (change budget ``changed = added + extended/2``) over the current Q
    *against the native remaining fragments*, whose identity, axis and original
    indices come from the saved native plan (never re-derived from the route).
    Unchanged fragments keep their exact internal old connector via ``path_sets``.

Both share one frozen fallback, computed from the legal old suffix plus a
deterministic greedy completion.  The fallback is recorded separately and never
masquerades as a core result.

Neither function is the author's online robot system, and neither is a
globally optimal coverage algorithm.
"""
import time

from oarp_replan.ranks import Rank, rank_replan
from oarp_replan.tour import OldService, path_sets, tour_replan

from common_geometry import GridMetric

import native

METHOD_RANK0 = "OARP_RANK0_FULLTOUR_SCENE"
METHOD_REPLAN2 = "OARP_REPLAN2_NATIVE_SCENE"
CORE_VERSION = "oarp_native_refs_v1_20261018"
ADAPTER_VERSION = "oarp_native_entry_v1_20261018"


def _metric(free):
    return GridMetric(free)


def fallback_route(current, base, pending, free):
    """The frozen shared fallback: greedy nearest over ``pending`` then the base.

    Explicitly an engineering candidate, not the paper's online exploration.
    """
    metric = _metric(free)
    remaining = set(pending)
    route = [tuple(current)]
    covered = set()
    while remaining:
        here = route[-1]
        target = min(remaining, key=lambda p: (metric.distance(here, p), p))
        route.extend(metric.path(here, target)[1:])
        covered.add(target)
        remaining.discard(target)
    route.extend(metric.path(route[-1], tuple(base))[1:])
    return tuple(route)


def _tour_order(blocks, start, end, free, seconds, seed, exact=False):
    """Run the frozen GTSP and return the state order (list of state indices)."""
    g = _geometry(start, end, free, seconds)
    return tour_replan(g, blocks, seconds=seconds, seed=seed, exact=exact)


def _geometry(start, end, free, seconds):
    from model import Geometry, Snapshot
    snapshot = Snapshot("tour-geometry", frozenset(free), frozenset(), frozenset(),
                        tuple(start), tuple(end), (), radius=0)
    return Geometry(snapshot, time.perf_counter() + max(0.05, seconds))


def _strips_from_tour(blocks, states, order, axis_by_key, prefix):
    """Translate a decoded GTSP tour into visit-ordered strips.

    `states` interleaves `(path, reversed(path))` per block, so the parity of a
    state index tells the direction.  The axis of a retained path block comes from
    the native remnant it carries, never from re-reading the geometry.
    """
    strips = []
    if not order or len(order) < 2:
        return strips
    for state_index in order[1:-1]:
        path = states[state_index]
        block_index = state_index // 2
        reversed_direction = bool(state_index % 2)
        block = blocks[block_index]
        cells = tuple(path) if not reversed_direction else tuple(reversed(path))
        if block["kind"] == "path" and block["rank_keys"]:
            axis = axis_by_key.get(block["rank_keys"][0]) or _axis(cells)
        else:
            axis = _axis(cells)
        strips.append((f"{prefix}-{len(strips)}", axis, cells, reversed_direction))
    return strips


def rank0_fulltour(case, q_cells, free, current, base, seed, seconds, plan_id):
    """Variant 0: no change budget, every rank re-enters the full tour."""
    deadline = time.perf_counter() + seconds
    pending = frozenset(q_cells)
    ranked = rank_replan(pending, old=(), cap=None, variant=0, deadline=deadline,
                         integer_fallback=True, allow_certification_repair=True)
    detail = {"variant": 0, "rank_status": ranked.get("status"),
              "rank_objective": ranked.get("objective"),
              "rank_metrics": ranked.get("metrics"),
              "rank_seconds": ranked.get("seconds"),
              "rank_attempts": ranked.get("attempts"),
              "certification_repair": ranked.get("certification_repair", False),
              "old_services_passed": 0,
              "cap": None}
    if ranked.get("ranks") is None:
        return None, detail
    ranks = ranked["ranks"]
    # no old services: every rank is a free block, nothing retains an old order
    blocks = path_sets(ranks, (), (), frozenset(free))
    tour = _tour_order(blocks, current, base, free,
                      max(0.05, deadline - time.perf_counter()), seed)
    detail.update({"tour_status": tour.get("solver", {}).get("timeout") is False and
                   "converged" or "timeout",
                   "tour_solver": tour.get("solver"),
                   "blocks": [{"kind": b["kind"], "rank_keys": b["rank_keys"]}
                              for b in blocks]})
    ordered_strips = _strips_from_tour(blocks, tour.get("states") or [],
                                       tour.get("order") or [], {}, "rank0")
    if not ordered_strips:
        return None, detail
    plan = native.build_plan(plan_id, METHOD_RANK0, seed, current, base,
                             ordered_strips, _metric(free),
                             rank_status=str(ranked.get("status")),
                             rank_objective=ranked.get("objective"),
                             tour_status=detail["tour_status"])
    return plan, detail


def _axis(cells):
    if len(cells) == 1:
        return "V"      # a single cell has no geometric axis; kept explicitly
    return "H" if cells[0][1] == cells[-1][1] else "V"


def replan2_native(case, remnants, q_cells, free, current, base, seed, seconds,
                   plan_id, cap_override):
    """Model 2 against the native fragments; unchanged fragments keep their path."""
    deadline = time.perf_counter() + seconds
    pending = frozenset(q_cells)
    services = tuple(OldService(Rank(r.axis, tuple(r.cells)), r.original_indices[0],
                               r.original_indices[-1])
                     for r in remnants if r.cells)
    old = tuple(s.rank for s in services)
    ranked = rank_replan(pending, old=old, cap=cap_override, variant=2,
                         deadline=deadline, integer_fallback=True,
                         allow_certification_repair=True)
    detail = {"variant": 2, "cap": cap_override,
              "rank_status": ranked.get("status"),
              "rank_objective": ranked.get("objective"),
              "rank_metrics": ranked.get("metrics"),
              "rank_seconds": ranked.get("seconds"),
              "rank_attempts": ranked.get("attempts"),
              "certification_repair": ranked.get("certification_repair", False),
              "old_services_passed": len(services)}
    if ranked.get("ranks") is None:
        return None, detail
    old_route = tuple(case["old_route"])
    try:
        blocks = path_sets(ranked["ranks"], services, old_route, frozenset(free))
    except (ValueError, RuntimeError) as exc:
        detail["path_sets_error"] = f"{type(exc).__name__}: {exc}"
        return None, detail
    detail["blocks"] = [{"kind": b["kind"], "rank_keys": b["rank_keys"]}
                        for b in blocks]
    tour = _tour_order(blocks, current, base, free,
                      max(0.05, deadline - time.perf_counter()), seed)
    detail.update({"tour_status": "converged" if tour.get("solver", {}).get("timeout") is False
                   else "timeout", "tour_solver": tour.get("solver")})
    axis_by_key = {}
    for remnant in remnants:
        base_key = (remnant.axis, tuple(remnant.cells))
        axis_by_key[base_key] = remnant.axis
    ordered_strips = _strips_from_tour(blocks, tour.get("states") or [],
                                       tour.get("order") or [], axis_by_key, "replan2")
    if not ordered_strips:
        return None, detail
    plan = native.build_plan(plan_id, METHOD_REPLAN2, seed, current, base,
                             ordered_strips, _metric(free),
                             rank_status=str(ranked.get("status")),
                             rank_objective=ranked.get("objective"),
                             tour_status=detail["tour_status"])
    return plan, detail
