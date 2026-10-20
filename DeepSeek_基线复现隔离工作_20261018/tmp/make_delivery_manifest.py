"""Generate manifests/delivery_sha256.json.

Scope: every regular file under OUT except
  * ``manifests/delivery_sha256.json`` itself (it cannot hash itself), and
  * ``tmp/`` scratch (temporary scripts and the redirected TEMP/TMP target).

``sources/`` IS included, including the pinned dependency tree, because the
question "what exactly was delivered" must be answerable without trusting a
second manifest.
"""
import datetime
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"tmp"}
SKIP = {"manifests/delivery_sha256.json"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    files = {}
    total = 0
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(OUT).as_posix()
        if relative in SKIP:
            continue
        if relative.split("/")[0] in EXCLUDE_DIRS:
            continue
        if "__pycache__" in relative.split("/"):
            continue
        files[relative] = sha256(path)
        total += path.stat().st_size
    payload = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "root": str(OUT),
        "scope": "every regular file under the delivery root, excluding this manifest and tmp/",
        "exclusions": sorted(EXCLUDE_DIRS) + ["manifests/delivery_sha256.json", "__pycache__"],
        "file_count": len(files),
        "total_bytes": total,
        "files": files,
    }
    target = OUT / "manifests" / "delivery_sha256.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {target} with {len(files)} files, {total} bytes")


if __name__ == "__main__":
    main()
