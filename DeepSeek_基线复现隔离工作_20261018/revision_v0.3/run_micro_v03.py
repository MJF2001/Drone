"""v0.3 micro runner: registered, two-phase, sealed.

Every planner call goes through ``adapters.registry.run``, which writes a ``start``
row before the call and an ``end`` row after it.  The runner additionally:

* refuses to seal the batch when any ledger write failed (``LedgerWriteError``
  before a call, or a recorded end-row failure) - the planning results are still
  saved, but the batch is marked incomplete;
* writes a **seal** (bytes, lines, SHA256) of the ledger after the batch, so a
  later verifier can prove the old prefix was not rewritten;
* joins every formal ``end`` row to its saved route by ``run_id``.

Writes only under ``revision_v0.3/``.
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

V03 = Path(__file__).resolve().parent
sys.path.insert(0, str(V03 / "src_v03"))

import bootstrap_v03  # noqa: E402,F401  must come first

from problem import PlanRequest, Termination, validate_inputs, environment_status  # noqa: E402
from adapters import registry  # noqa: E402

OUT = bootstrap_v03.OUT
ART = V03 / "artifacts_v03"
LOGS = V03 / "logs_v03"
MANIFESTS = V03 / "manifests_v03"
CASES = OUT / "tests" / "fixtures" / "cases"


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


def seal_ledger(ledger, batch, kind, task_hash):
    raw = ledger.read_bytes()
    lines = raw.count(b"\n")
    payload = {
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "batch": batch, "kind": kind, "task_set_sha256": task_hash,
        "ledger": str(ledger.relative_to(V03)),
        "bytes": len(raw), "lines": lines,
        "sha256_of_prefix": hashlib.sha256(raw).hexdigest(),
        "rule": "appends are allowed; the first <bytes> bytes must keep this hash",
    }
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    (MANIFESTS / "ledger_seal.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def main(argv=None):
    argv = list(argv or [])
    kind = argv[argv.index("--kind") + 1] if "--kind" in argv else "formal"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch = f"v03_{kind}_{stamp}"
    for directory in (ART / "runs", ART / "routes", LOGS, MANIFESTS):
        directory.mkdir(parents=True, exist_ok=True)

    cases = load_cases()
    methods = list(registry.available())
    task_hash = task_set_sha256(cases, methods)
    plan = [(request.case_id, method) for _, request, _ in cases for method in methods]

    log_path = LOGS / f"run_micro_v03_{stamp}.log"
    log = open(log_path, "w", encoding="utf-8")

    def say(text=""):
        print(text, flush=True)
        log.write(text + "\n")
        log.flush()

    say(f"run_micro v0.3  batch={batch} kind={kind}")
    say(f"cases={len(cases)} methods={len(methods)} planned_calls={len(plan)}")
    say(f"task_set_sha256={task_hash}")
    say(f"interpreter={sys.executable}")
    say("module resolution: " + json.dumps(bootstrap_v03.resolution_report(), ensure_ascii=False))
    say("")

    rows, seen, failures = [], [], []
    ledger_failures_at_start = len(registry.LEDGER_FAILURES)

    for payload, request, path in cases:
        soft = validate_inputs(request)
        env = environment_status(request)
        say(f"[{request.case_id}] pending={len(request.pending)} deferred={len(request.deferred)} "
            f"env={env['code']} soft={[code for code, _ in soft]}")
        for method in methods:
            plan_id = f"{request.case_id}::{method}"
            registry.CONTEXT.update({"batch": batch, "kind": kind,
                                     "plan_id": plan_id, "task_set_sha256": task_hash})
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
            seen.append(plan_id)

            if result is None:
                failures.append({"plan_id": plan_id, "error": error})
                say(f"    {method:14s} EXCEPTION")
                continue

            row = result.as_row(request)
            row.update({
                "run_id": record.get("run_id", ""), "batch": batch, "kind": kind,
                "plan_id": plan_id, "case_id": request.case_id,
                "wall_seconds": elapsed,
                "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "environment": env, "input_soft_notes": [code for code, _ in soft],
                "task_set_sha256": task_hash,
                "registry_version": registry.METHODS[method]["version"],
                "registry_kind": registry.METHODS[method]["kind"],
                "adaptation_class": registry.METHODS[method].get("adaptation_class", ""),
                "ledger_write_error": (result.meta or {}).get("ledger_write_error", ""),
            })
            rows.append(row)
            route_dir = ART / "routes" / request.case_id
            route_dir.mkdir(parents=True, exist_ok=True)
            (route_dir / f"{method}.json").write_text(
                json.dumps({"case_id": request.case_id, "method_id": method,
                            "method_version": row["method_version"],
                            "run_id": row["run_id"], "batch": batch, "kind": kind,
                            "status": row["status"], "route": row["route"],
                            "route_steps": row["route_steps"], "seed": request.seed,
                            "audit": result.audit, "resource_check": row["resource_check"],
                            "termination": row["termination"], "errors": row["errors"]},
                           ensure_ascii=False, indent=1), encoding="utf-8")
            audit = result.audit or {}
            ok = "valid" if audit.get("valid") else "NOT-VALID:" + ",".join(audit.get("errors", []))
            say(f"    {method:14s} {row['status']:34s} steps={row['route_steps']} "
                f"{elapsed:6.3f}s natural={int(bool(row['termination'].get('natural')))} {ok}")

    (ART / "runs" / "micro_runs_v03.json").write_text(
        json.dumps({"stamp": stamp, "batch": batch, "kind": kind,
                    "task_set_sha256": task_hash, "planned_calls": len(plan),
                    "cases": len(cases), "methods": methods,
                    "rows": rows, "failures": failures}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (ART / "runs" / "run_manifest_v03.json").write_text(
        json.dumps({"stamp": stamp, "batch": batch, "kind": kind,
                    "task_set_sha256": task_hash,
                    "planned": [{"plan_id": f"{case}::{method}", "case_id": case,
                                 "method_id": method} for case, method in plan],
                    "fixture_sha256": {payload["case_id"]:
                                       hashlib.sha256(path.read_bytes()).hexdigest()
                                       for payload, _, path in cases}},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    missing = sorted(set(f"{c}::{m}" for c, m in plan) - set(seen))
    extra = sorted(set(seen) - set(f"{c}::{m}" for c, m in plan))
    new_ledger_failures = registry.LEDGER_FAILURES[ledger_failures_at_start:]
    say("")
    say(f"registered={len(seen)} planned={len(plan)} missing={len(missing)} extra={len(extra)}")
    say(f"ledger_write_failures={len(new_ledger_failures)}")

    hard = []
    from finalize import SUCCESS_STATUSES
    for row in rows:
        audit = row["audit"]
        errors = set(audit["errors"]) if audit else {"no_audit"}
        movement = {"wrong_start", "missing_return", "illegal_step",
                    "collision_or_out_of_bounds"} & errors
        if movement:
            hard.append(row)
        elif not audit["valid"] and row["status"] in SUCCESS_STATUSES:
            hard.append(row)
    say(f"hard problems={len(hard)}")
    for row in hard:
        say(f"  HARD {row['case_id']} {row['method_id']} {row['status']} {row['audit']['errors']}")

    complete = (not failures and not missing and not extra and not hard
                and not new_ledger_failures)
    if complete:
        seal = seal_ledger(registry.LEDGER, batch, kind, task_hash)
        say(f"ledger sealed: bytes={seal['bytes']} lines={seal['lines']} "
            f"sha256={seal['sha256_of_prefix'][:16]}...")
    else:
        say("BATCH NOT SEALED: evidence is incomplete (see the counters above)")

    log.close()
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
