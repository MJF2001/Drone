"""A-stage: inventory + hash + copy + verify, read-only on SRC.

Run with the OUT-local interpreter, bytecode writing disabled:

    python -B -X utf8 tmp/stage_a_copy.py

Writes:
    manifests/inventory.csv                 one row per copied item group
    manifests/source_copy_sha256.json       per-file source/destination hashes
    manifests/protected_sources_before.json hashes of the protected SRC files
Never writes outside OUT and never opens an SRC file for writing.
"""
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
SRC = Path(r"D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone")
CSTAR = Path(r"D:\0A无人机仿真\0A算法复现\0A算法复现\cstar_strict")
S1 = SRC / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
DOC = SRC / "研究方案_剩余覆盖重规划_20261009" / "论文资料汇总_三篇文献与论文主题_20261009"

REF = OUT / "sources" / "reference_tree"
REF_ALGO = REF / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
CSTAR_OUT = OUT / "sources" / "cstar_historical"
LIT = OUT / "sources" / "literature"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files_under(root):
    if root.is_file():
        return [root]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            out.append(Path(dirpath) / name)
    return out


# ---------------------------------------------------------------- item groups
# (method_id, role, absolute source file/dir, destination root, why)
GROUPS = [
    ("SHARED", "shared_geometry", S1 / "model.py", REF_ALGO,
     "frozen shared discrete geometry used by all v2 baselines"),
    ("SHARED", "shared_geometry", S1 / "planners.py", REF_ALGO,
     "P2 candidate generation, nearest neighbour and 2-opt primitives"),
    ("SHARED", "shared_geometry", S1 / "audit.py", REF_ALGO,
     "historical independent route auditor kept for cross-checking"),
    ("SHARED", "shared_geometry", S1 / "bfs_metric_geometry.py", REF_ALGO,
     "batched exact BFS metric, engineering optimisation only"),
    ("SHARED", "shared_geometry", S1 / "unified_geometry.py", REF_ALGO,
     "query-order-independent connector policy and single-cell audit"),
    ("SHARED", "shared_geometry", S1 / "unified_candidates.py", REF_ALGO,
     "TREE_MST and P2_SHARED candidate entry points"),
    ("SHARED", "shared_geometry", S1 / "p2_search_audit.py", REF_ALGO,
     "instrumented P2_MULTI (stage events, multi-start variant)"),
    ("SHARED", "shared_geometry", S1 / "baseline_suite.py", REF_ALGO,
     "v2 dispatch for P2_MULTI / OARP_CORE2 / TREE_MST with contract checks"),
    ("SHARED", "shared_geometry", SRC / "portable_frozen.py", REF,
     "portable loader that resolves the frozen v2 source relative to itself"),
    ("OARP_CORE2", "package", S1 / "oarp_replan", REF_ALGO,
     "OARP-Replan core: rank LP/MIP, order module, GTSP/path-set TOUR, budget"),
    ("P2_MULTI", "frozen", S1 / "frozen_baselines" / "v2_20261012", REF_ALGO / "frozen_baselines",
     "frozen v2 baseline bundle actually exported by portable_frozen"),
    ("PPCPP_CORE4", "candidate", S1 / "candidate_baselines" / "PPCPP_CORE4" / "v0.1_20261014",
     REF_ALGO / "candidate_baselines" / "PPCPP_CORE4",
     "PPCPP_CORE4 v0.1_20261014 candidate plus its integrity manifest"),
    ("SHARED", "dependency", S1 / ".deps", REF_ALGO,
     "pinned numpy / pyscipopt / author-maintained glns python extension"),
    ("CSTAR", "historical_implementation", CSTAR, CSTAR_OUT,
     "historical C* strict reproduction (geometry/rcg/planner/tests/results)"),
    ("EPSILON_STAR", "literature", DOC / "补充文献基线核查_20261016" / "epsilon_star_author_preprint.txt", LIT,
     "author preprint full text used as the epsilon-star rule source"),
    ("EPSILON_STAR", "literature", DOC / "补充文献基线核查_20261016" / "epsilon_star_author_preprint.pdf", LIT,
     "author preprint PDF, hash evidence for the text extraction"),
    ("EPSILON_STAR", "literature_evidence", DOC / "基线机制核查_20261016", LIT / "基线机制核查_20261016",
     "rendered pages 3-5, mechanism JSON and source hashes for epsilon-star"),
    ("CSTAR", "literature", DOC / "Cstar_coverage_unknown_原文.pdf", LIT,
     "C* original paper as held by the project"),
    ("CSTAR", "literature", DOC / "文献基线核查_20261014" / "Cstar_coverage_unknown_原文.txt", LIT,
     "extracted C* text used for the mechanism table"),
    ("CSTAR", "historical_spec", DOC / "Cstar_历史复现实现约定_SPEC.md", LIT,
     "historical C* implementation conventions (ambiguity decisions)"),
    ("CSTAR", "historical_spec", DOC / "Cstar_历史复现说明_README.md", LIT,
     "historical C* reproduction readme and validation record"),
    ("CSTAR", "historical_spec", DOC / "Cstar_历史障碍后覆盖修复验证.md", LIT,
     "proves the historical C* is unknown-environment and not our model"),
    ("OARP_CORE2", "literature", DOC / "OARP-Replan_2311.17837v2.pdf", LIT,
     "OARP-Replan paper"),
    ("OARP_CORE2", "literature", DOC / "文献基线核查_20261014" / "OARP-Replan_2311.17837v2.txt", LIT,
     "OARP-Replan extracted text"),
    ("TRACE", "literature", DOC / "TRACE_2609.21777v1.pdf", LIT,
     "TRACE paper, needed for the specification only this round"),
    ("TRACE", "literature", DOC / "文献基线核查_20261014" / "TRACE_2609.21777v1.txt", LIT,
     "TRACE extracted text, needed for the specification only this round"),
    ("SHARED", "literature_manifest", DOC / "文献基线核查_20261014" / "local_pdf_manifest.json", LIT,
     "manifest for the local PDF copies"),
    ("SHARED", "dependency_manifest", DOC / "文件来源与校验.json", LIT,
     "project-level provenance manifest for literature files"),
]

