"""Read-only verification of the whole round.

It starts no planner, touches no network and writes nothing (the negative
self-tests live in ``tests/test_selftest.py`` and only write under ``tmp/``).

Checks
------
1. the frozen protocol, the method configuration and the input index still match
   ``protocol/sha256.json`` and the real files;
2. the 10 inputs still match the authoritative case hashes and the replay copies;
3. the ledger: two-phase pairing, unique run ids, no unregistered rows, and every
   planned cell of every batch present exactly once;
4. every saved result joins to its ledger rows by ``run_id`` on case, method,
   seed, status, steps, core version and source hash;
5. every saved route re-audited from the input, and the semantic gate applied;
6. ``within_budget`` is consistent with ``call_total`` versus the row's soft limit;
7. the ledger prefixes recorded per batch are intact (appends allowed);
8. the earlier deliveries (v0.1/v0.2/v0.3) are untouched, checked against their
   own manifests;
9. the call budget is respected.

Usage:  python -B -X utf8 verify.py [--json]
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent          # verify.py lives at the NEW root
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401  (fixes module resolution; no planner is started)

from classify import BUCKETS, classify  # noqa: E402
from labels import effective_status  # noqa: E402
from grading import grade  # noqa: E402

PROTOCOL = NEW / "protocol"
RUNS = NEW / "runs"
MANIFESTS = NEW / "manifests"
LEDGER = NEW / "logs" / "call_ledger.csv"
OLD = NEW.parent / "DeepSeek_基线复现隔离工作_20261018"
BUDGET = {"preparation": 60, "preflight": 10, "development": 300, "total": 370}


class Report:
    def __init__(self):
        self.failures = []
        self.checks = 0

    def check(self, condition, message):
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------- protocol first
def check_protocol(report):
    hashes = json.loads((PROTOCOL / "sha256.json").read_text(encoding="utf-8"))
    for name in ("protocol.json", "method_config.json", "input_index.csv",
                 "planned_runs.csv", "preflight_planned_runs.csv"):
        path = PROTOCOL / name
        if report.check(path.is_file(), f"protocol file missing: {name}"):
            report.check(sha256(path) == hashes[name], f"protocol file changed: {name}")
    for map_id, expected in hashes["cases"].items():
        path = bootstrap.CASES / f"{map_id}.json"
        if report.check(path.is_file(), f"case missing: {map_id}"):
            report.check(sha256(path) == expected, f"case changed: {map_id}")
    for name, expected in hashes["preflight_inputs"].items():
        path = NEW / "preflight" / "inputs" / f"{name}.json"
        if report.check(path.is_file(), f"preflight input missing: {name}"):
            report.check(sha256(path) == expected, f"preflight input changed: {name}")

    config = json.loads((PROTOCOL / "method_config.json").read_text(encoding="utf-8"))
    for method_id, info in config["methods"].items():
        for name, path in info["source_files"].items():
            target = Path(path)
            if report.check(target.is_file(), f"source file missing for {method_id}: {name}"):
                pass
        digest = hashlib.sha256()
        for name in sorted(info["source_files"], key=lambda n: list(info["source_files"]).index(n)):
            path = Path(info["source_files"][name])
            digest.update(str(path).encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        report.check(digest.hexdigest() == info["source_sha256"],
                     f"source hash of {method_id} no longer matches the frozen config")


# --------------------------------------------------------------------- ledger
def check_ledger(report):
    if not report.check(LEDGER.is_file(), "ledger missing"):
        return []
    rows = read_csv(LEDGER)
    report.check(rows, "ledger empty")
    by_run = {}
    pairs = [(row["run_id"], row.get("phase")) for row in rows]
    report.check(len(pairs) == len(set(pairs)), "duplicate (run_id, phase) row")
    for row in rows:
        if row.get("kind") == "unregistered":
            report.check(False, f"unregistered call: {row.get('plan_id')}")
        by_run.setdefault(row["run_id"], {})[row.get("phase")] = row
    for run_id, entry in by_run.items():
        if "start" not in entry:
            report.check(False, f"end without start: {run_id}")
        if "end" not in entry:
            report.check(False, f"start without end: {run_id}")
    attempts = [row for row in rows if row.get("phase") == "start"]
    kinds = {}
    for row in attempts:
        kinds[row.get("kind")] = kinds.get(row.get("kind"), 0) + 1
    recheck = sum(1 for row in attempts if row.get("batch") == "PREFLIGHT_RECHECK")
    preparation = kinds.get("preparation", 0) + recheck
    report.check(kinds.get("development", 0) <= BUDGET["development"],
                 f"development attempts {kinds.get('development', 0)} exceed the budget")
    report.check(preparation <= BUDGET["preparation"],
                 f"preparation attempts {preparation} exceed the budget")
    report.check(len(attempts) <= BUDGET["total"],
                 f"total attempts {len(attempts)} exceed the budget")
    return rows


def prefix_ok(path, seal):
    """Pure check: the sealed prefix is unchanged while appends stay legal."""
    raw = Path(path).read_bytes()
    if len(raw) < seal["bytes"]:
        return False, "ledger shrank below the sealed length"
    if hashlib.sha256(raw[: seal["bytes"]]).hexdigest() != seal["sha256_of_prefix"]:
        return False, "sealed ledger prefix was rewritten"
    if raw.count(b"\n") < seal["lines"]:
        return False, "ledger has fewer lines than the seal"
    return True, "prefix intact"


def _norm(value):
    if value is None or value == "":
        return ""
    return str(value)


JOIN_FIELDS = ("case_id", "method_id", "status", "route_steps", "seed",
               "core_version", "source_sha256")


def join_routes(rows, routes_by_run_id):
    """Pure join: every ledger ``end`` row must match its saved result."""
    problems = []
    for row in rows:
        if row.get("phase") != "end":
            continue
        run_id = row.get("run_id")
        saved = routes_by_run_id.get(run_id)
        if saved is None:
            problems.append(f"no saved result for run_id {run_id}")
            continue
        for field in JOIN_FIELDS:
            if _norm(row.get(field)) != _norm(saved.get(field)):
                problems.append(f"field {field} differs for {run_id}: "
                                f"ledger={row.get(field)!r} result={saved.get(field)!r}")
        total = float(saved.get("call_total_seconds") or 0.0)
        limit = float(row.get("soft_limit_seconds") or 0.0) or None
        if limit:
            expected = total <= limit
            if bool(saved.get("within_budget")) != expected:
                problems.append(f"within_budget inconsistent for {run_id}: "
                                f"{total:.3f}s vs {limit:.3f}s")
    return problems


def check_seals(report):
    for path in sorted(MANIFESTS.glob("ledger_seal_*.json")):
        seal = json.loads(path.read_text(encoding="utf-8"))
        ok, message = prefix_ok(LEDGER, seal)
        report.check(ok, f"{path.name}: {message}")


# ---------------------------------------------------------------- joins/results
def check_batches(report, ledger_rows):
    ends = {(row["run_id"]): row for row in ledger_rows if row.get("phase") == "end"}
    results = {}
    for path in sorted(RUNS.glob("*/results/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        results[payload["run_id"]] = payload

    defect_path = MANIFESTS / "known_defects.json"
    defects = {}
    if defect_path.is_file():
        defects = {item["run_id"]: item for item in
                   json.loads(defect_path.read_text(encoding="utf-8"))["defects"]}

    missing_batches = []
    for plan_name, batch in (("preflight_planned_runs.csv", "PREFLIGHT"),
                             ("preflight_recheck_planned_runs.csv", "PREFLIGHT_RECHECK"),
                             ("planned_runs.csv", None)):
        plan_path = PROTOCOL / plan_name
        if not plan_path.is_file():
            continue
        plan = read_csv(plan_path)
        batches = {row["batch"] for row in plan} if batch is None else {batch}
        for name in sorted(batches):
            planned = [row for row in plan if row["batch"] == name]
            status_path = RUNS / name / "status.csv"
            if not status_path.is_file():
                missing_batches.append(name)
                continue
            status = {row["run_id"]: row for row in read_csv(status_path)}
            for row in planned:
                run_id = row["run_id"]
                report.check(run_id in status, f"{name}: {run_id} not in status.csv")
                report.check(run_id in ends, f"{name}: {run_id} has no end row")
                entry = status.get(run_id, {})
                if entry.get("state") == "not_started":
                    continue
                if run_id not in results:
                    defect = defects.get(run_id)
                    if defect:
                        report.check(defect.get("superseded_by") in results,
                                     f"{name}: {run_id} is a known defect but its "
                                     f"replacement result is missing")
                        continue
                    report.check(False, f"{name}: {run_id} has no saved result")
                    continue
                if run_id in ends:
                    report.check(run_id in results, f"{name}: {run_id} result missing")
    # one join pass over every ledger end row that belongs to a planned run
    planned_ids = {row["run_id"] for path in PROTOCOL.glob("*planned_runs.csv")
                   for row in read_csv(path)}
    for problem in join_routes([row for row in ledger_rows
                                if row.get("phase") == "end"
                                and row["run_id"] in planned_ids
                                and row["run_id"] in results], results):
        report.check(False, f"join: {problem}")
    return missing_batches



def check_routes(report):
    from audit_independent import audit_route
    import inputs
    seen = 0
    for path in sorted(RUNS.glob("*/results/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "runner_exception":
            report.check(False, f"runner exception recorded: {payload['run_id']}")
            continue
        request = inputs.build_any(payload["case_id"], payload["soft_limit_seconds"],
                                   payload["seed"])
        route = tuple(map(tuple, payload["route"])) if payload.get("route") else ()
        audit = audit_route(request, route)
        report.check(audit["route_steps"] == payload.get("route_steps"),
                     f"{payload['run_id']}: step count differs on re-audit")
        report.check(audit["errors"] == (payload.get("audit") or {}).get("errors"),
                     f"{payload['run_id']}: audit errors changed since the run")
        for violation in grade(effective_status(payload), audit, payload.get("termination")):
            report.check(False, f"{payload['run_id']}: {violation}")
        bucket, _ = classify(payload)
        report.check(bucket in BUCKETS, f"{payload['run_id']}: unknown bucket {bucket}")
        seen += 1
    report.check(seen > 0, "no saved results to audit")
    return seen


# ------------------------------------------------------------------ old trees
def check_earlier_deliveries(report):
    for root, manifest, label in (
            (OLD / "revision_v0.3", OLD / "revision_v0.3" / "manifests_v03" / "delivery_sha256.json", "v0.3"),
            (OLD / "revision_v0.2", OLD / "revision_v0.2" / "manifests_v02" / "delivery_sha256.json", "v0.2"),
            (OLD, OLD / "manifests" / "delivery_sha256.json", "v0.1")):
        if not manifest.is_file():
            report.check(False, f"{label}: manifest missing")
            continue
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        append_only = set(payload.get("append_only") or [])
        changed = []
        for relative, expected in payload["files"].items():
            if relative in append_only:
                continue
            target = root / relative
            if not target.is_file() or sha256(target) != expected:
                changed.append(relative)
        report.check(not changed, f"{label}: {len(changed)} sealed files changed: {changed[:3]}")


def main(argv=None):
    argv = list(argv or [])
    report = Report()
    check_protocol(report)
    rows = check_ledger(report)
    missing_batches = []
    if rows:
        check_seals(report)
        missing_batches = check_batches(report, rows)
        count = check_routes(report)
    else:
        count = 0
    check_earlier_deliveries(report)
    if "--require-batches" in argv:
        report.check(not missing_batches,
                     f"batches without a status file: {missing_batches}")

    summary = {"checks": report.checks, "failures": len(report.failures),
               "results_audited": count,
               "batches_not_run": missing_batches,
               "ledger_rows": len(rows) if rows else 0}
    if "--json" in argv:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"checks run: {report.checks}  results audited: {count}  "
              f"ledger rows: {summary['ledger_rows']}")
    if report.failures:
        print(f"VERIFY FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:60]:
            print("  -", failure)
        return 1
    print("VERIFY OK: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
