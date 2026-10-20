"""Method registry and call recorder for the development comparison round.

Changes against v0.3 (all of them requested by the acceptance notes or by the
round's execution draft, section 5):

* ``core_version`` and ``adapter_version`` are separate fields, and the source
  files of every method are hashed at import time, so a result can never claim a
  version that its imported code does not have (acceptance note 1);
* ``validate_inputs`` runs inside the measured region, so the end-to-end time
  covers input checking + preprocessing + construction + search + connector +
  return + the pre-return output check (draft section 5.5);
* the *public* soft limit is applied to every method, and a call whose required
  validation finished after the limit is flagged ``within_budget = False`` with
  the overrun in seconds; its status is kept (the engine really produced it) but
  it is not counted as an in-budget result (draft section 5.6);
* two-phase ledger with ``start`` written and fsynced before the call, a failure
  to write it aborts the call, and the end row carries the fields the verifier
  joins on (draft section 5.7);
* the run id can be supplied by the protocol (``CONTEXT['run_id']``) so a parent
  watchdog process can correlate a killed child with its ledger rows.
"""
import csv
import hashlib
import importlib.util
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bootstrap

NEW = bootstrap.NEW
LEDGER = NEW / "logs" / "call_ledger.csv"
ADAPTER_VERSION = "dev_compare_20261018"

LEDGER_COLUMNS = [
    "run_id", "phase", "batch", "kind", "registered_utc", "plan_id", "case_id",
    "method_id", "core_version", "adapter_version", "seed", "soft_limit_seconds",
    "status", "natural", "within_budget", "budget_overrun_seconds",
    "call_total_seconds", "adapter_call_seconds", "route_steps", "coverage_complete",
    "audit_valid", "fallback_used", "completion_steps", "adaptation_class",
    "task_set_sha256", "source_sha256", "note",
]

#: ``sources`` lists the modules whose content defines the method's behaviour;
#: they are hashed at import time and the digest is written into every row.
METHODS = {
    "P2_MULTI": {
        "core_version": "v2_20261012",
        "kind": "self_built_engineering_baseline",
        "paper": "none (own multi-start scan + nearest neighbour + 2-opt)",
        "adaptation_class": "frozen_v2_bundle",
        "sources": ["baseline_suite", "p2_search_audit", "planners", "model",
                    "unified_geometry", "bfs_metric_geometry", "audit"],
        "adapter": None,
    },
    "TREE_MST": {
        "core_version": "v2_20261012",
        "kind": "self_built_engineering_baseline",
        "paper": "none (metric MST + preorder + 2-opt); NOT TRACE, NOT STC",
        "adaptation_class": "frozen_v2_bundle",
        "sources": ["baseline_suite", "unified_candidates", "planners", "model",
                    "unified_geometry", "bfs_metric_geometry", "audit"],
        "adapter": None,
    },
    "OARP_CORE2": {
        "core_version": "v2_20261012",
        "kind": "literature_core_adaptation",
        "paper": "OARP-Replan arXiv 2311.17837v2, scenario-2 core only",
        "adaptation_class": "oarp_core2_unit_step",
        "sources": ["baseline_suite", "oarp_replan.ranks", "oarp_replan.tour",
                    "oarp_replan.budget", "model", "unified_geometry", "audit"],
        "adapter": None,
    },
    "PPCPP_CORE4": {
        "core_version": "v0.1_20261014",
        "kind": "literature_core_adaptation",
        "paper": "PPCPP author manuscript, four-neighbour core",
        "adaptation_class": "ppcpp_core4_four_neighbour",
        "sources": ["candidate_ppcpp_core4_20261014", "model", "unified_geometry",
                    "audit", "baseline_suite"],
        "adapter": None,
    },
    "EPSILON_STAR": {
        "core_version": "epsilon_star_core_v0.3_20261018",
        "kind": "literature_core_adaptation",
        "paper": "Song & Gupta, epsilon-star (author preprint)",
        "adaptation_class": "epsilon_star_transit_credit",
        "sources": ["epsilon_core.maps", "epsilon_core.etm", "adapters.epsilon_star",
                    "common_geometry", "model"],
        "adapter": None,
    },
}
ORDER = ("P2_MULTI", "TREE_MST", "OARP_CORE2", "PPCPP_CORE4", "EPSILON_STAR")