REPORT_NAMES = [
    "02_论文主题与具体研究问题.md", "04_OARP-Replan精读_问题与机制.md",
    "06_TRACE全文精读与严格核查.md", "42_三种基线适配审查与冻结说明_20261012.md",
    "59_文献覆盖与基线复现台账_20261016.md", "61_对比基线总表与四种经典方法适配成本_20261016.md",
    "69_连续执行历史共同预算比较结果_20261016.md", "70_旧计划热启动整体对照结果_20261017.md",
    "71_真实执行历史下固定范围对照结果_20261017.md", "72_初始修复候选保留机制验证_20261017.md",
    "73_约束释放与扩大范围规则离线核验_20261017.md", "74_先局部后整体共同预算验证_20261017.md",
    "00_阅读入口.md",
]


def main():
    rows, file_rows = [], []
    missing = []
    for method_id, role, source, dest_root, why in GROUPS:
        if not source.exists():
            missing.append(str(source))
            continue
        members = files_under(source)
        if source.is_file():
            targets = [(source, dest_root / source.name)]
        else:
            targets = [(p, dest_root / source.name / p.relative_to(source)) for p in members]
        for src_file, dst_file in targets:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            s_hash, d_hash = sha256(src_file), sha256(dst_file)
            if s_hash != d_hash:
                raise SystemExit(f"copy mismatch: {src_file}")
            file_rows.append({
                "method_id": method_id, "role": role,
                "source_path": str(src_file), "source_bytes": src_file.stat().st_size,
                "source_sha256": s_hash,
                "copy_path": str(dst_file.relative_to(OUT)), "copy_bytes": dst_file.stat().st_size,
                "copy_sha256": d_hash, "verified_equal": True,
            })
        rows.append({
            "method_id": method_id, "role": role, "source_root": str(source),
            "copy_root": str(dest_root.relative_to(OUT)), "files": len(targets),
            "bytes": sum(p.stat().st_size for p in members), "why": why,
        })

    for name in REPORT_NAMES:
        src_file = DOC / name
        if not src_file.exists():
            missing.append(str(src_file))
            continue
        dst_file = OUT / "sources" / "reports_referenced" / name
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        s_hash, d_hash = sha256(src_file), sha256(dst_file)
        if s_hash != d_hash:
            raise SystemExit(f"copy mismatch: {src_file}")
        file_rows.append({
            "method_id": "EVIDENCE", "role": "referenced_report",
            "source_path": str(src_file), "source_bytes": src_file.stat().st_size,
            "source_sha256": s_hash,
            "copy_path": str(dst_file.relative_to(OUT)), "copy_bytes": dst_file.stat().st_size,
            "copy_sha256": d_hash, "verified_equal": True,
        })
    rows.append({"method_id": "EVIDENCE", "role": "referenced_report",
                 "source_root": str(DOC), "copy_root": "sources/reports_referenced",
                 "files": len(REPORT_NAMES), "bytes": sum((DOC / n).stat().st_size for n in REPORT_NAMES
                                                          if (DOC / n).exists()),
                 "why": "the numbered reports this round cites as evidence"})

    (OUT / "manifests").mkdir(exist_ok=True)
    payload = {
        "generated_by": "tmp/stage_a_copy.py",
        "src_root": str(SRC), "cstar_root": str(CSTAR),
        "copy_policy": "copy2 (bytes + mtime), no hardlink/junction/symlink; __pycache__ excluded",
        "files": len(file_rows),
        "total_bytes": sum(r["copy_bytes"] for r in file_rows),
        "entries": file_rows,
        "missing_sources": missing,
    }
    (OUT / "manifests" / "source_copy_sha256.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    with open(OUT / "inventory.csv", "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["method_id", "role", "source_root", "copy_root",
                                                "files", "bytes", "why"])
        writer.writeheader()
        writer.writerows(rows)

    # re-read every source afterwards: the protection baseline for the closing check
    protect = {r["source_path"]: r["source_sha256"] for r in file_rows}
    (OUT / "manifests" / "protected_sources_before.json").write_text(
        json.dumps({"count": len(protect), "sha256": protect}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"groups={len(rows)} files={len(file_rows)} bytes={payload['total_bytes']}")
    if missing:
        print("MISSING:")
        for item in missing:
            print("  ", item)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
