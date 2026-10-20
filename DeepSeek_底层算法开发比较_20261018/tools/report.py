"""Build the result tables and the example figures from saved results only.

No planner is started.  Everything is read from ``runs/*/results/*.json`` and the
protocol, so the report can be regenerated without touching the experiment.

Outputs
-------
``reports/tables.md``     all tables, in the order the report cites them
``reports/summary.json``  the same numbers, machine readable
``figures/*.png``         up to three "worse than P2" and three "better than P2"
                          examples, drawn from the saved routes
"""
import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401
import inputs  # noqa: E402
from classify import BUCKETS, classify, in_budget_success  # noqa: E402

RUNS = NEW / "runs"
REPORTS = NEW / "reports"
FIGURES = NEW / "figures"
BATCH_ORDER = ("LONG120", "BUDGET20", "BUDGET1")
METHOD_ORDER = ("P2_MULTI", "TREE_MST", "OARP_CORE2", "PPCPP_CORE4", "EPSILON_STAR")
SHORT = {"P2_MULTI": "P2", "TREE_MST": "MST", "OARP_CORE2": "OARP",
         "PPCPP_CORE4": "PPCPP", "EPSILON_STAR": "eps*"}


def load_results():
    out = []
    for path in sorted(RUNS.glob("*/results/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "runner_exception":
            continue
        payload["bucket"] = classify(payload)[0]
        payload["in_budget_success"] = in_budget_success(payload)
        out.append(payload)
    return out


def load_status():
    rows = {}
    for path in sorted(RUNS.glob("*/status.csv")):
        import csv
        with open(path, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows[row["run_id"]] = row
    return rows


def fmt(value, digits=3):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def table_batch_summary(results, status):
    lines = ["## T1 逐批次×方法汇总", "",
             "`n` 为计划数；`可计入` 指合法且 `within_budget=true`；`自然/截断` 在上述可计入项内区分；"
             "`均值步数`、`均值总时` 只用可计入项。", "",
             "| 批次 | 方法 | n | 已执行 | 可计入 | 自然 | 截断 | 无合法路线 | 前提拒绝 | 环境不可行 | 均值步数 | 均值总时(s) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for batch in BATCH_ORDER:
        for method in METHOD_ORDER:
            rows = [r for r in results if r["batch"] == batch and r["method_id"] == method]
            if not rows:
                continue
            counted = [r for r in rows if r["in_budget_success"]]
            natural = sum(1 for r in counted if r["bucket"] == "natural_complete_valid")
            buckets = Counter(r["bucket"] for r in rows)
            steps = [r["route_steps"] for r in counted if r["route_steps"] is not None]
            times = [r["call_total_seconds"] for r in counted if r["call_total_seconds"]]
            lines.append(
                f"| {batch} | {SHORT[method]} | {len(rows)} | {len(rows)} | {len(counted)} | "
                f"{natural} | {len(counted) - natural} | {buckets['no_valid_route']} | "
                f"{buckets['input_precondition_rejected']} | {buckets['environment_infeasible']} | "
                f"{fmt(statistics.mean(steps) if steps else None, 1)} | "
                f"{fmt(statistics.mean(times) if times else None, 3)} |")
    lines.append("")
    return lines


def table_steps(results):
    lines = ["## T2 逐图步数（两个种子逐项）", "",
             "同一格内为 `种子A/种子B`；`×` 表示该次不可计入（失败或超预算）。", ""]
    header = "| 图 | " + " | ".join(f"{SHORT[m]} L120 | {SHORT[m]} B20 | {SHORT[m]} B1"
                                    for m in METHOD_ORDER) + " |"
    lines += [header, "|" + "---|" * (1 + 3 * len(METHOD_ORDER))]
    for map_id in inputs.MAP_IDS:
        cells = [f"`{map_id.replace('_development','')}`"]
        for method in METHOD_ORDER:
            for batch in ("LONG120", "BUDGET20", "BUDGET1"):
                rows = sorted([r for r in results if r["case_id"] == map_id
                               and r["method_id"] == method and r["batch"] == batch],
                              key=lambda r: r["seed"])
                if not rows:
                    cells.append("— / —")
                    continue
                parts = []
                for row in rows[:2]:
                    parts.append(str(row["route_steps"]) if row["in_budget_success"] else "×")
                while len(parts) < 2:
                    parts.append("—")
                cells.append(" / ".join(parts))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def paired(results):
    """(batch, case, seed) -> {method: row} for in-budget valid results."""
    groups = defaultdict(dict)
    for row in results:
        if row["in_budget_success"]:
            groups[(row["batch"], row["case_id"], row["seed"])][row["method_id"]] = row
    return groups


def table_paired(results):
    groups = paired(results)
    lines = ["## T3 相对 P2 的配对比较（只在双方都可计入的配对里计算）", "",
             "相对差 = (L_method − L_P2) / L_P2，负数表示该方法更短。`基数0` 计入 `P2=0` 的配对，另列。", "",
             "| 批次 | 方法 | 有效配对 | 短/平/长 | 有效配对的均值相对差 | 地图等权均值相对差 | 基数0配对 |",
             "|---|---|---:|---|---:|---:|---:|"]
    for batch in BATCH_ORDER:
        for method in METHOD_ORDER:
            if method == "P2_MULTI":
                continue
            diffs, per_map, zero = [], defaultdict(list), 0
            short = tie = long = 0
            for (b, case, seed), group in groups.items():
                if b != batch or "P2_MULTI" not in group or method not in group:
                    continue
                base = group["P2_MULTI"]["route_steps"]
                value = group[method]["route_steps"]
                if not base:
                    zero += 1
                    continue
                diff = (value - base) / base
                diffs.append(diff)
                per_map[case].append(diff)
                if value < base:
                    short += 1
                elif value == base:
                    tie += 1
                else:
                    long += 1
            map_means = [statistics.mean(v) for v in per_map.values() if v]
            lines.append(
                f"| {batch} | {SHORT[method]} | {len(diffs)} | {short}/{tie}/{long} | "
                f"{fmt(statistics.mean(diffs) if diffs else None, 4)} | "
                f"{fmt(statistics.mean(map_means) if map_means else None, 4)} | {zero} |")
    lines.append("")
    return lines


def table_quality_time(results):
    lines = ["## T4 质量与时间二维表（可计入项）", "",
             "中位步数、中位端到端时间与两者同时给出的位置；不能只按一个指标宣布冠军。", "",
             "| 批次 | 方法 | 中位步数 | 中位总时(s) | 可计入率 | 步数最短次数 |", "|---|---|---:|---:|---:|---:|"]
    for batch in BATCH_ORDER:
        per_method = {}
        for method in METHOD_ORDER:
            rows = [r for r in results if r["batch"] == batch and r["method_id"] == method]
            counted = [r for r in rows if r["in_budget_success"]]
            if not rows:
                continue
            steps = [r["route_steps"] for r in counted if r["route_steps"] is not None]
            times = [r["call_total_seconds"] for r in counted if r["call_total_seconds"]]
            per_method[method] = {
                "median_steps": statistics.median(steps) if steps else None,
                "median_time": statistics.median(times) if times else None,
                "rate": len(counted) / len(rows) if rows else 0.0,
            }
        # count how often each method is the shortest among the counted ones
        groups = paired(results)
        wins = Counter()
        for (b, case, seed), group in groups.items():
            if b != batch:
                continue
            best = min(row["route_steps"] for row in group.values())
            for method, row in group.items():
                if row["route_steps"] == best:
                    wins[method] += 1
        for method in METHOD_ORDER:
            if method not in per_method:
                continue
            info = per_method[method]
            lines.append(f"| {batch} | {SHORT[method]} | {fmt(info['median_steps'], 1)} | "
                         f"{fmt(info['median_time'], 3)} | {fmt(info['rate'], 2)} | {wins[method]} |")
    lines.append("")
    return lines


def table_p2_stages(results):
    lines = ["## T5 P2 的阶段证据（引擎自报 `events`，已剔除父子包含）", "",
             "只统计 P2 的行；`出现次数` 是该阶段有真实计时的记录数，缺插桩的阶段不会被填 0。", "",
             "| 批次 | 阶段 | 出现次数 | 合计秒 | 中位秒 |", "|---|---|---:|---:|---:|"]
    for batch in BATCH_ORDER:
        rows = [r for r in results if r["batch"] == batch and r["method_id"] == "P2_MULTI"]
        values = defaultdict(list)
        for row in rows:
            for name, seconds in (row.get("stage_seconds") or {}).items():
                if name.startswith("engine:") and isinstance(seconds, (int, float)):
                    values[name[len("engine:"):]].append(seconds)
        for name in sorted(values, key=lambda n: -sum(values[n]))[:14]:
            lines.append(f"| {batch} | `{name}` | {len(values[name])} | "
                         f"{fmt(sum(values[name]), 3)} | {fmt(statistics.median(values[name]), 4)} |")
    lines.append("")
    return lines


def examples(results, limit=3):
    """Best/worst paired examples against P2, chosen by a fixed rule.

    Uses every cell where both sides produced a *valid* route, regardless of the
    budget verdict, because the largest gaps sit exactly on the cells where P2
    overran its budget; the budget state is carried along as a column.
    """
    groups = defaultdict(dict)
    for row in results:
        if (row.get("audit") or {}).get("valid"):
            groups[(row["batch"], row["case_id"], row["seed"])][row["method_id"]] = row
    entries = []
    for (batch, case, seed), group in groups.items():
        if batch not in BATCH_ORDER or "P2_MULTI" not in group:
            continue
        base = group["P2_MULTI"]["route_steps"]
        if not base:
            continue
        for method, row in group.items():
            if method == "P2_MULTI":
                continue
            entries.append({"batch": batch, "case_id": case, "seed": seed,
                            "method_id": method, "p2_steps": base,
                            "steps": row["route_steps"],
                            "relative": (row["route_steps"] - base) / base,
                            "run_id": row["run_id"],
                            "p2_within": bool(groups[(batch, case, seed)]["P2_MULTI"]["in_budget_success"]),
                            "method_within": bool(row["in_budget_success"])})
    entries.sort(key=lambda item: (item["relative"], item["case_id"], item["method_id"]))
    # relative = (method - P2) / P2: negative means the method is SHORTER than P2,
    # which is the case P2 loses.  Take the extremes on both sides.
    def pick(candidates):
        chosen, seen = [], set()
        for item in candidates:
            key = (item["case_id"], item["method_id"])
            if key in seen:
                continue
            seen.add(key)
            chosen.append(item)
            if len(chosen) == limit:
                break
        return chosen

    worst_for_p2 = pick([e for e in entries if e["relative"] < 0])
    best_for_p2 = pick([e for e in reversed(entries) if e["relative"] > 0])
    return {"p2_worse": worst_for_p2, "p2_better": best_for_p2}


def draw(entry, results_by_run, path):
    from PIL import Image, ImageDraw
    request = inputs.build_any(entry["case_id"], 120.0, entry["seed"])
    cells = request.free | request.published_targets
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    scale = max(1, min(6, 900 // max(1, max(x1 - x0 + 1, y1 - y0 + 1))))
    width, height = (x1 - x0 + 1) * scale + 20, (y1 - y0 + 1) * scale + 40
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw_ctx = ImageDraw.Draw(image)

    def box(point):
        x = (point[0] - x0) * scale + 10
        y = (point[1] - y0) * scale + 30
        return x, y, x + scale - 1, y + scale - 1

    for point in request.published_targets:
        draw_ctx.rectangle(box(point), outline=(150, 200, 150))
    for point in request.covered:
        draw_ctx.rectangle(box(point), fill=(200, 220, 245))
    for point in request.free:
        draw_ctx.rectangle(box(point), outline=(235, 235, 235))
    for point in request.published_targets - request.free:
        draw_ctx.rectangle(box(point), fill=(120, 120, 120))
    p2 = results_by_run.get(entry["run_id"].replace(entry["method_id"], "P2_MULTI"))
    if p2 and p2.get("route"):
        points = [((p[0] - x0) * scale + 10 + scale // 2,
                   (p[1] - y0) * scale + 30 + scale // 2) for p in p2["route"]]
        draw_ctx.line(points, fill=(120, 170, 230), width=1)
    method_row = results_by_run.get(entry["run_id"])
    if method_row and method_row.get("route"):
        points = [((p[0] - x0) * scale + 10 + scale // 2,
                   (p[1] - y0) * scale + 30 + scale // 2) for p in method_row["route"]]
        draw_ctx.line(points, fill=(200, 40, 40), width=max(1, scale // 2))
    draw_ctx.text((10, 8), f"{entry['case_id']} seed={entry['seed']} "
                           f"{entry['method_id']} {entry['steps']} vs P2 {entry['p2_steps']}",
                  fill=(0, 0, 0))
    image.save(path)


def table_fallback(results):
    lines = ["## T7 保底来源与覆盖（哪些成绩其实不是该方法自己的路线）", "",
             "`保底` 指该方法最终提交的是共享保底候选（旧路线后缀 / 共同贪心），"
             "不是它自己的核心构造结果。这一列必须和方法名一起读。", "",
             "| 批次 | 方法 | 结果数 | 保底 | 核心 | 核心链路可计速率 | 主要 final_source |",
             "|---|---|---:|---:|---:|---:|---|"]
    for batch in BATCH_ORDER:
        for method in METHOD_ORDER:
            rows = [r for r in results if r["batch"] == batch and r["method_id"] == method]
            if not rows:
                continue
            fallback = [r for r in rows if r.get("fallback_used")]
            core = [r for r in rows if not r.get("fallback_used")]
            core_counted = [r for r in core if r["in_budget_success"]]
            sources = Counter(str(r.get("final_source")) for r in rows)
            top = ", ".join(f"`{name}`×{count}" for name, count in sources.most_common(3))
            lines.append(f"| {batch} | {SHORT[method]} | {len(rows)} | {len(fallback)} | {len(core)} | "
                         f"{len(core_counted)}/{len(core)} | {top} |")
    lines.append("")
    return lines


def table_pairing(results):
    lines = ["## T8 配对覆盖：被排除的配对在哪里", "",
             "`双方可计入` 才是 T3 的分母。P2 超预算的格子会被整对排除，"
             "因此 T3 的结果条件于“P2 在预算内完成”。", "",
             "| 批次 | 图 | 种子 | P2 可计入 | 可配对方法数 | 说明 |", "|---|---|---|---:|---:|---|"]
    groups = defaultdict(dict)
    for row in results:
        groups[(row["batch"], row["case_id"], row["seed"])][row["method_id"]] = row
    for batch in BATCH_ORDER:
        for map_id in inputs.MAP_IDS:
            for seed in sorted({row["seed"] for row in results if row["batch"] == batch}):
                group = groups.get((batch, map_id, seed), {})
                p2 = group.get("P2_MULTI")
                if p2 is None:
                    continue
                ok = bool(p2["in_budget_success"])
                pairs = sum(1 for method in METHOD_ORDER
                            if method != "P2_MULTI" and method in group
                            and ok and group[method]["in_budget_success"])
                note = "" if ok else f"P2 status={p2['status']} total={p2['call_total_seconds']:.1f}s"
                lines.append(f"| {batch} | `{map_id.replace('_development','')}` | {seed} | "
                             f"{'是' if ok else '否'} | {pairs} | {note} |")
    lines.append("")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures", action="store_true")
    args = parser.parse_args(argv or [])

    results = load_results()
    status = load_status()
    groups = paired(results)
    example_info = examples(results)

    lines = ["# 开发比较结果表（由 tools/report.py 生成）", "",
             f"读取 {len(results)} 条保存结果；计划任务 {len(status)} 条。", ""]
    lines += table_batch_summary(results, status)
    lines += table_steps(results)
    lines += table_paired(results)
    lines += table_quality_time(results)
    lines += table_p2_stages(results)
    lines += table_fallback(results)
    lines += table_pairing(results)

    lines += ["## T6 相对 P2 的极端例子（固定规则选取）", "",
              "按配对相对差排序，取 P2 相对更长的最多 3 例和 P2 相对更短的最多 3 例；"
              "同一用例每个方法只出现一次。", "",
              "| 方向 | 图 | 种子 | 方法 | 该方法步数 | P2 步数 | 相对差 |", "|---|---|---|---|---:|---:|---:|"]
    for tag, items in (("P2 更长", example_info["p2_worse"]), ("P2 更短", example_info["p2_better"])):
        for item in items:
            lines.append(f"| {tag} | `{item['case_id'].replace('_development','')}` | {item['seed']} | "
                         f"{SHORT[item['method_id']]} | {item['steps']} | {item['p2_steps']} | "
                         f"{item['relative']:+.4f} |")
    lines.append("")

    (REPORTS / "tables.md").write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "results": len(results),
        "by_batch": {batch: sum(1 for r in results if r["batch"] == batch) for batch in BATCH_ORDER},
        "by_method": dict(Counter(r["method_id"] for r in results)),
        "buckets": dict(Counter(r["bucket"] for r in results)),
        "in_budget_success": sum(1 for r in results if r["in_budget_success"]),
        "status_rows": len(status),
        "states": dict(Counter(row.get("state") for row in status.values())),
        "hard_timeouts": sum(1 for row in status.values()
                             if row.get("termination") == "hard_timeout"),
        "not_started": sum(1 for row in status.values() if row.get("state") == "not_started"),
        "paired_groups": len(groups),
        "examples": example_info,
    }
    (REPORTS / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.figures and results:
        FIGURES.mkdir(exist_ok=True)
        by_run = {row["run_id"]: row for row in results}
        for tag, items in (("p2worse", example_info["p2_worse"]),
                           ("p2better", example_info["p2_better"])):
            for index, item in enumerate(items, 1):
                path = FIGURES / f"{tag}_{index}_{item['case_id']}_{item['method_id']}.png"
                draw(item, by_run, path)
                print("figure:", path.name)

    print(json.dumps({key: summary[key] for key in
                      ("results", "by_batch", "buckets", "in_budget_success",
                       "not_started", "hard_timeouts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