CORE_SUFFIX = {   # which tree each method's sources live in
    "P2_MULTI": "frozen", "TREE_MST": "frozen", "OARP_CORE2": "frozen",
    "PPCPP_CORE4": "candidate", "EPSILON_STAR": "new",
}

_source_digests = {}


def _module_path(name):
    if name == "candidate_ppcpp_core4_20261014":
        return bootstrap.CANDIDATE / "source" / (name + ".py")
    if name.startswith("adapters.epsilon_star"):
        return Path(__file__).resolve().parent / "epsilon_star.py"
    module = importlib.import_module(name)
    return Path(module.__file__).resolve()


def source_digest(method_id):
    """SHA256 over the method's source files (path + content), computed once."""
    if method_id in _source_digests:
        return _source_digests[method_id]
    digest = hashlib.sha256()
    paths = {}
    for name in METHODS[method_id]["sources"]:
        path = _module_path(name)
        paths[name] = str(path)
        digest.update(str(path).encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    value = {"sha256": digest.hexdigest(), "files": paths}
    _source_digests[method_id] = value
    return value


# --------------------------------------------------------------- call recorder
CONTEXT = {"batch": None, "kind": None, "plan_id": None, "task_set_sha256": None,
           "run_id": None, "soft_limit": None}
LAST_RECORD = None
LEDGER_FAILURES = []
ADAPTERS_WITH_OPTIONS = ("EPSILON_STAR",)


class LedgerWriteError(RuntimeError):
    """The call could not be registered, so it must not be executed."""


def _batch_for(kind):
    return f"cmp_{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"


def _append(row):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in LEDGER_COLUMNS})
        handle.flush()
        os.fsync(handle.fileno())


def _epsilon(request, clock=None, **kwargs):
    from adapters import epsilon_star
    return epsilon_star.run(request, clock, **kwargs)


METHODS["EPSILON_STAR"]["adapter"] = _epsilon


def _call_reference(method_id, request, clock, **kwargs):
    if kwargs:
        raise TypeError(f"{method_id} does not accept adapter options")
    from adapters import reference_methods
    return reference_methods.run_reference(method_id, request, clock)


for _name in ("P2_MULTI", "TREE_MST", "OARP_CORE2", "PPCPP_CORE4"):
    METHODS[_name]["adapter"] = (lambda name: lambda request, clock=None, **kw:
                                 _call_reference(name, request, clock, **kw))(_name)


def available():
    out = []
    for name in ORDER:
        if name == "EPSILON_STAR" and importlib.util.find_spec("adapters.epsilon_star") is None:
            continue
        out.append(name)
    return tuple(out)


def describe(method_id):
    """Everything a report needs to name the method honestly."""
    entry = METHODS[method_id]
    digest = source_digest(method_id)
    return {
        "method_id": method_id,
        "core_version": entry["core_version"],
        "adapter_version": ADAPTER_VERSION,
        "kind": entry["kind"],
        "paper": entry["paper"],
        "adaptation_class": entry["adaptation_class"],
        "source_sha256": digest["sha256"],
        "source_files": digest["files"],
    }


def describe_all():
    return {name: describe(name) for name in available()}


