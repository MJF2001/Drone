"""Emit manifests/method_matrix.csv: one row per method, as the draft requires.

Every hash is computed from the delivered copy, not typed by hand.
"""
import csv
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
REF = OUT / "sources" / "reference_tree" / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
FROZEN = REF / "frozen_baselines" / "v2_20261012"
CAND = REF / "candidate_baselines" / "PPCPP_CORE4" / "v0.1_20261014"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def joined(paths):
    return "; ".join(f"{p.relative_to(OUT)}:{sha(p)}" for p in paths)


ROWS = [
    {
        "method_id": "P2_MULTI",
        "classification": "self_built_engineering_baseline",
        "version": "v2_20261012",
        "original_paper": "none",
        "source_files": joined([FROZEN / "source" / "p2_search_audit.py",
                                FROZEN / "source" / "planners.py",
                                FROZEN / "source" / "unified_geometry.py",
                                FROZEN / "source" / "bfs_metric_geometry.py",
                                FROZEN / "source" / "baseline_suite.py"]),
        "current_model_interface": "src/adapters/reference_methods.py::run_reference (wraps the frozen entry point unchanged)",
        "validated_this_round": "adapter vs direct frozen call identical on 17 fixtures; 17 legal routes; exact-gap recorded",
        "unresolved": "reports 'finished' with an empty route when the resource limit excludes every candidate (downgraded by the adapter, frozen code untouched); no per-stage timings persisted in historical runs; multi-start budget consumption unmeasured",
        "reuse_next_round": "keep as the self-built reference solver; add a separately named instrumented diagnostic variant rather than editing the frozen file",
    },
    {
        "method_id": "TREE_MST",
        "classification": "self_built_engineering_baseline",
        "version": "v2_20261012",
        "original_paper": "none (explicitly not TRACE / STC / FS-STC / C*)",
        "source_files": joined([FROZEN / "source" / "unified_candidates.py",
                                FROZEN / "source" / "planners.py"]),
        "current_model_interface": "src/adapters/reference_methods.py::run_reference",
        "validated_this_round": "adapter vs direct frozen call identical; legal routes on every solvable fixture",
        "unresolved": "no stage timing; returns status 'planned' rather than 'finished' (passed through, not normalised)",
        "reuse_next_round": "keep as the tree-initialisation engineering reference only",
    },
    {
        "method_id": "OARP_CORE2",
        "classification": "literature_core_adaptation",
        "version": "v2_20261012",
        "original_paper": "OARP-Replan arXiv 2311.17837v2, scenario 2 core only",
        "source_files": joined([FROZEN / "source" / "oarp_replan" / "ranks.py",
                                FROZEN / "source" / "oarp_replan" / "tour.py",
                                FROZEN / "source" / "oarp_replan" / "budget.py",
                                FROZEN / "source" / "baseline_suite.py",
                                FROZEN / "runtime_profile.json"]),
        "current_model_interface": "src/adapters/reference_methods.py::run_reference",
        "validated_this_round": "adapter vs direct frozen call identical; legal routes where the method accepts the input",
        "unresolved": "old_services requires the old route to enumerate every original pending target (raises otherwise; reported as input_precondition_unmet on m16/m17); cap_for_time is an empirical synthesis estimate, not a bound; no stage timing",
        "reuse_next_round": "keep as a literature core adaptation; document the old-route precondition in the protocol before comparing",
    },
    {
        "method_id": "PPCPP_CORE4",
        "classification": "literature_core_adaptation",
        "version": "v0.1_20261014",
        "original_paper": "PPCPP author manuscript, four-neighbour core",
        "source_files": joined([CAND / "source" / "candidate_ppcpp_core4_20261014.py",
                                CAND / "profile.json",
                                CAND / "manifest.json"]),
        "current_model_interface": "src/adapters/reference_methods.py::run_reference (via the candidate's own manifest-checking loader)",
        "validated_this_round": "candidate manifest hashes verified; adapter vs direct candidate call identical; legal routes",
        "unresolved": "weights selected on a development grid that overlaps historical batches; seed does not influence decisions; no stage timing",
        "reuse_next_round": "keep as a literature core adaptation; never treat the tuning batch as an independent test",
    },
    {
        "method_id": "EPSILON_STAR",
        "classification": "literature_core_adaptation",
        "version": "epsilon_star_core_v0.1_20261018",
        "original_paper": "Song & Gupta, epsilon-star (author preprint)",
        "source_files": joined([OUT / "src" / "epsilon_core" / "maps.py",
                                OUT / "src" / "epsilon_core" / "etm.py",
                                OUT / "src" / "adapters" / "epsilon_star.py"]),
        "current_model_interface": "src/adapters/epsilon_star.py::run",
        "validated_this_round": "hand-computable MAPS/ETM checks on a 4x2 map; random fine-cell selection (not nearest-first); level-escape test; legal routes on all solvable fixtures; one route over the tight resource limit labelled resource_exceeded",
        "unresolved": "transit crediting suppresses the WT task branch (documented loss); turn cost disabled; no forbidden ring; hierarchy depth uneven on odd sizes; completeness theorem not inherited",
        "reuse_next_round": "keep as a literature core adaptation; decide the credit-mode policy explicitly before any performance comparison",
    },
    {
        "method_id": "CSTAR",
        "classification": "historical_reproduction_adaptation",
        "version": "cstar_adapt_v0.1_20261018",
        "original_paper": "C* arXiv 2505.13782v3 (unknown-environment)",
        "source_files": joined([OUT / "sources" / "cstar_historical" / "cstar_strict" / "planner.py",
                                OUT / "sources" / "cstar_historical" / "cstar_strict" / "rcg.py",
                                OUT / "sources" / "cstar_historical" / "cstar_strict" / "geometry.py",
                                OUT / "src" / "adapters" / "cstar.py"]),
        "current_model_interface": "src/adapters/cstar.py::run",
        "validated_this_round": "mechanism-to-source table; degeneration measurement (frontier ring only, zero interior samples); legal four-neighbour realisation of diagonal RCG edges",
        "unresolved": "C* sweeps RCG frontier samples, not target cells, so under a target-only task it over-covers; the published-map mode cannot sample the interior; the RCG can disconnect on a published-free pocket behind a blocked ring",
        "reuse_next_round": "keep as a mechanism study; do not enter it into a target-only ranking without deciding the comparison basis",
    },
]


def main():
    target = OUT / "manifests" / "method_matrix.csv"
    fields = ["method_id", "classification", "version", "original_paper", "source_files",
              "current_model_interface", "validated_this_round", "unresolved", "reuse_next_round"]
    with open(target, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"wrote {target} with {len(ROWS)} rows")
    print(json.dumps({"methods": [row["method_id"] for row in ROWS]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
