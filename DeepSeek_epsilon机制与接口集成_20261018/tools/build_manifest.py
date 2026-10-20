"""Delivery hash manifest for this round.

Covers every delivered file except ``tmp/`` and the manifest itself.  The ledger is
append-only and is protected by the per-batch prefix seals instead of a whole-file
hash.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
TARGET = NEW / "manifests" / "delivery_sha256.json"
SKIP = {"manifests/delivery_sha256.json"}
SKIP_DIRS = {"tmp"}
APPEND_ONLY = ["logs/call_ledger.csv"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    files = {}
    for dirpath, dirnames, filenames in os.walk(NEW):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and d != "__pycache__")
        for name in sorted(filenames):
            path = Path(dirpath) / name
            relative = path.relative_to(NEW).as_posix()
            if relative in SKIP:
                continue
            files[relative] = sha256(path)
    payload = {
        "round": "epsilon_mechanism_and_interface_integration_20261018",
        "root": str(NEW),
        "scope": "every file under OUT except tmp/ and this manifest",
        "exclusions": sorted(SKIP_DIRS) + list(SKIP) + ["__pycache__"],
        "append_only": APPEND_ONLY,
        "append_only_rule": "prefix seals under manifests/ledger_seal_*.json",
        "file_count": len(files),
        "total_bytes": sum((NEW / name).stat().st_size for name in files),
        "files": files,
        "seals": {path.name: sha256(path)
                  for path in sorted((NEW / "manifests").glob("ledger_seal_*.json"))},
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    print(f"files={len(files)} bytes={payload['total_bytes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
