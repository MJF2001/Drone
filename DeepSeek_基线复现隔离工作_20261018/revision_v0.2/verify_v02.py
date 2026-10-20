"""Read-only checker for revision v0.2.

It never starts a planner, never touches the network and never rebuilds a
result.  It reads files, recomputes hashes, re-audits the SAVED routes and
applies the stricter success semantics requested by R5.

Run:  python -B -X utf8 revision_v0.2/verify_v02.py

Checks
------
1. the sealed v0.1 delivery still matches its own manifest (nothing was edited
   in place);
2. every file of this revision against ``manifests_v02/delivery_sha256.json``;
3. every saved v0.2 route re-audited from the frozen fixture inputs, with the
   R5 rule: a success status must satisfy legal movement, full coverage AND the
   resource limit, not coverage alone;
4. ledger integrity: unique run ids, the planned task set fully covered, no
   duplicates, kind counts reported;
5. the checker's own negative self test (a "finished, full coverage, over
   resource" record must be rejected);
6. no bytecode caches or scratch files inside the revision.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

V02 = Path(__file__).resolve().parent
OUT = V02.parent
sys.path.insert(0, str(V02 / "src_v02"))

import bootstrap_v02  # noqa: E402,F401  fixes resolution: src_v02 first, src_v01 second

CASES = OUT / "tests" / "fixtures" / "cases"
ART = V02 / "artifacts_v02"
LOGS = V02 / "logs_v02"
MANIFESTS = V02 / "manifests_v02"
LEDGER = LOGS / "call_ledger_v02.csv"

SUCCESS = ("finished", "planned", "planned_at_timeout", "complete_coverage",
           "finished_with_safety_limit")
FAILURE = ("environment_infeasible", "no_legal_route_within_resource",
           "resource_exceeded", "coverage_incomplete", "invalid_route",
           "input_precondition_unmet", "adapter_assertion", "planning_failure",
           "timeout", "no_legal_candidate", "deadline_before_complete_route",
           "safety_limit_before_complete_route")
MOVEMENT = {"wrong_start", "missing_return", "illegal_step",
            "collision_or_out_of_bounds"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------- R5 gate
def grade(status, audit, termination=None):
    """Return the list of semantic violations for one record (R5).

    ``success requires every legality condition``: legal movement, a base return,
    full coverage of the pending set and a satisfied resource limit.
    """
    problems = []
    errors = set(audit.get("errors") or [])
    route_empty = audit.get("route_steps") is None

    if status in SUCCESS:
        if not audit.get("valid"):
            problems.append("success_status_with_invalid_audit")
        if not audit.get("coverage_complete"):
            problems.append("success_status_without_full_coverage")
        resource = audit.get("resource") or {}
        if resource.get("ok") is False:
            problems.append("success_status_over_resource")
        if errors & MOVEMENT:
            problems.append("success_status_with_illegal_movement")
        if route_empty:
            problems.append("success_status_without_route")
    elif status in FAILURE:
        if status == "resource_exceeded" and "distance_budget_exceeded" not in errors:
            problems.append("resource_exceeded_without_resource_error")
        if status == "coverage_incomplete" and "coverage_omission" not in errors:
            problems.append("coverage_incomplete_without_omission")
        if status == "environment_infeasible" and not route_empty:
            problems.append("environment_infeasible_with_a_route")
        if status in ("timeout", "deadline_before_complete_route",
                      "safety_limit_before_complete_route"):
            if (termination or {}).get("natural"):
                problems.append("truncated_status_marked_natural")
    else:
        problems.append(f"unknown_status:{status}")

    if not route_empty and (errors & MOVEMENT) and status in SUCCESS:
        problems.append("illegal_route_presented_as_success")
    return problems


# ------------------------------------------------------------------- the checks
class Report:
    def __init__(self):
        self.failures = []
        self.checks = 0

    def check(self, condition, message):
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition


def check_sealed_v01(report):
    manifest = OUT / "manifests" / "delivery_sha256.json"
    if not report.check(manifest.is_file(), "sealed v0.1 delivery manifest missing"):
        return
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    changed, missing = [], []
    for relative, expected in payload["files"].items():
        target = OUT / relative
        if not target.is_file():
            missing.append(relative)
        elif sha256(target) != expected:
            changed.append(relative)
    report.check(not missing, f"{len(missing)} sealed v0.1 files disappeared: {missing[:3]}")
    report.check(not changed, f"{len(changed)} sealed v0.1 files changed: {changed[:3]}")
    report.check(payload.get("exclusions") == ["tmp", "manifests/delivery_sha256.json",
                                              "__pycache__"],
                 "sealed manifest exclusion list changed")


def check_required(report):
    required = [
        "README_v02.md", "变更表.md", "意见处理证据.md", "verify_v02.py",
        "run_micro_v02.py", "reports_v02/C_star_账本数据流与适配分类.md",
        "reports_v02/协议草案_v0.2.md",
        "src_v02/finalize.py", "src_v02/deadline.py", "src_v02/result.py",
        "src_v02/problem.py",
        "src_v02/adapters/epsilon_star.py", "src_v02/adapters/cstar.py",
        "src_v02/adapters/reference_methods.py", "src_v02/epsilon_core/etm.py",
        "src_v02/epsilon_core/maps.py",
        "tests_v02/test_r1_empty_pending.py", "tests_v02/test_r2_deadline.py",
        "tests_v02/test_r3_timing.py", "tests_v02/test_r5_semantics.py",
        "artifacts_v02/runs/micro_runs_v02.json",
        "artifacts_v02/runs/run_manifest_v02.json",
        "logs_v02/call_ledger_v02.csv",
        "manifests_v02/delivery_sha256.json",
        "evidence/permissions/current_state.txt",
        "evidence/permissions/recovery_record.json",
        "evidence/behavior_matrix.csv",
    ]
    for name in required:
        report.check((V02 / name).is_file(), f"missing required v0.2 file: {name}")


def load_request(case_id):
    from problem import PlanRequest, Termination
    payload = json.loads((CASES / f"{case_id}.json").read_text(encoding="utf-8"))
    grid = payload["grid"]
    return PlanRequest(
        case_id=case_id, free=frozenset(map(tuple, grid["free"])),
        published_targets=frozenset(map(tuple, grid["published_targets"])),
        covered=frozenset(map(tuple, grid["covered"])), current=tuple(grid["current"]),
        base=tuple(grid["base"]), old_route=tuple(map(tuple, grid["old_route"])),
        remaining_resource=grid["remaining_resource"],
        initial_targets=frozenset(map(tuple, grid["initial_targets"])),
        termination=Termination(time_limit_seconds=30.0))


def check_saved_routes(report):
    from audit_independent import audit_route
    routes_root = ART / "routes"
    seen = 0
    for route_file in sorted(routes_root.glob("*/*.json")):
        payload = json.loads(route_file.read_text(encoding="utf-8"))
        case_id = payload["case_id"]
        if not report.check((CASES / f"{case_id}.json").is_file(),
                            f"saved route for unknown case: {case_id}"):
            continue
        request = load_request(case_id)
        route = tuple(map(tuple, payload["route"])) if payload.get("route") else ()
        audit = audit_route(request, route)
        report.check(audit["route_steps"] == payload.get("route_steps"),
                     f"step count differs on re-audit: {route_file}")
        report.check(audit["errors"] == (payload.get("audit") or {}).get("errors"),
                     f"audit errors changed since the run: {route_file}")
        report.check(audit["resource"]["ok"] ==
                     (payload.get("resource_check") or {}).get("ok"),
                     f"resource verdict changed since the run: {route_file}")
        for violation in grade(payload["status"], audit, payload.get("termination")):
            report.check(False, f"{violation}: {route_file}")
        seen += 1
    report.check(seen > 0, "no saved v0.2 routes to audit")


def check_ledger(report):
    if not report.check(LEDGER.is_file(), "call ledger missing"):
        return
    with open(LEDGER, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report.check(len(rows) > 0, "call ledger empty")

    ids = [row["run_id"] for row in rows]
    report.check(len(ids) == len(set(ids)), "duplicate run_id in the ledger")
    report.check(all(row["plan_id"] for row in rows), "ledger row without a plan_id")
    formal_rows = [row for row in rows if row["kind"] == "formal"]
    report.check(formal_rows, "no formal rows in the ledger")
    report.check(all(row["task_set_sha256"] for row in formal_rows),
                 "formal ledger row without a task-set hash")

    manifest_path = ART / "runs" / "run_manifest_v02.json"
    if report.check(manifest_path.is_file(), "run manifest missing"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        planned = {item["plan_id"] for item in manifest["planned"]}
        batches = {row["batch"] for row in rows}
        report.check(manifest["batch"] in batches,
                     "the run manifest's batch is not in the ledger")
        this_batch = [row for row in rows if row["batch"] == manifest["batch"]
                      and row["kind"] == "formal"]
        produced = {row["plan_id"] for row in this_batch}
        missing = sorted(planned - produced)
        extra = sorted(produced - planned)
        report.check(not missing, f"{len(missing)} planned cells missing: {missing[:5]}")
        report.check(not extra, f"{len(extra)} unplanned cells registered: {extra[:5]}")
        report.check(len(produced) == len(this_batch),
                     "duplicate (case, method) rows in the formal batch")
        for row in this_batch:
            report.check(row["task_set_sha256"] == manifest["task_set_sha256"],
                         f"task set hash mismatch in row {row['run_id']}")

    kinds = {}
    for row in rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    report.check("formal" in kinds, "no formal calls registered")
    return kinds


def check_fixture_hashes(report):
    manifest_path = ART / "runs" / "run_manifest_v02.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for case_id, expected in manifest["fixture_sha256"].items():
        path = CASES / f"{case_id}.json"
        if report.check(path.is_file(), f"fixture missing: {case_id}"):
            report.check(sha256(path) == expected, f"fixture changed: {case_id}")


def check_delivery_manifest(report):
    path = MANIFESTS / "delivery_sha256.json"
    if not report.check(path.is_file(), "v0.2 delivery manifest missing"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    report.check(len(payload["files"]) > 10, "v0.2 delivery manifest looks empty")
    append_only = set(payload.get("append_only") or [])
    for relative, expected in payload["files"].items():
        if relative == "manifests_v02/delivery_sha256.json" or relative in append_only:
            continue
        target = V02 / relative
        if report.check(target.is_file(), f"delivered v0.2 file missing: {relative}"):
            report.check(sha256(target) == expected, f"delivered v0.2 file changed: {relative}")


def check_hygiene(report):
    caches = [p for p in V02.rglob("__pycache__") if p.is_dir()]
    report.check(not caches, f"bytecode caches present: {[str(p) for p in caches[:3]]}")
    junk = [p for p in (V02 / "scratch").glob("*") if p.is_file()]
    report.check(not junk, f"scratch files left behind: {[p.name for p in junk[:3]]}")


def check_negative_self_test(report):
    """The gate must reject the case R5 is about."""
    over_budget_full = {
        "valid": False, "coverage_complete": True,
        "errors": ["distance_budget_exceeded"],
        "resource": {"limit": 3, "used": 10, "ok": False},
        "route_steps": 10,
    }
    violations = grade("finished", over_budget_full, {"natural": True})
    report.check("success_status_over_resource" in violations,
                 "the gate accepted a finished, fully covered, over-budget record "
                 "(this is exactly the R5 hole)")
    report.check("success_status_with_invalid_audit" in violations,
                 "the gate accepted an invalid audit as success")

    incomplete = {"valid": False, "coverage_complete": False,
                  "errors": ["coverage_omission"], "resource": {"ok": True},
                  "route_steps": 5}
    report.check("success_status_without_full_coverage" in grade("finished", incomplete, {}),
                 "the gate accepted a coverage omission as success")

    good = {"valid": True, "coverage_complete": True, "errors": [],
            "resource": {"ok": True}, "route_steps": 5}
    report.check(grade("finished", good, {"natural": True}) == [],
                 "the gate rejects a genuinely valid record")


def main():
    report = Report()
    kinds = None
    check_sealed_v01(report)
    check_required(report)
    check_saved_routes(report)
    kinds = check_ledger(report)
    check_fixture_hashes(report)
    check_delivery_manifest(report)
    check_hygiene(report)
    check_negative_self_test(report)

    print(f"checks run: {report.checks}")
    if kinds:
        print("ledger kinds: " + json.dumps(kinds, ensure_ascii=False, sort_keys=True))
    if report.failures:
        print(f"VERIFY v0.2 FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:60]:
            print("  -", failure)
        return 1
    print("VERIFY v0.2 OK: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
