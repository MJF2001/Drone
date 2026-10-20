"""Build manifests_v02/delivery_sha256.json.

For every file of the revision it records:
  * the SHA256 of the delivered copy;
  * if a same-named file exists in the sealed v0.1 tree (``src_v02/x`` -> ``src/x``),
    that file's SHA256 and whether the two differ.

That makes "what did this revision change" checkable without trusting a table.
``scratch/`` is excluded (temporary run area), as is this manifest itself.
"""
import hashlib
import json
from pathlib import Path

V02 = Path(__file__).resolve().parent.parent
OUT = V02.parent
TARGET = V02 / "manifests_v02" / "delivery_sha256.json"
SKIP_DIRS = {"scratch"}
SKIP = {"manifests_v02/delivery_sha256.json"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def v01_counterpart(relative):
    if relative.startswith("src_v02/"):
        return OUT / "src" / relative[len("src_v02/"):]
    return None


def main():
    files, modified, identical, added = {}, {}, [], []
    for path in sorted(V02.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(V02).as_posix()
        if relative in SKIP or relative.split("/")[0] in SKIP_DIRS:
            continue
        if "__pycache__" in relative.split("/"):
            continue
        digest = sha256(path)
        files[relative] = digest
        counterpart = v01_counterpart(relative)
        if counterpart is None:
            added.append(relative)
            continue
        if not counterpart.is_file():
            added.append(relative)      # new file, not a modification
            continue
        other = sha256(counterpart)
        same = other == digest
        modified[relative] = {
            "v01_path": counterpart.relative_to(OUT).as_posix(),
            "v01_sha256": other,
            "v02_sha256": digest,
            "identical_to_v01": same,
            "size_delta": path.stat().st_size - counterpart.stat().st_size,
        }
        if same:
            identical.append(relative)

    payload = {
        "revision": "v0.2",
        "root": str(V02),
        "scope": "every file under revision_v0.2 except scratch/ and this manifest",
        "exclusions": sorted(SKIP_DIRS) + ["manifests_v02/delivery_sha256.json", "__pycache__"],
        "file_count": len(files),
        "total_bytes": sum((V02 / name).stat().st_size for name in files),
        "files": files,
        "compared_with_v01": modified,
        "identical_to_v01": identical,
        "added_or_renamed": added,
        "sealed_v01_manifest": "manifests/delivery_sha256.json",
        # append-only evidence: every further planner call legitimately grows it,
        # so verify_v02 checks its INVARIANTS instead of its hash
        "append_only": ["logs_v02/call_ledger_v02.csv",
                        "artifacts_v02/runs/micro_runs_v02.json",
                        "artifacts_v02/runs/run_manifest_v02.json"],
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    print(f"files={len(files)} bytes={payload['total_bytes']}")
    print(f"copied-then-modified: {len(modified)} "
          f"(identical to v0.1: {len(identical)})")
    print(f"added (no v0.1 counterpart): {len(added)}")
    for name in sorted(modified):
        flag = "same" if modified[name]["identical_to_v01"] else "CHANGED"
        print(f"  {flag:8s} {name}")


if __name__ == "__main__":
    main()
