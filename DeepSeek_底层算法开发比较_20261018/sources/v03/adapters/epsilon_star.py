"""EPSILON_STAR adapter, revision v0.3.

v0.3 closes two review items on top of v0.2:

**A - the deadline no longer leaks, and its metadata is final, not initial**
    * every expensive step is bracketed by ``deadline.check()`` (construction,
      the ETM loop, each connector call, the return flight, and the pre-return
      audit);
    * each complete candidate records when it was generated, when its audit
      finished and whether it was accepted;
    * a candidate whose *audit* finishes after the deadline is NOT a pre-deadline
      candidate: the graded route becomes empty, the status becomes
      ``deadline_before_complete_route``, and the late route is kept only as
      ``meta.diagnostic_route`` with its timings;
    * ``meta.deadline`` is written at the very end, so ``checks``, ``elapsed`` and
      ``hit`` are the real final values.

**B - the pre-return legality check is inside the measured cost**
    ``finalize`` (which audits the route) runs before ``clock.stop_total()``, so
    ``adapter_call`` covers construction + search + connector + return + the
    mandatory result validation.  External post-hoc audit is still separate.

Model adaptations are unchanged from ``revision_v0.2`` / ``specs/epsilon_star_adaptation.md``.
"""
import time

from deadline import Deadline, DeadlineExceeded
from finalize import finalize, SUCCESS_STATUSES
from problem import environment_status
from result import PlanResult, StageClock
from common_geometry import GridMetric

from epsilon_core.maps import MAPS
from epsilon_core.etm import ETM

METHOD_ID = "EPSILON_STAR"
METHOD_VERSION = "epsilon_star_core_v0.3_20261018"

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

    ``deadline_clock`` is a test hook for a controllable clock; production calls
    leave it ``None`` and use ``time.perf_counter``.
    """
    clock = clock or StageClock()
    settings = _settings(request, options)
    deadline = Deadline(request.termination.time_limit_seconds, clock=deadline_clock)
    meta = {"settings": settings}
    errors = []
    route = ()
    natural = False
    reason = ""
    failure_status = None
    success_status = "finished"

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
                deadline.check()
                t0 = time.perf_counter()
                route = metric.path(tuple(request.current), tuple(request.base))
                clock.add("direct_return", time.perf_counter() - t0)
                deadline.check()              # A: the connector may cross it
                natural = True
                reason = "empty_pending_direct_return"
                meta["etm"] = None
            else:
                deadline.check()
                t0 = time.perf_counter()
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

                terminal = etm.trace.terminal
                natural = terminal in ("FN_no_unexplored_cell", "FN_no_positive_potential")
                reason = terminal
                meta["etm"] = etm.summary()

                if terminal == "deadline":
                    failure_status = "deadline_before_complete_route"
                    natural = False
                elif terminal in ("step_limit", "state_cycle", "no_progress"):
                    failure_status = "safety_limit_before_complete_route"
                    success_status = "finished_with_safety_limit"
                    natural = False

                if terminal != "deadline" and etm.current != tuple(request.base):
                    t0 = time.perf_counter()
                    try:
                        etm.return_to_base(tuple(request.base), deadline=deadline)
                        clock.add("return_seconds", time.perf_counter() - t0)
                    except DeadlineExceeded:
                        clock.add("return_seconds", time.perf_counter() - t0)
                        failure_status = "deadline_before_complete_route"
                        natural = False
                        reason = "deadline_in_return"
                        meta["etm"]["terminal"] = "deadline_in_return"
                route = tuple(etm.route)
    except DeadlineExceeded as exc:
        failure_status = "deadline_before_complete_route"
        natural = False
        reason = "deadline_before_complete_route"
        route = ()
        errors.append(str(exc))
    except Exception as exc:  # noqa: BLE001 - becomes a recorded failure, not a crash
        failure_status = "adapter_assertion"
        natural = False
        reason = f"adapter_assertion:{type(exc).__name__}"
        route = ()
        errors.append(str(exc))

    return _finish(request, route, clock, deadline, natural=natural, reason=reason,
                   failure_status=failure_status, success_status=success_status,
                   errors=errors, meta=meta)


def _finish(request, route, clock, deadline, *, natural, reason, failure_status,
            success_status, errors, meta):
    """Audit the candidate inside the measured cost, then stop the clock (A + B)."""
    generated = deadline.elapsed()
    diagnostic = ()
    late = False

    # A: never audit after the deadline and then call the result a candidate
    try:
        deadline.check()
    except DeadlineExceeded as exc:
        errors.append(f"deadline_before_audit:{exc}")
        diagnostic = tuple(route)
        route = ()
        failure_status = "deadline_before_complete_route"
        success_status = "deadline_before_complete_route"
        natural = False
        reason = "deadline_before_audit"
        late = True

    outcome = finalize(request, route, natural=natural, reason=reason,
                       failure_status=failure_status or "no_legal_route_within_resource",
                       success_status=success_status, errors=errors, meta=meta)
    audited = deadline.elapsed()

    if not late and audited > deadline.limit:
        # the audit itself crossed the deadline: the candidate is post-deadline
        late = True
        deadline.hit = True
        diagnostic = tuple(route)
        route = ()                       # the late route is never the graded route
        carried = list(outcome["errors"]) + ["post_deadline_candidate_excluded"]
        meta = dict(outcome["meta"])
        meta["diagnostic_audit"] = {
            "status": outcome["status"], "errors": outcome["errors"],
            "route_steps": outcome["audit"].get("route_steps"),
            "valid": outcome["audit"].get("valid")}
        outcome = finalize(request, (), natural=False,
                           reason="deadline_before_complete_route",
                           failure_status="deadline_before_complete_route",
                           success_status="deadline_before_complete_route",
                           errors=carried, meta=meta)

    total = clock.stop_total()                      # B: after finalize
    row = PlanResult(
        method_id=METHOD_ID, method_version=METHOD_VERSION,
        status=outcome["status"], reason=outcome["reason"], route=tuple(route),
        resource_check=outcome["resource_check"],
        termination=outcome["termination"],
        fallback_used=False, fallback_steps=None,
        best_candidate_source="etm_core_route" if route else "",
        final_source="etm_core_route" if route else "",
        errors=outcome["errors"], meta=outcome["meta"], stage_seconds={})
    row.stage_seconds = clock.snapshot()
    row.audit = outcome["audit"]
    row.meta["adapter_seconds"] = total
    row.meta["deadline"] = deadline.report()        # A: final, not initial
    row.meta["candidate"] = {
        "generated_seconds": generated,
        "validated_seconds": audited,
        "accepted": outcome["status"] in SUCCESS_STATUSES,
        "post_deadline": late,
        "diagnostic_route_steps": (len(diagnostic) - 1) if diagnostic else None,
    }
    if diagnostic:
        row.meta["diagnostic_route"] = [list(p) for p in diagnostic]
        row.meta["diagnostic_route_source"] = "produced but not validated before the deadline"
    row.meta["credit_mode_note"] = (
        "transit: physical coverage credited on every traversed cell, so the "
        "WT 'task here' branch cannot fire"
        if row.meta["settings"]["credit"] == "transit"
        else "waypoint: diagnostic replay of the paper's move/task separation")
    return row
