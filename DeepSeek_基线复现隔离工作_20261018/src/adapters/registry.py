"""Single registry for every method this round can run.

``kind`` uses the classification the user asked for and must stay accurate:

  self_built_engineering_baseline   P2_MULTI, TREE_MST   (own code, not a paper)
  literature_core_adaptation        OARP_CORE2, PPCPP_CORE4, EPSILON_STAR
  historical_reproduction_adaptation CSTAR

No method is described as a complete reproduction of any paper.
"""
from adapters import reference_methods

METHODS = {
    "P2_MULTI": {
        "version": "v2_20261012",
        "kind": "self_built_engineering_baseline",
        "paper": "none (own multi-start scan + nearest neighbour + 2-opt)",
        "source": "sources/reference_tree/.../frozen_baselines/v2_20261012/source/p2_search_audit.py",
        "fidelity": "self-built; multi-start/perturbation enhancement of the two simple "
                    "starting orders; not a paper reproduction",
        "adapter": lambda request, clock=None: reference_methods.run_reference("P2_MULTI", request, clock),
    },
    "TREE_MST": {
        "version": "v2_20261012",
        "kind": "self_built_engineering_baseline",
        "paper": "none (metric MST over remaining targets + preorder + 2-opt)",
        "source": "sources/reference_tree/.../frozen_baselines/v2_20261012/source/unified_candidates.py",
        "fidelity": "self-built; explicitly NOT TRACE, NOT STC, NOT FS-STC, NOT C*",
        "adapter": lambda request, clock=None: reference_methods.run_reference("TREE_MST", request, clock),
    },
    "OARP_CORE2": {
        "version": "v2_20261012",
        "kind": "literature_core_adaptation",
        "paper": "OARP-Replan (arXiv 2311.17837v2), core scenario 2 only",
        "source": "sources/reference_tree/.../frozen_baselines/v2_20261012/source/oarp_replan/",
        "fidelity": "rank LP/MIP + retained path sets + directed start/end GTSP; NOT the "
                    "full OARP-Replan system, NOT OARP-Original",
        "adapter": lambda request, clock=None: reference_methods.run_reference("OARP_CORE2", request, clock),
    },
    "PPCPP_CORE4": {
        "version": "v0.1_20261014",
        "kind": "literature_core_adaptation",
        "paper": "PPCPP (author manuscript), four-neighbour core",
        "source": "sources/reference_tree/.../candidate_baselines/PPCPP_CORE4/v0.1_20261014/",
        "fidelity": "three reward terms + dead-end recovery + return; weights selected on a "
                    "development grid; NOT full PPCPP, no online weight optimisation",
        "adapter": lambda request, clock=None: reference_methods.run_reference("PPCPP_CORE4", request, clock),
    },
    "EPSILON_STAR": {
        "version": "epsilon_star_core_v0.1_20261018",
        "kind": "literature_core_adaptation",
        "paper": "epsilon-star (Song & Gupta, author preprint)",
        "source": "src/adapters/epsilon_star.py + src/epsilon_core/",
        "fidelity": "multiscale MAPS + ETM state machine + level escape kept; move/task "
                    "separation replaced by transit crediting; Bug2 replaced by the common "
                    "connector; NOT a full reproduction of the paper experiments",
        "adapter": None,  # filled below to keep the import lazy
    },
    "CSTAR": {
        "version": "cstar_adapt_v0.1_20261018",
        "kind": "historical_reproduction_adaptation",
        "paper": "C* (arXiv 2505.13782v3)",
        "source": "src/adapters/cstar.py + src/cstar_core/",
        "fidelity": "historical unknown-environment reproduction ported to the current model; "
                    "explicitly NOT the unknown-environment C* of the paper",
        "adapter": None,
    },
}

ORDER = ("P2_MULTI", "OARP_CORE2", "TREE_MST", "PPCPP_CORE4", "EPSILON_STAR", "CSTAR")


def _epsilon(request, clock=None):
    from adapters import epsilon_star
    return epsilon_star.run(request, clock)


def _cstar(request, clock=None):
    from adapters import cstar
    return cstar.run(request, clock)


METHODS["EPSILON_STAR"]["adapter"] = _epsilon
METHODS["CSTAR"]["adapter"] = _cstar


def available():
    """Methods whose adapter module is present in this delivery."""
    import importlib.util
    out = []
    for name in ORDER:
        required = {"EPSILON_STAR": "adapters.epsilon_star",
                    "CSTAR": "adapters.cstar"}.get(name)
        if required and importlib.util.find_spec(required) is None:
            continue
        out.append(name)
    return tuple(out)


def run(method_id, request, clock=None):
    if method_id not in METHODS:
        raise KeyError(f"unknown method {method_id}")
    return METHODS[method_id]["adapter"](request, clock)


def describe():
    return {name: {key: value for key, value in METHODS[name].items() if key != "adapter"}
            for name in ORDER}
