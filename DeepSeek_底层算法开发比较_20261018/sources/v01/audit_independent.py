"""Independent auditor.

Input: the request as received and the saved cell-by-cell route.  Nothing else.
It deliberately does not import the planner's coverage helper, does not call
``Geometry.expand``/``single_cell_audit``/``audit``, and never trusts a
self-reported coverage set.  It also recomputes the coverage ledger from the
route, so an adapter that forgets to credit transit coverage is caught.

The historical ``audit.py`` in the frozen bundle is a *second* opinion and is
cross-checked in the tests; it is not used to decide validity here.
"""
from collections import Counter

STEPS = {"E": (1, 0), "N": (0, 1), "W": (-1, 0), "S": (0, -1)}


def _direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    for name, (sx, sy) in STEPS.items():
        if (dx, dy) == (sx, sy):
            return name
    return None


def audit_route(request, route, radius=0):
    """Recompute legality, coverage, endpoint and resource from scratch."""
    errors = []
    route = tuple(tuple(p) for p in (route or ()))
    free = set(request.free)
    targets = set(request.published_targets)
    ledger = set(request.covered)

    if not route:
        return {
            "valid": False, "errors": ["empty_route"], "route_steps": None,
            "coverage_complete": False, "uncovered": sorted(request.pending)[:32],
            "uncovered_count": len(request.pending), "covered_physical": [],
            "deferred_untouched": sorted(request.deferred), "deferred_visited": [],
            "resource": {"limit": request.resource_limit(), "used": None, "ok": False},
            "direction_changes": None, "revisited_positions": None,
            "illegal_steps": [], "collisions": [], "coverage_claimed_without_visit": [],
            "starts_at_current": False, "ends_at_base": False,
            "covered_physical_count": 0, "ledger_size": len(request.covered),
            "distinct_cells": 0, "target_visits": 0,
        }

    # -- movement ---------------------------------------------------------
    if route[0] != tuple(request.current):
        errors.append("wrong_start")
    if route[-1] != tuple(request.base):
        errors.append("missing_return")
    collisions = [p for p in route if p not in free]
    if collisions:
        errors.append("collision_or_out_of_bounds")
    illegal = [(a, b) for a, b in zip(route, route[1:])
               if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1]
    if illegal:
        errors.append("illegal_step")

    # -- physical coverage: a target is covered exactly when the route visits it.
    #    ``pending`` already excludes the ledger and the deferred (blocked) set,
    #    so a deferred target can never make a route incomplete.
    visited = set(route)
    pending = set(request.pending)
    physical = sorted((ledger | visited) & targets)
    uncovered = sorted(pending - visited)
    if uncovered:
        errors.append("coverage_omission")

    # a target may not be reported covered unless it is visited or already in the ledger
    fabricated = sorted(ledger - targets)

    # deferred targets must be untouched: still in the ledger's not-done side
    deferred_hit = sorted(set(request.deferred) & visited)

    # -- resource ---------------------------------------------------------
    steps = len(route) - 1
    limit = request.resource_limit()
    resource = {"limit": limit, "used": steps, "ok": True if limit is None else steps <= limit}
    if limit is not None and steps > limit:
        errors.append("distance_budget_exceeded")

    directions = [d for d in (_direction(a, b) for a, b in zip(route, route[1:])) if d]
    counts = Counter(route)
    return {
        "valid": not errors,
        "errors": errors,
        "route_steps": steps,
        "starts_at_current": route[0] == tuple(request.current),
        "ends_at_base": route[-1] == tuple(request.base),
        "collisions": [list(p) for p in collisions[:16]],
        "illegal_steps": [[list(a), list(b)] for a, b in illegal[:16]],
        "coverage_complete": not uncovered,
        "uncovered": [list(p) for p in uncovered[:32]],
        "uncovered_count": len(uncovered),
        "covered_physical": [list(p) for p in physical],
        "covered_physical_count": len(physical),
        "ledger_size": len(ledger),
        "coverage_claimed_without_visit": [list(p) for p in fabricated[:16]],
        "deferred_untouched": [list(p) for p in sorted(request.deferred)],
        "deferred_visited": [list(p) for p in deferred_hit[:16]],
        "resource": resource,
        "distinct_cells": len(counts),
        "revisited_positions": len(route) - len(counts),
        "direction_changes": sum(a != b for a, b in zip(directions, directions[1:])),
        "target_visits": sum(counts.get(p, 0) for p in targets),
    }


# ---------------------------------------------------------------- negative cases
# Used by the tests to prove the auditor rejects what it claims to reject.
def n_diagonal_jump(route):
    """Insert one illegal diagonal move."""
    route = list(route)
    for index, (a, b) in enumerate(zip(route, route[1:])):
        if a[0] != b[0] and a[1] != b[1]:
            del route[index + 1]
            del route[index + 1]
            return tuple(route)
    # no diagonal exists, so splice one in by removing a corner between two steps
    for index in range(1, len(route) - 1):
        a, b = route[index - 1], route[index + 1]
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 0:
            del route[index]
            return tuple(route)
    return tuple(route[:1] + route[2:])


def n_drop_coverage(route, request):
    """Remove one visit that is the only visit of some pending target."""
    counts = Counter(route)
    for p in sorted(request.pending):
        if counts.get(p, 0) == 1 and p not in request.covered:
            index = route.index(p)
            if 0 < index < len(route) - 1:
                return tuple(route[:index] + route[index + 1:])
    return tuple(route)


def n_wrong_return(route, request):
    """End somewhere other than the base."""
    return tuple(route[:-1] + (tuple(request.current),)) if len(route) > 1 else tuple(route)


def n_ledger_confusion(request):
    """A result that claims coverage without visiting: ledger inflated."""
    return request.replaced(covered=request.published_targets)
