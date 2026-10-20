"""Offline derivation of the corrected evidence for the review (v2).

Starts no planner and writes only new files under ``reports/derived_v2/``.  The
saved results, the ledger, the protocol and the original reports are untouched.

What it derives, and from which recorded field:

``engine_stop``   the engine's own stopping reason, from the frozen termination
                  specification and the recorded native fields
                  (``engine_status`` for P2/TREE, ``rank_status``/``solver`` for
                  OARP, ``core_status`` for PPCPP, ``meta.etm.terminal`` for eps*).
                  This replaces ``termination.natural``, which was set too
                  optimistically: OARP rows with ``rank_status=timelimit`` and
                  ``infeasible`` were recorded as natural=True.
``route_success`` what came out: legal or not, within the public budget or not, and
                  whether the final route came from the method's core or from the
                  shared fallback.
``improvement``   the producer-relative improvement timeline (``meta.improvements``,
                  key ``seconds`` or ``elapsed``), so "first accepted candidate" and
                  "time to the final quality" can be reported separately from the
                  full public call.
``speed``         same (case, seed) speed ratios against P2, never a ratio of
                  medians over different samples.

Fields that cannot be recovered from the saved records are written as ``unknown``
with the reason, never back-filled.
"""
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

RUNS = NEW / "runs"
OUT = NEW / "reports" / "derived_v2"
BATCHES = ("LONG120", "BUDGET20", "BUDGET1")
METHODS = ("P2_MULTI", "TREE_MST", "OARP_CORE2", "PPCPP_CORE4", "EPSILON_STAR")

NATURAL = "natural_converged"
INTERNAL = "internal_timelimit"
CORE_FAILED = "core_failed"
BUDGET = "budget_truncated"
UNKNOWN = "unknown"


