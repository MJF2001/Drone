"""Count planner attempts per batch and enforce the round's call budget.

The budget is counted from the two-phase ledger (one ``start`` row is one
attempt), never from the number of unittest names or plan rows.  A hard failure
here must stop the round rather than silently overshoot.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
LEDGER = NEW / "logs" / "call_ledger.csv"

BUDGET = {"preparation": 60, "preflight": 10, "development": 300, "total": 370}


def read_ledger():
    if not LEDGER.is_file():
        return []
    with open(LEDGER, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def summary():
    rows = read_ledger()
    attempts = [row for row in rows if row.get("phase") == "start"]
    ends = {row["run_id"] for row in rows if row.get("phase") == "end"}
    # the targeted PPCPP re-check after the runner fix counts as preparation:
    # it repeats two cells, it does not re-run the preflight batch
    by_kind = Counter("preparation" if row.get("batch") == "PREFLIGHT_RECHECK"
                      else row.get("kind") for row in attempts)
    orphans = [row["run_id"] for row in attempts if row["run_id"] not in ends]
    return {"attempts": len(attempts), "by_kind": dict(by_kind),
            "end_rows": len(ends), "runs_without_end": sorted(orphans),
            "budget": BUDGET,
            "remaining": {"preparation": BUDGET["preparation"] - by_kind.get("preparation", 0),
                          "preflight": BUDGET["preflight"] - by_kind.get("preflight", 0),
                          "development": BUDGET["development"] - by_kind.get("development", 0),
                          "total": BUDGET["total"] - len(attempts)}}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero when any budget is exceeded")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    info = summary()
    target = NEW / "manifests" / "call_budget.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
    else:
        print(f"attempts={info['attempts']} by_kind={info['by_kind']} "
              f"runs_without_end={len(info['runs_without_end'])}")
        print(f"remaining={info['remaining']}")
    if args.check:
        over = [key for key, value in info["remaining"].items() if value < 0]
        if over:
            print(f"BUDGET EXCEEDED: {over}")
            return 1
        if info["runs_without_end"]:
            print(f"UNPAIRED RUNS: {info['runs_without_end'][:5]}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
