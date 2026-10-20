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
    """Only genuinely instrumented stages.  Nothing is inferred from the total."""
    stages = {}
    ambiguous = False
    for event in detail.get("events") or []:
        name = event.get("stage")
        if name is None or "start" not in event or "end" not in event:
            ambiguous = True
            continue
        stages[name] = stages.get(name, 0.0) + (event["end"] - event["start"])
    if ambiguous:
        stages["_unbounded_events_excluded"] = 1
    return stages


def _termination(status):
    if status in TERMINAL_NATURAL:
        return {"natural": True, "reason": status}
    if status in TERMINAL_TRUNCATED:
        return {"natural": False, "reason": "wall_clock_cap_triggered", "method_status": status}
    return {"natural": False, "reason": "no_legal_route", "method_status": status}


def _envelope(method_id, method_version, request, raw, clock):
    # P2_MULTI returns its instrumented trace at the top level (no 'detail' key),
    # OARP_CORE2 and PPCPP_CORE4 nest it.  Handle both shapes so no stage timing
    # or candidate source is silently dropped.
    detail = raw.get("detail")
    if not isinstance(detail, dict):
        detail = raw
    status = raw.get("status", "unknown")
    source = raw.get("source")
    stage = _stage_seconds(detail)
    stage["adapter_call"] = clock.stages.get("adapter_call", 0.0)
    version = method_version
    if method_id == PPCPP_METHOD:
        version = detail.get("version", method_version)
    route = tuple(raw.get("route") or ())
    if not route and status in TERMINAL_NATURAL:
        # The frozen entries report a natural finish even when no legal incumbent
        # fits the resource limit (verified on the m12_resource_tight fixture).
        # The adapter must not repeat that claim, so the status is downgraded and
        # the engine's own status is kept in meta.
        status = "no_legal_route_within_resource"
    return PlanResult(
        method_id=method_id,
        method_version=version,
        status=status,
        reason=str(raw.get("reason") or detail.get("error") or detail.get("interruption") or ""),
        route=route,
        resource_check={"reported_seconds": raw.get("seconds"),
                        "budget_seconds": request.termination.time_limit_seconds,
                        "overrun_gt_10ms": raw.get("overrun_gt_10ms")},
        termination=_termination(status),
        fallback_used=bool(raw.get("fallback_selected")) or source in FALLBACK_SOURCES,
        fallback_steps=_fallback_steps(detail),
        best_candidate_source=source or "",
        final_source=source or "",
        stage_seconds=stage,
        errors=[str(x) for x in (detail.get("error"), detail.get("interruption")) if x],
        meta={
            "frozen_methods": list(portable_frozen.METHODS),
            "engine_status": raw.get("status"),
            "engine_reason": raw.get("reason"),
            "improvements": detail.get("improvements"),
            "core_finished": raw.get("core_finished"),
            "core_status": detail.get("core_status"),
            "core_steps": detail.get("core_steps"),
            "active_stage": raw.get("active_stage"),
            "engine_seconds": raw.get("seconds"),
            "shared_fallback_names": list(FALLBACK_SOURCES),
            "solver": (detail.get("tour") or {}).get("solver") if isinstance(detail.get("tour"), dict) else None,
            "rank_cap": detail.get("rank_cap"),
            "rank_status": (detail.get("rank") or {}).get("status") if isinstance(detail.get("rank"), dict) else None,
            "block_count": len(detail.get("blocks") or []) if detail.get("blocks") else None,
        },
    )


def run_reference(method_id, request, clock=None):
    """Run one of the four pre-existing methods unchanged."""
    clock = clock or StageClock()
    clock.start("adapter_call")
    try:
        env = environment_status(request)
        if not env["ok"]:
            clock.stop()
            return PlanResult(method_id=method_id,
                              method_version=_version(method_id),
                              status="environment_infeasible",
                              reason=f"{env['code']}",
                              resource_check={"limit": request.resource_limit(), "used": None, "ok": False},
                              termination={"natural": False, "reason": "environment_infeasible"},
                              stage_seconds=clock.as_dict(),
                              meta={"environment": env})
        snapshot = request.to_snapshot()
        budget = float(request.termination.time_limit_seconds)
        history_targets = sorted(request.history_targets)
        try:
            raw = _call(method_id, snapshot, history_targets, budget, request.seed)
        except (ValueError, AssertionError, RuntimeError, TimeoutError) as exc:
            # A method-specific input precondition or an internal assertion.
            # The record is kept together with its traceback; nothing is repaired
            # here and no substitute route is produced.
            import traceback
            return PlanResult(
                method_id=method_id, method_version=_version(method_id),
                status=_rejection_status(str(exc)), reason=str(exc),
                resource_check={"limit": request.resource_limit(), "used": None, "ok": False},
                termination={"natural": False, "reason": "adapter_rejected_input"},
                stage_seconds=clock.as_dict(),
                errors=[str(exc)],
                meta={"environment": env, "traceback": traceback.format_exc(),
                      "adapter_note": "the frozen entry point rejected this input; "
                                      "no substitute route was produced"})
        result = _envelope(method_id, _version(method_id), request, raw, clock)
        result.meta["environment"] = env
        result.meta["snapshot_description"] = {
            "targets": len(snapshot.targets), "covered": len(snapshot.covered),
            "radius": snapshot.radius, "distance_budget": snapshot.distance_budget,
        }
        return result
    finally:
        clock.stop()


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
