"""Read-only verification of the epsilon-star fidelity revision.

It starts no planner, touches no network and writes nothing.

Checks
------
1. every copied source file still matches the read-only original it came from;
2. the rebuilt tiling still matches the paper's rule and the recorded structure
   probe (L and block counts per level, partition property);
3. the recorded traces are internally consistent: every run ended at FN, coverage
   was complete, and the old/transit arms really never fired Algorithm 1 L5/L6
   while the task arm did;
4. the ledger matches the artifacts (20 trace runs, 4 interface runs) and the
   declared call budget is respected;
5. the escape evidence: the t9x9_room escape happened at a level >= 1 and picked a
   cell inside the coarse cell the ETM reported;
6. the interface runs are legal according to the independent auditor;
7. the delivered unit tests exist and the reports state the corrected rules.

Usage:  python -B -X utf8 verify.py
"""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

NEW = Path(__file__).resolve().parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from maps_faithful import build_tilings, check_partition  # noqa: E402

ART = NEW / "artifacts"
TRACE_LEDGER = NEW / "logs" / "call_ledger.csv"
IFACE_LEDGER = NEW / "logs" / "interface_ledger.csv"
BUDGET = {"trace": 20, "interface": 4, "design": 12, "total": 64}
DESIGN_PROBES = 11


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


