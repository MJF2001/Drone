"""Current-task problem statement for this round.

Model (fixed by the user, not by this file):

* single vehicle, four-neighbour, one-cell-per-step movement;
* the cell directly below is the only inspected cell, so the footprint radius is
  ``0``: being at a target cell covers that target;
* passing over a target cell completes it, including during transit;
* already-covered free cells and non-target free cells stay passable;
* obstacles are simultaneously no-fly and occluding.  A published target that is
  blocked is *deferred*: kept in the ledger, not deleted, not marked complete;
* only currently published information may be used.

Ledger identities used throughout:

    P  currently published targets
    C  actually covered targets            (C subset of P)
    F  currently free cells
    Q  remaining and currently checkable   Q = (P - C) and F
    D  remaining but deferred              D = (P - C) - F

The frozen v2 suite expects ``snapshot.targets`` to be already free, so a
``Snapshot`` is built with ``targets = P and F`` and ``covered = C``.  The
deferred set is exported separately and never silently dropped.
"""
from dataclasses import dataclass, field, replace

from bootstrap import FROZEN, OUT  # noqa: F401  (keeps import order explicit)

from model import Snapshot  # frozen shared geometry

from common_geometry import GridMetric, NoPath, assert_legal


class InputError(ValueError):
    """Contradictory input.  Never silently repaired."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Termination:
    """Termination configuration handed to an adapter.

    ``time_limit_seconds`` is a hard wall-clock safety cap, not a natural stop.
    ``natural`` names the method's own stopping rule, and ``extra`` carries
    method-specific limits (iteration count, 2-opt passes, ...).
    """

    time_limit_seconds: float = 30.0
    natural: str = "method_natural_termination"
    extra: dict = field(default_factory=dict)

    def as_dict(self):
        return {"time_limit_seconds": self.time_limit_seconds,
                "natural": self.natural, "extra": dict(self.extra)}


@dataclass(frozen=True)
class PlanRequest:
    """Uniform input for every method."""

    case_id: str
    free: frozenset
    published_targets: frozenset
    covered: frozenset
    current: tuple
    base: tuple
    old_route: tuple = ()
    remaining_resource: int = None
    seed: int = 0
    termination: Termination = field(default_factory=Termination)
    initial_targets: frozenset = None
    meta: dict = field(default_factory=dict)

    # -- derived sets ----------------------------------------------------
    @property
    def pending(self):
        return frozenset((self.published_targets - self.covered) & self.free)

    @property
    def deferred(self):
        return frozenset((self.published_targets - self.covered) - self.free)

    @property
    def history_targets(self):
        """Pre-event published targets, used only as an OARP rank reference."""
        return self.published_targets if self.initial_targets is None else self.initial_targets

    def resource_limit(self):
        if self.remaining_resource is None:
            return None
        return int(self.remaining_resource)

    def to_snapshot(self):
        budget = self.resource_limit()
        return Snapshot(
            name=self.case_id,
            free=frozenset(self.free),
            targets=frozenset(self.published_targets & self.free),
            covered=frozenset(self.covered),
            current=tuple(self.current),
            base=tuple(self.base),
            old_route=tuple(tuple(p) for p in self.old_route),
            radius=0,
            distance_budget=budget if budget is not None else 1 << 30,
        )

    def replaced(self, **kwargs):
        return replace(self, **kwargs)

    def describe(self):
        return {
            "case_id": self.case_id,
            "free": len(self.free), "published_targets": len(self.published_targets),
            "covered": len(self.covered), "pending": len(self.pending),
            "deferred": len(self.deferred), "current": list(self.current),
            "base": list(self.base), "old_route_len": len(self.old_route),
            "remaining_resource": self.remaining_resource, "seed": self.seed,
            "termination": self.termination.as_dict(),
            "meta": dict(self.meta),
        }


def validate_inputs(request):
    """Reject contradictions instead of deleting tasks.

    Returns a list of ``(code, detail)`` pairs; raises ``InputError`` for the
    first hard contradiction so a caller cannot continue on bad input.
    """
    soft = []
    if not isinstance(request.free, frozenset) or not isinstance(request.published_targets, frozenset):
        raise InputError("input_types", "free and published_targets must be frozensets")
    if request.current not in request.free:
        raise InputError("current_not_free", str(request.current))
    if request.base not in request.free:
        raise InputError("base_not_free", str(request.base))
    if not request.covered <= request.published_targets:
        extra = sorted(request.covered - request.published_targets)[:5]
        raise InputError("covered_not_published", str(extra))
    if request.remaining_resource is not None and request.remaining_resource < 0:
        # v0.2 (R1): a remaining resource of exactly 0 is a legal state, not a
        # contradictory input.  It means "no step is left"; a route with
        # route_steps > 0 then fails the resource check like any other route.
        raise InputError("negative_resource", str(request.remaining_resource))
    if request.termination.time_limit_seconds <= 0:
        raise InputError("nonpositive_time_limit", str(request.termination.time_limit_seconds))
    blocked_targets = request.published_targets - request.free
    if blocked_targets & request.covered:
        # A target the vehicle already covered may later be built over.  That is
        # not a contradiction: the ledger keeps the completion and the blocked
        # cell simply cannot be flown again.  It is reported, never deleted.
        soft.append(("covered_target_now_blocked",
                     str(sorted(blocked_targets & request.covered)[:5])))
    for p in request.old_route:
        if p not in request.free:
            soft.append(("old_route_crosses_blocked", str(p)))
            break
    return soft


def reachability(request):
    """Independent four-neighbour reachability of base and of every pending target."""
    metric = GridMetric(request.free)
    seen = metric.reachable(tuple(request.current))
    if tuple(request.base) not in seen:
        return {"ok": False, "code": "base_unreachable", "cell": list(request.base)}
    unreachable = sorted(request.pending - {tuple(p) for p in seen})
    if unreachable:
        return {"ok": False, "code": "target_unreachable", "cells": [list(c) for c in unreachable[:16]],
                "count": len(unreachable)}
    return {"ok": True, "code": "ok"}


def environment_status(request):
    """Environment-level infeasibility, reported separately from planner failure."""
    result = reachability(request)
    if not result["ok"]:
        return result
    if not request.pending:
        return {"ok": True, "code": "nothing_pending"}
    return {"ok": True, "code": "solvable_environment"}
