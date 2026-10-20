"""Copy the read-only sources this round needs into NEW/sources, with hashes.

Nothing is written outside NEW.  No hard link, junction or symlink is used: every
file is copied with ``shutil.copy2`` and both sides are hashed.

Layout produced::

    sources/reference_tree/   frozen v2 + PPCPP candidate + pinned deps
    sources/v01/              sealed v0.1 src/  (bootstrap, model glue, audit)
    sources/v02/              revision_v0.2 src_v02/
    sources/v03/              revision_v0.3 src_v03/
    sources/cases/            the 10 real continuous-history states (+ provenance)
    sources/micro/            the 17 micro fixtures (preflight input reference)
    sources/docs/             the numbered reports and handoff documents read this round

Writes ``manifests/source_copy.json`` with per-file source/copy hash pairs.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
WORKSPACE = NEW.parent
OLD = WORKSPACE / "DeepSeek_基线复现隔离工作_20261018"
SRC = WORKSPACE / ".remote_Drone"
DIAG = SRC / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010" / "continuous_history_diagnostics"
DOC = SRC / "研究方案_剩余覆盖重规划_20261009" / "论文资料汇总_三篇文献与论文主题_20261009"

SOURCES = NEW / "sources"

GROUPS = [
    ("frozen_v2", OLD / "sources" / "reference_tree", SOURCES / "reference_tree",
     "frozen v2 bundle, PPCPP candidate, pinned numpy/pyscipopt/glns"),
    ("v01_src", OLD / "src", SOURCES / "v01", "sealed v0.1 planner glue"),
    ("v02_src", OLD / "revision_v0.2" / "src_v02", SOURCES / "v02", "revision v0.2 modules"),
    ("v03_src", OLD / "revision_v0.3" / "src_v03", SOURCES / "v03", "revision v0.3 modules"),
    ("cases", DIAG / "preparation_verification_v0.1_20261016" / "cases",
     SOURCES / "cases", "authoritative post-event states for the 10 development snapshots"),
    ("case_manifest", DIAG / "preparation_verification_v0.1_20261016" / "sha256.json",
     SOURCES / "cases_manifest", "hash manifest of the verified case set"),
    ("case_report", DIAG / "preparation_verification_v0.1_20261016" / "report_record.json",
     SOURCES / "cases_manifest", "record of what the verification stage checked"),
    ("case_summary", DIAG / "preparation_verification_v0.1_20261016" / "summary.json",
     SOURCES / "cases_manifest", "summary of the verification stage"),
    ("replay_cases", DIAG / "saved_initial_route_replay_v0.1_20261016",
     SOURCES / "replay_cases", "independent replay copy, used only to confirm identity"),
    ("micro", OLD / "tests" / "fixtures" / "cases", SOURCES / "micro",
     "17 micro fixtures carried over"),
]

DOC_NAMES = [
    "42_三种基线适配审查与冻结说明_20261012.md",
    "59_文献覆盖与基线复现台账_20261016.md",
    "61_对比基线总表与四种经典方法适配成本_20261016.md",
    "67_连续执行历史开发验证协议与输入预检_20261016.md",
    "68_连续执行初始计划准备与事件状态核验_20261016.md",
    "69_连续执行历史共同预算比较结果_20261016.md",
    "70_旧计划热启动整体对照结果_20261017.md",
    "71_真实执行历史下固定范围对照结果_20261017.md",
    "72_初始修复候选保留机制验证_20261017.md",
    "73_约束释放与扩大范围规则离线核验_20261017.md",
    "74_先局部后整体共同预算验证_20261017.md",
]

ROOT_DOCS = [
    ("research_reorder", SRC / "研究思路重整_底层路径规划优先_待用户审查_20261018.md",
     "the user-approved research order"),
    ("src_agents", SRC / "AGENTS.md", "source repository entry rules"),
    ("v03_acceptance", WORKSPACE / "主会话验收_DeepSeek_20261018" / "v0.3阶段验收结论.md",
     "v0.3 stage acceptance conclusion"),
    ("v02_acceptance", WORKSPACE / "主会话验收_DeepSeek_20261018" / "v0.2复核结论与最小修订清单.md",
     "v0.2 review findings"),
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def files_under(root):
    if root.is_file():
        return [root]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            out.append(Path(dirpath) / name)
    return out


def main():
    entries = []
    missing = []
    for group, source, dest, why in GROUPS:
        if not source.exists():
            missing.append(str(source))
            continue
        members = files_under(source)
        # ``dest`` is the FINAL directory; files keep their path relative to the
        # source root rather than gaining a second copy of the source's own name
        pairs = ([(source, dest / source.name)] if source.is_file()
                 else [(p, dest / p.relative_to(source)) for p in members])
        for src_file, dst_file in pairs:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            a, b = sha256(src_file), sha256(dst_file)
            if a != b:
                raise SystemExit(f"copy mismatch: {src_file}")
            entries.append({"group": group, "why": why,
                            "source": str(src_file), "source_bytes": src_file.stat().st_size,
                            "source_sha256": a,
                            "copy": str(dst_file.relative_to(NEW)),
                            "copy_sha256": b})

    docs = SOURCES / "docs"
    for name in DOC_NAMES:
        src_file = DOC / name
        if not src_file.is_file():
            missing.append(str(src_file))
            continue
        dst = docs / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst)
        a, b = sha256(src_file), sha256(dst)
        if a != b:
            raise SystemExit(f"copy mismatch: {src_file}")
        entries.append({"group": "docs", "why": "report read this round",
                        "source": str(src_file), "source_bytes": src_file.stat().st_size,
                        "source_sha256": a, "copy": str(dst.relative_to(NEW)),
                        "copy_sha256": b})

    for group, src_file, why in ROOT_DOCS:
        if not src_file.is_file():
            missing.append(str(src_file))
            continue
        dst = docs / src_file.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst)
        a, b = sha256(src_file), sha256(dst)
        if a != b:
            raise SystemExit(f"copy mismatch: {src_file}")
        entries.append({"group": group, "why": why,
                        "source": str(src_file), "source_bytes": src_file.stat().st_size,
                        "source_sha256": a, "copy": str(dst.relative_to(NEW)),
                        "copy_sha256": b})

    payload = {
        "generated_by": "tools/stage_copy.py",
        "policy": "copy2, no hard link / junction / symlink, __pycache__ excluded",
        "workspace": str(WORKSPACE),
        "files": len(entries),
        "total_bytes": sum(entry["source_bytes"] for entry in entries),
        "entries": entries,
        "missing": missing,
    }
    target = NEW / "manifests" / "source_copy.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"copied {len(entries)} files, {payload['total_bytes']/1e6:.1f} MB -> {target}")
    if missing:
        print("MISSING:")
        for item in missing:
            print("  ", item)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
