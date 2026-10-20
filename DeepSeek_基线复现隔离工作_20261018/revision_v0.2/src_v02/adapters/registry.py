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
        "version": "epsilon_star_core_v0.2_20261018",
        "kind": "literature_core_adaptation",
        "paper": "epsilon-star (Song & Gupta, author preprint)",
        "source": "revision_v0.2/src_v02/adapters/epsilon_star.py + epsilon_core/",
        "fidelity": "multiscale MAPS + ETM state machine + level escape kept; move/task "
                    "separation replaced by transit crediting; Bug2 replaced by the common "
                    "connector; NOT a full reproduction of the paper experiments",
        "adapter": None,  # filled below to keep the import lazy
    },
    "CSTAR": {
        "version": "cstar_restart_diag_v0.2_20261018",
        "kind": "historical_reproduction_adaptation",
        "paper": "C* (arXiv 2505.13782v3)",
        "source": "revision_v0.2/src_v02/adapters/cstar.py + src/cstar_core/ (v0.1, reused read-only)",
        "fidelity": "RESTART DIAGNOSTIC: the real coverage ledger does not enter the "
                    "core planning state, so the core re-sweeps the whole published free "
                    "region; not a residual-task core adaptation and not the "
                    "unknown-environment C* of the paper",
        "adaptation_class": "restart_diagnostic_ledger_not_in_core",
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


# --------------------------------------------------------------- call recorder
# R5: v0.1 only registered the calls made by its runner, so "total planner calls
# this round" could not be answered.  Every call through this registry is now
# appended to one ledger, tagged with a kind and a plan cell id.  Test and
# development calls are therefore registered too, and nothing has to be estimated.
import csv
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

V02_ROOT = Path(__file__).resolve().parents[2]
LEDGER = V02_ROOT / "logs_v02" / "call_ledger_v02.csv"

LEDGER_COLUMNS = ["run_id", "batch", "kind", "registered_utc", "plan_id", "case_id",
                  "method_id", "method_version", "seed", "time_limit_seconds", "status",
                  "route_steps", "seconds", "valid", "natural", "fallback_used",
                  "completion_steps", "adaptation_class", "task_set_sha256", "note"]

#: set by the runner before each call; tests leave it empty
CONTEXT = {"batch": None, "kind": None, "plan_id": None, "task_set_sha256": None}
LAST_RECORD = None


def _batch_for(kind):
    return f"v02_{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"


def _append(row):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new = not LEDGER.exists()
    # append with plain utf-8: utf-8-sig in append mode would inject a BOM
    # in the middle of the file on every later call
    with open(LEDGER, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in LEDGER_COLUMNS})


def run(method_id, request, clock=None):
    global LAST_RECORD
    if method_id not in METHODS:
        raise KeyError(f"unknown method {method_id}")
    kind = CONTEXT.get("kind") or os.environ.get("DSH_RUN_KIND") or "unregistered"
    batch = CONTEXT.get("batch") or _batch_for(kind)
    run_id = uuid.uuid4().hex
    plan_id = CONTEXT.get("plan_id") or (f"{request.case_id}::{method_id}"
                                         if request is not None else method_id)
    begin = time.perf_counter()
    error = ""
    result = None
    try:
        result = METHODS[method_id]["adapter"](request, clock)
        return result
    except Exception:
        import traceback
        error = traceback.format_exc()
        raise
    finally:
        seconds = time.perf_counter() - begin
        audit = getattr(result, "audit", None) or {}
        meta = getattr(result, "meta", None) or {}
        record = {
            "run_id": run_id, "batch": batch, "kind": kind,
            "registered_utc": datetime.now(timezone.utc).isoformat(),
            "plan_id": plan_id,
            "case_id": getattr(request, "case_id", ""),
            "method_id": method_id,
            "method_version": getattr(result, "method_version", ""),
            "seed": getattr(request, "seed", ""),
            "time_limit_seconds": getattr(getattr(request, "termination", None),
                                          "time_limit_seconds", ""),
            "status": getattr(result, "status", "adapter_exception"),
            "route_steps": (len(result.route) - 1) if getattr(result, "route", ()) else "",
            "seconds": f"{seconds:.6f}",
            "valid": audit.get("valid", ""),
            "natural": (getattr(result, "termination", None) or {}).get("natural", ""),
            "fallback_used": getattr(result, "fallback_used", ""),
            "completion_steps": (meta.get("route") or {}).get("completion_steps", ""),
            "adaptation_class": METHODS[method_id].get("adaptation_class", ""),
            "task_set_sha256": CONTEXT.get("task_set_sha256") or "",
            "note": error.splitlines()[-1][:200] if error else "",
        }
        try:
            _append(record)
        except Exception:                     # noqa: BLE001 - never mask the call
            pass
        LAST_RECORD = record


def describe():
    return {name: {key: value for key, value in METHODS[name].items() if key != "adapter"}
            for name in ORDER}
