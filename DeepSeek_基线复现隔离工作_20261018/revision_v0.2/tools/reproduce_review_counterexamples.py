"""Re-run the three reviewer counterexamples against v0.2, with the REAL clock.

The unit tests for R2 use an injected fake clock so they never depend on flaky
nanosecond timing.  This tool deliberately does the opposite: it reproduces the
reviewer's exact scenario with the ordinary wall clock, so the claim "the limit
is now actually read" is also shown without a fake clock.
"""
import json
import sys
from pathlib import Path

V02 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V02 / "src_v02"))

import bootstrap_v02  # noqa: E402,F401

from adapters import registry  # noqa: E402

# R5: these calls are development calls, and they are registered as such.
registry.CONTEXT["kind"] = "development"
from problem import PlanRequest, Termination  # noqa: E402

TARGET = V02 / "evidence" / "review_counterexamples.json"


def r1():
    cells = {(0, 0), (1, 0), (2, 0)}
    request = PlanRequest(case_id="r1_counterexample", free=frozenset(cells),
                          published_targets=frozenset(cells), covered=frozenset(cells),
                          current=(0, 0), base=(2, 0), old_route=(),
                          remaining_resource=1, seed=1,
                          termination=Termination(time_limit_seconds=30.0))
    rows = []
    for method in registry.available():
        result = registry.run(method, request)
        rows.append({"method": method, "status": result.status,
                     "reason": result.reason,
                     "route_steps": result.route_steps,
                     "audit_valid": (result.audit or {}).get("valid"),
                     "audit_errors": (result.audit or {}).get("errors"),
                     "natural": result.termination.get("natural"),
                     "success": result.status in ("finished", "planned",
                                                  "planned_at_timeout",
                                                  "complete_coverage",
                                                  "finished_with_safety_limit")})
    return {"case": "R1 empty task, resource 1, return needs 2 steps", "rows": rows}


def r2():
    cells = frozenset((x, y) for x in range(5) for y in range(5))
    request = PlanRequest(case_id="r2_counterexample", free=cells,
                          published_targets=cells, covered=frozenset(),
                          current=(0, 0), base=(0, 0), old_route=(),
                          remaining_resource=None, seed=1,
                          termination=Termination(time_limit_seconds=1e-9))
    result = registry.run("EPSILON_STAR", request)
    return {"case": "R2 epsilon-star, 5x5, time_limit_seconds=1e-9, real clock",
            "status": result.status, "reason": result.reason,
            "route_steps": result.route_steps,
            "natural": result.termination.get("natural"),
            "deadline": result.meta.get("deadline"),
            "adapter_call_seconds": result.stage_seconds.get("adapter_call")}


def r3():
    payload = json.loads((bootstrap_v02.OUT / "tests" / "fixtures" / "cases"
                          / "m02_extension_only.json").read_text(encoding="utf-8"))
    grid = payload["grid"]
    request = PlanRequest(case_id="r3_counterexample",
                          free=frozenset(map(tuple, grid["free"])),
                          published_targets=frozenset(map(tuple, grid["published_targets"])),
                          covered=frozenset(map(tuple, grid["covered"])),
                          current=tuple(grid["current"]), base=tuple(grid["base"]),
                          old_route=tuple(map(tuple, grid["old_route"])),
                          remaining_resource=grid["remaining_resource"],
                          seed=1, termination=Termination(time_limit_seconds=30.0))
    rows = []
    for method in registry.available():
        result = registry.run(method, request)
        rows.append({"method": method,
                     "adapter_call": result.stage_seconds.get("adapter_call"),
                     "total": result.stage_seconds.get("_total"),
                     "instrumented": result.stage_seconds.get("_instrumented"),
                     "missing": result.stage_seconds.get("_missing")})
    return {"case": "R3 end-to-end time is non-zero and fixed after stop", "rows": rows}


def main():
    payload = {"generated_by": "tools/reproduce_review_counterexamples.py",
               "r1": r1(), "r2": r2(), "r3": r3()}
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    for row in payload["r1"]["rows"]:
        print(f"  R1 {row['method']:14s} status={row['status']:34s} "
              f"steps={row['route_steps']} success={row['success']} natural={row['natural']}")
    print(f"  R2 {payload['r2']['status']} steps={payload['r2']['route_steps']} "
          f"natural={payload['r2']['natural']} adapter_call={payload['r2']['adapter_call_seconds']}")
    for row in payload["r3"]["rows"]:
        print(f"  R3 {row['method']:14s} adapter_call={row['adapter_call']:.6f} "
              f"missing={row['missing']}")


if __name__ == "__main__":
    main()
