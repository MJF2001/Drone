"""Adapters for the four methods that already existed.

Nothing is re-implemented.  Each adapter calls the frozen / candidate entry
point that was copied byte-for-byte into ``sources/reference_tree`` and only
translates the request/result envelopes.  Behaviour identity is asserted in
``tests/test_behavior_identity.py`` against a direct call to the same entry
point.

``P2_MULTI`` / ``OARP_CORE2`` / ``TREE_MST``  -> frozen v2 ``baseline_suite.solve``
``PPCPP_CORE4``                              -> candidate ``v0.1_20261014`` loader

Both preserve their own shared fallback candidates (old suffix / common greedy
sweep).  The adapter reports how much of the final route came from that shared
fallback; it never removes it and never adds a P2 post-processing step.
"""
import sys

import bootstrap  # noqa: F401  (installs the frozen source and .deps)

import portable_frozen
from baseline_suite import solve as frozen_solve
from result import PlanResult, StageClock

from common_geometry import GridMetric
from finalize import finalize, SUCCESS_STATUSES
from problem import environment_status

FROZEN_METHODS = ("P2_MULTI", "OARP_CORE2", "TREE_MST")
PPCPP_METHOD = "PPCPP_CORE4"

FALLBACK_SOURCES = ("old_suffix", "common_fallback", "common_old_suffix", "common_GD_adapter")

TERMINAL_NATURAL = ("planned", "finished")
TERMINAL_TRUNCATED = ("planned_at_timeout", "deadline", "timeout")


def _fallback_steps(detail):
    improvements = detail.get("improvements") or []
    for record in improvements:
        if record.get("source") in FALLBACK_SOURCES:
            return record.get("steps")
    return None


def _stage_seconds(detail):
    """Only genuinely instrumented stages, made DISJOINT (R3).

    The frozen P2 instrumentation nests ``<label>_passes`` inside
    ``<label>_opt``; summing both would double count.  The inner record is
    dropped and listed, so the returned stages can be summed without exceeding
    the end-to-end time.
    """
    stages = {}
    ambiguous = False
    for event in detail.get("events") or []:
        name = event.get("stage")
        if name is None or "start" not in event or "end" not in event:
            ambiguous = True
            continue
        stages[name] = stages.get(name, 0.0) + (event["end"] - event["start"])
    dropped = []
    for name in sorted(stages):
        if not name.endswith("_passes"):
            continue
        stem = name[: -len("_passes")]
        # the frozen instrumentation nests "<label>_passes" inside either
        # "<label>_opt" (core 2-opt / multi-start) or "<label>" (the deep pass)
        if stem in stages or (stem + "_opt") in stages:
            dropped.append(name)
    for name in dropped:
        stages.pop(name, None)
    if dropped:
        stages["_overlapping_dropped"] = 1
        stages["_overlapping_names"] = ",".join(dropped)
    if ambiguous:
        stages["_unbounded_events_excluded"] = 1
    return stages



def run_reference(method_id, request, clock=None):
    """Run one of the four pre-existing methods unchanged.

    v0.2 (R3): the end-to-end time is fixed by ``clock.stop_total()`` *before*
    the stage snapshot is taken, so ``adapter_call`` is a real measurement.  The
    stage snapshot is attached afterwards; no overlapping stage is summed.
    v0.2 also routes every branch through ``finalize`` so that a success status
    always implies legal movement, a returned base and a satisfied resource.
    """
    clock = clock or StageClock()
    result = None
    try:
        env = environment_status(request)
        if not env["ok"]:
            result = _build(method_id, request, env, route=(), raw=None,
                            status="environment_infeasible", reason=str(env["code"]),
                            meta={"environment": env}, clock=None)
            return result
        snapshot = request.to_snapshot()
        budget = float(request.termination.time_limit_seconds)
        history_targets = sorted(request.history_targets)
        try:
            raw = _call(method_id, snapshot, history_targets, budget, request.seed)
        except (ValueError, AssertionError, RuntimeError, TimeoutError) as exc:
            import traceback
            result = _build(method_id, request, env, route=(), raw=None,
                            status=_rejection_status(str(exc)), reason=str(exc),
                            meta={"environment": env, "traceback": traceback.format_exc(),
                                  "adapter_note": "the frozen entry point rejected this input; "
                                                  "no substitute route was produced"},
                            clock=None)
            return result
        result = _build(method_id, request, env, route=tuple(raw.get("route") or ()),
                        raw=raw, status=raw.get("status", "unknown"),
                        reason="", meta={}, clock=None, snapshot=snapshot)
        return result
    finally:
        if result is not None:
            clock.stop_total()                       # R3: total fixed after stop
            snapshot = clock.snapshot()
            engine = result.meta.pop("engine_stages", None) or {}
            if engine:
                for name, seconds in engine.items():
                    if name.startswith("_"):
                        continue           # bookkeeping, not a measured stage
                    snapshot[f"engine:{name}"] = seconds
                    snapshot["_instrumented"].append(f"engine:{name}")
                if engine.get("_overlapping_names"):
                    snapshot["_engine_overlapping_dropped"] = engine["_overlapping_names"]
            else:
                # say it is missing instead of reporting 0.0 as a measurement
                snapshot["_missing"].append("internal_stage_split")
                result.meta["engine_stage_instrumentation"] = "none"
            result.stage_seconds = snapshot


