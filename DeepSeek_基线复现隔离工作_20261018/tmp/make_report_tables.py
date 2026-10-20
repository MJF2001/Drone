"""Generate reports/微图结果表.md from the saved artifacts (read-only on results).

This is a reporting helper: it never starts a planner.  It reads
``artifacts/runs/micro_runs.json`` and ``artifacts/runs/exact_micro.json`` and
renders the tables used by ``reports/本轮复现与适配报告.md``.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
METHODS = ["P2_MULTI", "OARP_CORE2", "TREE_MST", "PPCPP_CORE4", "EPSILON_STAR", "CSTAR"]
SHORT = {"P2_MULTI": "P2", "OARP_CORE2": "OARP", "TREE_MST": "MST",
         "PPCPP_CORE4": "PPCPP", "EPSILON_STAR": "ε*", "CSTAR": "C*"}


def main():
    runs = json.loads((OUT / "artifacts" / "runs" / "micro_runs.json").read_text(encoding="utf-8"))
    exact = {row["case_id"]: row for row in
             json.loads((OUT / "artifacts" / "runs" / "exact_micro.json").read_text(encoding="utf-8"))["rows"]}
    rows = {(row["case_id"], row["method_id"]): row for row in runs["rows"]}
    cases = sorted({row["case_id"] for row in runs["rows"]})

    lines = ["# 微图结果表（由 tmp/make_report_tables.py 生成，请勿手改）", "",
             f"运行批次 `{runs['stamp']}`，{runs['cases']} 个微图 × {len(runs['methods'])} 个方法 "
             f"= {len(runs['rows'])} 次调用。",
             "",
             "**这不是性能排名。** 微图只用于正确性与代价口径核验；"
             "步数列只说明“在这个小例子上离精确最优多远”。", ""]

    # ---- completeness of execution
    lines += ["## 1. 执行完整性", "",
              "| 项目 | 数值 |", "|---|---|"]
    lines.append(f"| 调用总数 | {len(runs['rows'])} |")
    lines.append(f"| 适配器抛出异常 | {len(runs['failures'])} |")
    statuses = {}
    for row in runs["rows"]:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    for status, count in sorted(statuses.items(), key=lambda item: -item[1]):
        lines.append(f"| status = `{status}` | {count} |")
    legal = sum(1 for row in runs["rows"]
                if not ({"wrong_start", "missing_return", "illegal_step",
                         "collision_or_out_of_bounds"} & set(row["audit"]["errors"])))
    lines.append(f"| 移动合法（四邻接、避障、起终点正确） | {legal}/{len(runs['rows'])} |")
    complete = sum(1 for row in runs["rows"] if row["audit"]["coverage_complete"])
    lines.append(f"| 覆盖完整 | {complete}/{len(runs['rows'])} |")
    lines.append("")

    # ---- steps vs exact
    lines += ["## 2. 步数 vs 精确最优", "",
              "`opt` 是 `tests/exact_reference.py` 的独立精确最优（状态空间 "
              "`(当前位置, 已覆盖目标掩码)` 上的 BFS）。`-` 表示环境不可行或该实例未精确求解。", ""]
    header = "| 实例 | opt | " + " | ".join(SHORT[m] for m in METHODS) + " |"
    lines += [header, "|" + "---|" * (len(METHODS) + 2)]
    for case_id in cases:
        answer = exact.get(case_id, {})
        optimum = answer.get("steps") if answer.get("status") == "optimal" else None
        cells = []
        for method in METHODS:
            row = rows.get((case_id, method))
            if row is None:
                cells.append("—")
            elif row["route_steps"] is None:
                cells.append("`" + row["status"] + "`")
            else:
                cells.append(str(row["route_steps"]))
        lines.append(f"| {case_id} | {optimum if optimum is not None else '—'} | "
                     + " | ".join(cells) + " |")
    lines.append("")

    # ---- gap to exact, per method
    lines += ["## 3. 与精确最优的比值（仅精确可解实例）", "",
              "只用 `status='optimal'` 且方法给出完整合法路线的实例；比值 = 方法步数 / 最优步数。", "",
              "| 方法 | 实例数 | 中位比值 | 最大比值 | 恰好最优的实例数 |",
              "|---|---|---|---|---|"]
    for method in METHODS:
        ratios = []
        best = 0
        for case_id in cases:
            answer = exact.get(case_id, {})
            if answer.get("status") != "optimal":
                continue
            row = rows.get((case_id, method))
            if row is None or row["route_steps"] is None:
                continue
            if not row["audit"]["coverage_complete"]:
                continue
            ratios.append(row["route_steps"] / answer["steps"])
            if row["route_steps"] == answer["steps"]:
                best += 1
        if not ratios:
            lines.append(f"| {SHORT[method]} | 0 | — | — | — |")
            continue
        ratios.sort()
        median = ratios[len(ratios) // 2] if len(ratios) % 2 else \
            (ratios[len(ratios) // 2 - 1] + ratios[len(ratios) // 2]) / 2
        lines.append(f"| {SHORT[method]} | {len(ratios)} | {median:.3f} | {max(ratios):.3f} | {best} |")
    lines.append("")

    # ---- fallback and termination
    lines += ["## 4. 保底使用与终止方式", "",
              "| 方法 | 使用共同保底 | 自然结束 | 截断/其余 |", "|---|---|---|---|"]
    for method in METHODS:
        subset = [row for row in runs["rows"] if row["method_id"] == method]
        fallback = sum(1 for row in subset if row["fallback_used"])
        natural = sum(1 for row in subset if row["termination"].get("natural"))
        lines.append(f"| {SHORT[method]} | {fallback}/{len(subset)} | {natural}/{len(subset)} | "
                     f"{len(subset) - natural}/{len(subset)} |")
    lines.append("")
    lines.append("注：`environment_infeasible` 与 `input_precondition_unmet` 会计入"
                 "“截断/其余”，因为这不是自然完成。")
    lines.append("")

    # ---- stage timing availability
    lines += ["## 5. 阶段计时是否可用（不是耗时比较）", "",
              "| 方法 | 有逐阶段耗时 | 说明 |", "|---|---|---|"]
    for method in METHODS:
        subset = [row for row in runs["rows"] if row["method_id"] == method]
        instrumented = [row for row in subset
                        if len([key for key in row["stage_seconds"]
                                if not key.startswith("_")]) > 1]
        note = {
            "P2_MULTI": "P2 自带的 `events` 提供真实分段时刻",
            "OARP_CORE2": "只有总秒数，无阶段切分（缺失，不推断）",
            "TREE_MST": "只有总秒数（缺失，不推断）",
            "PPCPP_CORE4": "只有总秒数（缺失，不推断）",
            "EPSILON_STAR": "MAPS 构造 / ETM / 返航分别计时",
            "CSTAR": "见其适配说明",
        }[method]
        lines.append(f"| {SHORT[method]} | {len(instrumented)}/{len(subset)} | {note} |")
    lines.append("")

    # ---- deferred handling
    deferred_cases = sorted({row["case_id"] for row in runs["rows"] if row["deferred_at_start"]})
    lines += ["## 6. 暂缓目标（障碍遮挡、不删除、不计完成）", "",
              f"含暂缓目标的实例：{', '.join(deferred_cases) if deferred_cases else '无'}。", ""]
    for case_id in deferred_cases:
        subset = [row for row in runs["rows"] if row["case_id"] == case_id]
        touched = sum(1 for row in subset if row["audit"]["deferred_visited"])
        credited = sum(1 for row in subset
                       if set(map(tuple, row["audit"]["covered_physical"])) &
                       set(map(tuple, row["audit"]["deferred_untouched"])))
        lines.append(f"- `{case_id}`：{len(subset)} 次调用中，飞越暂缓格 {touched} 次，"
                     f"把暂缓格计入覆盖 {credited} 次。")
    lines.append("")

    target = OUT / "reports" / "微图结果表.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {target} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
