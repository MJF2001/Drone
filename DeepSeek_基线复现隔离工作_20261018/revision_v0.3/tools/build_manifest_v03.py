"""Build manifests_v03/delivery_sha256.json.

Records for every delivered file of this revision:
  * its SHA256;
  * if a same-named file exists in revision_v0.2 (``src_v03/x`` -> ``revision_v0.2/src_v02/x``)
    or in the sealed v0.1 tree (``src/x``), that file's hash and whether they differ.

``scratch/`` and this manifest are excluded.  ``logs_v03/call_ledger_v03.csv`` is
marked append-only: it is protected by the *prefix seal* (bytes + line count +
SHA256 of the sealed prefix) instead of a whole-file hash, because every further
planner call legitimately appends to it.
"""
import hashlib
import json
from pathlib import Path

V03 = Path(__file__).resolve().parent.parent
OUT = V03.parent
V02 = OUT / "revision_v0.2"
TARGET = V03 / "manifests_v03" / "delivery_sha256.json"
SKIP_DIRS = {"scratch"}
SKIP = {"manifests_v03/delivery_sha256.json"}
APPEND_ONLY = ["logs_v03/call_ledger_v03.csv"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def counterparts(relative):
    """Candidate earlier versions of the same logical file."""
    if not relative.startswith("src_v03/"):
        return []
    tail = relative[len("src_v03/"):]
    return [(V02 / "src_v02" / tail, "v0.2"), (OUT / "src" / tail, "v0.1")]


def main():
    files, compared, identical, added = {}, {}, [], []
    for path in sorted(V03.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(V03).as_posix()
        if relative in SKIP or relative.split("/")[0] in SKIP_DIRS:
            continue
        if "__pycache__" in relative.split("/"):
            continue
        digest = sha256(path)
        files[relative] = digest

        candidates = [(p, label) for p, label in counterparts(relative) if p.is_file()]
        if not candidates:
            added.append(relative)
            continue
        previous, label = candidates[0]
        other = sha256(previous)
        same = other == digest
        compared[relative] = {
            "basis": label,
            "basis_path": previous.relative_to(OUT).as_posix(),
            "basis_sha256": other,
            "v03_sha256": digest,
            "identical": same,
            "size_delta": path.stat().st_size - previous.stat().st_size,
        }
        if same:
            identical.append(relative)

    seal_path = V03 / "manifests_v03" / "ledger_seal.json"
    payload = {
        "revision": "v0.3",
        "root": str(V03),
        "scope": "every file under revision_v0.3 except scratch/ and this manifest",
        "exclusions": sorted(SKIP_DIRS) + ["manifests_v03/delivery_sha256.json", "__pycache__"],
        "append_only": APPEND_ONLY,
        "append_only_rule": "protected by manifests_v03/ledger_seal.json prefix hash; "
                            "appends are legal, rewrites are not",
        "file_count": len(files),
        "total_bytes": sum((V03 / name).stat().st_size for name in files),
        "files": files,
        "compared_with_earlier_revisions": compared,
        "identical_to_earlier": identical,
        "added": added,
        "ledger_seal": json.loads(seal_path.read_text(encoding="utf-8")) if seal_path.is_file() else None,
        "sealed_manifests": {
            "v0.1": "manifests/delivery_sha256.json",
            "v0.2": "revision_v0.2/manifests_v02/delivery_sha256.json",
        },
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    print(f"files={len(files)} bytes={payload['total_bytes']}")
    print(f"compared with earlier revisions: {len(compared)} "
          f"(identical: {len(identical)}), added: {len(added)}")
    for name in sorted(compared):
        flag = "same" if compared[name]["identical"] else "CHANGED"
        print(f"  {flag:8s} {name}  (basis {compared[name]['basis']})")


if __name__ == "__main__":
    main()
