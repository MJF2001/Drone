"""Case loading and the local input-validation wrapper.

The sealed v0.1 validator rejects any non-positive remaining resource.  The round's
case list needs one case where the resource is exactly 0, the task is empty and the
vehicle is already at the base: zero steps are needed, so rejecting it would be
wrong.  Rather than editing the sealed module, this wrapper re-admits exactly that
situation and nothing else:

    resource == 0  AND  Q == {}  AND  current == base

Everything else about the sealed validator is unchanged, and the re-admission is
reported in ``soft`` so a record can never hide it.  ``tests/test_inputs.py``
checks that resource 0 with a non-empty task, or away from the base, is still
rejected.
"""
import json

import bootstrap
from problem import InputError, PlanRequest, Termination, validate_inputs

CASES = bootstrap.PROTOCOL / "cases.json"
DEFAULT_SOFT_LIMIT = 10.0


def load_cases():
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def find_case(case_id):
    for case in load_cases():
        if case["case_id"] == case_id:
            return case
    raise KeyError(f"unknown case {case_id}")


def load_case(case_id, seed, soft_limit=DEFAULT_SOFT_LIMIT):
    case = find_case(case_id)
    return PlanRequest(
        case_id=case_id,
        free=frozenset(map(tuple, case["free"])),
        published_targets=frozenset(map(tuple, case["published_targets"])),
        covered=frozenset(map(tuple, case["covered"])),
        current=tuple(case["current"]),
        base=tuple(case["base"]),
        old_route=tuple(map(tuple, case["old_route"])),
        remaining_resource=case["remaining_resource"],
        seed=seed,
        termination=Termination(time_limit_seconds=float(soft_limit)),
        meta={"case_note": case.get("note", ""), "expected": case.get("expected", {})},
    )


def validate_request(request):
    """Return ``{"ok": bool, "code", "detail", "soft", "extension"}``."""
    try:
        soft = list(validate_inputs(request))
    except InputError as exc:
        code = getattr(exc, "code", "input_error")
        detail = getattr(exc, "detail", str(exc))
        if (code == "nonpositive_resource"
                and request.remaining_resource == 0
                and not request.pending
                and tuple(request.current) == tuple(request.base)):
            return {"ok": True, "code": "ok",
                    "detail": "resource 0 accepted: empty task at the base",
                    "soft": [("resource_zero_at_base", "0")],
                    "extension": "resource_zero_empty_task_at_base"}
        return {"ok": False, "code": code, "detail": str(detail), "soft": [],
                "extension": None}
    return {"ok": True, "code": "ok", "detail": "", "soft": soft, "extension": None}
