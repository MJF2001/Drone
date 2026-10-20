"""The public entry shared by both references.

One deadline covers the whole call: input checks, normalisation, geometry, the
shared fallback, rank model construction and solve, the GTSP matrix and search, the
route expansion and the pre-return audit.

The candidate boundary is explicit and kept as three separate instants:

    generated  -> the core produced a route
    audited    -> the independent audit finished
    accepted   -> complete + returned + within resource AND audited before the deadline

A late candidate never becomes a graded result; it is kept as ``diagnostic_route``.
``candidate_accepted_in_time`` and ``call_within_budget`` are recorded separately:
an early legal candidate is not erased by a later late one, but a call that overruns
the public budget still reports the overrun.
"""
import time

from deadline import Deadline, DeadlineExceeded
from finalize import finalize

import native
import methods
from problem import PlanRequest

FLAG_KEYS = ("route_valid", "coverage_complete", "resource_valid", "returned_base",
             "rank_status", "rank_optimal", "tour_status", "core_candidate_valid",
             "fallback_selected", "natural", "termination_reason",
             "call_within_budget", "candidate_accepted_in_time", "within_budget")


def _clock_deadline(seconds, clock):
    return Deadline(seconds, clock)


def _audit(request, route):
    from audit_independent import audit_route
    return audit_route(request, route)


def run(request, method_id, *, seconds, seed, clock=None, deadline_clock=None,
        native_plan=None, remnants=None, cap_override=None, fallback_only=False):
    """Run one reference.  ``request`` must be a ``problem.PlanRequest``."""
    deadline = _clock_deadline(seconds, deadline_clock)
    started = time.perf_counter()
    stages = {}
    flags = {key: None for key in FLAG_KEYS}
    detail = {"method_id": method_id, "cap_override": cap_override,
              "variant": 0 if method_id == methods.METHOD_RANK0 else 2}

    def mark(name, begin):
        stages[name] = stages.get(name, 0.0) + (time.perf_counter() - begin)

    fallback = ()
    core_plan = None
    diagnostic = ()
    status = None
    meta = {}

    from problem import environment_status
    environment = environment_status(request)
    if not environment["ok"]:
        outcome = finalize(request, (), natural=False, reason=environment["code"],
                           failure_status="environment_infeasible",
                           errors=[environment["code"]], meta={})
        flags.update({"termination_reason": environment["code"], "natural": False})
        return _result(request, outcome, (), {}, flags, detail, environment,
                       deadline, diagnostic=(), late=False)

    try:
        deadline.check()
        begin = time.perf_counter()
        # --- shared fallback: a legal early candidate, never a core result
        fallback = methods.fallback_route(request.current, request.base,
                                          request.pending, request.free)
        mark("fallback", begin)
        fb_audit = _audit(request, fallback)
        if fb_audit["valid"]:
            flags["fallback_candidate_valid"] = True
        deadline.check()

        if not fallback_only:
            begin = time.perf_counter()
            remaining = max(0.05, deadline.remaining)
            if method_id == methods.METHOD_RANK0:
                plan, detail_core = methods.rank0_fulltour(
                    None, request.pending, request.free, request.current,
                    request.base, seed, remaining, f"core-{method_id}")
            else:
                plan, detail_core = methods.replan2_native(
                    {"old_route": tuple(request.old_route)}, remnants or (),
                    request.pending, request.free, request.current, request.base,
                    seed, remaining, f"core-{method_id}", cap_override)
            detail.update(detail_core)
            mark("core", begin)
            deadline.check()
            if plan is not None:
                core_plan = plan
                flags["rank_status"] = str(detail.get("rank_status"))
                flags["rank_optimal"] = str(detail.get("rank_status")) in ("optimal",)
                flags["tour_status"] = detail.get("tour_status")
    except DeadlineExceeded as exc:
        detail["interruption"] = f"deadline: {exc}"
    except Exception as exc:                                  # noqa: BLE001
        detail["interruption"] = f"{type(exc).__name__}: {exc}"

    # --- candidate selection: the fallback is kept only if the core produced nothing
    begin = time.perf_counter()
    core_route = tuple(core_plan.route) if core_plan is not None else ()
    core_audit = _audit(request, core_route) if core_route else None
    flags["core_candidate_valid"] = bool(core_audit and core_audit["valid"])
    mark("audit_core", begin)
    audited = deadline.elapsed()

    if core_route and core_audit["valid"]:
        route = core_route
        flags["fallback_selected"] = False
    else:
        route = fallback
        flags["fallback_selected"] = True

    if audited > deadline.limit and route:
        diagnostic = route
        route = ()
        deadline.hit = True

    outcome = finalize(request, route,
                       natural=bool(flags.get("tour_status") == "converged"),
                       reason="rank_and_tour" if not flags["fallback_selected"] else "fallback",
                       failure_status="deadline_before_complete_route" if deadline.hit else None,
                       success_status="finished",
                       errors=list(detail.get("errors") or []), meta={})

    audit = outcome["audit"]
    flags["route_valid"] = bool(audit.get("valid"))
    flags["coverage_complete"] = bool(audit.get("coverage_complete"))
    flags["returned_base"] = bool(audit.get("ends_at_base"))
    flags["resource_valid"] = (audit.get("resource") or {}).get("ok")
    flags["natural"] = bool(outcome["termination"].get("natural"))
    flags["termination_reason"] = outcome["reason"]
    flags["candidate_accepted_in_time"] = bool(route) and not deadline.hit
    flags["call_within_budget"] = audited <= deadline.limit
    flags["within_budget"] = flags["call_within_budget"]

    result = _result(request, outcome, route, stages, flags, detail, environment,
                     deadline, diagnostic=diagnostic, late=bool(diagnostic))
    if core_plan is not None:
        result.meta["core_plan"] = core_plan.as_dict()
    return result


def _result(request, outcome, route, stages, flags, detail, environment, deadline,
            diagnostic=(), late=False):
    from result import PlanResult
    from methods import CORE_VERSION, ADAPTER_VERSION
    meta = dict(outcome.get("meta") or {})
    meta.update({
        "core_version": CORE_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "flags": dict(flags),
        "core_detail": detail,
        "environment": environment,
        "candidate": {"generated": bool(detail.get("rank_status")),
                      "audited": bool(outcome.get("audit")),
                      "accepted": bool(flags.get("candidate_accepted_in_time")),
                      "post_deadline": late},
        "decisions": [],
    })
    if diagnostic:
        meta["diagnostic_route"] = [list(p) for p in diagnostic]
        meta["diagnostic_route_source"] = "audited after the deadline; diagnostic only"
    stage_seconds = dict(stages)
    stage_seconds["_sum"] = round(sum(stage_seconds.values()), 6)
    meta["deadline"] = deadline.report()
    result = PlanResult(
        method_id=detail.get("method_id", "OARP"),
        method_version=CORE_VERSION,
        route=tuple(route),
        status=outcome["status"], reason=outcome["reason"],
        audit=outcome["audit"], resource_check=outcome["resource_check"],
        termination=outcome["termination"],
        fallback_used=bool(flags.get("fallback_selected")),
        stage_seconds=stage_seconds, errors=outcome.get("errors") or [],
        meta=meta)
    return result
