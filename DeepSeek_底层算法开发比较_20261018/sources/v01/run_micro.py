"""Run every available method on every micro fixture and save the evidence.

This is the only program in the delivery that starts a planner.  It writes:

    artifacts/runs/micro_runs.json      one row per (case, method)
    artifacts/routes/<case>/<method>.json  the saved cell-by-cell route and audit
    artifacts/runs/exact_micro.json     exact optimum for the small instances
    logs/call_ledger.csv                every planner invocation, including repeats
    logs/run_micro_<stamp>.log          the console transcript

Micro instances only: this is a correctness run, not a performance comparison,
and it must not be read as a ranking.
"""
import csv
import hashlib
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(OUT / "tests"))

from bootstrap import ARTIFACTS, LOGS, OUT as OUT_ROOT, FIXTURES  # noqa: E402
from problem import PlanRequest, Termination, validate_inputs, environment_status  # noqa: E402
from audit_independent import audit_route  # noqa: E402
from adapters import registry  # noqa: E402

CASES = OUT / "tests" / "fixtures" / "cases"


def load_cases():
    out = []
    for path in sorted(CASES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        grid = payload["grid"]
        request = PlanRequest(
            case_id=payload["case_id"],
            free=frozenset(map(tuple, grid["free"])),
            published_targets=frozenset(map(tuple, grid["published_targets"])),
            covered=frozenset(map(tuple, grid["covered"])),
            current=tuple(grid["current"]),
            base=tuple(grid["base"]),
            old_route=tuple(map(tuple, grid["old_route"])),
            remaining_resource=grid["remaining_resource"],
            initial_targets=frozenset(map(tuple, grid["initial_targets"])),
            seed=20261018,
            termination=Termination(time_limit_seconds=30.0,
                                    natural="method_specific"),
            meta={"fixture": path.name, "notes": payload["notes"], "event": payload["event"]},
        )
        out.append((payload, request, path))
    return out


def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOGS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "runs").mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "routes").mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"run_micro_{stamp}.log"
    log = open(log_path, "w", encoding="utf-8")
    ledger_path = LOGS / "call_ledger.csv"
    new_ledger = not ledger_path.exists()
    ledger = open(ledger_path, "a", newline="", encoding="utf-8-sig")
    writer = csv.writer(ledger)
    if new_ledger:
        writer.writerow(["stamp", "case_id", "method_id", "method_version", "seed",
                         "time_limit_seconds", "status", "route_steps", "seconds",
                         "valid", "natural_termination", "fallback_used"])

    def say(text=""):
        print(text, flush=True)
        log.write(text + "\n")
        log.flush()

    cases = load_cases()
    methods = list(registry.available())
    say(f"run_micro {stamp}: {len(cases)} cases x {len(methods)} methods = {len(cases) * len(methods)}")
    say(f"methods: {methods}")
    say(f"interpreter: {sys.executable}")
    say(f"PYTHONDONTWRITEBYTECODE={__import__('os').environ.get('PYTHONDONTWRITEBYTECODE')}")
    say("")

    rows, failures = [], []
    for payload, request, path in cases:
        soft = validate_inputs(request)
        env = environment_status(request)
        audit_input = audit_route(request, ())
        say(f"[{request.case_id}] pending={len(request.pending)} deferred={len(request.deferred)} "
            f"env={env['code']} soft={[code for code, _ in soft]}")
        for method in methods:
            begin = time.perf_counter()
            try:
                result = registry.run(method, request)
                error = ""
            except Exception:
                error = traceback.format_exc()
                result = None
            elapsed = time.perf_counter() - begin
            if result is None:
                say(f"    {method:14s} EXCEPTION")
                failures.append({"case_id": request.case_id, "method": method, "error": error})
                writer.writerow([stamp, request.case_id, method, "", request.seed,
                                 request.termination.time_limit_seconds, "adapter_exception",
                                 "", f"{elapsed:.6f}", "", "", ""])
                continue
            audit = audit_route(request, result.route)
            result.audit = audit
            row = result.as_row(request)
            row.update({
                "case_id": request.case_id,
                "audit": audit,
                "wall_seconds": elapsed,
                "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "environment": env,
                "input_soft_notes": [code for code, _ in soft],
                "registry_version": registry.METHODS[method]["version"],
                "registry_kind": registry.METHODS[method]["kind"],
                "pending_at_start": len(request.pending),
                "deferred_at_start": len(request.deferred),
                "exact_note": "reference only when artifacts/runs/exact_micro.json says optimal",
            })
            rows.append(row)
            route_dir = ARTIFACTS / "routes" / request.case_id
            route_dir.mkdir(parents=True, exist_ok=True)
            (route_dir / f"{method}.json").write_text(
                json.dumps({"case_id": request.case_id, "method_id": method,
                            "method_version": row["method_version"],
                            "status": row["status"], "route": row["route"],
                            "route_steps": row["route_steps"], "audit": audit},
                           ensure_ascii=False, indent=1), encoding="utf-8")
            writer.writerow([stamp, request.case_id, method, row["method_version"],
                             request.seed, request.termination.time_limit_seconds,
                             row["status"], row["route_steps"], f"{elapsed:.6f}",
                             audit["valid"], result.termination.get("natural"), row["fallback_used"]])
            ledger.flush()
            ok = "valid" if audit["valid"] else "INVALID:" + ",".join(audit["errors"])
            say(f"    {method:14s} status={row['status']:22s} steps={row['route_steps']} "
                f"fallback={int(bool(row['fallback_used']))} natural={int(bool(result.termination.get('natural')))} "
                f"{elapsed:6.3f}s {ok}")

    (ARTIFACTS / "runs" / "micro_runs.json").write_text(
        json.dumps({"stamp": stamp, "cases": len(cases), "methods": methods,
                    "rows": rows, "failures": failures}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # ---- exact reference on the small instances
    from exact_reference import exact_optimum
    exact = []
    for payload, request, path in cases:
        if not env_ok(request):
            exact.append({"case_id": request.case_id, "status": "skipped_infeasible_input",
                          "pending": len(request.pending)})
            continue
        if len(request.pending) > 12:
            exact.append({"case_id": request.case_id, "status": "skipped_too_large",
                          "pending": len(request.pending)})
            continue
        answer = exact_optimum(request)
        exact.append({"case_id": request.case_id, "pending": len(request.pending), **answer})
        say(f"[exact] {request.case_id:34s} {answer}")
    (ARTIFACTS / "runs" / "exact_micro.json").write_text(
        json.dumps({"stamp": stamp, "rows": exact}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    ledger.close()
    say("")
    say(f"rows={len(rows)} failures={len(failures)}")
    expected_empty = {"environment_infeasible", "no_legal_route_within_resource",
                      "input_precondition_unmet", "adapter_assertion",
                      "planning_failure", "timeout", "no_legal_candidate"}
    hard = []
    declared = []
    for row in rows:
        errors = row["audit"]["errors"]
        if not errors:
            continue
        movement = {"wrong_start", "missing_return", "illegal_step",
                    "collision_or_out_of_bounds"} & set(errors)
        if movement:
            hard.append(row)
        elif row["status"] in expected_empty or row["status"] == "resource_exceeded" \
                or set(errors) <= {"empty_route", "coverage_omission", "distance_budget_exceeded"}:
            declared.append(row)
        else:
            hard.append(row)
    say(f"hard problems={len(hard)}  declared/labelled deviations={len(declared)}")
    for row in hard:
        say(f"  HARD {row['case_id']:34s} {row['method_id']:14s} {row['status']:22s} "
            f"{','.join(row['audit']['errors'])}")
    for row in declared:
        say(f"  ok*  {row['case_id']:34s} {row['method_id']:14s} {row['status']:22s} "
            f"{','.join(row['audit']['errors'])}")
    log.close()
    return 0 if not hard and not failures else 1


def env_ok(request):
    status = environment_status(request)
    return status["ok"]


if __name__ == "__main__":
    sys.exit(main())
