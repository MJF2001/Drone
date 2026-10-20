"""Interface micro-runs: the revised core through the unified request/result shapes.

Four calls only (two maps x two credit modes), all logged.  This exists to show the
revision is not a stand-alone script: it returns the shared result row, the shared
auditor accepts or rejects the route, and the mode difference is visible end to end.

Run:  python -B -X utf8 tools/run_interface.py
"""
import csv
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import adapter  # noqa: E402
from problem import PlanRequest, Termination  # noqa: E402

LEDGER = NEW / "logs" / "interface_ledger.csv"
ART = NEW / "artifacts"
FIELDS = ["run_id", "case_id", "mode", "status", "natural", "steps", "audit_valid",
          "coverage_complete", "tasks", "line6", "line5", "escapes", "terminal",
          "credit_mode"]


def rect(x0, y0, w, h):
    return frozenset((x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h))


def cases():
    out = []
    free = rect(0, 0, 4, 4)
    out.append(("i4x4_open", dict(
        free=free, published_targets=free, covered=frozenset(), current=(0, 0),
        base=(0, 0), old_route=(), remaining_resource=None)))

    free = rect(0, 0, 6, 4) - {(2, 2)}
    targets = free - {(5, 3)}                     # one published target is blocked
    out.append(("i6x4_ledger", dict(
        free=free, published_targets=free, covered=frozenset({(0, 0), (0, 1)}),
        current=(0, 1), base=(0, 1),
        old_route=((0, 1), (1, 1), (2, 1), (3, 1)), remaining_resource=400)))
    return out


def main():
    ART.mkdir(parents=True, exist_ok=True)
    rows, details = [], []
    for case_id, spec in cases():
        request = PlanRequest(case_id=case_id, seed=20261018,
                              termination=Termination(time_limit_seconds=30.0), **spec)
        for mode in ("task", "transit"):
            result = adapter.run(request, mode=mode)
            row = result.as_row(request)
            engine = result.meta["engine"]
            entry = {
                "run_id": f"IFACE:{case_id}:{mode}", "case_id": case_id, "mode": mode,
                "status": row["status"], "natural": row["termination"]["natural"],
                "steps": row["route_steps"], "audit_valid": row["audit"]["valid"],
                "coverage_complete": row["audit"]["coverage_complete"],
                "tasks": engine["tasks"],
                "line6": engine["rules"].get("line6_task_here", 0),
                "line5": engine["rules"].get("line5_up_down_unexplored", 0),
                "escapes": engine["extremum_escapes"],
                "terminal": engine["terminal"], "credit_mode": engine["credit_mode"],
            }
            rows.append(entry)
            details.append({"entry": entry, "request": request.describe(),
                            "audit": row["audit"], "route": row["route"],
                            "maps": result.meta["maps"],
                            "stage_seconds": result.stage_seconds})
            print(json.dumps(entry, ensure_ascii=False))

    with open(LEDGER, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (ART / "interface_runs.json").write_text(
        json.dumps({"runs": details, "planner_calls": len(rows)}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    lines = ["# 统一接口微跑（4 次调用）", "",
             "| run_id | 模式 | 状态 | 自然终止 | 步数 | 审计合法 | 覆盖完整 | 作业数 | line6 | line5 | 逃逸 |",
             "|---|---|---|---|---:|---|---|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| `{row['run_id']}` | {row['mode']} | {row['status']} | "
                     f"{row['natural']} | {row['steps']} | {row['audit_valid']} | "
                     f"{row['coverage_complete']} | {row['tasks']} | {row['line6']} | "
                     f"{row['line5']} | {row['escapes']} |")
    lines.append("")
    (NEW / "reports" / "接口微跑_结果.md").write_text("\n".join(lines), encoding="utf-8")
    print("planner calls:", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
