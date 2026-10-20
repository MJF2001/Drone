"""EPSILON_STAR adapter: core adaptation of epsilon-star to the current model.

Labelled ``EPSILON_STAR_CORE`` because the two central mechanisms are kept --
the multiscale MAPS of Eq. (2)-(3) and the ETM state machine of Algorithm 1 with
level-by-level escape from a local extremum -- while several model adaptations
are unavoidable and are listed in ``specs/epsilon_star_adaptation.md``.

Nothing here is a full reproduction of the paper's Player/Stage experiments, and
the paper's completeness theorem is not re-proved for this model.
"""
import time

from result import PlanResult, StageClock
from problem import environment_status
from common_geometry import GridMetric

from epsilon_core.maps import MAPS
from epsilon_core.etm import ETM

METHOD_ID = "EPSILON_STAR"
METHOD_VERSION = "epsilon_star_core_v0.1_20261018"

DEFAULT = {
    "credit": "transit",          # model-mandated; "waypoint" is diagnostic only
    "neighbourhood0_halfwidth": 3,  # paper's 7x7 local neighbourhood at level 0
    "forbidden_ring": 0,          # no inertia in this model -> no buffer ring
    "travel_cost": 1.0,           # Eq. (5) CTr, unit steps
    "turn_cost": 0.0,             # Eq. (5) CTu, no private turn penalty
    "max_steps": 20000,
}


def run(request, clock=None, options=None):
    settings = dict(DEFAULT)
    settings.update(options or {})
    clock = clock or StageClock()
    clock.start("adapter_call")
    stage = {}

    try:
        env = environment_status(request)
        if not env["ok"]:
            return PlanResult(
                method_id=METHOD_ID, method_version=METHOD_VERSION,
                status="environment_infeasible", reason=env["code"],
                resource_check={"limit": request.resource_limit(), "used": None, "ok": False},
                termination={"natural": False, "reason": "environment_infeasible"},
                stage_seconds=clock.as_dict(), meta={"environment": env})

        metric = GridMetric(request.free)
        pending = sorted(request.pending)

        # ---- empty Q: nothing to cover, only the return flight remains
        if not pending:
            route = metric.path(tuple(request.current), tuple(request.base))
            return PlanResult(
                method_id=METHOD_ID, method_version=METHOD_VERSION,
                status="finished", reason="empty_pending_direct_return",
                route=route,
                resource_check={"limit": request.resource_limit(),
                                "used": len(route) - 1,
                                "ok": None if request.resource_limit() is None
                                else len(route) - 1 <= request.resource_limit()},
                termination={"natural": True, "reason": "nothing_pending"},
                final_source="direct_return", best_candidate_source="direct_return",
                stage_seconds=clock.as_dict(),
                meta={"settings": settings, "environment": env})

        # ---- MAPS construction
        t0 = time.perf_counter()
        maps = MAPS(request.free, request.published_targets, request.covered,
                    forbidden_ring=settings["forbidden_ring"],
                    neighbourhood0_halfwidth=settings["neighbourhood0_halfwidth"])
        stage["maps_constructed_seconds"] = time.perf_counter() - t0

        # ---- ETM
        etm = ETM(maps, request.current, seed=request.seed, credit=settings["credit"],
                  travel_cost=settings["travel_cost"], turn_cost=settings["turn_cost"],
                  metric=metric)
        t0 = time.perf_counter()
        etm.run(max_steps=settings["max_steps"])
        stage["etm_seconds"] = time.perf_counter() - t0

        # ---- fixed base return (adaptation: the paper halts at FN in place)
        t0 = time.perf_counter()
        if etm.current != tuple(request.base):
            etm.return_to_base(tuple(request.base))
        stage["return_seconds"] = time.perf_counter() - t0

        route = tuple(etm.route)
        steps = len(route) - 1
        missing = sorted(request.pending - etm.physically_covered)
        limit = request.resource_limit()

        if missing:
            status = "coverage_incomplete"
            reason = f"coverage_omitted:{len(missing)}"
        elif limit is not None and steps > limit:
            status = "resource_exceeded"
            reason = "distance_budget_exceeded"
        else:
            status = "finished"
            reason = etm.trace.terminal or "FN_no_unexplored_cell"

        natural = etm.trace.terminal not in ("step_limit", "state_cycle", "no_progress")
        termination = {
            "natural": natural,
            "reason": reason if natural else "safety_limit_triggered",
            "etm_terminal": etm.trace.terminal,
            "machine_state": etm.state,
        }

        clock.add("maps_and_etm", sum(stage.values()))
        return PlanResult(
            method_id=METHOD_ID, method_version=METHOD_VERSION,
            status=status, reason=reason, route=route,
            resource_check={"limit": limit, "used": steps,
                            "ok": None if limit is None else steps <= limit},
            termination=termination,
            fallback_used=False, fallback_steps=None,
            best_candidate_source="etm_core_route",
            final_source="etm_core_route",
            stage_seconds={**clock.stages, **stage},
            errors=[f"missing:{len(missing)}"] if missing else [],
            meta={
                "settings": settings,
                "environment": env,
                "maps": maps.describe(),
                "etm": etm.summary(),
                "pending_at_start": len(pending),
                "deferred_at_start": len(request.deferred),
                "credit_mode_note": (
                    "transit: physical coverage credited on every traversed cell, so the "
                    "WT 'task here' branch cannot fire" if settings["credit"] == "transit"
                    else "waypoint: diagnostic replay of the paper's move/task separation"),
            })
    finally:
        clock.stop()
