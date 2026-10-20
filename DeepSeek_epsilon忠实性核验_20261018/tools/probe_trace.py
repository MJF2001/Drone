"""Step-by-step trajectory probe: old core vs the two revised modes.

Three arms on the same maps:

``old``      the previous implementation (``sources/v02_epsilon_core`` maps + etm),
             i.e. exactly the code that produced the earlier development results.
``transit``  the revised MAPS/ETM with the previous credit rule (credit on every
             traversed cell).  Isolates the effect of the level/neighbourhood fixes.
``task``     the revised MAPS/ETM with the paper's credit rule (the MAPS learns a
             cell is explored only when the ETM tasks it in WT).

Nothing here is a performance run: the maps are tiny and the point is which
decision branches fire, not how long they take.

Run:  python -B -X utf8 tools/probe_trace.py
"""
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from common_geometry import GridMetric  # noqa: E402
from etm_faithful import ETM  # noqa: E402
from maps_faithful import MAPS  # noqa: E402

LEDGER = NEW / "logs" / "call_ledger.csv"
ART = NEW / "artifacts"


def load(alias, path):
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


def maps():
    out = []
    free = rect(0, 0, 4, 4)
    out.append({"name": "t4x4", "free": free, "targets": set(free),
                "covered": set(), "base": (0, 0), "current": (0, 0)})

    free = rect(0, 0, 6, 4) - {(2, 2)}
    targets = free - {(5, 3)}
    out.append({"name": "t6x4_blocked", "free": free, "targets": set(targets),
                "covered": {(0, 0), (0, 1)}, "base": (0, 0), "current": (0, 1)})

    free = rect(0, 0, 8, 8) - rect(3, 3, 2, 1)
    targets = free
    out.append({"name": "t8x8_obstacle", "free": free, "targets": set(targets),
                "covered": set(), "base": (0, 0), "current": (0, 0)})

    # a pocket behind a wall: the cell at (4,0) cannot be reached by a straight
    # segment from the left, so D^0 empties while D^1 is still positive and the
    # level-by-level escape (CP1..CPL) has to run
    free = rect(0, 0, 7, 7) - {(3, y) for y in range(0, 6)}
    out.append({"name": "t7x7_pocket", "free": free, "targets": set(free),
                "covered": set(), "base": (0, 0), "current": (0, 0)})

    # a closed room with one opening: the interior is not directly reachable from
    # outside, so D^0 empties and the CP1..CPL escape has to run (it fired once in
    # the design probe)
    free = rect(0, 0, 9, 9) - ((rect(3, 3, 5, 5) - rect(4, 4, 3, 3)) - {(5, 3)})
    out.append({"name": "t9x9_room", "free": free, "targets": set(free),
                "covered": set(), "base": (0, 0), "current": (0, 0)})
    return out


def ledger_write(row):
    fields = ["run_id", "arm", "case_id", "seed", "status", "terminal",
              "steps", "tasks", "moves", "extremum_escapes", "levels_used",
              "rules", "coverage_complete", "note"]
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def run_arm(arm, case, seed, old_modules):
    free = frozenset(case["free"])
    targets = frozenset(case["targets"])
    covered = frozenset(case["covered"])
    current = case["current"]
    base = case["base"]
    metric = GridMetric(free)

    if arm == "old":
        old_maps = old_modules["maps"]
        old_etm = old_modules["etm"]
        maps_obj = old_maps.MAPS(free, targets, covered)
        engine = old_etm.ETM(maps_obj, current, seed=seed, credit="transit", metric=metric)
        engine.run(max_steps=4000)
        engine.return_to_base(base)
        summary = engine.summary()
        decisions = [(d.step, "CP", d.level, d.rule, tuple(d.lam), round(d.potential, 3),
                      tuple(sorted((d.waypoint,))), tuple(d.waypoint))
                     for d in engine.trace.decisions]
        route = tuple(engine.route)
        levels = dict(maps_obj.describe()["blocks_per_level"])
        rules = dict(Counter(d[3] for d in decisions))
        tasks = summary["tasks"]
        moves = summary["moves"]
        terminal = summary["terminal"]
        escapes = summary["extremum_escapes"]
    else:
        mode = "transit" if arm == "transit" else "task"
        maps_obj = MAPS(free, targets, covered)
        engine = ETM(maps_obj, current, seed=seed, credit=mode, metric=metric)
        engine.run(max_steps=4000)
        engine.return_to_base(base)
        summary = engine.summary()
        decisions = [(d.step, d.state, d.level, d.rule, tuple(d.lam),
                      round(d.lam_potential, 3), tuple(d.waypoint_set), tuple(d.chosen))
                     for d in engine.trace.decisions]
        route = tuple(engine.route)
        levels = {str(k): len(v) for k, v in maps_obj.tilings.items()}
        rules = summary["rules"]
        tasks = summary["tasks"]
        moves = summary["moves"]
        terminal = summary["terminal"]
        escapes = summary["extremum_escapes"]

    uncovered = targets - set(route)
    return {
        "arm": arm, "case": case["name"], "seed": seed, "terminal": terminal,
        "steps": len(route) - 1, "tasks": tasks, "moves": moves,
        "extremum_escapes": escapes, "rules": rules, "levels": levels,
        "coverage_complete": not uncovered,
        "uncovered_targets": len(uncovered),
        "decisions": decisions, "route": route,
        "line3_or_6_fired": rules.get("line6_task_here", 0) + rules.get("line5_up_down_unexplored", 0),
    }