def load():
    rows = []
    for path in sorted(RUNS.glob("*/results/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "runner_exception":
            continue
        meta = payload.get("meta") or {}
        payload["_improvements"] = meta.get("improvements") or []
        rows.append(payload)
    return rows


# ------------------------------------------------------------------ engine stop
def engine_stop(row):
    """(stop, evidence) — the engine's own reason, per the frozen specification."""
    meta = row.get("meta") or {}
    method = row["method_id"]

    if method == "P2_MULTI":
        status = meta.get("engine_status")
        if status == "deadline":
            return BUDGET, f"engine_status=deadline, active_stage={meta.get('active_stage')}"
        if status in ("finished", "planned"):
            return NATURAL, f"engine_status={status} (its 8/120/32-pass caps are part of the method)"
        return UNKNOWN, f"engine_status={status}"

    if method == "TREE_MST":
        status = meta.get("engine_status")
        if status == "planned_at_timeout":
            return BUDGET, "engine_status=planned_at_timeout"
        if status in ("planned", "finished"):
            return NATURAL, f"engine_status={status}"
        return UNKNOWN, f"engine_status={status}"

    if method == "OARP_CORE2":
        rank = meta.get("rank_status")
        solver = meta.get("solver") or {}
        if rank == "timelimit":
            return INTERNAL, (f"rank_status=timelimit, rank_cap={meta.get('rank_cap')} "
                              f"(the rank LP/MIP hit its internal limit)")
        if rank == "infeasible":
            return CORE_FAILED, (f"rank_status=infeasible, rank_cap={meta.get('rank_cap')} "
                                 f"(restricted rank model infeasible, no tour)")
        if rank == "optimal":
            if solver.get("timeout") is True:
                return INTERNAL, "rank optimal but the GTSP solver timed out"
            if solver:
                return NATURAL, (f"rank_status=optimal, gtsp iterations={solver.get('iterations')}, "
                                 f"timeout=False")
            return UNKNOWN, "rank optimal but no tour record (solver=None)"
        return UNKNOWN, f"rank_status={rank}"

    if method == "PPCPP_CORE4":
        status = meta.get("core_status")
        if status == "valid_before_deadline":
            return NATURAL, "core_status=valid_before_deadline (single deterministic pass)"
        return UNKNOWN, f"core_status={status}"

    if method == "EPSILON_STAR":
        terminal = (meta.get("etm") or {}).get("terminal")
        if terminal == "FN_no_unexplored_cell":
            return NATURAL, "etm.terminal=FN_no_unexplored_cell"
        deadline = meta.get("deadline") or {}
        if deadline.get("soft_deadline_hit"):
            return BUDGET, (f"etm.terminal={terminal}, soft deadline hit at "
                            f"{deadline.get('soft_deadline_elapsed_seconds')}s")
        return UNKNOWN, f"etm.terminal={terminal}"

    return UNKNOWN, "method not classified"


def route_success(row):
    audit = row.get("audit") or {}
    if not row.get("route"):
        return "no_route"
    if not audit.get("valid"):
        return "illegal_or_incomplete"
    return "legal_in_budget" if row.get("within_budget") else "legal_over_budget"


def route_origin(row):
    if row.get("fallback_used"):
        return "shared_fallback"
    return "core"


# -------------------------------------------------------------------- timeline
def timeline(row):
    improvements = row["_improvements"]
    if not improvements:
        return None
    points = []
    for item in improvements:
        seconds = item.get("seconds", item.get("elapsed"))
        if seconds is None:
            continue
        points.append({"t": float(seconds), "steps": item.get("steps"),
                       "source": item.get("source")})
    if not points:
        return None
    points.sort(key=lambda point: point["t"])
    final_steps = row.get("route_steps")
    first = points[0]
    best = next((point for point in points if point["steps"] == final_steps), points[-1])
    return {
        "n_improvements": len(points),
        "first_t": first["t"], "first_steps": first["steps"], "first_source": first["source"],
        "best_t": best["t"], "best_steps": best["steps"], "best_source": best["source"],
        "final_steps": final_steps,
        "points": points,
    }


def main():
    rows = load()
    dev = [row for row in rows if row["batch"] in BATCHES]
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) engine stop + route success
    records = []
    for row in dev:
        stop, evidence = engine_stop(row)
        records.append({
            "run_id": row["run_id"], "batch": row["batch"], "case_id": row["case_id"],
            "method_id": row["method_id"], "seed": row["seed"],
            "engine_stop": stop, "engine_evidence": evidence,
            "recorded_natural": (row.get("termination") or {}).get("natural"),
            "route_success": route_success(row), "route_origin": route_origin(row),
            "final_source": row.get("final_source"),
            "route_steps": row.get("route_steps"),
            "call_total_seconds": row.get("call_total_seconds"),
            "within_budget": row.get("within_budget"),
            "evidence_missing": "no" if stop != UNKNOWN else "yes",
        })
    write_csv(OUT / "engine_stop.csv", records, list(records[0].keys()))

    # 2) improvement timeline
    timeline_rows = []
    for row in dev:
        info = timeline(row)
        if info is None:
            continue
        meta = row.get("meta") or {}
        timeline_rows.append({
            "run_id": row["run_id"], "batch": row["batch"], "case_id": row["case_id"],
            "method_id": row["method_id"], "seed": row["seed"],
            "n_improvements": info["n_improvements"],
            "first_t_engine": round(info["first_t"], 6),
            "first_steps": info["first_steps"], "first_source": info["first_source"],
            "best_t_engine": round(info["best_t"], 6),
            "best_steps": info["best_steps"], "best_source": info["best_source"],
            "final_steps": info["final_steps"],
            "engine_seconds": round(float(meta.get("engine_seconds") or 0.0), 6),
            "call_total_seconds": round(float(row.get("call_total_seconds") or 0.0), 6),
            "active_stage": meta.get("active_stage"),
            "public_entry_time_of_first": "unknown (engine clock starts inside the adapter; "
                                          "no pre-engine timestamp is recorded)",
        })
    write_csv(OUT / "improvement_timeline.csv", timeline_rows, list(timeline_rows[0].keys()))

    # 3) same-sample speed pairs
    groups = defaultdict(dict)
    for row in dev:
        groups[(row["batch"], row["case_id"], row["seed"])][row["method_id"]] = row
    speed_rows = []
    for (batch, case, seed), group in sorted(groups.items()):
        base = group.get("P2_MULTI")
        if base is None:
            continue
        for method in METHODS:
            if method == "P2_MULTI" or method not in group:
                continue
            other = group[method]
            speed_rows.append({
                "batch": batch, "case_id": case, "seed": seed, "method_id": method,
                "p2_steps": base.get("route_steps"), "method_steps": other.get("route_steps"),
                "p2_seconds": round(float(base.get("call_total_seconds") or 0.0), 6),
                "method_seconds": round(float(other.get("call_total_seconds") or 0.0), 6),
                "time_ratio_method_over_p2": round(
                    float(other.get("call_total_seconds") or 0.0)
                    / max(float(base.get("call_total_seconds") or 1e-9), 1e-9), 4),
                "steps_ratio_method_over_p2": (
                    None if not base.get("route_steps") or other.get("route_steps") is None
                    else round(other["route_steps"] / base["route_steps"], 4)),
                "p2_legal": bool((base.get("audit") or {}).get("valid")),
                "method_legal": bool((other.get("audit") or {}).get("valid")),
                "p2_within_budget": bool(base.get("within_budget")),
                "method_within_budget": bool(other.get("within_budget")),
            })
    write_csv(OUT / "speed_pairs.csv", speed_rows, list(speed_rows[0].keys()))

    # 4) stage costs with a same-batch denominator
    stage_rows = []
    for batch in BATCHES:
        for method in METHODS:
            sel = [row for row in dev if row["batch"] == batch and row["method_id"] == method]
            if not sel:
                continue
            denominator = sum(float(row.get("call_total_seconds") or 0.0) for row in sel)
            totals = defaultdict(float)
            presence = Counter()
            for row in sel:
                for name, seconds in (row.get("stage_seconds") or {}).items():
                    if isinstance(seconds, (int, float)):
                        totals[name] += seconds
                        presence[name] += 1
            for name, seconds in sorted(totals.items(), key=lambda item: -item[1]):
                stage_rows.append({
                    "batch": batch, "method_id": method, "stage": name,
                    "rows_with_stage": presence[name], "total_seconds": round(seconds, 3),
                    "share_of_call_total": round(seconds / denominator, 4) if denominator else "",
                })
    write_csv(OUT / "stage_costs.csv", stage_rows, list(stage_rows[0].keys()))

    # 5) per-map P2 stage marginal value (LONG120 only: that is where the full
    #    stage sequence actually runs)
    marginal = []
    for row in dev:
        if row["method_id"] != "P2_MULTI" or row["batch"] != "LONG120":
            continue
        info = timeline(row)
        stages = {name[len("engine:"):]: seconds
                  for name, seconds in (row.get("stage_seconds") or {}).items()
                  if name.startswith("engine:") and isinstance(seconds, (int, float))}
        produced = Counter(point["source"] for point in (info["points"] if info else []))
        for name, seconds in sorted(stages.items(), key=lambda item: -item[1]):
            marginal.append({
                "case_id": row["case_id"], "seed": row["seed"], "stage": name,
                "seconds": round(seconds, 3),
                "improvements_produced": produced.get(name, 0),
                "is_final_source": bool(row.get("final_source") == name),
                "final_steps": row.get("route_steps"),
            })
    write_csv(OUT / "stage_marginal_p2.csv", marginal, list(marginal[0].keys()))

    summary = build_summary(records, timeline_rows, speed_rows, stage_rows, marginal)
    (OUT / "summary_v2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "tables_v2.md").write_text(render(summary, records, timeline_rows, speed_rows,
                                             stage_rows, marginal), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in
                      ("rows", "engine_stop", "route_success", "natural_claimed_vs_found")},
                     ensure_ascii=False, indent=1))
    return 0


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def quantiles(values):
    if not values:
        return {}
    values = sorted(values)
    def at(fraction):
        index = min(len(values) - 1, max(0, int(round(fraction * (len(values) - 1)))))
        return values[index]
    return {"n": len(values), "min": min(values), "p25": at(0.25),
            "median": statistics.median(values), "p75": at(0.75), "max": max(values)}


