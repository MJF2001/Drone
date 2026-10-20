"""One shared classification of a saved result, used by the verifier and the report.

The five buckets are the taxonomy fixed in ``protocol/protocol.json``; the budget
verdict (``within_budget``) is orthogonal and reported separately, because a legal
route produced after the public soft limit is still a route but not an in-budget
result.
"""

NATURAL = "natural_complete_valid"
TRUNCATED = "truncated_with_valid_candidate"
NO_ROUTE = "no_valid_route"
REJECTED = "input_precondition_rejected"
INFEASIBLE = "environment_infeasible"

BUCKETS = (NATURAL, TRUNCATED, NO_ROUTE, REJECTED, INFEASIBLE)


def classify(row):
    """Return (bucket, explanation) for one saved result payload."""
    status = row.get("status")
    audit = row.get("audit") or {}
    termination = row.get("termination") or {}

    if status == "environment_infeasible":
        return INFEASIBLE, "base or outstanding target unreachable"
    if status in ("input_precondition_unmet", "adapter_assertion"):
        return REJECTED, f"{status}: {row.get('reason', '')}"[:160]
    if not row.get("route") or not audit.get("valid"):
        return NO_ROUTE, f"status={status} errors={audit.get('errors')}"[:160]
    if termination.get("natural"):
        return NATURAL, "engine reported its own termination and the route is valid"
    return TRUNCATED, f"engine stopped by {termination.get('reason', 'a cap')} with a valid route"


def in_budget_success(row):
    """A result that may be counted as an in-budget completion."""
    bucket, _ = classify(row)
    if bucket not in (NATURAL, TRUNCATED):
        return False
    return bool(row.get("within_budget"))
