"""The semantic gate, as one module used by both the checker and the tests.

A record may only be labelled a success when the independent audit says the route
is legal, returns to the base, covers every pending target and fits the remaining
resource.  A failure label must carry the error that justifies it.
"""
SUCCESS = ("finished", "planned", "planned_at_timeout", "complete_coverage",
           "finished_with_safety_limit")
FAILURE = ("environment_infeasible", "no_legal_route_within_resource",
           "resource_exceeded", "coverage_incomplete", "invalid_route",
           "input_precondition_unmet", "adapter_assertion", "planning_failure",
           "timeout", "no_legal_candidate", "deadline_before_complete_route",
           "safety_limit_before_complete_route")
MOVEMENT = {"wrong_start", "missing_return", "illegal_step",
            "collision_or_out_of_bounds"}


def grade(status, audit, termination=None):
    """Return the list of semantic problems for one record (empty means clean)."""
    problems = []
    errors = set(audit.get("errors") or [])
    route_empty = audit.get("route_steps") is None
    termination = termination or {}

    if status in SUCCESS:
        if not audit.get("valid"):
            problems.append("success_status_with_invalid_audit")
        if not audit.get("coverage_complete"):
            problems.append("success_status_without_full_coverage")
        if (audit.get("resource") or {}).get("ok") is False:
            problems.append("success_status_over_resource")
        if errors & MOVEMENT:
            problems.append("success_status_with_illegal_movement")
        if route_empty:
            problems.append("success_status_without_route")
        if termination.get("natural") is False and status in ("finished", "complete_coverage"):
            problems.append("success_status_marked_unnatural")
    elif status in FAILURE:
        if status == "resource_exceeded" and "distance_budget_exceeded" not in errors:
            problems.append("resource_exceeded_without_resource_error")
        if status == "coverage_incomplete" and "coverage_omission" not in errors:
            problems.append("coverage_incomplete_without_omission")
        if status == "environment_infeasible" and not route_empty:
            problems.append("environment_infeasible_with_a_route")
        if status in ("timeout", "deadline_before_complete_route",
                      "safety_limit_before_complete_route"):
            if termination.get("natural"):
                problems.append("truncated_status_marked_natural")
    else:
        problems.append(f"unknown_status:{status}")
    return problems
