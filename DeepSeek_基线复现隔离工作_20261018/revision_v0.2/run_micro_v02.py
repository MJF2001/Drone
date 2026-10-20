"""v0.2 micro runner: every planner call is registered, with a run id.

R5 fix: the v0.1 ledger only had a batch stamp, so "how many planner calls did
this round make" could not be answered for test and development calls.  Here
every call -- formal, test, development -- carries a ``run_id``, a ``kind`` and
the ``plan_id`` it was supposed to fill, and the planned task set is written next
to the results so missing and duplicated cells can be detected.

Writes only under ``revision_v0.2/``; the sealed v0.1 artifacts are untouched.
"""
import csv
import hashlib
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

V02 = Path(__file__).resolve().parent
sys.path.insert(0, str(V02 / "src_v02"))
sys.path.insert(0, str(V02 / "tests_v02"))

import bootstrap_v02  # noqa: E402,F401  must come first: fixes module resolution

from problem import PlanRequest, Termination, validate_inputs, environment_status  # noqa: E402
from adapters import registry  # noqa: E402

OUT = bootstrap_v02.OUT
ART = V02 / "artifacts_v02"
LOGS = V02 / "logs_v02"
CASES = OUT / "tests" / "fixtures" / "cases"
LEDGER = LOGS / "call_ledger_v02.csv"

COLUMNS = ["run_id", "batch", "kind", "registered_utc", "plan_id", "case_id", "method_id",
           "method_version", "seed", "time_limit_seconds", "status", "route_steps",
           "seconds", "valid", "natural", "fallback_used", "completion_steps",
           "adaptation_class", "task_set_sha256", "note"]


def load_cases():
    cases = []
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
            termination=Termination(time_limit_seconds=30.0, natural="method_specific"),
            meta={"fixture": path.name, "notes": payload["notes"], "event": payload["event"]},
        )
        cases.append((payload, request, path))
    return cases


