"""Read-only checker for revision v0.3.

It never starts a planner, never touches the network and never rebuilds a result.

Checks
------
1. the sealed v0.1 and v0.2 deliveries still match their own manifests;
2. every file of this revision against ``manifests_v03/delivery_sha256.json``
   (append-only evidence excluded);
3. the ledger: two-phase pairing, unique run ids, no unregistered calls, the
   formal batch matches the planned task set, and each formal end row joins to
   its saved route by ``run_id`` with matching fields;
4. the sealed ledger prefix is byte-identical (appends after the seal are fine);
5. every saved route re-audited from the frozen fixture inputs and passed through
   the shared semantic gate;
6. self tests: the gate and the ledger auditor must reject the negative cases
   (over-budget success, missing end row, duplicated run id, tampered prefix,
   missing route, hard termination).

Run:  python -B -X utf8 revision_v0.3/verify_v03.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

V03 = Path(__file__).resolve().parent
OUT = V03.parent
V02 = OUT / "revision_v0.2"
sys.path.insert(0, str(V03 / "src_v03"))

import bootstrap_v03  # noqa: E402,F401  fixes resolution

from grading import grade, SUCCESS  # noqa: E402

CASES = OUT / "tests" / "fixtures" / "cases"
ART = V03 / "artifacts_v03"
LOGS = V03 / "logs_v03"
MANIFESTS = V03 / "manifests_v03"
LEDGER = LOGS / "call_ledger_v03.csv"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Report:
    def __init__(self):
        self.failures = []
        self.checks = 0

    def check(self, condition, message):
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition


# --------------------------------------------------------------- ledger auditor
def read_ledger(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_ledger(rows):
    """Pure function: return the list of problems of a two-phase ledger."""
    problems = []
    order = {}
    seen_run_ids = {}
    for index, row in enumerate(rows):
        run_id = row.get("run_id") or ""
        phase = row.get("phase") or ""
        if not run_id:
            problems.append(f"row {index}: missing run_id")
            continue
        if phase not in ("start", "end"):
            problems.append(f"row {index}: bad phase {phase!r}")
            continue
        seen_run_ids[run_id] = seen_run_ids.get(run_id, 0) + 1
        order.setdefault(run_id, {})[phase] = row
        if row.get("kind") == "unregistered":
            problems.append(f"row {index}: unregistered call {row.get('plan_id')}")
    for run_id, entry in order.items():
        if "start" not in entry:
            problems.append(f"end without start: {run_id}")
        if "end" not in entry:
            problems.append(f"start without end (hard termination?): {run_id}")
    for run_id, count in seen_run_ids.items():
        if count != 2:
            problems.append(f"run_id repeated {count} times (expected start+end): {run_id}")
    return problems


def _norm(value):
    """Compare ledger text with JSON values: None and "" both mean "absent"."""
    if value is None or value == "":
        return ""
    return str(value)


def join_routes(rows, routes_by_run_id):
    """Pure function: every formal end row must join to its saved route."""
    problems = []
    for row in rows:
        if row.get("phase") != "end" or row.get("kind") != "formal":
            continue
        run_id = row.get("run_id")
        saved = routes_by_run_id.get(run_id)
        if saved is None:
            problems.append(f"no saved route for run_id {run_id} ({row.get('plan_id')})")
            continue
        for field in ("case_id", "method_id", "status", "route_steps", "seed"):
            if _norm(row.get(field)) != _norm(saved.get(field)):
                problems.append(f"field {field} differs for {run_id}: "
                                f"ledger={row.get(field)!r} route={saved.get(field)!r}")
    return problems


def prefix_ok(path, seal):
    raw = path.read_bytes()
    if len(raw) < seal["bytes"]:
        return False, "ledger shrank below the sealed length"
    prefix = raw[: seal["bytes"]]
    if hashlib.sha256(prefix).hexdigest() != seal["sha256_of_prefix"]:
        return False, "sealed ledger prefix was rewritten"
    if raw.count(b"\n") < seal["lines"]:
        return False, "ledger has fewer lines than the seal"
    return True, "prefix intact"


# ------------------------------------------------------------------ the checks
def check_manifests(report):
    for root, manifest_path, label in (
            (OUT, OUT / "manifests" / "delivery_sha256.json", "v0.1"),
            (V02, V02 / "manifests_v02" / "delivery_sha256.json", "v0.2")):
        if not report.check(manifest_path.is_file(), f"{label} manifest missing"):
            continue
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        append_only = set(payload.get("append_only") or [])
        changed, missing = [], []
        for relative, expected in payload["files"].items():
            if relative in append_only:
                continue
            target = root / relative
            if not target.is_file():
                missing.append(relative)
            elif sha256(target) != expected:
                changed.append(relative)
        report.check(not missing, f"{label}: {len(missing)} sealed files gone: {missing[:3]}")
        report.check(not changed, f"{label}: {len(changed)} sealed files changed: {changed[:3]}")

    manifest = MANIFESTS / "delivery_sha256.json"
    if not report.check(manifest.is_file(), "v0.3 manifest missing"):
        return
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    append_only = set(payload.get("append_only") or [])
    for relative, expected in payload["files"].items():
        if relative == "manifests_v03/delivery_sha256.json" or relative in append_only:
            continue
        target = V03 / relative
        if report.check(target.is_file(), f"delivered v0.3 file missing: {relative}"):
            report.check(sha256(target) == expected, f"delivered v0.3 file changed: {relative}")


def check_required(report):
    required = [
        "README_v03.md", "变更表.md", "证据_v0.3.md", "verify_v03.py", "run_micro_v03.py",
        "src_v03/bootstrap_v03.py", "src_v03/finalize.py", "src_v03/grading.py",
        "src_v03/adapters/registry.py", "src_v03/adapters/epsilon_star.py",
        "src_v03/adapters/__init__.py",
        "tests_v03/test_a_deadline_edges.py", "tests_v03/test_b_timing_boundary.py",
        "tests_v03/test_c_ledger_integrity.py",
        "artifacts_v03/runs/micro_runs_v03.json",
        "artifacts_v03/runs/run_manifest_v03.json",
        "logs_v03/call_ledger_v03.csv",
        "manifests_v03/delivery_sha256.json", "manifests_v03/ledger_seal.json",
    ]
    for name in required:
        report.check((V03 / name).is_file(), f"missing required v0.3 file: {name}")


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
    seen = 0
    for route_file in sorted((ART / "routes").glob("*/*.json")):
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
        for violation in grade(payload["status"], audit, payload.get("termination")):
            report.check(False, f"{violation}: {route_file}")
        seen += 1
    report.check(seen > 0, "no saved v0.3 routes to audit")


def check_ledger(report):
    if not report.check(LEDGER.is_file(), "ledger missing"):
        return
    rows = read_ledger(LEDGER)
    report.check(len(rows) > 0, "ledger empty")
    for problem in audit_ledger(rows):
        report.check(False, f"ledger: {problem}")

    manifest_path = ART / "runs" / "run_manifest_v03.json"
    if report.check(manifest_path.is_file(), "run manifest missing"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        batch = manifest["batch"]
        formal_end = [row for row in rows
                      if row["batch"] == batch and row["kind"] == "formal"
                      and row["phase"] == "end"]
        planned = {item["plan_id"] for item in manifest["planned"]}
        produced = {row["plan_id"] for row in formal_end}
        report.check(not (planned - produced),
                     f"{len(planned - produced)} planned cells missing: "
                     f"{sorted(planned - produced)[:5]}")
        report.check(not (produced - planned),
                     f"{len(produced - planned)} unplanned cells: {sorted(produced - planned)[:5]}")
        report.check(len(produced) == len(formal_end),
                     "duplicate (case, method) cells inside the formal batch")
        for row in formal_end:
            report.check(row["task_set_sha256"] == manifest["task_set_sha256"],
                         f"task set hash mismatch in {row['run_id']}")

        routes_by_run = {}
        for route_file in (ART / "routes").glob("*/*.json"):
            payload = json.loads(route_file.read_text(encoding="utf-8"))
            routes_by_run[payload.get("run_id")] = payload
        for problem in join_routes(rows, routes_by_run):
            report.check(False, f"join: {problem}")

    seal_path = MANIFESTS / "ledger_seal.json"
    if report.check(seal_path.is_file(), "ledger seal missing"):
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        ok, message = prefix_ok(LEDGER, seal)
        report.check(ok, f"ledger seal: {message}")


def check_self_tests(report):
    """The gate and the ledger auditor must reject the known negative cases."""
    over = {"valid": False, "coverage_complete": True,
            "errors": ["distance_budget_exceeded"],
            "resource": {"limit": 3, "used": 10, "ok": False}, "route_steps": 10}
    report.check("success_status_over_resource" in grade("finished", over, {"natural": True}),
                 "gate accepted a finished, fully covered, over-budget record")

    incomplete = {"valid": False, "coverage_complete": False,
                  "errors": ["coverage_omission"], "resource": {"ok": True}, "route_steps": 5}
    report.check("success_status_without_full_coverage" in grade("finished", incomplete, {}),
                 "gate accepted a coverage omission")

    good = {"valid": True, "coverage_complete": True, "errors": [],
            "resource": {"ok": True}, "route_steps": 5}
    report.check(grade("finished", good, {"natural": True}) == [],
                 "gate rejects a genuinely valid record")

    base = {"run_id": "r1", "phase": "start", "kind": "formal", "plan_id": "c::m",
            "batch": "b"}
    end = dict(base, phase="end")
    report.check(audit_ledger([base, end]) == [], "clean two-phase ledger rejected")
    report.check(any("start without end" in p for p in audit_ledger([base])),
                 "hard termination (start without end) not detected")
    report.check(any("end without start" in p for p in audit_ledger([end])),
                 "end without start not detected")
    report.check(any("repeated" in p for p in audit_ledger([base, end, base, end])),
                 "duplicated run_id not detected")
    report.check(any("unregistered" in p
                     for p in audit_ledger([dict(base, kind="unregistered"), end])),
                 "unregistered call not detected")

    rows = [dict(base, phase="end", case_id="c", method_id="m", status="finished",
                 route_steps="5", seed="1")]
    saved = {"r1": {"case_id": "c", "method_id": "m", "status": "finished",
                    "route_steps": 5, "seed": 1}}
    report.check(join_routes(rows, saved) == [], "clean join rejected")
    report.check(any("no saved route" in p for p in join_routes(rows, {})),
                 "missing saved route not detected")
    tampered = {"r1": dict(saved["r1"], status="resource_exceeded")}
    report.check(any("status differs" in p for p in join_routes(rows, tampered)),
                 "tampered status not detected")

    prefix = b"aaa\n"
    seal = {"bytes": len(prefix), "lines": 1,
            "sha256_of_prefix": hashlib.sha256(prefix).hexdigest()}
    tmp = V03 / "scratch" / "_seal_probe.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(prefix)
    report.check(prefix_ok(tmp, seal)[0], "intact prefix rejected")
    tmp.write_bytes(b"aaa\nbbb\n")
    report.check(prefix_ok(tmp, seal)[0], "plain append rejected")
    tmp.write_bytes(b"zzz\nbbb\n")
    report.check(not prefix_ok(tmp, seal)[0], "rewritten prefix not detected")
    tmp.unlink()


def check_hygiene(report):
    caches = [p for p in V03.rglob("__pycache__") if p.is_dir()]
    report.check(not caches, f"bytecode caches present: {[str(p) for p in caches[:3]]}")
    junk = [p for p in (V03 / "scratch").glob("*") if p.is_file()]
    report.check(not junk, f"scratch files left behind: {[p.name for p in junk[:3]]}")


def main():
    report = Report()
    check_required(report)
    check_manifests(report)
    check_saved_routes(report)
    check_ledger(report)
    check_self_tests(report)
    check_hygiene(report)

    print(f"checks run: {report.checks}")
    if LOGS.joinpath("call_ledger_v03.csv").is_file():
        rows = read_ledger(LEDGER)
        kinds = {}
        for row in rows:
            if row["phase"] == "end":
                kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
        print("ledger end rows by kind: " + json.dumps(kinds, ensure_ascii=False, sort_keys=True))
    if report.failures:
        print(f"VERIFY v0.3 FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:60]:
            print("  -", failure)
        return 1
    print("VERIFY v0.3 OK: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