def main():
    ART.mkdir(parents=True, exist_ok=True)
    old_maps = load("maps_old", NEW / "sources" / "v02_epsilon_core" / "maps.py")
    old_etm = load("etm_old", NEW / "sources" / "v02_epsilon_core" / "etm.py")
    old_modules = {"maps": old_maps, "etm": old_etm}

    runs = []
    trace_rows = []
    for case in maps():
        for arm in ("old", "transit", "task"):
            for seed in (20261018, 20261019):
                if arm != "task" and seed != 20261018:
                    continue            # the second seed only for the deliverable mode
                run_id = f"TRACE:{case['name']}:{arm}:{seed}"
                try:
                    result = run_arm(arm, case, seed, old_modules)
                    status = "ok"
                except Exception as exc:                      # noqa: BLE001
                    runs.append({"run_id": run_id, "arm": arm, "case": case["name"],
                                 "seed": seed, "status": "exception",
                                 "note": f"{type(exc).__name__}: {exc}"})
                    ledger_write({"run_id": run_id, "arm": arm, "case_id": case["name"],
                                  "seed": seed, "status": "exception",
                                  "note": f"{type(exc).__name__}: {exc}"})
                    continue
                result["run_id"] = run_id
                runs.append({key: result[key] for key in
                             ("run_id", "arm", "case", "seed", "terminal", "steps", "tasks",
                              "moves", "extremum_escapes", "rules", "levels",
                              "coverage_complete", "uncovered_targets",
                              "line3_or_6_fired")})
                for step in result["decisions"]:
                    trace_rows.append({"run_id": run_id, "arm": arm, "case": case["name"],
                                       "seed": seed, "step": step[0], "state": step[1],
                                       "level": step[2], "rule": step[3],
                                       "lam": step[4], "lam_potential": step[5],
                                       "waypoint_set": list(step[6]), "chosen": step[7]})
                ledger_write({"run_id": run_id, "arm": arm, "case_id": case["name"],
                              "seed": seed, "status": status, "terminal": result["terminal"],
                              "steps": result["steps"], "tasks": result["tasks"],
                              "moves": result["moves"],
                              "extremum_escapes": result["extremum_escapes"],
                              "levels_used": json.dumps(result["levels"]),
                              "rules": json.dumps(result["rules"]),
                              "coverage_complete": result["coverage_complete"], "note": ""})

    with open(ART / "trace_decisions.csv", "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0].keys()))
        writer.writeheader()
        writer.writerows(trace_rows)
    (ART / "trace_runs.json").write_text(
        json.dumps({"runs": runs, "planner_calls": len(runs)}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    lines = ["# 逐步轨迹探针（三臂对照）", "",
             "`line3/6` 是 Algorithm 1 第 3–6 行（当前格未探索 → 作业或上下移动）的触发次数；",
             "`escapes` 是进入 CP1..CPL 的次数。", "",
             "| 用例 | 臂 | 种子 | 终止 | 步数 | 作业数 | 改进级逃逸 | line3/6 | 规则计数 | 覆盖完整 |",
             "|---|---|---|---|---:|---:|---:|---:|---|---|"]
    for row in runs:
        lines.append(f"| `{row['case']}` | {row['arm']} | {row.get('seed','')} | "
                     f"{row.get('terminal','')} | {row.get('steps','')} | {row.get('tasks','')} | "
                     f"{row.get('extremum_escapes','')} | {row.get('line3_or_6_fired','')} | "
                     f"{row.get('rules','')} | {row.get('coverage_complete','')} |")
    lines.append("")
    (NEW / "reports" / "逐步轨迹_结果.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("planner calls:", len(runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
