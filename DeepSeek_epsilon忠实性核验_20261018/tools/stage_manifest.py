"""Record the provenance of every copied source file (source hash + copy hash).

Read-only: only hashes the read-only originals and the copies inside this directory.
"""
import hashlib
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
WORKSPACE = NEW.parent
CMP = WORKSPACE / "DeepSeek_底层算法开发比较_20261018"
BASE = WORKSPACE / "DeepSeek_基线复现隔离工作_20261018"
FROZEN_SRC = (CMP / "sources" / "reference_tree" / "研究方案_剩余覆盖重规划_20261009"
              / "算法小型验证_20261010" / "frozen_baselines" / "v2_20261012" / "source")

PAIRS = [
    (CMP / "sources" / "v01" / "problem.py", "sources/v01/problem.py"),
    (CMP / "sources" / "v01" / "result.py", "sources/v01/result.py"),
    (CMP / "sources" / "v01" / "common_geometry.py", "sources/v01/common_geometry.py"),
    (CMP / "sources" / "v01" / "audit_independent.py", "sources/v01/audit_independent.py"),
    (FROZEN_SRC / "model.py", "sources/v01/model.py"),
    (CMP / "sources" / "v02" / "epsilon_core" / "maps.py", "sources/v02_epsilon_core/maps.py"),
    (CMP / "sources" / "v02" / "epsilon_core" / "etm.py", "sources/v02_epsilon_core/etm.py"),
    (CMP / "src" / "adapters" / "epsilon_star.py", "sources/epsilon_star.py"),
    (BASE / "sources" / "literature" / "epsilon_star_author_preprint.txt",
     "sources/literature/epsilon_star_author_preprint.txt"),
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    entries, problems = [], []
    for source, relative in PAIRS:
        copy = NEW / relative
        if not source.is_file() or not copy.is_file():
            problems.append(f"missing: {source} -> {copy}")
            continue
        a, b = sha256(source), sha256(copy)
        entries.append({"source": str(source), "source_sha256": a,
                        "copy": relative, "copy_sha256": b, "identical": a == b})
        if a != b:
            problems.append(f"copy differs: {relative}")
    payload = {"policy": "copy2, byte-for-byte; nothing written to the sources",
               "files": entries, "problems": problems}
    target = NEW / "manifests" / "source_copy.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {target}  files={len(entries)} problems={len(problems)}")
    for problem in problems:
        print("  -", problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
