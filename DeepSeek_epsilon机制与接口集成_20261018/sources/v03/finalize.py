"""One place where a route becomes a graded result (R1 / R3 fix).

Every branch of every adapter -- environment infeasible, empty task, normal,
deadline -- is funnelled through :func:`finalize`.  "Success" therefore always
means all of:

    starts at the real current position
    ends at the base
    every step is a four-neighbour step over currently free cells
    every still-pending target is visited
    ``route_steps`` fits the remaining resource

An empty task does not make the return flight free, and a route that overruns
the resource is reported as ``resource_exceeded`` even when it covers the task.

Failure routes may still be saved; their status must then be a failure status.

v0.3: the audit is reached through the ``audit_independent`` module object rather
than a module-level binding, so a test can wrap it (to inject a slow audit or a
clock jump) without editing this file.  The call itself is inside the adapter's
timed region, so the returned cost includes the pre-return legality check.
"""
import audit_independent

SUCCESS_STATUSES = ("finished", "planned", "planned_at_timeout", "complete_coverage",
                    "finished_with_safety_limit")
FAILURE_STATUSES = (
    "environment_infeasible", "no_legal_route_within_resource", "resource_exceeded",
    "coverage_incomplete", "invalid_route", "input_precondition_unmet",
    "adapter_assertion", "planning_failure", "timeout", "no_legal_candidate",
    "deadline_before_complete_route", "safety_limit_before_complete_route",
)

MOVEMENT_ERRORS = {"wrong_start", "missing_return", "illegal_step", "collision_or_out_of_bounds"}


def finalize(request, route, *, natural, reason, fallback_used=False, fallback_steps=None,
             best_candidate_source="", final_source="", stage_seconds=None, errors=None,
             meta=None, success_status="finished", failure_status=None):
    """Return the audit plus the status the record must carry.

    ``success_status`` is only used when the audit really passes.
    ``failure_status`` is a hint from the engine (e.g. ``timeout``); it is used
    only when the route is not a complete legal completion.
    """
    audit = audit_independent.audit_route(request, route)
    errors = list(errors or [])
    route = tuple(tuple(p) for p in (route or ()))
    limit = request.resource_limit()
    steps = audit.get("route_steps")

    has_route = bool(route)
    movement = MOVEMENT_ERRORS & set(audit["errors"])
    coverage = "coverage_omission" in audit["errors"]
    resource = "distance_budget_exceeded" in audit["errors"]

    if has_route and audit["valid"]:
        status = success_status
        natural_out = bool(natural)
        reason_out = reason
    elif not has_route:
        status = failure_status or "no_legal_route_within_resource"
        natural_out = False
        reason_out = reason or status
    else:
        # a route exists but is not a complete legal completion
        if movement and movement != {"missing_return"}:
            status = "invalid_route"
        elif movement == {"missing_return"} and failure_status:
            status = failure_status            # e.g. the deadline cut the return
        elif coverage and not resource:
            status = "coverage_incomplete"
        elif resource and not coverage:
            status = "resource_exceeded"
        elif coverage and resource:
            status = "coverage_incomplete"
            errors.append("also_over_resource")
        else:
            status = "invalid_route"
        natural_out = False
        if status in ("coverage_incomplete", "resource_exceeded"):
            reason_out = status
        else:
            reason_out = reason or status
        if coverage:
            errors.append(f"uncovered:{audit['uncovered_count']}")
        if resource:
            errors.append(f"over_resource:{steps}>{limit}")
        if movement:
            errors.extend(sorted(movement))

    resource_check = {
        "limit": limit,
        "used": steps,
        "ok": (None if limit is None else (steps is not None and steps <= limit)),
        "source": "recomputed_from_route",
    }
    return {
        "status": status,
        "reason": reason_out,
        "audit": audit,
        "resource_check": resource_check,
        "termination": {"natural": natural_out and status in SUCCESS_STATUSES,
                        "reason": reason_out, "engine_natural": bool(natural)},
        "errors": errors,
        "meta": dict(meta or {}),
    }
