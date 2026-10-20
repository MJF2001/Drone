"""Manifest for the offline v2 addendum.

The v1 delivery manifest (``manifests/delivery_sha256.json``) is sealed: the review
asked for a derived report, not for edits to the sealed set.  This manifest

* records the hash of the v1 manifest and re-verifies every v1 file against it, so
  the addendum can prove the original delivery is untouched;
* records the hashes of the addendum files (the v2 report, the derived tables and
  the two derivation/verification tools).

No earlier file is rewritten.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
V1 = NEW / "manifests" / "delivery_sha256.json"
TARGET = NEW / "manifests" / "delivery_sha256_v2.json"
ADDENDUM = [
    "reports/结果报告_v2.md",
    "reports/derived_v2/tables_v2.md",
    "reports/derived_v2/summary_v2.json",
    "reports/derived_v2/engine_stop.csv",
    "reports/derived_v2/improvement_timeline.csv",
    "reports/derived_v2/speed_pairs.csv",
    "reports/derived_v2/stage_costs.csv",
    "reports/derived_v2/stage_marginal_p2.csv",
    "tools/derive_v2.py",
    "verify_v2.py",
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    if not V1.is_file():
        raise SystemExit("the v1 manifest is missing")
    sealed = json.loads(V1.read_text(encoding="utf-8"))
    append_only = set(sealed.get("append_only") or [])
    changed, missing = [], []
    for relative, expected in sealed["files"].items():
        if relative in append_only:
            continue
        path = NEW / relative
        if not path.is_file():
            missing.append(relative)
        elif sha256(path) != expected:
            changed.append(relative)

    addendum = {}
    for relative in ADDENDUM:
        path = NEW / relative
        if not path.is_file():
            raise SystemExit(f"addendum file missing: {relative}")
        addendum[relative] = sha256(path)

    payload = {
        "revision": "v2-addendum",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "the v1 manifest stays sealed; this file covers only the addendum "
                  "and re-verifies every v1 file",
        "v1_manifest": {"path": "manifests/delivery_sha256.json", "sha256": sha256(V1),
                        "file_count": sealed["file_count"]},
        "v1_recheck": {"checked": len(sealed["files"]) - len(append_only),
                       "changed": changed, "missing": missing,
                       "append_only_skipped": sorted(append_only)},
        "addendum_files": addendum,
        "addendum_count": len(addendum),
        "new_planner_calls": 0,
        "note": "reports/结果报告.md remains the as-run report; reports/结果报告_v2.md "
                "is the corrected interpretation and supersedes its claims, not its data",
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    print(f"v1 files rechecked: {payload['v1_recheck']['checked']} "
          f"(changed {len(changed)}, missing {len(missing)})")
    print(f"addendum files: {len(addendum)}")
    if changed or missing:
        print("PROBLEM: the sealed delivery changed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