def _build(method_id, request, env, *, route, raw, status, reason, meta, clock,
           snapshot=None):
    """Assemble a PlanResult through the shared finalizer (v0.2)."""
    detail = {}
    if isinstance(raw, dict):
        nested = raw.get("detail")
        detail = nested if isinstance(nested, dict) else raw
    stage = _stage_seconds(detail)
    source = (raw or {}).get("source")
    engine_status = (raw or {}).get("status", status)
    natural = engine_status in TERMINAL_NATURAL
    success_status = engine_status if engine_status in SUCCESS_STATUSES else "finished"

    if status in ("environment_infeasible", "input_precondition_unmet", "adapter_assertion"):
        failure_status = status
    else:
        failure_status = _failure_hint(engine_status)

    # v0.2 (R1): when the engine produced no route at all, say WHY.  If even the
    # direct return does not fit the remaining resource, the resource is the
    # reason, not "the planner failed".
    if not route and failure_status in ("no_legal_route_within_resource", "planning_failure"):
        limit = request.resource_limit()
        if limit is not None:
            try:
                direct = GridMetric(request.free).distance(tuple(request.current),
                                                           tuple(request.base))
            except Exception:                                   # noqa: BLE001
                direct = None
            if direct is not None and direct > limit:
                failure_status = "no_legal_route_within_resource"
                reason = f"resource_exceeds_direct_return:{direct}>{limit}"

    fallback_used = bool((raw or {}).get("fallback_selected")) or source in FALLBACK_SOURCES
    outcome = finalize(
        request, route,
        natural=natural and status not in ("environment_infeasible",
                                           "input_precondition_unmet",
                                           "adapter_assertion"),
        reason=reason or str((raw or {}).get("reason") or ""),
        failure_status=failure_status,
        success_status=success_status,
        errors=[str(x) for x in (detail.get("error"), detail.get("interruption")) if x],
        meta=dict(meta))

    merged = dict(meta)
    merged.update(outcome["meta"])
    merged.update({
        "frozen_methods": list(portable_frozen.METHODS),
        "engine_status": engine_status,
        "engine_reason": (raw or {}).get("reason"),
        "improvements": detail.get("improvements"),
        "core_finished": (raw or {}).get("core_finished"),
        "core_status": detail.get("core_status"),
        "core_steps": detail.get("core_steps"),
        "active_stage": (raw or {}).get("active_stage"),
        "engine_seconds": (raw or {}).get("seconds"),
        "shared_fallback_names": list(FALLBACK_SOURCES),
        "solver": (detail.get("tour") or {}).get("solver") if isinstance(detail.get("tour"), dict) else None,
        "rank_cap": detail.get("rank_cap"),
        "rank_status": (detail.get("rank") or {}).get("status") if isinstance(detail.get("rank"), dict) else None,
        "block_count": len(detail.get("blocks") or []) if detail.get("blocks") else None,
        "environment": env,
        "engine_stage_instrumentation": "engine_events" if stage else "none",
        "engine_stages": stage,
    })
    if snapshot is not None:
        merged["snapshot_description"] = {
            "targets": len(snapshot.targets), "covered": len(snapshot.covered),
            "radius": snapshot.radius, "distance_budget": snapshot.distance_budget,
        }

    version = _version(method_id)
    if method_id == PPCPP_METHOD:
        version = detail.get("version", version)
    row = PlanResult(
        method_id=method_id, method_version=version,
        status=outcome["status"], reason=outcome["reason"], route=route,
        resource_check=outcome["resource_check"],
        termination=outcome["termination"],
        fallback_used=fallback_used, fallback_steps=_fallback_steps(detail),
        best_candidate_source=source or "", final_source=source or "",
        stage_seconds={},
        errors=outcome["errors"], meta=merged)
    row.audit = outcome["audit"]          # v0.2: the independent audit is carried
    return row


def _failure_hint(engine_status):
    return {"timeout": "timeout",
            "deadline": "no_legal_route_within_resource",
            "planning_failure": "planning_failure",
            "environment_infeasible": "environment_infeasible"}.get(
                engine_status, "no_legal_route_within_resource")


def _version(method_id):
    if method_id in FROZEN_METHODS:
        return "v2_20261012"
    return "v0.1_20261014"


def _rejection_status(message):
    """Distinguish an input precondition from an internal assertion."""
    if "old route omitted original pending targets" in message:
        # OARP_CORE2's rank reference needs the old route to enumerate every
        # original pending cell; see specs/oarp_core2_mechanism.md.
        return "input_precondition_unmet"
    return "adapter_assertion"


def _call(method_id, snapshot, history_targets, budget, seed):
    if method_id in FROZEN_METHODS:
        return frozen_solve(snapshot, history_targets, method_id, budget, seed, portable_frozen.PROFILE)
    if method_id == PPCPP_METHOD:
        loader = bootstrap.load_ppcpp_candidate()
        return loader.solve(snapshot, history_targets, budget, seed)
    raise ValueError(f"unknown reference method: {method_id}")