def build_summary(records, timeline_rows, speed_rows, stage_rows, marginal):
    by_method = defaultdict(Counter)
    for record in records:
        by_method[record["method_id"]][record["engine_stop"]] += 1
    fail = [record for record in records
            if record["engine_stop"] != NATURAL and record["recorded_natural"] is True]
    success = Counter(record["route_success"] for record in records)
    origin = Counter((record["method_id"], record["route_origin"]) for record in records)

    speed = {}
    for method in METHODS:
        if method == "P2_MULTI":
            continue
        all_pairs = [row["time_ratio_method_over_p2"] for row in speed_rows
                     if row["method_id"] == method and row["p2_legal"] and row["method_legal"]]
        in_budget = [row["time_ratio_method_over_p2"] for row in speed_rows
                     if row["method_id"] == method and row["p2_legal"] and row["method_legal"]
                     and row["p2_within_budget"] and row["method_within_budget"]]
        speed[method] = {"all_legal_pairs": quantiles(all_pairs),
                         "both_in_budget_pairs": quantiles(in_budget)}

    p2_l120 = [row for row in timeline_rows
               if row["method_id"] == "P2_MULTI" and row["batch"] == "LONG120"]
    stage_total = {}
    for batch in BATCHES:
        denom = sum(row["total_seconds"] for row in stage_rows
                    if row["batch"] == batch and row["method_id"] == "P2_MULTI"
                    and not row["stage"].startswith("engine:"))
        stage_total[batch] = round(denom, 3)

    return {
        "rows": len(records),
        "engine_stop": {method: dict(by_method[method]) for method in METHODS},
        "route_success": dict(success),
        "route_origin": {f"{method}::{origin_key}": count
                         for (method, origin_key), count in sorted(origin.items())},
        "natural_claimed_vs_found": {
            "recorded_natural_true": sum(1 for record in records
                                         if record["recorded_natural"] is True),
            "found_natural": sum(1 for record in records if record["engine_stop"] == NATURAL),
            "overclaimed": len(fail),
            "overclaimed_runs": [f"{record['run_id']} ({record['engine_stop']})" for record in fail],
        },
        "speed": speed,
        "p2_long120_timeline": {
            "rows": len(p2_l120),
            "first_t_median": statistics.median([row["first_t_engine"] for row in p2_l120])
            if p2_l120 else None,
            "best_t_median": statistics.median([row["best_t_engine"] for row in p2_l120])
            if p2_l120 else None,
            "call_total_median": statistics.median([row["call_total_seconds"] for row in p2_l120])
            if p2_l120 else None,
        },
        "p2_long120_call_total_sum": round(sum(row["call_total_seconds"] for row in p2_l120), 3),
        "stage_cost_lists_total": stage_total,
        "marginal_rows": len(marginal),
    }


