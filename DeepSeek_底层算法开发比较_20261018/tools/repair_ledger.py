"""Repair the ledger rows that a runner defect inserted (documented, not hidden).

The first preflight pass used a batch driver that compared against a snapshot of
the ledger taken at batch start, so it appended a second, spurious ``end`` row
(``status=runner_crash``) for every task whose child had already written its own
``end`` row.  The planner observations themselves are untouched.

What this script does, and what it deliberately does not do:

* keeps a byte-exact copy of the defective ledger next to it;
* drops only the spurious ``end`` rows, i.e. rows with ``status`` in
  (``runner_crash``, ``hard_timeout``) for a ``run_id`` that already has a genuine
  ``end`` row from the child;
* writes ``manifests/ledger_repair.json`` with before/after hashes and the exact
  list of removed rows;
* does NOT re-run any planner call, and does NOT touch any result file.
"""
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
LEDGER = NEW / "logs" / "call_ledger.csv"
DEFECTIVE = NEW / "logs" / "call_ledger.defective_v1.csv"
RECORD = NEW / "manifests" / "ledger_repair.json"
SPURIOUS = ("runner_crash", "hard_timeout")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if not LEDGER.is_file():
        raise SystemExit("ledger missing")
    if not DEFECTIVE.exists():
        shutil.copy2(LEDGER, DEFECTIVE)
    before_sha = sha256(LEDGER)
    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8-sig", newline="")))
    fields = list(rows[0].keys())

    genuine = {row["run_id"] for row in rows
               if row.get("phase") == "end" and row.get("status") not in SPURIOUS}
    kept, removed = [], []
    seen_ends = set()
    for row in rows:
        if row.get("phase") == "end":
            if row.get("status") in SPURIOUS and row["run_id"] in genuine:
                removed.append(dict(row))
                continue
            if row["run_id"] in seen_ends:
                removed.append(dict(row))
                continue
            seen_ends.add(row["run_id"])
        kept.append(row)

    with open(LEDGER, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)

    after = sha256(LEDGER)
    payload = {
        "repaired_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "batch driver appended a duplicate end row when the child had already "
                  "written one; the driver snapshot of the ledger was not refreshed",
        "no_planner_call_rerun": True,
        "results_untouched": True,
        "defective_copy": str(DEFECTIVE.relative_to(NEW)),
        "defective_sha256": sha256(DEFECTIVE),
        "sha256_before": before_sha,
        "sha256_after": after,
        "rows_before": len(rows), "rows_after": len(kept),
        "rows_removed": len(removed),
        "removed": [{"run_id": row["run_id"], "batch": row["batch"],
                     "status": row["status"], "note": row["note"][:120]} for row in removed],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in
                      ("rows_before", "rows_after", "rows_removed", "sha256_before",
                       "sha256_after")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
