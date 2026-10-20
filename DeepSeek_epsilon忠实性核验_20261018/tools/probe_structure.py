"""Structural probe: MAPS levels and neighbourhoods, old vs new, against the paper.

No planner is started: the probe only constructs tilings and potential surfaces.

For each test map it prints/records
  * the expected structure derived by hand from the paper's rule,
  * what the previous implementation produced (imported from ``sources/v02_epsilon_core``
    under the alias ``maps_old``),
  * what the revised implementation produces,
  * partition and neighbourhood assertions.

Run:  python -B -X utf8 tools/probe_structure.py
"""
import importlib.util
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from maps_faithful import MAPS, check_partition  # noqa: E402

OLD_PATH = NEW / "sources" / "v02_epsilon_core" / "maps.py"


def load_old():
    spec = importlib.util.spec_from_file_location("maps_old", OLD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


def make_map(name, cells, targets=None, covered=None):
    cells = set(cells)
    targets = set(targets if targets is not None else cells)
    covered = set(covered or ())
    return {"name": name, "free": frozenset(cells), "targets": frozenset(targets),
            "covered": frozenset(covered)}


#: expected structure, derived by hand from the paper's rule (see reports/原文对应表.md):
#: "expected_L" number of split rounds, "expected_counts" |T^l| for l = L..1
EXPECTED = {
    "4x4 open": {"L": 1, "counts": {1: 4}, "sizes": {1: [(2, 2)]}},
    "8x8 open": {"L": 2, "counts": {2: 4, 1: 16}, "sizes": {2: [(4, 4)], 1: [(2, 2)]}},
    "6x4 open": {"L": 1, "counts": {1: 4}, "sizes": {1: [(3, 2)]}},
    "9x3 strip": {"L": 2, "counts": {2: 2, 1: 4}, "sizes": {2: [(4, 3), (5, 3)],
                                                         1: [(2, 3), (3, 3)]}},
    "5x5 odd": {"L": 1, "counts": {1: 4}, "sizes": {1: [(2, 2), (2, 3), (3, 2), (3, 3)]}},
    "7x5 mixed": {"L": 2, "counts": {2: 4, 1: 6},
                  "sizes": {2: [(3, 2), (3, 3), (4, 2), (4, 3)],
                            1: [(2, 2), (2, 3), (3, 2), (3, 3)]}},
}


def build_maps():
    maps = []
    maps.append(make_map("4x4 open", rect(0, 0, 4, 4)))
    maps.append(make_map("8x8 open", rect(0, 0, 8, 8)))
    maps.append(make_map("6x4 open", rect(0, 0, 6, 4)))
    maps.append(make_map("9x3 strip", rect(0, 0, 9, 3)))
    maps.append(make_map("5x5 odd", rect(0, 0, 5, 5)))

    free = rect(0, 0, 7, 5) - {(3, 2)}
    targets = set(free) - {(0, 4)}
    maps.append(make_map("7x5 mixed", free, targets, covered={(1, 1)}))
    return maps


def probe_new(case):
    maps = MAPS(case["free"], case["targets"], case["covered"])
    x0 = min(p[0] for p in maps.state)
    x1 = max(p[0] for p in maps.state)
    y0 = min(p[1] for p in maps.state)
    y1 = max(p[1] for p in maps.state)
    problems = check_partition(maps.tilings, x0, x1, y0, y1)
    blocks = {str(level): [(b.x0, b.x1, b.y0, b.y1) for b in blocks]
              for level, blocks in sorted(maps.tilings.items())}
    return {
        "L": maps.L,
        "counts": {level: len(v) for level, v in sorted(maps.tilings.items())},
        "sizes": {level: sorted({(b.width, b.height) for b in v})
                  for level, v in sorted(maps.tilings.items())},
        "blocks": blocks,
        "partition_problems": problems,
        "describe": maps.describe(),
    }


def probe_old(case):
    old = load_old()
    maps = old.MAPS(case["free"], case["targets"], case["covered"])
    counts = {}
    sizes = {}
    for level, blocks in maps.nodes_by_level.items():
        counts[level] = len(blocks)
        sizes[level] = sorted({(b.width, b.height) for b in blocks})
    root = maps.tree["node"]
    return {
        "reported_max_level": maps.max_depth,
        "counts": dict(sorted(counts.items())),
        "sizes": {str(k): v for k, v in sorted(sizes.items())},
        "root_is_a_coarse_cell": any(b.key() == root.key()
                                     for level, blocks in maps.nodes_by_level.items()
                                     if level >= 1 for b in blocks),
        "finest_coarse_level_size": sizes.get(1, []),
        "coarse_levels_built": sorted(maps.E.keys()),
    }


def padded_window(blocks, block):
    """The previous implementation's window: pad both axes by max(width, height)."""
    pad = max(block.width, block.height)
    left, right = block.x0 - pad, block.x1 + pad
    low, high = block.y0 - pad, block.y1 + pad
    return [other for other in blocks
            if not (other.x1 < left or other.x0 > right
                    or other.y1 < low or other.y0 > high)]


def probe_neighbourhood(case):
    """Compare the padded window with the paper's 3x3 coarse-cell window.

    Both are evaluated on the *same* level set (the revised level 1), so the
    comparison isolates the window rule from the level-numbering defect.
    """
    new_maps = MAPS(case["free"], case["targets"], case["covered"])
    if new_maps.L < 1:
        return None
    blocks = new_maps.tilings[1]
    block = max(blocks, key=lambda b: (b.width != b.height, b.width))
    cell = (block.x0, block.y0)
    old_like = padded_window(blocks, block)
    new_like = new_maps.neighbourhood(cell, 1)
    return {
        "cell": list(cell),
        "level": 1,
        "block": [block.x0, block.x1, block.y0, block.y1],
        "block_size": [block.width, block.height],
        "padded_count": len(old_like),
        "paper_count": len(new_like),
        "padded_sizes": sorted({(b.width, b.height) for b in old_like}),
        "paper_sizes": sorted({(b.width, b.height) for b in new_like}),
        "same_set": sorted(b.key() for b in old_like) == sorted(b.key() for b in new_like),
        "paper_is_at_most_3x3": len(new_like) <= 9,
    }


def main():
    cases = build_maps()
    report = {"maps": [], "neighbourhood": []}
    for case in cases:
        expected = EXPECTED[case["name"]]
        old = probe_old(case)
        new = probe_new(case)
        rows = {
            "name": case["name"],
            "expected": expected,
            "old": old,
            "new": new,
            "matches_expected": (new["L"] == expected["L"]
                                 and new["counts"] == expected["counts"]
                                 and {level: {tuple(x) for x in v}
                                      for level, v in new["sizes"].items()}
                                 == {level: {tuple(x) for x in v}
                                     for level, v in expected["sizes"].items()}),
            "partition_ok": not new["partition_problems"],
        }
        report["maps"].append(rows)
        hood = probe_neighbourhood(case)
        if hood:
            report["neighbourhood"].append({"name": case["name"], **hood})

    target = NEW / "artifacts" / "structure_probe.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 结构探针结果（无规划器调用）", "",
             "| 地图 | 期望 L | 期望各层块数 | 旧实现各层块数 | 新实现 L | 新实现各层块数 | 与期望一致 | 分区合法 |",
             "|---|---:|---|---|---:|---|---|---|"]
    for row in report["maps"]:
        lines.append(f"| `{row['name']}` | {row['expected']['L']} | "
                     f"{row['expected']['counts']} | {row['old']['counts']} | {row['new']['L']} | "
                     f"{row['new']['counts']} | {'是' if row['matches_expected'] else '否'} | "
                     f"{'是' if row['partition_ok'] else '否'} |")
    lines += ["", "## 邻居窗口对比（同一层集合：新实现的 Level 1）", "",
              "旧公式是 `pad = max(width, height)` 两轴同时外扩；新实现按论文取 3×3 个粗格。", "",
              "| 地图 | 探针块 | 块尺寸 | 旧公式块数 | 论文 3×3 块数 | 旧块尺寸 | 论文块尺寸 | 同一集合 |",
              "|---|---|---|---:|---:|---|---|---|"]
    for row in report["neighbourhood"]:
        lines.append(f"| `{row['name']}` | {row['block']} | {row['block_size']} | "
                     f"{row['padded_count']} | {row['paper_count']} | {row['padded_sizes']} | "
                     f"{row['paper_sizes']} | {'是' if row['same_set'] else '否'} |")
    lines.append("")
    (NEW / "reports" / "结构探针_结果.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    bad = [row["name"] for row in report["maps"] if not row["matches_expected"] or not row["partition_ok"]]
    print("mismatches:", bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