def task_set_sha256(cases, methods):
    payload = json.dumps({"cases": sorted(request.case_id for _, request, _ in cases),
                          "methods": sorted(methods)}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()



def main(argv=None):
    argv = list(argv or [])
    kind = argv[argv.index("--kind") + 1] if "--kind" in argv else "formal"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch = f"v02_{kind}_{stamp}"
    CASES.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "runs").mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    cases = load_cases()
    methods = list(registry.available())
    task_hash = task_set_sha256(cases, methods)
    plan = [(request.case_id, method) for _, request, _ in cases for method in methods]

    log_path = LOGS / f"run_micro_v02_{stamp}.log"
    log = open(log_path, "w", encoding="utf-8")

    def say(text=""):
        print(text, flush=True)
        log.write(text + "\n")
        log.flush()

    say(f"run_micro v0.2  batch={batch} kind={kind}")
    say(f"cases={len(cases)} methods={len(methods)} planned_calls={len(plan)}")
    say(f"task_set_sha256={task_hash}")
    say(f"interpreter={sys.executable}")
    say(f"PYTHONDONTWRITEBYTECODE={os.environ.get('PYTHONDONTWRITEBYTECODE')}")
    say(f"module_resolution={json.dumps(bootstrap_v02.resolution_report(), ensure_ascii=False)}")
    say("")

    rows, plan_cells_seen, failures = [], [], []
    for payload, request, path in cases:
        soft = validate_inputs(request)
        env = environment_status(request)
        say(f"[{request.case_id}] pending={len(request.pending)} deferred={len(request.deferred)} "
            f"env={env['code']} soft={[code for code, _ in soft]}")
        for method in methods:
            run_id = uuid.uuid4().hex
            plan_id = f"{request.case_id}::{method}"
            # R5: the registry records every call itself; the runner only supplies
            # the batch, the kind and the plan cell it is filling.
            registry.CONTEXT.update({"batch": batch, "kind": kind,
                                     "plan_id": plan_id,
                                     "task_set_sha256": task_hash})
            begin = time.perf_counter()
            error = ""
            result = None
            try:
                result = registry.run(method, request)
            except Exception:
                error = traceback.format_exc()
            record = registry.LAST_RECORD or {}
            registry.CONTEXT.update({"batch": None, "kind": None,
                                     "plan_id": None, "task_set_sha256": None})
            elapsed = time.perf_counter() - begin
            registered = datetime.now(timezone.utc).isoformat()

            if result is None:
                failures.append({"run_id": run_id, "plan_id": plan_id, "error": error})
                plan_cells_seen.append(plan_id)
                say(f"    {method:14s} EXCEPTION")
                continue

            row = result.as_row(request)
            row.update({
                "run_id": run_id, "batch": batch, "kind": kind, "plan_id": plan_id,
                "case_id": request.case_id, "wall_seconds": elapsed,
                "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "environment": env, "input_soft_notes": [code for code, _ in soft],
                "task_set_sha256": task_hash,
                "registry_version": registry.METHODS[method]["version"],
                "registry_kind": registry.METHODS[method]["kind"],
                "adaptation_class": registry.METHODS[method].get("adaptation_class", ""),
                "pending_at_start": len(request.pending),
                "deferred_at_start": len(request.deferred),
            })
            rows.append(row)
            route_dir = ART / "routes" / request.case_id
            route_dir.mkdir(parents=True, exist_ok=True)
            (route_dir / f"{method}.json").write_text(
                json.dumps({"case_id": request.case_id, "method_id": method,
                            "method_version": row["method_version"], "run_id": run_id,
                            "batch": batch, "kind": kind, "status": row["status"],
                            "route": row["route"], "route_steps": row["route_steps"],
                            "audit": result.audit, "resource_check": row["resource_check"],
                            "termination": row["termination"], "errors": row["errors"]},
                           ensure_ascii=False, indent=1), encoding="utf-8")
            plan_cells_seen.append(plan_id)
            audit = result.audit or {}
            ok = "valid" if audit.get("valid") else "NOT-VALID:" + ",".join(audit.get("errors", []))
            say(f"    {method:14s} {row['status']:34s} steps={row['route_steps']} {elapsed:6.3f}s "
                f"natural={int(bool(row['termination'].get('natural')))} {ok}")

    (ART / "runs" / "micro_runs_v02.json").write_text(
        json.dumps({"stamp": stamp, "batch": batch, "kind": kind,
                    "task_set_sha256": task_hash, "planned_calls": len(plan),
                    "cases": len(cases), "methods": methods,
                    "rows": rows, "failures": failures}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (ART / "runs" / "run_manifest_v02.json").write_text(
        json.dumps({"stamp": stamp, "batch": batch, "kind": kind,
                    "task_set_sha256": task_hash,
                    "planned": [{"plan_id": f"{case}::{method}", "case_id": case,
                                 "method_id": method} for case, method in plan],
                    "fixture_sha256": {payload["case_id"]:
                                       hashlib.sha256(path.read_bytes()).hexdigest()
                                       for payload, _, path in cases}},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    planned = {f"{case}::{method}" for case, method in plan}
    produced = set(plan_cells_seen)
    missing = sorted(planned - produced)
    extra = sorted(produced - planned)
    say("")
    say(f"registered={len(plan_cells_seen)} planned={len(plan)} missing={len(missing)} extra={len(extra)}")
    for item in missing[:10]:
        say(f"  MISSING {item}")
    for item in extra[:10]:
        say(f"  EXTRA   {item}")

    hard = []
    for row in rows:
        errors = set(row["audit"]["errors"]) if row["audit"] else {"no_audit"}
        movement = {"wrong_start", "missing_return", "illegal_step",
                    "collision_or_out_of_bounds"} & errors
        if movement:
            hard.append(row)
        elif not row["audit"]["valid"] and row["status"] in registry_successes():
            hard.append(row)
    say(f"hard problems={len(hard)}")
    for row in hard:
        say(f"  HARD {row['case_id']} {row['method_id']} {row['status']} {row['audit']['errors']}")

    log.close()
    if failures or missing or extra or hard:
        return 1
    return 0


def registry_successes():
    from finalize import SUCCESS_STATUSES
    return set(SUCCESS_STATUSES)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

