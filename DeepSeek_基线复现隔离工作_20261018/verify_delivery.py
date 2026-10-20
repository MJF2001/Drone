"""Read-only delivery checker.

It never starts a planner, never touches the network, never rebuilds a result.
It only reads files and recomputes hashes, then re-audits the *saved* routes.

Checks
-----
1. every copied source still matches the SHA256 recorded at copy time, and the
   frozen / candidate bundles still match their own manifests;
2. the protected source tree (`.remote_Drone`, the historical C* implementation)
   is unchanged compared with the before-copy baseline;
3. every saved route under `artifacts/routes` audited from the fixture inputs,
   using the independent auditor, never the planner's own claim;
4. the fixture files still match their recorded hashes;
5. the delivery SHA256 manifest in `manifests/delivery_sha256.json` matches every
   delivered file (the manifest itself excluded);
6. no bytecode cache or stray temporary artefact exists inside the delivery.

Exit code 0 means every check passed.  Any failure prints the exact file.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
SRC = Path(r"D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone")
CSTAR_SRC = Path(r"D:\0A无人机\0A算法复现\0A算法复现\cstar_strict")

REQUIRED = [
    "README.md",
    "inventory.csv",
    "verify_delivery.py",
    "specs/unified_interface.md",
    "specs/method_original_mapping.md",
    "specs/oarp_core2_mechanism.md",
    "specs/ppcpp_core4_mechanism.md",
    "specs/epsilon_star_adaptation.md",
    "specs/cstar_adaptation.md",
    "specs/TRACE_spec.md",
    "specs/LKH_spec.md",
    "reports/本轮复现与适配报告.md",
    "reports/微图结果表.md",
    "reports/P2现状与下一轮比较协议草案.md",
    "交主会话验收.md",
    "manifests/source_copy_sha256.json",
    "manifests/protected_sources_before.json",
    "manifests/method_matrix.csv",
    "manifests/delivery_sha256.json",
    "src/adapters/cstar.py",
    "src/epsilon_core/maps.py",
    "src/epsilon_core/etm.py",
    "tests/test_cstar_micro.py",
    "artifacts/cstar_trace/degeneration_public_map.json",
    "artifacts/epsilon_trace/toy_4x2_decisions.json",
]


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

    def ok(self):
        return not self.failures


def check_required(report):
    for name in REQUIRED:
        report.check((OUT / name).is_file(), f"missing required file: {name}")
    for extra in ("artifacts/runs/micro_runs.json", "artifacts/runs/exact_micro.json",
                  "logs/call_ledger.csv"):
        report.check((OUT / extra).is_file(), f"missing evidence file: {extra}")


def check_copied_sources(report):
    payload = json.loads((OUT / "manifests" / "source_copy_sha256.json").read_text(encoding="utf-8"))
    report.check(payload["files"] == len(payload["entries"]),
                 "source_copy_sha256.json file count mismatch")
    for entry in payload["entries"]:
        source = Path(entry["source_path"])
        copy = OUT / entry["copy_path"]
        if not report.check(copy.is_file(), f"copied file missing: {entry['copy_path']}"):
            continue
        report.check(sha256(copy) == entry["copy_sha256"],
                     f"copied file changed: {entry['copy_path']}")
        if source.is_file():
            report.check(sha256(source) == entry["source_sha256"],
                         f"SOURCE CHANGED since the copy: {entry['source_path']}")


def check_bundle_manifests(report):
    frozen = OUT / "sources" / "reference_tree" / "研究方案_剩余覆盖重规划_20261009" / \
        "算法小型验证_20261010" / "frozen_baselines" / "v2_20261012"
    candidate = OUT / "sources" / "reference_tree" / "研究方案_剩余覆盖重规划_20261009" / \
        "算法小型验证_20261010" / "candidate_baselines" / "PPCPP_CORE4" / "v0.1_20261014"
    manifest = json.loads((frozen / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["source_sha256"].items():
        report.check(sha256(frozen / "source" / name) == expected,
                     f"frozen source no longer matches v2_20261012: {name}")
    report.check(sha256(frozen / "runtime_profile.json") == manifest["runtime_profile_sha256"],
                 "frozen runtime profile changed")
    candidate_manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in candidate_manifest["files_sha256"].items():
        report.check(sha256(candidate / name) == expected,
                     f"candidate file no longer matches v0.1_20261014: {name}")


def check_protected_sources(report):
    protected = json.loads((OUT / "manifests" / "protected_sources_before.json").read_text(encoding="utf-8"))
    changed = []
    missing = []
    for path, expected in protected["sha256"].items():
        target = Path(path)
        if not target.is_file():
            missing.append(path)
        elif sha256(target) != expected:
            changed.append(path)
    report.check(not missing, f"{len(missing)} protected sources disappeared, first: {missing[:3]}")
    report.check(not changed, f"{len(changed)} protected sources changed, first: {changed[:3]}")


def load_request(payload):
    sys.path.insert(0, str(OUT / "src"))
    from problem import PlanRequest, Termination
    grid = payload["grid"]
    return PlanRequest(
        case_id=payload["case_id"],
        free=frozenset(map(tuple, grid["free"])),
        published_targets=frozenset(map(tuple, grid["published_targets"])),
        covered=frozenset(map(tuple, grid["covered"])),
        current=tuple(grid["current"]),
        base=tuple(grid["base"]),
        old_route=tuple(map(tuple, grid["old_route"])),
        remaining_resource=grid["remaining_resource"],
        initial_targets=frozenset(map(tuple, grid["initial_targets"])),
        termination=Termination(time_limit_seconds=30.0))


def check_saved_routes(report):
    sys.path.insert(0, str(OUT / "src"))
    from audit_independent import audit_route

    case_dir = OUT / "tests" / "fixtures" / "cases"
    fixtures = {}
    for path in sorted(case_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        fixtures[payload["case_id"]] = (payload, path)

    routes_root = OUT / "artifacts" / "routes"
    seen = 0
    for route_file in sorted(routes_root.glob("*/*.json")):
        payload = json.loads(route_file.read_text(encoding="utf-8"))
        case_id = payload["case_id"]
        if not report.check(case_id in fixtures, f"saved route for unknown case: {case_id}"):
            continue
        fixture, fixture_path = fixtures[case_id]
        request = load_request(fixture)
        route = tuple(map(tuple, payload["route"])) if payload.get("route") else ()
        audit = audit_route(request, route)
        stored = payload.get("audit") or {}
        report.check(audit["valid"] == stored.get("valid"),
                     f"re-audit disagrees with the stored verdict: {route_file}")
        report.check(audit["route_steps"] == payload.get("route_steps"),
                     f"re-audit step count differs: {route_file}")
        report.check(audit["errors"] == stored.get("errors"),
                     f"re-audit errors differ: {route_file}")
        if payload.get("status") in ("finished", "planned", "planned_at_timeout",
                                     "complete_coverage"):
            report.check(audit["coverage_complete"],
                         f"saved route claims completion but omits targets: {route_file}")
        seen += 1
    report.check(seen > 0, "no saved routes to audit")


def check_fixtures(report):
    run_file = OUT / "artifacts" / "runs" / "micro_runs.json"
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    recorded = {}
    for row in payload["rows"]:
        recorded.setdefault(row["case_id"], row["fixture_sha256"])
    for case_id, expected in recorded.items():
        path = OUT / "tests" / "fixtures" / "cases" / f"{case_id}.json"
        report.check(path.is_file(), f"fixture missing: {case_id}")
        if path.is_file():
            report.check(sha256(path) == expected, f"fixture changed since the run: {case_id}")


def check_delivery_manifest(report):
    path = OUT / "manifests" / "delivery_sha256.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    listed = payload["files"]
    report.check(len(listed) > 20, "delivery manifest looks empty")
    for relative, expected in listed.items():
        if relative == "manifests/delivery_sha256.json":
            continue
        target = OUT / relative
        if not report.check(target.is_file(), f"delivered file missing: {relative}"):
            continue
        report.check(sha256(target) == expected, f"delivered file changed: {relative}")


def check_hygiene(report):
    caches = [p for p in OUT.rglob("__pycache__") if p.is_dir()]
    report.check(not caches, f"bytecode caches present: {[str(p.relative_to(OUT)) for p in caches[:3]]}")
    stray = [p for p in (OUT / "tmp").glob("*") if p.suffix in (".log", ".tmp")]
    report.check(not stray, f"stray temporary files: {[p.name for p in stray[:3]]}")


def check_ledger(report):
    path = OUT / "logs" / "call_ledger.csv"
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report.check(len(rows) > 0, "call ledger is empty")
    report.check(all(row["case_id"] for row in rows), "call ledger rows without a case id")
    report.check(all(row["method_id"] for row in rows), "call ledger rows without a method id")
    exceptions = [row for row in rows if row["status"] == "adapter_exception"]
    report.check(not exceptions,
                 f"{len(exceptions)} planner calls ended in an adapter exception")


def main():
    report = Report()
    check_required(report)
    check_copied_sources(report)
    check_bundle_manifests(report)
    check_protected_sources(report)
    check_saved_routes(report)
    check_fixtures(report)
    check_delivery_manifest(report)
    check_hygiene(report)
    check_ledger(report)

    print(f"checks run: {report.checks}")
    if report.ok():
        print("VERIFY OK: every check passed")
        return 0
    print(f"VERIFY FAILED: {len(report.failures)} problem(s)")
    for failure in report.failures[:60]:
        print("  -", failure)
    return 1


if __name__ == "__main__":
    sys.exit(main())
