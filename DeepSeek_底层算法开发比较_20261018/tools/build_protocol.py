"""Freeze the protocol, the method configuration, the input index and the run plan.

Everything this round will execute is decided here, before any development run:

* ``protocol/protocol.json``      budgets, hard caps, seeds, order rule, stop rules,
                                  timing and budget semantics, taxonomy, cache policy
* ``protocol/method_config.json`` the five methods with core/adapter version, source
                                  hashes and the termination specification
* ``protocol/input_index.csv``    the 10 real states with sizes, endpoints and hashes
* ``protocol/planned_runs.csv``   all 300 development tasks (plus the 10 preflight ones)
* ``protocol/sha256.json``        hashes of everything above and of the sources

The script refuses to overwrite a frozen protocol unless ``--force`` is given.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402
from adapters import registry  # noqa: E402
import inputs  # noqa: E402

PROTOCOL = NEW / "protocol"

SEEDS = (20261018, 20261019)
BATCHES = [
    ("LONG120", 120.0, 135.0),
    ("BUDGET1", 1.0, 15.0),
    ("BUDGET20", 20.0, 35.0),
]
PREFLIGHT = {"batch": "PREFLIGHT", "soft": 2.0, "hard": 15.0, "seed": SEEDS[0]}
WALL_CLOCK_CAP_HOURS = 6
MAX_PLANNER_CALLS = {"preparation": 60, "preflight": 10, "development": 300, "total": 370}

TERMINATION_SPEC = {
    "P2_MULTI": {
        "construction": "two scan orders (H/V) and two nearest-neighbour orders; for each, "
                        "raw order then 2-opt with at most 8 passes",
        "natural": "every core 2-opt segment ends with 'no_improving_2opt_move' or the "
                   "8-pass cap, the 120-pass deep stage and the 32-pass multi-start stages "
                   "end the same way, and the wall-clock budget was not reached",
        "budget_effect": "the soft budget is the only external stop; when it fires the "
                         "engine returns 'planned_at_timeout' with the best incumbent",
        "native_status_fields": ["status", "active_stage", "events[].termination", "source"],
    },
    "TREE_MST": {
        "construction": "one metric MST over pending targets + current position, one "
                        "preorder in each direction, one fixed-endpoint 2-opt (<=8 passes)",
        "natural": "the single construction finishes (one 2-opt pass sequence with no "
                   "improving move or the 8-pass cap); there is no outer restart loop",
        "budget_effect": "only the soft deadline can interrupt; the engine reports 'planned' "
                         "or 'planned_at_timeout'",
        "native_status_fields": ["status", "detail.improvements"],
    },
    "OARP_CORE2": {
        "construction": "rank LP (SCIP) -> integer MIP fallback -> path sets -> directed "
                        "start/end GTSP solved by the bundled GLNS",
        "natural": "LP optimal and integral (or the MIP fallback optimal) AND the GTSP solver "
                   "reports natural convergence (timeout=False)",
        "budget_effect": "the rank budget cap is derived from the remaining time via the frozen "
                         "runtime profile, so the number of allowed new ranks DEPENDS on the "
                         "budget: this is a budget-conditioned algorithm",
        "native_status_fields": ["status", "detail.rank.status", "detail.rank_cap",
                                 "detail.tour.solver.timeout", "detail.cap_source"],
        "warning": "a GLNS time limit exhausted is NOT natural convergence; a SCIP optimum is "
                   "optimal for the rank model, not for the coverage route",
    },
    "PPCPP_CORE4": {
        "construction": "one deterministic core walk: reward-driven neighbour choice with a "
                        "dead-end recovery jump, then the fixed return",
        "natural": "the core route is built and passes the pre-return audit before the deadline",
        "budget_effect": "only the soft deadline can interrupt; the engine reports its own "
                         "core_status",
        "native_status_fields": ["status", "detail.core_status", "detail.core_steps"],
        "warning": "a route that equals the shared fallback must be reported as fallback, not as "
                   "a PPCPP result",
    },
    "EPSILON_STAR": {
        "construction": "multiscale MAPS construction, then the ETM loop (one physical step per "
                        "iteration), then the base return",
        "natural": "the ETM reaches FN because no positive potential remains at any level",
        "budget_effect": "the public soft deadline; a candidate whose audit finishes after the "
                         "deadline is kept only as a diagnostic route",
        "native_status_fields": ["status", "meta.etm.terminal", "meta.candidate",
                                 "meta.deadline"],
        "warning": "state_cycle and the step cap are ARTIFICIAL safety truncations, not the "
                   "paper's natural termination",
    },
}

TAXONOMY = {
    "natural_complete_valid": "the engine's own termination was reached and the route is legal, "
                              "complete and within the resource",
    "truncated_with_valid_candidate": "a time/iteration cap fired but a legal complete route "
                                      "was already produced",
    "no_valid_route": "no legal complete route was produced",
    "input_precondition_rejected": "the method's own input precondition was not met",
    "environment_infeasible": "the base or an outstanding target is unreachable (reported by "
                              "the independent reachability check, not by the planner)",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def method_order(case_index, seed_index):
    shift = (case_index + seed_index) % len(registry.ORDER)
    return registry.ORDER[shift:] + registry.ORDER[:shift]


def build_plan():
    rows = []
    order_index = 0
    for batch, soft, hard in BATCHES:
        for i, map_id in enumerate(inputs.MAP_IDS):
            for j, seed in enumerate(SEEDS):
                for method in method_order(i, j):
                    order_index += 1
                    rows.append({
                        "run_id": f"{batch}:{map_id}:{method}:{seed}",
                        "batch": batch, "kind": "development",
                        "order_index": order_index,
                        "case_id": map_id, "method_id": method, "seed": seed,
                        "soft_limit_seconds": soft, "hard_limit_seconds": hard,
                    })
    return rows


def build_preflight_plan():
    rows = []
    for index, case_id in enumerate(("pf_open_small", "pf_obstacle_small")):
        for position, method in enumerate(registry.ORDER):
            rows.append({
                "run_id": f"PREFLIGHT:{case_id}:{method}:{PREFLIGHT['seed']}",
                "batch": "PREFLIGHT", "kind": "preflight",
                "order_index": index * len(registry.ORDER) + position + 1,
                "case_id": case_id, "method_id": method, "seed": PREFLIGHT["seed"],
                "soft_limit_seconds": PREFLIGHT["soft"],
                "hard_limit_seconds": PREFLIGHT["hard"],
            })
    return rows


def main(argv):
    force = "--force" in argv
    target = PROTOCOL / "protocol.json"
    if target.exists() and not force:
        raise SystemExit("protocol already frozen; pass --force only if you accept "
                         "invalidating the recorded hash")

    PROTOCOL.mkdir(parents=True, exist_ok=True)
    descriptions = registry.describe_all()
    plan = build_plan()
    preflight_plan = build_preflight_plan()

    index_rows = []
    for map_id in inputs.MAP_IDS:
        info = inputs.describe(map_id)
        info["normalised_sha256"] = hashlib.sha256(
            json.dumps({"free": info["free"], "published": info["published"],
                        "covered": info["covered"], "pending": info["pending"],
                        "deferred": info["deferred"], "current": info["current"],
                        "base": info["base"], "distance_budget": info["distance_budget"]},
                       sort_keys=True).encode("utf-8")).hexdigest()
        index_rows.append(info)
    write_csv(PROTOCOL / "input_index.csv", index_rows, list(index_rows[0].keys()))

    fields = ["run_id", "batch", "kind", "order_index", "case_id", "method_id", "seed",
              "soft_limit_seconds", "hard_limit_seconds"]
    write_csv(PROTOCOL / "planned_runs.csv", plan, fields)
    write_csv(PROTOCOL / "preflight_planned_runs.csv", preflight_plan, fields)

    protocol = {
        "round": "deepseek_development_comparison_20261018",
        "generated_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "purpose": "decide where P2's route quality and computing cost stand under the same "
                   "complete residual task, and whether the short-budget gap comes from an "
                   "unfinished construction/search or from a quality gap after natural "
                   "termination",
        "not_claimed": ["P2 is sufficient", "any method is the domain best",
                        "TRACE/LKH are represented", "the micro fixtures are a performance set"],
        "model": {
            "grid": "four-neighbour, equal unit steps, arriving on a target cell covers it",
            "task": "complete the same current checkable residual targets Q=(P-C) and F and "
                    "return to the same base",
            "history": "the real coverage ledger and the real old remaining route are inputs "
                       "for every method; no SEED/PLUS1 style scope selection this round",
            "information": "only the currently published map is visible",
        },
        "seeds": list(SEEDS),
        "seed_meaning": "the seed is passed to every method; P2/OARP/GLNS use it for their "
                        "randomised stages, TREE_MST and PPCPP_CORE4 are deterministic and "
                        "ignore it. Two seeds are not a statistical power claim.",
        "batches": [{"batch": name, "soft_limit_seconds": soft, "hard_limit_seconds": hard,
                     "calls": len(inputs.MAP_IDS) * len(SEEDS) * len(registry.ORDER)}
                    for name, soft, hard in BATCHES],
        "batch_execution_order": [name for name, _, _ in BATCHES],
        "method_order_rule": "for case index i and seed index j the method order is "
                             "ORDER rotated left by (i+j) mod 5; ORDER = "
                             + " -> ".join(registry.ORDER),
        "preflight": {"inputs": ["pf_open_small", "pf_obstacle_small"],
                      "soft_limit_seconds": PREFLIGHT["soft"],
                      "hard_limit_seconds": PREFLIGHT["hard"],
                      "seed": PREFLIGHT["seed"],
                      "calls": len(preflight_plan),
                      "purpose": "runner / records / legality only, no performance screening"},
        "call_budget": MAX_PLANNER_CALLS,
        "wall_clock_cap_hours": WALL_CLOCK_CAP_HOURS,
        "timing": {
            "call_total_seconds": "public entry to the finished pre-return output check, "
                                  "including input validation, preprocessing, construction, "
                                  "search, connector, return and the audit",
            "adapter_call_seconds": "the adapter's own measure, a subset of call_total",
            "excluded": "ledger disk writes, the external post-hoc audit and the process "
                        "start-up",
            "process_startup": "recorded per task by the parent as wall minus call_total",
        },
        "budget_verdict": "a call counts as in-budget only when call_total_seconds <= the "
                          "public soft limit; later calls keep their produced route but are "
                          "reported with within_budget=false and the overrun in seconds",
        "taxonomy": TAXONOMY,
        "stop_rules": {
            "hard_cap": "the parent kills a task at the per-batch hard cap and records a "
                        "hard_timeout end row; the route is not used",
            "wall_clock": f"no new task starts after {WALL_CLOCK_CAP_HOURS} h from the batch "
                          "start; the remaining list is kept as not started",
            "no_retry": "a failed task is not retried, a successful task is not rerun, and a "
                        "task that never started gets no fabricated failure row",
            "early_stop": "if LONG120 shows a runner or semantic defect the later two batches "
                          "are not started",
        },
        "cache_policy": {
            "per_batch_cache": "each batch runs with its own TEMP/TMP and cache directory under "
                               "NEW/tmp/cache/<batch>",
            "graph_independent_dependency": "OARP_CORE2 reads the frozen runtime_profile.json "
                                            "(an offline calibration constant); it is graph "
                                            "independent and is disclosed, not recomputed",
            "no_cross_method_sharing": "no distance matrix, route or optimisation state is "
                                       "shared between methods or batches",
        },
        "ledger": {"two_phase": True, "seal": "prefix bytes + lines + SHA256 per batch",
                   "kinds": ["preparation", "preflight", "development"]},
        "frozen_at": "before any development run",
    }
    (PROTOCOL / "protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=1), encoding="utf-8")

    method_config = {
        "adapter_version": registry.ADAPTER_VERSION,
        "methods": descriptions,
        "termination_spec": TERMINATION_SPEC,
        "excluded_this_round": {
            "CSTAR": "restart diagnostic only; its real ledger never reaches the core planning "
                     "state, so it is not a residual-task C* adaptation and does not enter the "
                     "ranking",
            "TRACE": "specification only, not implemented",
            "LKH": "specification only, not downloaded or built",
        },
        "shared_fallback": "P2_MULTI, TREE_MST, OARP_CORE2 and PPCPP_CORE4 each submit the shared "
                           "old-suffix / common greedy candidates first; the report must show "
                           "core, fallback and final source separately",
    }
    (PROTOCOL / "method_config.json").write_text(
        json.dumps(method_config, ensure_ascii=False, indent=1), encoding="utf-8")

    hashes = {
        "protocol.json": sha256(PROTOCOL / "protocol.json"),
        "method_config.json": sha256(PROTOCOL / "method_config.json"),
        "input_index.csv": sha256(PROTOCOL / "input_index.csv"),
        "planned_runs.csv": sha256(PROTOCOL / "planned_runs.csv"),
        "preflight_planned_runs.csv": sha256(PROTOCOL / "preflight_planned_runs.csv"),
        "cases": {map_id: inputs.describe(map_id)["source_sha256"] for map_id in inputs.MAP_IDS},
        "preflight_inputs": {path.stem: sha256(path)
                             for path in sorted((NEW / "preflight" / "inputs").glob("*.json"))},
        "sources": {name: info["source_sha256"] for name, info in descriptions.items()},
        "source_files": {name: info["source_files"] for name, info in descriptions.items()},
    }
    (PROTOCOL / "sha256.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"frozen: {PROTOCOL}")
    print(f"development planned runs: {len(plan)}  preflight: {len(preflight_plan)}")
    for name, soft, hard in BATCHES:
        print(f"  {name}: soft={soft}s hard={hard}s calls={sum(1 for r in plan if r['batch'] == name)}")
    print("method order for (case 0, seed 0):", " -> ".join(method_order(0, 0)))


if __name__ == "__main__":
    main(sys.argv[1:])
