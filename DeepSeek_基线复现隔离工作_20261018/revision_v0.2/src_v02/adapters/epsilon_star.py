"""EPSILON_STAR adapter, revision v0.2.

Changes against v0.1 (all three were review findings):

R1  the empty-task branch is no longer special-cased into "finished".  Every
    branch goes through :func:`finalize.finalize`, so a return flight that
    overruns the remaining resource is reported as ``resource_exceeded`` even
    when there is nothing left to cover.
R2  the public ``termination.time_limit_seconds`` is now actually enforced, as a
    cooperative soft deadline covering MAPS construction, the ETM loop, every
    connector call and the base return.  If it is crossed before a complete
    legal route exists the record says ``deadline_before_complete_route`` and the
    route is NOT completed after the deadline.  ``max_steps`` stays a separate
    iteration cap and is named as such.
R3  the stage snapshot is taken after the clock is stopped; the end-to-end time
    is reported once as ``adapter_call``; no overlapping stage is summed into a
    fake total.

Model adaptations are unchanged from ``specs/epsilon_star_adaptation.md``.
"""
import time

from deadline import Deadline, DeadlineExceeded
from finalize import finalize
from problem import environment_status
from result import PlanResult, StageClock
from common_geometry import GridMetric

from epsilon_core.maps import MAPS
from epsilon_core.etm import ETM

METHOD_ID = "EPSILON_STAR"
METHOD_VERSION = "epsilon_star_core_v0.2_20261018"

DEFAULT = {
    "credit": "transit",            # model-mandated; "waypoint" is diagnostic only
    "neighbourhood0_halfwidth": 3,  # paper's 7x7 local neighbourhood at level 0
    "forbidden_ring": 0,            # no inertia in this model -> no buffer ring
    "travel_cost": 1.0,             # Eq. (5) CTr, unit steps
    "turn_cost": 0.0,               # Eq. (5) CTu, no private turn penalty
    "max_steps": 20000,             # ITERATION cap, not a time limit
}


def _settings(request, options):
    merged = dict(DEFAULT)
    merged.update(options or {})
    for key in DEFAULT:
        if isinstance(request.meta, dict) and key in request.meta:
            merged[key] = request.meta[key]
    return merged


def run(request, clock=None, options=None, deadline_clock=None):
    """Plan with adapted epsilon-star.

    ``deadline_clock`` exists only so a test can inject a fake clock; production
    calls leave it ``None`` and use ``time.perf_counter``.
    """
    clock = clock or StageClock()
    settings = _settings(request, options)
    deadline = Deadline(request.termination.time_limit_seconds, clock=deadline_clock)

    route = ()
    natural = False
    reason = ""
    failure_status = None
    success_status = "finished"
    meta = {"settings": settings, "deadline": deadline.report()}
    errors = []
    score = {"maps_and_etm": 0.0}

    t0 = time.perf_counter()
    env = environment_status(request)
    clock.add("environment", time.perf_counter() - t0)
    meta["environment"] = env

    try:
        if not env["ok"]:
            failure_status = "environment_infeasible"
            reason = env["code"]
            errors.append(f"environment_infeasible:{env['code']}")
        else:
            metric = GridMetric(request.free)
            pending = sorted(request.pending)

            if not pending:
                # R1: returning is a real flight and must pass the same checks.
                t0 = time.perf_counter()
                deadline.check()
                route = metric.path(tuple(request.current), tuple(request.base))
                clock.add("direct_return", time.perf_counter() - t0)
                natural = True
                reason = "empty_pending_direct_return"
                meta["etm"] = None
            else:
                t0 = time.perf_counter()
                deadline.check()
                maps = MAPS(request.free, request.published_targets, request.covered,
                            forbidden_ring=settings["forbidden_ring"],
                            neighbourhood0_halfwidth=settings["neighbourhood0_halfwidth"],
                            deadline=deadline)
                clock.add("maps_constructed_seconds", time.perf_counter() - t0)
                meta["maps"] = maps.describe()

                etm = ETM(maps, request.current, seed=request.seed,
                          credit=settings["credit"],
                          travel_cost=settings["travel_cost"],
                          turn_cost=settings["turn_cost"],
                          metric=metric, deadline=deadline)
                t0 = time.perf_counter()
                etm.run(max_steps=settings["max_steps"])
                clock.add("etm_seconds", time.perf_counter() - t0)

                route = tuple(etm.route)
                terminal = etm.trace.terminal
                meta["etm"] = etm.summary()
                natural = terminal in ("FN_no_unexplored_cell", "FN_no_positive_potential")
                reason = terminal

                if terminal in ("deadline", "deadline_in_return"):
                    failure_status = "deadline_before_complete_route"
                    natural = False
                elif terminal in ("step_limit", "state_cycle", "no_progress"):
                    # artificial safety stops, never the paper's FN
                    failure_status = "safety_limit_before_complete_route"
                    success_status = "finished_with_safety_limit"
                    natural = False

                # fixed base return, inside the same deadline (R2)
                if terminal not in ("deadline",) and etm.current != tuple(request.base):
                    t0 = time.perf_counter()
                    try:
                        etm.return_to_base(tuple(request.base), deadline=deadline)
                        clock.add("return_seconds", time.perf_counter() - t0)
                    except DeadlineExceeded:
                        clock.add("return_seconds", time.perf_counter() - t0)
                        meta["deadline"]["soft_deadline_hit"] = True
                        failure_status = "deadline_before_complete_route"
                        natural = False
                        reason = "deadline_in_return"
                        meta["etm"]["terminal"] = "deadline_in_return"
                route = tuple(etm.route)
    except DeadlineExceeded as exc:
        # the deadline was crossed before a complete legal route existed
        failure_status = "deadline_before_complete_route"
        natural = False
        reason = "deadline_before_complete_route"
        route = ()
        errors.append(str(exc))
        meta["deadline"]["soft_deadline_hit"] = True
    except Exception as exc:  # noqa: BLE001 - becomes a recorded failure, not a crash
        failure_status = "adapter_assertion"
        natural = False
        reason = f"adapter_assertion:{type(exc).__name__}"
        route = ()
        errors.append(str(exc))
    finally:
        score["maps_and_etm"] = sum(value for key, value in clock.stages.items()
                                   if key != "adapter_call")

    clock.declare_missing("per_decision_timing")
    total = clock.stop_total()                     # R3: total is fixed after stop

    outcome = finalize(
        request, route,
        natural=natural, reason=reason,
        failure_status=failure_status or "no_legal_route_within_resource",
        success_status=success_status,
        errors=errors, meta=meta,
        final_source="etm_core_route" if route else "",
        best_candidate_source="etm_core_route" if route else "",
    )

    row = PlanResult(
        method_id=METHOD_ID, method_version=METHOD_VERSION,
        status=outcome["status"], reason=outcome["reason"], route=route,
        resource_check=outcome["resource_check"],
        termination=outcome["termination"],
        fallback_used=False, fallback_steps=None,
        best_candidate_source=outcome["meta"].get("best_candidate_source", ""),
        final_source="etm_core_route" if route else "",
        errors=outcome["errors"],
        meta=outcome["meta"],
    )
    row.stage_seconds = clock.snapshot()
    row.meta["adapter_seconds"] = total
    row.meta["credit_mode_note"] = (
        "transit: physical coverage credited on every traversed cell, so the "
        "WT 'task here' branch cannot fire" if settings["credit"] == "transit"
        else "waypoint: diagnostic replay of the paper's move/task separation")
    row.audit = outcome["audit"]
    return row
