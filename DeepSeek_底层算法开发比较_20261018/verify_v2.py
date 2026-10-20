"""Read-only verification of the v2 addendum.

It starts no planner and writes nothing.  It answers one question: **is the v2
interpretation really derived from the sealed v1 results, without changing them?**

Checks
------
1. the v1 sealed manifest still matches the files on disk (append-only ledger
   excluded, it is protected by the per-batch prefix seals);
2. the ledger still holds exactly 313 planner attempts and every seal still passes,
   i.e. no planner call was made for this addendum;
3. the derived tables are re-derived from the raw results and compared with the
   saved CSVs: ``engine_stop``, ``route_success`` and ``route_origin`` counts, and
   the per-run classification of every one of the 300 development results;
4. the addendum manifest matches the addendum files;
5. the corrected claims quoted in ``reports/结果报告_v2.md`` appear with the values
   that the derivation actually produced (spot checks on the key numbers).

Usage:  python -B -X utf8 verify_v2.py
"""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

NEW = Path(__file__).resolve().parent   # this file sits at the NEW root
sys.path.insert(0, str(NEW / "src"))
sys.path.insert(0, str(NEW / "tools"))

import bootstrap  # noqa: E402,F401  (resolution only; no planner is started)

import derive_v2  # noqa: E402

V1 = NEW / "manifests" / "delivery_sha256.json"
V2 = NEW / "manifests" / "delivery_sha256_v2.json"
LEDGER = NEW / "logs" / "call_ledger.csv"
OUT = NEW / "reports" / "derived_v2"
EXPECTED_ATTEMPTS = 313


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


def check_v1(report):
    sealed = json.loads(V1.read_text(encoding="utf-8"))
    append_only = set(sealed.get("append_only") or [])
    for relative, expected in sealed["files"].items():
        if relative in append_only:
            continue
        path = NEW / relative
        if report.check(path.is_file(), f"v1 file missing: {relative}"):
            report.check(sha256(path) == expected, f"v1 file changed: {relative}")


def check_no_new_calls(report):
    rows = read_csv(LEDGER)
    attempts = [row for row in rows if row.get("phase") == "start"]
    report.check(len(attempts) == EXPECTED_ATTEMPTS,
                 f"planner attempts changed: {len(attempts)} != {EXPECTED_ATTEMPTS}")
    for path in sorted((NEW / "manifests").glob("ledger_seal_*.json")):
        seal = json.loads(path.read_text(encoding="utf-8"))
        raw = LEDGER.read_bytes()
        if not report.check(len(raw) >= seal["bytes"], f"{path.name}: ledger shrank"):
            continue
        report.check(hashlib.sha256(raw[: seal["bytes"]]).hexdigest()
                     == seal["sha256_of_prefix"], f"{path.name}: sealed prefix rewritten")


def check_derivation(report):
    rows = derive_v2.load()
    dev = [row for row in rows if row["batch"] in derive_v2.BATCHES]
    report.check(len(dev) == 300, f"expected 300 development results, found {len(dev)}")

    saved = {row["run_id"]: row for row in read_csv(OUT / "engine_stop.csv")}
    report.check(len(saved) == len(dev), "engine_stop.csv does not cover every result")
    stop_counts = Counter()
    success_counts = Counter()
    origin_counts = Counter()
    for row in dev:
        stop, evidence = derive_v2.engine_stop(row)
        entry = saved.get(row["run_id"])
        if not report.check(entry is not None, f"missing derived row: {row['run_id']}"):
            continue
        report.check(entry["engine_stop"] == stop,
                     f"{row['run_id']}: derived engine_stop differs ({entry['engine_stop']} vs {stop})")
        report.check(entry["route_success"] == derive_v2.route_success(row),
                     f"{row['run_id']}: derived route_success differs")
        report.check(entry["route_origin"] == derive_v2.route_origin(row),
                     f"{row['run_id']}: derived route_origin differs")
        stop_counts[stop] += 1
        success_counts[derive_v2.route_success(row)] += 1
        origin_counts[(row["method_id"], derive_v2.route_origin(row))] += 1

    summary = json.loads((OUT / "summary_v2.json").read_text(encoding="utf-8"))
    total_stop = sum(sum(info.values()) for info in summary["engine_stop"].values())
    report.check(total_stop == len(dev), "summary stop counts do not add up")
    for method, info in summary["engine_stop"].items():
        for key, value in info.items():
            report.check(value == sum(1 for row in dev
                                      if row["method_id"] == method
                                      and derive_v2.engine_stop(row)[0] == key),
                         f"summary engine_stop mismatch: {method}/{key}")
    report.check(summary["route_success"].get("legal_in_budget", 0) + 
                 summary["route_success"].get("legal_over_budget", 0) +
                 summary["route_success"].get("no_route", 0) == len(dev),
                 "summary route_success counts do not add up")
    report.check(summary["natural_claimed_vs_found"]["overclaimed"] == 11,
                 "the number of overclaimed natural runs changed")

    # the speed table must stay a same-sample ratio
    speed = read_csv(OUT / "speed_pairs.csv")
    for row in speed:
        if row["p2_seconds"] and float(row["p2_seconds"]) > 0:
            expected = round(float(row["method_seconds"]) / float(row["p2_seconds"]), 4)
            report.check(abs(expected - float(row["time_ratio_method_over_p2"])) < 1e-3,
                         f"speed ratio not recomputable for {row['run_id'] if 'run_id' in row else row['case_id']}")


def check_manifest(report):
    manifest = json.loads(V2.read_text(encoding="utf-8"))
    for relative, expected in manifest["addendum_files"].items():
        path = NEW / relative
        if report.check(path.is_file(), f"addendum file missing: {relative}"):
            report.check(sha256(path) == expected, f"addendum file changed: {relative}")
    report.check(manifest["v1_manifest"]["sha256"] == sha256(V1),
                 "the recorded v1 manifest hash no longer matches")
    report.check(not manifest["v1_recheck"]["changed"], "v1 changes were recorded")
    report.check(not manifest["v1_recheck"]["missing"], "v1 misses were recorded")


def check_claims(report):
    text = (NEW / "reports" / "结果报告_v2.md").read_text(encoding="utf-8")
    for needle in ("0.072", "31.707", "971.78", "12.1%", "223", "11 条",
                   "116、持平 4、更长 8", "cap=16", "cap=32"):
        report.check(needle in text, f"the v2 report no longer states {needle!r}")
    for forbidden in ("200 倍", "40 倍"):
        # these numbers may only appear inside the withdrawal sentence
        index = text.find(forbidden)
        while index != -1:
            window = text[max(0, index - 400):index]
            report.check(("撤回" in window) or ("原报告" in window),
                         f"the withdrawn claim {forbidden!r} is used as a live statement")
            index = text.find(forbidden, index + 1)


def main():
    report = Report()
    check_v1(report)
    check_no_new_calls(report)
    check_derivation(report)
    check_manifest(report)
    check_claims(report)
    print(f"checks run: {report.checks}")
    if report.failures:
        print(f"VERIFY v2 FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:40]:
            print("  -", failure)
        return 1
    print("VERIFY v2 OK: the addendum is derived from the sealed results, "
          "and those results are unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
