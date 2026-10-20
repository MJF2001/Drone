"""Freeze the protocol, the method configuration and the run plan.

Nothing is executed here.  Everything the round will run is decided before the 24
planned runs: cases, seeds, soft limit, hard watchdog, control-iteration cap,
control mode, cost parameters, tie-breaking, RNG usage, status map and call budget.
"""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from adapters import registry  # noqa: E402

PROTOCOL = NEW / "protocol"
SEEDS = (20261018, 20261019)
SOFT_LIMIT = 10.0
HARD_LIMIT = 15.0
MAX_STEPS = 20000
BUDGET = {"integration": 24, "boundary": 48, "defect": 24, "total": 96}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    cases = json.loads((PROTOCOL / "cases.json").read_text(encoding="utf-8"))["cases"]
    plan = []
    order = 0
    for case in cases:
        for seed in SEEDS:
            order += 1
            plan.append({
                "plan_id": f"INT:{case['case_id']}:{seed}",
                "run_id": f"INT:{case['case_id']}:{seed}",
                "kind": "integration",
                "order_index": order,
                "case_id": case["case_id"],
                "method_id": registry.METHOD_ID,
                "seed": seed,
                "soft_limit_seconds": SOFT_LIMIT,
                "hard_limit_seconds": HARD_LIMIT,
                "max_control_iterations": MAX_STEPS,
                "expected_status": case["expected"].get("status", ""),
            })
    write_csv(PROTOCOL / "planned_runs.csv", plan,
              list(plan[0].keys()))

    description = registry.describe()
    protocol = {
        "round": "epsilon_mechanism_and_interface_integration_20261018",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "method_id": registry.METHOD_ID,
            "core_version": description["core_version"],
            "adapter_version": description["adapter_version"],
            "adaptation_class": description["adaptation_class"],
            "not_claimed": "not a complete reproduction of the preprint; the paper's "
                           "continuous motion and continuous-time feedback are not modelled",
        },
        "task_semantics": {
            "pending": "Q = (P - C) and F, with P published, C the real coverage history, F free",
            "deferred": "D = (P - C) - F; kept, never counted as completed, never flown into",
            "motion": "four-neighbour unit steps over F only",
            "coverage": "arriving on a pending target covers it physically (transit counts)",
            "history": "C is real and never reset for this round; covered and non-target free "
                       "cells stay passable",
            "end": "the route must end at the base",
            "resource": "route_steps must fit the remaining budget when one is given",
        },
        "two_ledgers": {
            "control": "MAPS state; U means control-pending, not physically uncollected; "
                       "updated only when the ETM tasks a cell in WT",
            "physical": "recomputed by the independent auditor from the saved route",
            "tasking": "a logical task updates control state only; it adds no time, steps "
                       "or energy, and re-visiting a cell never counts as a new completion",
        },
        "timing": {
            "public_call": "from the adapter entry to the finished pre-return audit; covers "
                           "input checks, MAPS construction, the ETM loop, every connector "
                           "call, the return leg and the audit",
            "ledger": "the two-phase ledger write and its fsync happen outside the measured "
                      "algorithm time; the registry records the outer wall time separately",
            "process": "the subprocess start-up is measured by the parent and reported apart",
            "event_times": "all event times are relative to the same public entry",
        },
        "deadline": {
            "soft_limit_seconds": SOFT_LIMIT,
            "hard_watchdog_seconds": HARD_LIMIT,
            "max_control_iterations": MAX_STEPS,
            "checks": "before MAPS, every control iteration, before and after each connector "
                      "call, before the return leg, during the return, and before the audit",
            "candidate_boundary": "generated -> audited -> accepted; a route whose audit "
                                  "finishes after the deadline is diagnostic only",
            "semantics": "cooperative; a single BFS row may overrun slightly and is reported",
        },
        "parameters": description["parameters"],
        "tie_breaking": {
            "rng": "random.Random(seed), created once per call",
            "rng_use": ["choice among equipotential coarse blocks at a level",
                        "choice of an unexplored cell inside the selected block",
                        "choice among equal-cost waypoint candidates of Eq. (5)"],
            "deterministic_order": "waypoint sets and blocks are sorted before any choice",
            "initial_heading": None,
            "cost_units": "travel_cost per step, turn_cost per degree from the heading; "
                          "90 degrees therefore costs 90 travel units",
        },
        "status_map": {
            "finished": "natural FN, route legal, complete, returned, within resource",
            "finished_with_safety_limit": "artificial stop (iteration cap / state cycle / no "
                                          "progress) but a legal complete route was audited "
                                          "before the deadline",
            "deadline_before_complete_route": "no route was accepted before the deadline",
            "environment_infeasible": "base or a pending target is unreachable from the start",
            "input_precondition_unmet": "the request contradicts the model",
            "resource_exceeded": "legal and complete but the route exceeds the budget",
            "coverage_incomplete": "the route does not visit every pending target",
        },
        "stop_rules": {
            "per_call": "soft deadline, hard watchdog, control-iteration cap",
            "batch": "stop if a semantic violation appears in the integration batch",
            "round": "stop at 96 full planner calls or at any unresolved source problem",
        },
        "call_budget": BUDGET,
        "planned": {"cases": len(cases), "seeds": list(SEEDS), "runs": len(plan),
                    "soft_limit_seconds": SOFT_LIMIT, "hard_limit_seconds": HARD_LIMIT},
        "not_in_this_round": [
            "no development map, no 300-run comparison, no other method",
            "no holdout, no parameter sweep, no second control-frequency version",
            "no connector optimisation",
            "Remark 3.2 flood fill stays unimplemented",
        ],
    }
    (PROTOCOL / "protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=1), encoding="utf-8")

    method_config = {
        "method": description,
        "fixed": {"control_mode": "task", "travel_cost": 1.0, "turn_cost": 1.0,
                  "turn_cost_units": "per degree", "max_control_iterations": MAX_STEPS,
                  "initial_heading": None},
        "reused_protections": {
            "input": "sources/v01/problem.py (validate_inputs) through src/inputs.py, with "
                     "one documented re-admission: resource 0 with an empty task at the base",
            "deadline": "sources/v02/deadline.py",
            "finalize": "sources/v03/finalize.py",
            "grading": "sources/v03/grading.py",
            "audit": "sources/v01/audit_independent.py",
            "connector": "sources/v01/common_geometry.py",
            "ledger": "src/adapters/registry.py (local copy of the v0.3 two-phase recorder)",
        },
        "not_implemented": ["Remark 3.2 flood fill (not needed on a published map)",
                            "continuous motion / continuous-time feedback",
                            "physics-based forbidden buffer (radius 0 here)"],
        "evidence_strength": {
            "kept": "tiling rule, potentials, neighbourhoods, Algorithm 1 branches, Eq. (5)",
            "adapted": "four-neighbour steps, graph distance, supercover reachability, "
                       "Q-only positive potential, return leg",
            "interpretation": "7x5 continuation of stopped blocks, 9x3 single-axis split",
            "unknown": "the paper gives no numeric travel/turn cost",
        },
    }
    (PROTOCOL / "method_config.json").write_text(
        json.dumps(method_config, ensure_ascii=False, indent=1), encoding="utf-8")

    test_plan = f"""# 测试与调用计划（冻结）

## 分类与上限

| 分类 | 上限 | 内容 |
|---|---:|---|
| 预定微图集成 | 24 | 12 个案例 x 2 个种子（`protocol/planned_runs.csv`） |
| 边界测试中的完整调用 | 48 | 假时钟截止 4 项、审核注入 1 项、真实极小预算 1 项、空任务/资源 3 项、人工截断 2 项、账本故障（mock 单独计） |
| 定位缺陷与最小修复复验 | 24 | 冻结前的冒烟调用与修复后复验 |
| 合计 | 96 | 不被取代的调用一律登记 |

纯函数测试（层级、势场、邻域、式(5)、输入校验、状态映射）不执行完整 `run`，
不计入完整调用；`registry.run` 或 `adapter.run` 每执行一次计一次。

## 只读复核与可写测试分开

- `verify.py`：只读，不启动规划器、不追加账本；
- `tests/test_core_pure.py`：纯函数，可反复运行；
- `tests/test_boundaries.py`：会追加账本，运行前请确认预算。

## 边界测试清单

1. 假时钟：MAPS 跨截止、连接器跨截止、审核跨截止、截止前候选正常接受；
2. 空任务返航：资源 0 / 恰够 / 不足；
3. 审核入口注入 50 ms，`adapter_call` 随之增加 >= 0.04 s；
4. 真实极小时间预算（1e-9 s）确认真实时钟链路；
5. 人工截断（步数上限）不标自然 FN；
6. 账本：start 写失败规划器零调用、end 写失败上报、孤立 start 可识别、前缀封存。
"""
    (PROTOCOL / "test_plan.md").write_text(test_plan, encoding="utf-8")

    hashes = {
        "protocol.json": sha256(PROTOCOL / "protocol.json"),
        "method_config.json": sha256(PROTOCOL / "method_config.json"),
        "cases.json": sha256(PROTOCOL / "cases.json"),
        "planned_runs.csv": sha256(PROTOCOL / "planned_runs.csv"),
        "test_plan.md": sha256(PROTOCOL / "test_plan.md"),
        "sources": registry.source_digest()["files"],
        "source_sha256": registry.source_digest()["sha256"],
    }
    (PROTOCOL / "sha256.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"frozen {PROTOCOL}")
    print(f"planned runs: {len(plan)}  soft={SOFT_LIMIT}s hard={HARD_LIMIT}s")
    print("source digest:", hashes["source_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
