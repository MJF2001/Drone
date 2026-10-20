"""Two-phase call ledger for the two references.

Only the two new method ids are registered here; the historical OARP_CORE2 keeps
its own delivery and ledger and is never imported.

``start`` is written and fsync-ed before the core runs, so a start-write failure
means zero planner work.  ``end`` is written in ``finally``; a failure there is
recorded and the batch must refuse to seal.
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
LEDGER = NEW / "logs" / "calls_ledger.csv"

COLUMNS = [
    "run_id", "phase", "batch", "kind", "registered_utc", "plan_id", "case_id",
    "method_id", "core_version", "adapter_version", "seed", "cap_override",
    "soft_limit_seconds", "status", "natural", "call_total_seconds",
    "adapter_call_seconds", "route_steps", "coverage_complete", "audit_valid",
    "fallback_selected", "rank_status", "tour_status", "within_budget",
    "candidate_accepted_in_time", "task_set_sha256", "source_sha256", "note",
]

METHODS = ("OARP_RANK0_FULLTOUR_SCENE", "OARP_REPLAN2_NATIVE_SCENE")
CONTEXT = {"batch": None, "kind": None, "plan_id": None, "task_set_sha256": None,
           "run_id": None, "soft_limit": None, "case_id": None}
LEDGER_FAILURES = []
LAST_RECORD = None


class LedgerWriteError(RuntimeError):
    """The call could not be registered, so it must not be executed."""


def source_files():
    return {
        "native": str(bootstrap.SRC / "native.py"),
        "methods": str(bootstrap.SRC / "methods.py"),
        "entry": str(bootstrap.SRC / "entry.py"),
        "adapters.registry": str(bootstrap.SRC / "adapters" / "registry.py"),
    }


_DIGEST = None


def source_digest():
    global _DIGEST
    if _DIGEST is None:
        digest = hashlib.sha256()
        files = source_files()
        for name in sorted(files):
            digest.update(name.encode("utf-8"))
            digest.update(hashlib.sha256(Path(files[name]).read_bytes()).digest())
        _DIGEST = {"sha256": digest.hexdigest(), "files": files}
    return _DIGEST


def describe(method_id):
    from methods import CORE_VERSION, ADAPTER_VERSION
    return {"method_id": method_id, "core_version": CORE_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "source_sha256": source_digest()["sha256"],
            "source_files": source_digest()["files"]}


def _append(row):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in COLUMNS})
        handle.flush()
        os.fsync(handle.fileno())


def run(method_id, request, *, seconds, seed, clock=None, **kwargs):
    global LAST_RECORD
    if method_id not in METHODS:
        raise KeyError(f"unregistered method {method_id}")

    import entry
    from methods import CORE_VERSION, ADAPTER_VERSION

    kind = CONTEXT.get("kind") or os.environ.get("DSH_RUN_KIND") or "unregistered"
    batch = CONTEXT.get("batch") or f"oarp_{kind}"
    run_id = CONTEXT.get("run_id") or uuid.uuid4().hex
    plan_id = CONTEXT.get("plan_id") or f"{CONTEXT.get('case_id') or 'case'}::{method_id}"
    digest = source_digest()
    common = {
        "run_id": run_id, "batch": batch, "kind": kind,
        "registered_utc": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan_id, "case_id": CONTEXT.get("case_id") or getattr(request, "case_id", ""),
        "method_id": method_id, "core_version": CORE_VERSION,
        "adapter_version": ADAPTER_VERSION, "seed": seed,
        "cap_override": kwargs.get("cap_override", ""),
        "soft_limit_seconds": f"{float(seconds):.3f}",
        "task_set_sha256": CONTEXT.get("task_set_sha256") or "",
        "source_sha256": digest["sha256"],
    }
    try:
        _append({**common, "phase": "start"})
    except OSError as exc:
        LEDGER_FAILURES.append({"run_id": run_id, "phase": "start", "error": str(exc)})
        raise LedgerWriteError(f"cannot register the call start ({plan_id}): {exc}") from exc

    begin = time.perf_counter()
    error = ""
    result = None
    try:
        result = entry.run(request, method_id, seconds=seconds, seed=seed, clock=clock,
                           **kwargs)
        return result
    except Exception:
        import traceback
        error = traceback.format_exc()
        raise
    finally:
        total = time.perf_counter() - begin
        flags = (getattr(result, "meta", None) or {}).get("flags") or {}
        detail = (getattr(result, "meta", None) or {}).get("core_detail") or {}
        record = {
            **common, "phase": "end",
            "status": getattr(result, "status", "adapter_exception"),
            "natural": (getattr(result, "termination", None) or {}).get("natural", ""),
            "call_total_seconds": f"{total:.6f}",
            "adapter_call_seconds": f"{(getattr(result, 'stage_seconds', None) or {}).get('_sum', total):.6f}",
            "route_steps": ((len(result.route) - 1) if getattr(result, "route", ()) else ""),
            "coverage_complete": (getattr(result, "audit", None) or {}).get("coverage_complete", ""),
            "audit_valid": (getattr(result, "audit", None) or {}).get("valid", ""),
            "fallback_selected": flags.get("fallback_selected", ""),
            "rank_status": detail.get("rank_status", ""),
            "tour_status": detail.get("tour_status", ""),
            "within_budget": flags.get("call_within_budget", ""),
            "candidate_accepted_in_time": flags.get("candidate_accepted_in_time", ""),
            "note": error.splitlines()[-1][:200] if error else "",
        }
        if result is not None:
            result.meta["ledger"] = {"run_id": run_id, "batch": batch, "kind": kind,
                                     "call_total_seconds": total}
        try:
            _append(record)
        except OSError as exc:
            LEDGER_FAILURES.append({"run_id": run_id, "phase": "end", "error": str(exc)})
            if result is not None:
                result.meta["ledger_write_error"] = str(exc)
        LAST_RECORD = record
