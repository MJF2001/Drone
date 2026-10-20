"""Freeze the protocol, the case list and the run plan before any planned call.

Nothing is executed here beyond importing the modules to hash them.
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
import methods  # noqa: E402

PROTOCOL = NEW / "protocol"
SEED = 20261018
SOFT = 5.0
HARD = 10.0
RESOURCE = 1000

BUDGET = {"initial": 3, "event": 32, "interface": 24, "defect": 16,
          "full_total": 75, "strip": 56, "gtsp": 8,
          "scip_total": 640, "glns_total": 80}

RECT = [[x, y] for x in range(4) for y in range(3)]
VLINE = [[0, y] for y in range(4)]
#: the sparse preparation: five free cells in a row, targets only at both ends
SPARSE_FREE = [[x, 0] for x in range(5)]
SPARSE = [[0, 0], [4, 0]]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cases():
    base_rect = {"name": "prep_rect", "free": RECT, "published": RECT,
                 "covered": [], "current": [0, 0], "base": [0, 0],
                 "prefix_targets": 6}
    return {
        "preparations": [
            base_rect,
            {"name": "prep_vline", "free": VLINE, "published": VLINE, "covered": [],
             "current": [0, 0], "base": [0, 0], "prefix_targets": 3},
            {"name": "prep_sparse", "free": SPARSE_FREE, "published": SPARSE,
             "covered": [], "current": [0, 0], "base": [2, 0],
             "prefix_targets": 1},
        ],
        "events": [
            {"case_id": "N1", "prep": "prep_rect", "kind": "no_change",
             "expect": "normalized fragments equal the remaining native strips",
             "new_obstacles": [], "new_targets": [], "new_free": []},
            {"case_id": "N2", "prep": "prep_rect", "kind": "obstacle_target",
             "rule": "first cell in (y,x) order among uncovered, not current/base, "
                     "whose removal keeps Q and the base reachable",
             "new_obstacles": "select", "new_targets": [], "new_free": []},
            {"case_id": "N3", "prep": "prep_rect", "kind": "obstacle_connector",
             "rule": "first cell in route-index order among the native remaining "
                     "connector annotations, not current/base, not a pending service "
                     "cell, whose removal keeps Q completable",
             "new_obstacles": "select", "new_targets": [], "new_free": []},
            {"case_id": "N4", "prep": "prep_rect", "kind": "extend_straight",
             "new_obstacles": [], "new_targets": [[4, 0], [4, 1], [4, 2]],
             "new_free": [[4, 0], [4, 1], [4, 2]]},
            {"case_id": "N5", "prep": "prep_rect", "kind": "extend_corner",
             "new_obstacles": [], "new_targets": [[4, 2], [4, 3], [3, 3]],
             "new_free": [[4, 2], [4, 3], [3, 3]]},
            {"case_id": "N6", "prep": "prep_rect", "kind": "extend_plus_obstacle",
             "rule": "N4 extension published together with the N2 obstacle, and the "
                     "obstacle is chosen only from the old initial map",
             "new_obstacles": "select_n2", "new_targets": [[4, 0], [4, 1], [4, 2]],
             "new_free": [[4, 0], [4, 1], [4, 2]]},
            {"case_id": "N7", "prep": "prep_vline", "kind": "no_change",
             "expect": "the remaining vertical strip keeps axis V and its rank id",
             "new_obstacles": [], "new_targets": [], "new_free": []},
            {"case_id": "N8", "prep": "prep_sparse", "kind": "new_target",
             "expect": "Q becomes disconnected while F stays connected; the new "
                       "target is served through passable cells",
             "new_obstacles": [], "new_targets": [[2, 1]], "new_free": [[2, 1]]},
        ],
    }


def plan_rows():
    rows = [{"plan_id": f"INIT:{p['name']}", "run_id": f"INIT:{p['name']}",
             "kind": "initial", "order_index": i + 1, "case_id": p["name"],
             "method_id": methods.METHOD_RANK0, "seed": SEED,
             "cap_override": "", "soft_limit_seconds": SOFT,
             "hard_limit_seconds": HARD, "max_control_iterations": "",
             "expected_status": "planned"}
            for i, p in enumerate(cases()["preparations"])]
    index = len(rows)
    for event in cases()["events"]:
        configs = [(methods.METHOD_RANK0, ""), (methods.METHOD_REPLAN2, "0"),
                   (methods.METHOD_REPLAN2, "2"), (methods.METHOD_REPLAN2, "2*|Q|")]
        for method, cap in configs:
            index += 1
            suffix = f":cap{cap}" if cap else ""
            rows.append({
                "plan_id": f"{event['case_id']}:{method}{suffix}",
                "run_id": f"{event['case_id']}:{method}{suffix}",
                "kind": "event", "order_index": index, "case_id": event["case_id"],
                "method_id": method, "seed": SEED, "cap_override": cap,
                "soft_limit_seconds": SOFT, "hard_limit_seconds": HARD,
                "max_control_iterations": "", "expected_status": ""})
    return rows


def main():
    PROTOCOL.mkdir(parents=True, exist_ok=True)
    payload = cases()
    (PROTOCOL / "cases.json").write_text(
        json.dumps({"seed": SEED, "resource": RESOURCE,
                    "note": "coordinates are Cartesian (x, y); the rectangle is "
                            "x=0..3, y=0..2; every case is a deterministic input",
                    **payload}, ensure_ascii=False, indent=1), encoding="utf-8")

    rows = plan_rows()
    with open(PROTOCOL / "planned_runs.csv", "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    description = registry.describe(methods.METHOD_RANK0)
    protocol = {
        "round": "oarp_native_reference_20261018",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "methods": {
            "OARP_RANK0_FULLTOUR_SCENE": {
                "variant": 0, "cap": None, "old_services_passed": 0,
                "meaning": "rank minimisation over the current Q with no change budget; "
                           "every rank enters one full GTSP with both directions"},
            "OARP_REPLAN2_NATIVE_SCENE": {
                "variant": 2, "caps": [0, 2, "2*|Q|"],
                "meaning": "model 2 against native remaining fragments; unchanged "
                           "fragments keep their exact internal old connector"},
        },
        "not_claimed": ["the author's online robot system", "the paper's theoretical "
                        "guarantees", "global optimality", "the paper's main algorithm"],
        "task": {"pending": "Q = (P-C) and F", "deferred": "D = (P-C) - F, kept and never "
                 "completed", "motion": "four-neighbour unit steps over F",
                 "resource": "route_steps <= remaining budget"},
        "timing": {"public_soft_deadline_seconds": SOFT,
                   "subprocess_hard_cap_seconds": HARD,
                   "covered": "input checks, normalisation, geometry, fallback, rank "
                              "construction/solve, GTSP matrix and search, expansion, "
                              "pre-return audit",
                   "ledger": "start/end writes and fsync are outside the measured "
                             "algorithm time and are reported separately"},
        "candidate_boundary": "generated -> audited -> accepted; a route audited after "
                              "the deadline is diagnostic only",
        "flags": ["route_valid", "coverage_complete", "resource_valid", "returned_base",
                  "rank_status", "rank_optimal", "tour_status", "core_candidate_valid",
                  "fallback_selected", "natural", "termination_reason",
                  "call_within_budget", "candidate_accepted_in_time"],
        "fallback": "frozen shared greedy (nearest pending, then base); computed before "
                    "the core and never relabelled as a core result",
        "resource": RESOURCE,
        "seed": SEED,
        "call_budget": BUDGET,
        "stop_rules": {"per_call": "soft deadline and the subprocess hard cap",
                       "round": "stop at 75 full calls, 56 strip items or 8 GTSP items"},
        "not_in_this_round": ["real development maps", "holdout", "1/20/120 s matrix",
                              "parameter search", "MLC implementation",
                              "improving OARP"],
    }
    (PROTOCOL / "protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=1), encoding="utf-8")

    method_config = {
        "core_version": methods.CORE_VERSION,
        "adapter_version": methods.ADAPTER_VERSION,
        "methods": description,
        "parameters": {"seed": SEED, "soft_seconds": SOFT, "hard_seconds": HARD,
                       "replan2_caps": [0, 2, "2*|Q|"], "glns_mode": "default",
                       "glns_trials": 5, "glns_restarts": 3,
                       "rank_lp_then_mip": True, "certification_repair": True},
        "glns": {"backend": "author-glns-cpp-0.1.0 (locked dependency)",
                 "note": "the solver fields recorded per call are read back from the "
                         "solver object, not copied from any earlier metadata"},
        "budget_table": {"used_here": False,
                         "why": "this round uses explicit cap_override only; the "
                                "time-to-cap estimator is not re-calibrated"},
    }
    (PROTOCOL / "method_config.json").write_text(
        json.dumps(method_config, ensure_ascii=False, indent=1), encoding="utf-8")

    (PROTOCOL / "test_plan.md").write_text(f"""# Test and call plan (frozen)

| Category | Cap | Content |
|---|---:|---|
| Initial native preparation | 3 | rectangle, vertical line, sparse line |
| Event responses | 32 | 8 cases x (1 rank0 + 3 replan2 caps) |
| Interface boundary tests | 24 | fake clock, audit injection, empty Q, ledger faults (mock flagged) |
| Defect localisation / minimal re-check | 16 | only affected items, new run_id |
| Full-entry total | 75 | every attempt registered, including failed ones |
| Independent strip subproblems | 56 | 40 with certification on + 2 strict diagnostics + up to 14 re-checks |
| Independent exact GTSP | 8 | 1-6 service groups |

Micro calls: public soft deadline {SOFT}s, subprocess hard cap {HARD}s.
Math subproblems: at most 6 cells, {SOFT}s soft deadline. Exact GTSP: at most 6 groups.

Pure tests (structures, normalisation, serialisation) do not run a solver and are
not counted; anything that reaches a solver is registered.
""", encoding="utf-8")

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
    print(f"frozen {PROTOCOL}; planned rows={len(rows)}")
    print("source digest", hashes["source_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
