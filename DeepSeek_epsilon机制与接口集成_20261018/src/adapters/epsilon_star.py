"""epsilon-star adapter for the integrated candidate version.

The core is ``core.maps`` + ``core.etm`` (the mechanism-reference version, with
observation added).  This adapter is the only supported way to run it, and it
carries the protections that were accepted in v0.3:

* one public deadline over the whole call: input checks, MAPS construction, the
  ETM loop, every connector call, the return leg and the **final audit**;
* the candidate boundary "generated -> audited -> accepted": a route is only a
  graded result when its audit finished before the deadline, it covers Q, it
  returns to the base and it fits the resource; a route that passes the audit
  after the deadline is kept **as a diagnostic only**;
* ``finalize`` decides the status from the independent audit, so a valid route
  can never be recorded as a success just because the engine said so;
* ``meta.deadline`` is written last and holds the real check count, elapsed time
  and hit flag;
* multi-factor reporting: audit facts, engine terminal reason and the reason a
  result is not scorable are kept as separate fields.
"""
import time

from deadline import Deadline, DeadlineExceeded
from finalize import finalize, SUCCESS_STATUSES

from core.etm import ETM
from core.maps import MAPS
from common_geometry import GridMetric, NoPath
from problem import environment_status

METHOD_ID = "EPSILON_STAR"
#: the core keeps the paper's decision rules; the version string must not claim a
#: complete reproduction of the preprint
CORE_VERSION = "epsilon_star_core_integrated_v1_20261018"
ADAPTER_VERSION = "epsilon_star_adapter_integrated_v1_20261018"
ADAPTATION_CLASS = "epsilon_star_core_adapted_task_control"

DEFAULT_MODE = "task"
DEFAULT_TRAVEL_COST = 1.0
DEFAULT_TURN_COST = 1.0
DEFAULT_MAX_STEPS = 20000

NATURAL_FN = "FN_no_positive_potential"
ARTIFICIAL_TERMINALS = ("step_limit", "state_cycle", "no_progress")


def run(request, clock=None, deadline_clock=None, mode=DEFAULT_MODE,
        travel_cost=DEFAULT_TRAVEL_COST, turn_cost=DEFAULT_TURN_COST,
        max_steps=DEFAULT_MAX_STEPS):
    """One epsilon-star call.  Everything expensive is inside the deadline."""
    if mode != DEFAULT_MODE:
        raise ValueError("this round freezes the control mode to 'task'")
    if (travel_cost, turn_cost) != (DEFAULT_TRAVEL_COST, DEFAULT_TURN_COST):
        raise ValueError("this round freezes travel_cost=1.0, turn_cost=1.0")

    deadline = Deadline(request.termination.time_limit_seconds, deadline_clock)
    started = time.perf_counter()
    from inputs import validate_request
    verdict = validate_request(request)
    if not verdict["ok"]:
        from finalize import finalize as _finalize
        outcome = _finalize(request, (), natural=False, reason=verdict["code"],
                            failure_status="input_precondition_unmet",
                            errors=[f"input:{verdict['code']}:{verdict['detail']}"],
                            meta={})
        return _build_result(request, outcome, route=(), diagnostic=(),
                             deadline=deadline, deadline_meta=deadline.report(),
                             stage_seconds={}, engine={}, maps={},
                             environment={"ok": False, "code": verdict["code"]},
                             late=False, budget_reason="input_precondition_unmet",
                             mode=mode, travel_cost=travel_cost, turn_cost=turn_cost,
                             max_steps=max_steps, errors=[verdict["detail"]])
    time_source = lambda: time.perf_counter() - started   # noqa: E731

    stage = clock
    stage_seconds = {}
    errors = []
    environment = environment_status(request)
    route = ()
    diagnostic = ()
    engine_summary = {}
    maps_description = {}
    outcome = None
    late = False
    budget_reason = ""

    def mark(name, begin):
        stage_seconds[name] = stage_seconds.get(name, 0.0) + (time.perf_counter() - begin)
        if stage is not None:
            stage.add(name, stage_seconds[name])

    if not environment["ok"]:
        outcome = finalize(request, (), natural=False,
                           reason=environment["code"], failure_status="environment_infeasible",
                           errors=[environment["code"]], meta={})
        deadline_meta = deadline.report()
        return _build_result(request, outcome, route=(), diagnostic=(), deadline=deadline,
                             deadline_meta=deadline_meta, stage_seconds=stage_seconds,
                             engine={}, maps={}, environment=environment,
                             late=False, budget_reason="", mode=mode,
                             travel_cost=travel_cost, turn_cost=turn_cost,
                             max_steps=max_steps, errors=errors)

    try:
        deadline.check()
        begin = time.perf_counter()
        maps = MAPS(request.free, request.published_targets, request.covered,
                    deadline=deadline)
        mark("maps_build", begin)
        maps_description = maps.describe()

        begin = time.perf_counter()
        engine = ETM(maps, request.current, request.pending, seed=request.seed,
                     credit=mode, travel_cost=travel_cost, turn_cost=turn_cost,
                     metric=GridMetric(request.free), deadline=deadline,
                     time_source=time_source, max_steps=max_steps)
        engine.run()
        deadline.check()
        engine.return_to_base(request.base)
        mark("etm_and_return", begin)
        engine_summary = engine.summary()
        route = tuple(engine.route)
        deadline.check()
    except DeadlineExceeded as exc:
        errors.append(f"deadline:{exc}")
        diagnostic = tuple(engine.route) if engine_summary or "engine" in locals() else ()
        if not diagnostic and route:
            diagnostic = tuple(route)
        engine_summary = engine.summary() if "engine" in locals() else {}
        maps_description = maps.describe() if "maps" in locals() else {}
        route = ()
        outcome = finalize(request, (), natural=False,
                           reason="deadline_before_complete_route",
                           failure_status="deadline_before_complete_route",
                           errors=errors, meta={})
        deadline_meta = deadline.report()
        result = _build_result(request, outcome, route=(), diagnostic=diagnostic,
                               deadline=deadline, deadline_meta=deadline_meta,
                               stage_seconds=stage_seconds, engine=engine_summary,
                               maps=maps_description, environment=environment,
                               late=True, budget_reason="deadline_crossed",
                               mode=mode, travel_cost=travel_cost,
                               turn_cost=turn_cost, max_steps=max_steps,
                               errors=errors)
        if diagnostic:
            result.meta["diagnostic_route"] = [list(p) for p in diagnostic]
            result.meta["diagnostic_route_source"] = (
                "route existed when the deadline was crossed; not audited, not graded")
        return result
    except NoPath as exc:
        errors.append(f"no_path:{exc}")
        engine_summary = engine.summary() if "engine" in locals() else {}
        maps_description = maps.describe() if "maps" in locals() else {}
        route = ()
        outcome = finalize(request, (), natural=False, reason="no_legal_route_within_resource",
                           failure_status="no_legal_route_within_resource",
                           errors=errors, meta={})
        return _build_result(request, outcome, route=(), diagnostic=(), deadline=deadline,
                             deadline_meta=deadline.report(), stage_seconds=stage_seconds,
                             engine=engine_summary, maps=maps_description,
                             environment=environment, late=False,
                             budget_reason="connector_no_path", mode=mode,
                             travel_cost=travel_cost, turn_cost=turn_cost,
                             max_steps=max_steps, errors=errors)

    terminal = engine_summary.get("terminal", "")
    natural = terminal == NATURAL_FN
    if natural:
        success_status = "finished"
    elif terminal in ARTIFICIAL_TERMINALS:
        # a legal route from an artificial stop is allowed but must say so
        success_status = "finished_with_safety_limit"
    else:
        success_status = "planned_at_timeout"

    begin = time.perf_counter()
    outcome = finalize(request, route, natural=natural, reason=terminal,
                       failure_status=("deadline_before_complete_route" if not natural else None),
                       success_status=success_status, errors=errors, meta={})
    mark("audit", begin)
    audited = deadline.elapsed()

    if audited > deadline.limit:
        # the audit itself crossed the deadline: diagnostic only
        late = True
        diagnostic = route
        route = ()
        deadline.hit = True
        budget_reason = "audit_after_deadline"
        carried = list(outcome["errors"]) + ["post_deadline_candidate_excluded"]
        outcome = finalize(request, (), natural=False, reason="deadline_before_complete_route",
                           failure_status="deadline_before_complete_route",
                           errors=carried, meta={})
    else:
        budget_reason = "" if outcome["status"] in SUCCESS_STATUSES else outcome["status"]

    result = _build_result(request, outcome, route=route, diagnostic=diagnostic,
                           deadline=deadline, deadline_meta=deadline.report(),
                           stage_seconds=stage_seconds, engine=engine_summary,
                           maps=maps_description, environment=environment, late=late,
                           budget_reason=budget_reason, mode=mode,
                           travel_cost=travel_cost, turn_cost=turn_cost,
                           max_steps=max_steps, errors=errors)
    if diagnostic:
        result.meta["diagnostic_route"] = [list(p) for p in diagnostic]
        result.meta["diagnostic_route_source"] = (
            "route passed generation and audit only after the deadline; diagnostic only")
    return result