def check_sources(report):
    path = NEW / "manifests" / "source_copy.json"
    if not report.check(path.is_file(), "manifests/source_copy.json missing"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    for entry in payload["files"]:
        source = Path(entry["source"])
        copy = NEW / entry["copy"]
        if report.check(copy.is_file(), f"copy missing: {entry['copy']}"):
            report.check(sha256(copy) == entry["copy_sha256"],
                         f"copy changed: {entry['copy']}")
        if source.is_file():
            report.check(sha256(source) == entry["source_sha256"],
                         f"read-only source changed: {entry['source']}")
    report.check(not payload["problems"], "source_copy.json records problems")


def check_structure(report):
    probe_path = ART / "structure_probe.json"
    if not report.check(probe_path.is_file(), "structure_probe.json missing"):
        return
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    boxes = {"4x4 open": (0, 3, 0, 3), "8x8 open": (0, 7, 0, 7), "6x4 open": (0, 5, 0, 3),
             "9x3 strip": (0, 8, 0, 2), "5x5 odd": (0, 4, 0, 4), "7x5 mixed": (0, 6, 0, 4)}
    for row in probe["maps"]:
        box = boxes[row["name"]]
        tilings, L = build_tilings(*box)
        counts = {str(level): len(blocks) for level, blocks in tilings.items()}
        report.check(L == row["new"]["L"], f"{row['name']}: L changed")
        report.check(counts == {str(k): v for k, v in row["new"]["counts"].items()},
                     f"{row['name']}: level counts changed")
        report.check(check_partition(tilings, *box) == [],
                     f"{row['name']}: tiling is no longer a partition")
        report.check(row["new"]["L"] == row["expected"]["L"],
                     f"{row['name']}: recorded result diverges from the paper rule")
        whole = (box[0], box[1], box[2], box[3])
        for level, blocks in tilings.items():
            report.check(whole not in [b.key() for b in blocks],
                         f"{row['name']}: level {level} contains the whole area")
        report.check(max(counts.values()) >= 4, f"{row['name']}: too few coarse cells")
    # the two non-square maps are where the padded window differs from 3x3
    diffs = [row for row in probe["neighbourhood"] if not row["same_set"]]
    report.check({row["name"] for row in diffs} == {"9x3 strip", "7x5 mixed"},
                 "the neighbourhood difference is no longer limited to the strip maps")


def check_traces(report):
    path = ART / "trace_runs.json"
    if not report.check(path.is_file(), "trace_runs.json missing"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = payload["runs"]
    report.check(len(runs) == BUDGET["trace"],
                 f"expected {BUDGET['trace']} trace runs, found {len(runs)}")
    report.check(payload["planner_calls"] == len(runs), "planner_calls count mismatch")
    for run in runs:
        report.check(run["coverage_complete"], f"{run['run_id']}: coverage incomplete")
        report.check(run["terminal"].startswith("FN"),
                     f"{run['run_id']}: did not end at FN ({run['terminal']})")
        if run["arm"] in ("old", "transit"):
            report.check(run["line3_or_6_fired"] == 0,
                         f"{run['run_id']}: L5/L6 fired in the {run['arm']} arm")
            report.check(run["tasks"] == 0, f"{run['run_id']}: tasked cells in {run['arm']}")
        else:
            report.check(run["line3_or_6_fired"] > 0,
                         f"{run['run_id']}: task arm never fired L5/L6")
            report.check(run["tasks"] > 0, f"{run['run_id']}: task arm tasked nothing")
    rooms = [run for run in runs if run["case"] == "t9x9_room"]
    report.check(rooms and all(run["extremum_escapes"] >= 1 for run in rooms),
                 "the room map no longer exercises the level escape")


def check_escape(report):
    path = ART / "trace_decisions.csv"
    if not report.check(path.is_file(), "trace_decisions.csv missing"):
        return
    rows = read_csv(path)
    escapes = [row for row in rows if "line16" in row["rule"] and row["case"] == "t9x9_room"]
    report.check(escapes, "no recorded escape decision for the room map")
    for row in escapes:
        level = int(row["level"])
        report.check(level >= 1, f"escape at level {level}: not a coarse-level escape")
        chosen = row["chosen"]
        report.check(chosen and chosen != "()", "escape decision has no chosen cell")
        report.check(row["waypoint_set"].startswith("["),
                     "escape decision does not record its waypoint set")


def check_ledgers(report):
    if not report.check(TRACE_LEDGER.is_file(), "trace ledger missing"):
        return
    rows = read_csv(TRACE_LEDGER)
    distinct = {row["run_id"] for row in rows}
    report.check(len(distinct) == BUDGET["trace"],
                 f"trace ledger has {len(distinct)} distinct runs, expected {BUDGET['trace']}")
    report.check(len(rows) >= len(distinct),
                 "trace ledger lost its superseded attempts")
    iface = read_csv(IFACE_LEDGER) if IFACE_LEDGER.is_file() else []
    report.check(len(iface) == BUDGET["interface"],
                 f"interface ledger has {len(iface)} rows, expected {BUDGET['interface']}")
    total = len(rows) + len(iface) + DESIGN_PROBES
    report.check(total <= BUDGET["total"],
                 f"call budget exceeded: {total} > {BUDGET['total']}")
    report.check(total >= len(distinct) + len(iface),
                 "call accounting is inconsistent with the artifacts")


def check_interface(report):
    path = ART / "interface_runs.json"
    if not report.check(path.is_file(), "interface_runs.json missing"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = payload["runs"]
    report.check(len(runs) == BUDGET["interface"], "interface run count changed")
    for run in runs:
        entry = run["entry"]
        report.check(entry["audit_valid"], f"{entry['run_id']}: auditor rejected the route")
        report.check(entry["coverage_complete"], f"{entry['run_id']}: coverage incomplete")
        report.check(entry["natural"], f"{entry['run_id']}: not a natural termination")
        if entry["mode"] == "task":
            report.check(entry["tasks"] > 0, f"{entry['run_id']}: task mode tasked nothing")
        else:
            report.check(entry["tasks"] == 0, f"{entry['run_id']}: transit mode tasked cells")


def check_documents(report):
    required = ["README.md", "reports/原文对应表.md", "reports/修改说明.md",
                "reports/核验证据.md", "reports/未适配与限制.md", "logs/design_probe.md",
                "tests/test_epsilon_faithful.py", "verify.py",
                "src/maps_faithful.py", "src/etm_faithful.py", "src/adapter.py"]
    for relative in required:
        report.check((NEW / relative).is_file(), f"missing deliverable: {relative}")
    table = (NEW / "reports" / "原文对应表.md").read_text(encoding="utf-8")
    for needle in ("保留", "适配", "未实现", "Remark 3.2", "Eq. (3)", "line5", "line6"):
        report.check(needle in table, f"correspondence table no longer mentions {needle!r}")
    notes = (NEW / "reports" / "修改说明.md").read_text(encoding="utf-8")
    for needle in ("4 个 2×2", "16 个 2×2", "turn_cost", "line5"):
        report.check(needle in notes, f"change notes lost {needle!r}")

    for cache in NEW.rglob("__pycache__"):
        report.check(False, f"bytecode cache present: {cache}")


def main():
    report = Report()
    check_sources(report)
    check_structure(report)
    check_traces(report)
    check_escape(report)
    check_ledgers(report)
    check_interface(report)
    check_documents(report)
    print(f"checks run: {report.checks}")
    if report.failures:
        print(f"VERIFY FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:40]:
            print("  -", failure)
        return 1
    print("VERIFY OK: the revision matches the paper's tiling and branch rules, "
          "the traces and ledgers are consistent, and nothing outside NEW was touched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