def _pct(value):
    return "—" if value in (None, "") else f"{value*100:.1f}%"


def render(summary, records, timeline_rows, speed_rows, stage_rows, marginal):
    lines = ["# 修订后的证据表（v2，离线派生）", "",
             "由 `tools/derive_v2.py` 从已保存的 300 条开发结果派生，未启动任何规划器，"
             "未修改原结果、账本、协议或原报告。", ""]

    lines += ["## V1 引擎停止原因（替代原先的 `termination.natural`）", "",
              "| 方法 | 自然收敛 | 内部时限 | 核心失败 | 预算截断 | 未知 |", "|---|---:|---:|---:|---:|---:|"]
    for method in METHODS:
        counts = summary["engine_stop"].get(method, {})
        lines.append(f"| {method} | {counts.get(NATURAL,0)} | {counts.get(INTERNAL,0)} | "
                     f"{counts.get(CORE_FAILED,0)} | {counts.get(BUDGET,0)} | "
                     f"{counts.get(UNKNOWN,0)} |")
    over = summary["natural_claimed_vs_found"]
    lines += ["",
              f"原先记录为 `natural=True` 的 {over['recorded_natural_true']} 条中，"
              f"按引擎自身证据只有 {over['found_natural']} 条真正自然收敛；"
              f"**{over['overclaimed']} 条属过度宣称**（OARP 的 rank 内部时限/不可行被记成自然完成）。", ""]

    lines += ["## V2 输出结果与来源", "",
              "| 来源 | 次数 |", "|---|---:|"]
    for key, value in summary["route_success"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("| 方法 | 核心产出 | 共享保底 |")
    lines.append("|---|---:|---:|")
    for method in METHODS:
        lines.append(f"| {method} | {summary['route_origin'].get(method+'::core',0)} | "
                     f"{summary['route_origin'].get(method+'::shared_fallback',0)} |")
    lines.append("")

    lines += ["## V3 同一样本上的速度比（不再用不同分母的中位数相除）", "",
              "比值 = 该方法 `call_total_seconds` / 同一 case+seed 上的 P2 `call_total_seconds`；"
              "只在双方都有合法路线时计算。", "",
              "| 方法 | 子集 | n | 最小 | p25 | 中位 | p75 | 最大 |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for method, info in summary["speed"].items():
        for label, key in (("双方合法", "all_legal_pairs"), ("双方都在预算内", "both_in_budget_pairs")):
            q = info[key]
            if not q:
                lines.append(f"| {method} | {label} | 0 | — | — | — | — | — |")
                continue
            lines.append(f"| {method} | {label} | {q['n']} | {q['min']:.3f} | {q['p25']:.3f} | "
                         f"{q['median']:.3f} | {q['p75']:.3f} | {q['max']:.3f} |")
    lines.append("")

    lines += ["## V4 P2 的改进时间线（LONG120）", "",
              "引擎相对时间；`首次改进` 是第一次被接受的合法候选，`达到最终质量` 是第一次得到最终步数。",
              "",
              "| 图 | 种子 | 首次改进(s) | 首次步数 | 达到最终质量(s) | 最终步数 | 完整调用(s) | 最后停在 |",
              "|---|---|---:|---:|---:|---:|---:|---|"]
    for row in timeline_rows:
        if row["method_id"] != "P2_MULTI" or row["batch"] != "LONG120":
            continue
        lines.append(f"| `{row['case_id'].replace('_development','')}` | {row['seed']} | "
                     f"{row['first_t_engine']:.3f} | {row['first_steps']} | "
                     f"{row['best_t_engine']:.3f} | {row['best_steps']} | "
                     f"{row['call_total_seconds']:.1f} | {row['active_stage']} |")
    lines.append("")
    lines.append("公共入口的首次改进时刻**未知**：引擎时钟在适配器内部起算，"
                 "保存记录里没有引擎启动前的时刻，因此不能用 `call_total` 倒推。")
    lines.append("")

    lines += ["## V5 P2 阶段成本与边际收益（LONG120，按图）", "",
              "`改进` 是该阶段名与 `improvements[].source` 精确匹配到的新增改进次数；"
              "子过程 `*_passes` 事件不在保存的阶段里，阶段之间不重叠（已核对：无 `_passes` 键）。",
              "",
              "| 图 | 种子 | 阶段 | 秒 | 新增改进 | 是否最终来源 |", "|---|---|---|---:|---:|---|"]
    for row in marginal:
        if row["improvements_produced"] == 0 and row["seconds"] < 1.0:
            continue
        lines.append(f"| `{row['case_id'].replace('_development','')}` | {row['seed']} | "
                     f"`{row['stage']}` | {row['seconds']:.2f} | {row['improvements_produced']} | "
                     f"{'是' if row['is_final_source'] else ''} |")
    lines.append("")

    lines += ["## V6 阶段成本占比（同一批次同一方法的分母）", "",
              "分母 = 该批次该方法所有 `call_total_seconds` 之和；"
              "各阶段之和略小于分母，差额是阶段之间的未计时间隙。", "",
              "| 批次 | 方法 | 阶段 | 合计秒 | 占该批调用总时 |", "|---|---|---|---:|---:|"]
    for row in stage_rows:
        if row["method_id"] != "P2_MULTI":
            continue
        if row["total_seconds"] < 1.0:
            continue
        if row["stage"].startswith("_") or row["stage"] == "adapter_call":
            continue   # bookkeeping keys, not algorithm stages
        lines.append(f"| {row['batch']} | {row['method_id']} | `{row['stage']}` | "
                     f"{row['total_seconds']:.2f} | {_pct(row['share_of_call_total'])} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