def _build_result(request, outcome, *, route, diagnostic, deadline, deadline_meta,
                  stage_seconds, engine, maps, environment, late, budget_reason,
                  mode, travel_cost, turn_cost, max_steps, errors):
    from result import PlanResult

    meta = dict(outcome.get("meta") or {})
    meta.update({
        "core_version": CORE_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "adaptation_class": ADAPTATION_CLASS,
        "control_mode": mode,
        "ledgers": {
            "control": "MAPS state; U = control-pending, updated only at WT",
            "physical": "recomputed by the independent audit from the route",
        },
        "engine": {k: v for k, v in engine.items() if k != "decisions"},
        "events": engine.get("events", {}),
        "connector": engine.get("connector", {}),
        "maps": maps,
        "environment": environment,
        "parameters": {"travel_cost": travel_cost, "turn_cost": turn_cost,
                       "turn_cost_units": "per degree from the heading",
                       "max_control_iterations": max_steps,
                       "initial_heading": None},
        "candidate": {
            "generated": bool(engine.get("steps") is not None),
            "audited": bool(outcome.get("audit")),
            "accepted": bool(outcome.get("audit", {}).get("valid")) and not late,
            "post_deadline": late,
        },
        "decisions": list(engine.get("decisions") or []),
        "not_scorable_reason": budget_reason,
        "errors": list(errors) + list(outcome.get("errors") or []),
    })
    stage_seconds = dict(stage_seconds)
    stage_seconds["_sum"] = round(sum(v for k, v in stage_seconds.items()
                                     if not k.startswith("_")), 6)
    meta["deadline"] = deadline_meta
    result = PlanResult(
        method_id=METHOD_ID,
        method_version=CORE_VERSION,
        route=route,
        status=outcome["status"],
        reason=outcome["reason"],
        audit=outcome["audit"],
        resource_check=outcome["resource_check"],
        termination=outcome["termination"],
        fallback_used=False,
        stage_seconds=stage_seconds,
        errors=list(outcome.get("errors") or []),
        meta=meta,
    )
    meta["route"] = {"completion_steps": outcome["audit"].get("route_steps")}
    return result