def run(method_id, request, clock=None, **adapter_kwargs):
    """Execute one planner call, registered before and after with the same run id."""
    global LAST_RECORD
    if method_id not in METHODS:
        raise KeyError(f"unknown method {method_id}")
    if adapter_kwargs and method_id not in ADAPTERS_WITH_OPTIONS:
        raise TypeError(f"{method_id} does not accept adapter options: {sorted(adapter_kwargs)}")

    kind = CONTEXT.get("kind") or os.environ.get("DSH_RUN_KIND") or "unregistered"
    batch = CONTEXT.get("batch") or _batch_for(kind)
    run_id = CONTEXT.get("run_id") or uuid.uuid4().hex
    plan_id = CONTEXT.get("plan_id") or (f"{request.case_id}::{method_id}"
                                         if request is not None else method_id)
    limit = (CONTEXT.get("soft_limit")
             if CONTEXT.get("soft_limit") is not None
             else getattr(getattr(request, "termination", None), "time_limit_seconds", None))
    digest = source_digest(method_id)

    common = {
        "run_id": run_id, "batch": batch, "kind": kind,
        "registered_utc": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan_id,
        "case_id": getattr(request, "case_id", ""),
        "method_id": method_id,
        "core_version": METHODS[method_id]["core_version"],
        "adapter_version": ADAPTER_VERSION,
        "seed": getattr(request, "seed", ""),
        "soft_limit_seconds": "" if limit is None else f"{float(limit):.3f}",
        "adaptation_class": METHODS[method_id]["adaptation_class"],
        "task_set_sha256": CONTEXT.get("task_set_sha256") or "",
        "source_sha256": digest["sha256"],
    }

    try:
        _append({**common, "phase": "start"})
    except OSError as exc:
        LEDGER_FAILURES.append({"run_id": run_id, "phase": "start",
                                "plan_id": plan_id, "error": str(exc)})
        raise LedgerWriteError(f"cannot register the call start ({plan_id}): {exc}") from exc

    begin = time.perf_counter()
    error = ""
    result = None
    try:
        from problem import validate_inputs
        from labels import effective_status
        validate_inputs(request)          # inside the measured region (draft 5.5)
        result = METHODS[method_id]["adapter"](request, clock, **adapter_kwargs)
        # a run that reports "finished" but also "not natural" is a truncated run
        # holding a valid incumbent: keep the route, fix the label (see labels.py)
        label = effective_status({"status": result.status,
                                  "termination": result.termination})
        if label != result.status:
            result.meta["labelled_from"] = result.status
            result.status = label
        return result
    except Exception:
        import traceback
        error = traceback.format_exc()
        raise
    finally:
        total = time.perf_counter() - begin
        audit = getattr(result, "audit", None) or {}
        meta = getattr(result, "meta", None) or {}
        within, overrun = _budget_verdict(total, limit)
        record = {**common,
                  "phase": "end",
                  "status": getattr(result, "status", "adapter_exception"),
                  "natural": (getattr(result, "termination", None) or {}).get("natural", ""),
                  "within_budget": within,
                  "budget_overrun_seconds": overrun,
                  "call_total_seconds": f"{total:.6f}",
                  "adapter_call_seconds": f"{(getattr(result, 'stage_seconds', None) or {}).get('adapter_call', '')}",
                  "route_steps": ((len(result.route) - 1) if getattr(result, "route", ()) else ""),
                  "coverage_complete": audit.get("coverage_complete", ""),
                  "audit_valid": audit.get("valid", ""),
                  "fallback_used": getattr(result, "fallback_used", ""),
                  "completion_steps": (meta.get("route") or {}).get("completion_steps", ""),
                  "note": error.splitlines()[-1][:200] if error else ""}
        if result is not None:
            result.meta["adapter_version"] = ADAPTER_VERSION
            result.meta["core_version"] = METHODS[method_id]["core_version"]
            result.meta["source_sha256"] = digest["sha256"]
            result.meta["call_total_seconds"] = total
            result.meta["within_budget"] = within
            result.meta["budget_overrun_seconds"] = overrun
            termination = dict(getattr(result, "termination", None) or {})
            termination["within_budget"] = within
            termination["budget_overrun_seconds"] = overrun
            result.termination = termination
        try:
            _append(record)
        except OSError as exc:
            LEDGER_FAILURES.append({"run_id": run_id, "phase": "end",
                                    "plan_id": plan_id, "error": str(exc)})
            if result is not None:
                result.meta["ledger_write_error"] = str(exc)
        LAST_RECORD = record


def _budget_verdict(total, limit):
    """A call is in budget only when the whole call, validation included, fits."""
    if limit is None:
        return "", ""
    limit = float(limit)
    if total <= limit:
        return True, 0.0
    return False, round(total - limit, 6)
