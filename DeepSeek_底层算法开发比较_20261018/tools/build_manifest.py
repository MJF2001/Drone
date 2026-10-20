"""Delivery hash manifest for this round.

Records SHA256 for every delivered file under NEW, excluding ``tmp/`` (scratch and
per-batch caches) and the manifest itself.  Append-only evidence (the ledger) is
protected by the per-batch prefix seals instead of a whole-file hash, because
later batches legitimately append to it.

Every file copied from an earlier delivery is recorded together with the hash of
the file it was copied from, so the copy can be checked without re-reading the
read-only sources.
"""
import hashlib
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
TARGET = NEW / "manifests" / "delivery_sha256.json"
SKIP_DIRS = {"tmp"}
SKIP = {"manifests/delivery_sha256.json"}
APPEND_ONLY = ["logs/call_ledger.csv"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    copy_manifest = NEW / "manifests" / "source_copy.json"
    provenance = {}
    if copy_manifest.is_file():
        payload = json.loads(copy_manifest.read_text(encoding="utf-8"))
        for entry in payload["entries"]:
            provenance[entry["copy"]] = {
                "source": entry["source"],
                "source_sha256": entry["source_sha256"],
                "group": entry["group"],
            }

    files, groups = {}, {}
    for dirpath, dirnames, filenames in __import__("os").walk(NEW):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and d != "__pycache__")
        for name in sorted(filenames):
            path = Path(dirpath) / name
            relative = path.relative_to(NEW).as_posix()
            if relative in SKIP:
                continue
            files[relative] = sha256(path)
            groups[relative] = relative.split("/")[0]

    payload = {
        "round": "deepseek_development_comparison_20261018",
        "root": str(NEW),
        "scope": "every file under NEW except tmp/ and this manifest",
        "exclusions": sorted(SKIP_DIRS) + list(SKIP) + ["__pycache__"],
        "append_only": APPEND_ONLY,
        "append_only_rule": "protected by manifests/ledger_seal_*.json prefix hashes; "
                            "appends are legal, rewrites are not",
        "file_count": len(files),
        "total_bytes": sum((NEW / name).stat().st_size for name in files),
        "files": files,
        "groups": groups,
        "copied_from_sources": provenance,
        "sealed_ledgers": {path.name: sha256(path)
                           for path in sorted((NEW / "manifests").glob("ledger_seal_*.json"))},
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {}
    for group in groups.values():
        counts[group] = counts.get(group, 0) + 1
    print(f"wrote {TARGET}")
    print(f"files={len(files)} bytes={payload['total_bytes']}")
    print("by top directory:", json.dumps(counts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
