"""Two-phase call recorder for this round.

Only ``EPSILON_STAR`` is registered.  The protections are the ones accepted in
v0.3, kept in a local copy because the v0.3 registry points its ledger at the old
delivery directory:

* a ``start`` row is written and ``fsync``-ed **before** the planner runs; if that
  write fails the call is aborted and the planner is never invoked;
* an ``end`` row is written in ``finally``; if it fails the result is returned but
  the failure is recorded and the batch must not be sealed;
* the public ledger is append-only and sealed by a prefix hash after each batch;
* the ``run_id`` comes from the caller so a parent watchdog can correlate a killed
  child with its rows.
"""
import csv
import hashlib
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bootstrap

NEW = bootstrap.NEW
LEDGER = NEW / "logs" / "call_ledger.csv"

LEDGER_COLUMNS = [
    "run_id", "phase", "batch", "kind", "registered_utc", "plan_id", "case_id",
    "method_id", "core_version", "adapter_version", "seed", "soft_limit_seconds",
    "status", "natural", "call_total_seconds", "adapter_call_seconds",
    "route_steps", "coverage_complete", "audit_valid", "terminal",
    "first_physical_index", "control_fn_index", "return_steps", "task_set_sha256",
    "source_sha256", "note",
]

METHOD_ID = "EPSILON_STAR"

CONTEXT = {"batch": None, "kind": None, "plan_id": None, "task_set_sha256": None,
           "run_id": None, "soft_limit": None}

LEDGER_FAILURES = []
LAST_RECORD = None


class LedgerWriteError(RuntimeError):
    """The call could not be registered, so it must not be executed."""


def source_files():
    return {
        "core.maps": str(bootstrap.SRC / "core" / "maps.py"),
        "core.etm": str(bootstrap.SRC / "core" / "etm.py"),
        "adapters.epsilon_star": str(bootstrap.SRC / "adapters" / "epsilon_star.py"),
    }


_DIGEST = None


def source_digest():
    global _DIGEST
    if _DIGEST is not None:
        return _DIGEST
    digest = hashlib.sha256()
    files = source_files()
    for name in sorted(files):
        path = Path(files[name])
        digest.update(name.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    _DIGEST = {"sha256": digest.hexdigest(), "files": files}
    return _DIGEST


def describe():
    from adapters import epsilon_star
    digest = source_digest()
    return {
        "method_id": METHOD_ID,
        "core_version": epsilon_star.CORE_VERSION,
        "adapter_version": epsilon_star.ADAPTER_VERSION,
        "adaptation_class": epsilon_star.ADAPTATION_CLASS,
        "parameters": {"control_mode": epsilon_star.DEFAULT_MODE,
                       "travel_cost": epsilon_star.DEFAULT_TRAVEL_COST,
                       "turn_cost": epsilon_star.DEFAULT_TURN_COST,
                       "turn_cost_units": "per degree from the heading",
                       "max_control_iterations": epsilon_star.DEFAULT_MAX_STEPS,
                       "initial_heading": None},
        "source_sha256": digest["sha256"],
        "source_files": digest["files"],
    }


def available():
    return (METHOD_ID,)


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


def run(method_id, request, clock=None, **adapter_kwargs):
    global LAST_RECORD
    if method_id != METHOD_ID:
        raise KeyError(f"only {METHOD_ID} is registered in this round, got {method_id}")

    from adapters import epsilon_star

    kind = CONTEXT.get("kind") or os.environ.get("DSH_RUN_KIND") or "unregistered"
    batch = CONTEXT.get("batch") or f"eps_{kind}"
    run_id = CONTEXT.get("run_id") or uuid.uuid4().hex
    plan_id = CONTEXT.get("plan_id") or f"{request.case_id}::{method_id}"
    limit = (CONTEXT.get("soft_limit") if CONTEXT.get("soft_limit") is not None
             else getattr(request.termination, "time_limit_seconds", None))
    digest = source_digest()

    common = {
        "run_id": run_id, "batch": batch, "kind": kind,
        "registered_utc": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan_id, "case_id": getattr(request, "case_id", ""),
        "method_id": method_id,
        "core_version": epsilon_star.CORE_VERSION,
        "adapter_version": epsilon_star.ADAPTER_VERSION,
        "seed": getattr(request, "seed", ""),
        "soft_limit_seconds": "" if limit is None else f"{float(limit):.3f}",
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
        # input checking happens inside the adapter, so it is part of the public
        # call time and an invalid request still produces a graded record instead
        # of an exception escaping the runner
        result = epsilon_star.run(request, clock, **adapter_kwargs)
        return result
    except Exception:
        import traceback
        error = traceback.format_exc()
        raise
    finally:
        total = time.perf_counter() - begin
        meta = getattr(result, "meta", None) or {}
        audit = getattr(result, "audit", None) or {}
        events = meta.get("events") or {}
        record = {
            **common, "phase": "end",
            "status": getattr(result, "status", "adapter_exception"),
            "natural": (getattr(result, "termination", None) or {}).get("natural", ""),
            "call_total_seconds": f"{total:.6f}",
            "adapter_call_seconds": f"{(getattr(result, 'stage_seconds', None) or {}).get('_sum', total):.6f}"
            if getattr(result, "stage_seconds", None) else f"{total:.6f}",
            "route_steps": ((len(result.route) - 1) if getattr(result, "route", ()) else ""),
            "coverage_complete": audit.get("coverage_complete", ""),
            "audit_valid": audit.get("valid", ""),
            "terminal": (meta.get("engine") or {}).get("terminal", ""),
            "first_physical_index": events.get("index_first_physical_complete", ""),
            "control_fn_index": events.get("index_control_fn", ""),
            "return_steps": events.get("return_steps", ""),
            "note": error.splitlines()[-1][:200] if error else "",
        }
        if result is not None:
            result.meta["ledger"] = {"run_id": run_id, "batch": batch, "kind": kind,
                                     "call_total_seconds": total}
        try:
            _append(record)
        except OSError as exc:
            LEDGER_FAILURES.append({"run_id": run_id, "phase": "end",
                                    "plan_id": plan_id, "error": str(exc)})
            if result is not None:
                result.meta["ledger_write_error"] = str(exc)
        LAST_RECORD = record
