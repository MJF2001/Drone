"""Adapted C*: the historical reproduction, relabelled for the current model.

The algorithm core lives in ``src/cstar_core`` and is a structural port of
``sources/cstar_historical/cstar_strict``.  This module is the envelope:

* it reads the current task state (published map, real ledger, current position,
  base) and never resets history or turns a covered cell into an obstacle;
* it runs the C* outer loop in one of two modes (``public_map`` / ``sensed``);
* it realises every RCG edge as a legal four-neighbour cell path through
  ``common_geometry.GridMetric`` (the only connector);
* **the graded route is the C* route itself plus the fixed base return only.**
  Nothing is appended to it and no post-processing pass is attributed to C*.
  C* sweeps RCG frontier samples (full-area coverage under footprint radius 0),
  so on a target-only task it can over-cover and, if a pending target is never
  visited, the adapter reports ``coverage_incomplete`` and still saves the route.
  That is a task-definition mismatch, not a C* improvement opportunity.
* an **optional, non-default** variant (``completion_tsp=True``) appends the
  Algorithm-3 TSP machinery over the still-unvisited pending targets.  It is an
  *added* mechanism, is reported under the ``+completion`` version suffix and a
  distinct ``final_source``, and is never part of the graded row.
* it returns a base-returning route and the full envelope required by
  ``src/result.PlanResult``.

Adaptation label: ``cstar_restart_diag_v0.2_20261018``.

v0.2 (R4) renames the method honestly.  The real coverage ledger ``C`` reaches the
*envelope* (empty-task test, independent audit, optional completion) but it is NOT
part of the core planning state: ``CStar(start, known, sensor, seed, holes,
deadline, wall_clock)`` has no ``covered`` argument.  The core therefore re-sweeps
the whole published free region and is a **restart diagnostic**, not a residual-task
core adaptation.  The full data flow and the design that would inject the ledger
are in ``reports_v02/C_star_账本数据流与适配分类.md``.

It is *not* claimed to be the historical unknown-environment C*: the
mechanism-to-source table and every loss are in
``../specs/cstar_adaptation.md`` (v0.1, unchanged).
"""
from __future__ import annotations

import time

from common_geometry import GridMetric, NoPath
from finalize import finalize, SUCCESS_STATUSES
from problem import environment_status
from result import PlanResult, StageClock

from cstar_core.planner import CStar, optimize_tsp
from cstar_core.public_map import PublicMap, PublishedWorld, published_observation

METHOD_ID = "CSTAR"
METHOD_VERSION = "cstar_restart_diag_v0.2_20261018"
METHOD_VERSION_COMPLETION = METHOD_VERSION + "+completion"
ADAPTATION_CLASS = "restart_diagnostic_ledger_not_in_core"

MODE_PUBLIC = "public_map"
MODE_SENSED = "sensed"
MODES = (MODE_PUBLIC, MODE_SENSED)

#: Adapter parameters the current model does not specify.  They may be passed in
#: ``request.meta`` or in ``request.termination.extra`` (the latter wins).
DEFAULTS = {
    "mode": MODE_PUBLIC,        # "public_map" | "sensed"
    "sensor_radius": 2.0,       # only used by mode="sensed"; cells
    "holes": True,              # Algorithm 3 coverage-hole TSP enabled
    "max_iterations": 400,      # Algorithm 4 iteration cap (not wall clock)
    "completion_tsp": False,    # NON-DEFAULT added mechanism; labelled separately
}


def _options(request):
    options = dict(DEFAULTS)
    notes = []
    for label, source in (("meta", request.meta or {}),
                          ("termination.extra", request.termination.extra or {})):
        if not isinstance(source, dict):
            continue
        for key in DEFAULTS:
            if key in source:
                options[key] = source[key]
                notes.append(f"{key}<-{label}")
    mode = str(options["mode"])
    if mode not in MODES:
        notes.append(f"unknown_mode:{mode}->{MODE_PUBLIC}")
        mode = MODE_PUBLIC
    options["mode"] = mode
    try:
        options["sensor_radius"] = float(options["sensor_radius"])
    except (TypeError, ValueError):
        notes.append("bad_sensor_radius->2.0")
        options["sensor_radius"] = 2.0
    if options["sensor_radius"] <= 0:
        notes.append("nonpositive_sensor_radius->2.0")
        options["sensor_radius"] = 2.0
    try:
        options["max_iterations"] = max(1, int(options["max_iterations"]))
    except (TypeError, ValueError):
        notes.append("bad_max_iterations->400")
        options["max_iterations"] = 400
    options["holes"] = bool(options["holes"])
    options["completion_tsp"] = bool(options["completion_tsp"])
    options["_notes"] = notes
    return options



def _history_dataflow(request):
    """R4: where the real ledger does and does not reach."""
    return {
        "ledger_cells": len(request.covered),
        "reaches_core_planning_state": False,
        "used_in_envelope": ["empty_task_test", "independent_audit",
                             "optional_completion_tsp"],
        "not_used_in_core": ["RCG sampling", "pruning / essential classification",
                             "Algorithm 1 waypoint choice", "Algorithm 2 state update",
                             "Algorithm 3 hole TSP"],
        "core_constructor_arguments": ["start", "known", "sensor", "seed", "holes",
                                       "deadline", "wall_clock"],
        "classification": ADAPTATION_CLASS,
        "design_for_a_core_adaptation": "reports_v02/C_star_账本数据流与适配分类.md section 3",
    }


def _assemble(version, outcome, route, clock, *, fallback_used, fallback_steps,
              best, final):
    """Stop the clock first, then attach the stage snapshot (R3)."""
    clock.declare_missing("per_decision_timing")
    total = clock.stop_total()
    row = PlanResult(method_id=METHOD_ID, method_version=version,
                     status=outcome["status"], reason=outcome["reason"], route=route,
                     resource_check=outcome["resource_check"],
                     termination=outcome["termination"],
                     fallback_used=fallback_used, fallback_steps=fallback_steps,
                     best_candidate_source=best, final_source=final,
                     errors=outcome["errors"], meta=outcome["meta"],
                     stage_seconds={})
    row.stage_seconds = clock.snapshot()
    row.meta["adapter_seconds"] = total
    row.audit = outcome["audit"]
    return row


def run(request, clock=None):
    """Plan the current remaining coverage task with adapted C*."""
    clock = clock or StageClock()
    started = time.perf_counter()
    limit_seconds = float(request.termination.time_limit_seconds)
    deadline = started + limit_seconds

    # -- required first step -------------------------------------------
    t = time.perf_counter()
    env = environment_status(request)
    clock.add("environment", time.perf_counter() - t)
    options = _options(request)
    version = METHOD_VERSION_COMPLETION if options["completion_tsp"] else METHOD_VERSION

    if not env["ok"]:
        outcome = finalize(
            request, (), natural=False, reason=str(env["code"]),
            failure_status="environment_infeasible",
            errors=[f"environment_infeasible:{env['code']}"],
            meta={"environment": env, "mode": options["mode"], "options": options,
                  "deferred": [list(p) for p in sorted(request.deferred)],
                  "adaptation_class": ADAPTATION_CLASS,
                  "history": _history_dataflow(request)})
        return _assemble(version, outcome, (), clock, fallback_used=False,
                         fallback_steps=None, best="", final="")

    # -- nothing pending: the only legal answer is the direct return ----
    # v0.2 (R1): still a real flight.  It goes through finalize like every other
    # branch, so an over-budget return is reported, not called "finished".
    if not request.pending:
        t = time.perf_counter()
        metric = GridMetric(request.free)
        route = metric.path(tuple(request.current), tuple(request.base))
        clock.add("direct_return", time.perf_counter() - t)
        outcome = finalize(
            request, route, natural=True, reason="empty_pending_direct_return",
            failure_status="resource_exceeded",
            final_source="direct_return", best_candidate_source="direct_return",
            meta={"environment": env, "mode": options["mode"], "options": options,
                  "pending": 0,
                  "deferred": [list(p) for p in sorted(request.deferred)],
                  "adaptation_class": ADAPTATION_CLASS,
                  "history": _history_dataflow(request),
                  "route": {"cstar_steps": 0, "completion_steps": 0,
                            "base_return_steps": len(route) - 1,
                            "total_steps": len(route) - 1}},
            errors=[])
        result = _assemble(version, outcome, route, clock, fallback_used=False,
                           fallback_steps=None, best="direct_return", final="direct_return")
        return result

    # -- mode setup ------------------------------------------------------
    t = time.perf_counter()
    known = PublicMap()
    sensor = None
    if options["mode"] == MODE_PUBLIC:
        observation = published_observation(request.free, request.published_targets)
        known.update(observation)
    else:
        sensor = PublishedWorld(request.free, request.published_targets,
                                radius=options["sensor_radius"])
    clock.add("public_map", time.perf_counter() - t)

    # -- Algorithm 4 (the adapted outer loop) ----------------------------
    t = time.perf_counter()
    planner = CStar(start=tuple(request.current), known=known, sensor=sensor,
                    seed=request.seed, holes=options["holes"],
                    deadline=deadline, wall_clock=time.perf_counter)
    planner.run(options["max_iterations"])
    clock.add("cstar_loop", time.perf_counter() - t)

    cstar_route = tuple(planner.path)
    cstar_steps = len(cstar_route) - 1
    if cstar_route[0] != tuple(request.current):
        raise AssertionError("C* route does not start at the current position")

    # -- graded route: C* route + fixed base return ONLY -------------------
    # ``completion_tsp`` is a NON-DEFAULT, separately labelled added mechanism.
    # It is never part of the graded row and its steps are reported as such.
    t = time.perf_counter()
    metric = GridMetric(request.free)
    last = cstar_route[-1]
    base = tuple(request.base)
    pending = set(request.pending)
    remaining = sorted(pending - set(cstar_route))
    errors = []
    completion = ()
    base_return = ()
    completion_summary = None
    completion_steps = 0
    base_return_steps = 0

    if options["completion_tsp"] and remaining:
        try:
            points = set(remaining) | {last, base}
            cost = {}
            for a in sorted(points):
                for b in sorted(points):
                    if a != b:
                        cost[(a, b)] = metric.distance(a, b)
            order, before, after = optimize_tsp(points, last, base, cost)
            chain = [last]
            for a, b in zip(order, order[1:]):
                chain.extend(metric.path(a, b)[1:])
            # the TSP route starts at `last`; drop the duplicated first cell
            completion = tuple(chain[1:])
            completion_steps = len(completion)
            completion_summary = {"mechanism": "added_completion_tsp",
                                  "attribution": "NOT part of the C* result",
                                  "case": 1, "start": list(last), "end": list(base),
                                  "targets": len(remaining),
                                  "target_set": [list(p) for p in remaining],
                                  "order": [list(p) for p in order],
                                  "nn_length": before, "opt_length": after}
        except NoPath as error:  # pragma: no cover - environment_status prevents this
            errors.append(f"completion_tsp_no_path:{error}")
    if not completion and last != base:
        base_return = metric.path(last, base)[1:]
        base_return_steps = len(base_return)

    route = tuple(cstar_route) + completion + base_return
    if route[-1] != base:
        route = route + metric.path(route[-1], base)[1:]
        base_return_steps = len(route) - 1 - cstar_steps - completion_steps
    clock.add("connector_and_base_return", time.perf_counter() - t)

    # -- facts handed to the shared finalizer -----------------------------
    # The status itself is decided in ONE place (``finalize``) from the
    # independent audit of this route; nothing here pre-declares success.
    pending_left = sorted(pending - set(route))
    steps = len(route) - 1
    limit = request.resource_limit()
    if pending_left:
        errors.append(f"coverage_omitted:{len(pending_left)}")
    if limit is not None and steps > limit:
        errors.append(f"resource_exceeded:{steps}>{limit}")

    cstatus = planner.status
    if planner.error:
        errors.append(f"cstar_{cstatus}:{planner.error.strip().splitlines()[-1][:300]}")
    terminal_facts = {"cstar_status": cstatus, "iterations": planner.iterations,
                      "cap_seconds": limit_seconds,
                      "max_iterations": options["max_iterations"]}

    fallback_used = completion_steps > 0
    fallback_steps = completion_steps if fallback_used else None
    if completion_steps > 0 and cstar_steps > 0:
        final_source = "cstar_rcg+completion_tsp"
    elif completion_steps > 0:
        final_source = "completion_tsp_after_rcg_failure"
    elif cstar_steps > 0:
        final_source = "cstar_rcg+base_return" if base_return_steps else "cstar_rcg"
    else:
        final_source = "cstar_start_only+base_return" if base_return_steps else "cstar_start_only"

    # -- public-map / degeneration evidence -------------------------------
    graph_nodes = dict(planner.graph.nodes)
    sampled = sorted(p for p, n in graph_nodes.items() if n.kind in ("frontier", "start"))
    interior = [p for p in sampled
                if all((p[0] + dx, p[1] + dy) in known.free
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
    unsampled = sorted(known.free - set(sampled))
    tsp_events = [event for event in planner.events if event.get("type") == "tsp"]
    retreat_events = [event for event in planner.events if event.get("type") == "retreat"]

    meta = {
        "environment": env,
        "mode": options["mode"],
        "options": options,
        "adapted_from": "sources/cstar_historical/cstar_strict",
        "adaptation_label": version,
        "graded_route": "cstar_route+base_return" if not options["completion_tsp"]
                        else "cstar_route+completion_tsp+base_return",
        "request": {"case_id": request.case_id, "pending": len(request.pending),
                    "deferred": [list(p) for p in sorted(request.deferred)],
                    "published": len(request.published_targets),
                    "covered": len(request.covered), "current": list(request.current),
                    "base": list(request.base), "seed": request.seed},
        "cstar": {
            "status": cstatus,
            "error": planner.error.strip().splitlines()[-1][:300] if planner.error else "",
            "iterations": planner.iterations,
            "initial_samples": len(planner.initial_samples),
            "initial_known_free": planner.initial_known_free,
            "known_free_end": len(known.free),
            "observed_cells_end": len(known.cells),
            "nodes_end": len(planner.graph.nodes),
            "edges_end": sum(len(v) for v in planner.graph.edges.values()) // 2,
            "frontier_added": planner.graph.frontier_added,
            "link_count": planner.graph.link_count,
            "tsp_nodes": planner.graph.tsp_count,
            "total_pruned": planner.graph.total_pruned,
            "start_anchor": planner.graph.start_anchor,
            "retreat_events": len(retreat_events),
            "keep_open_count": planner.keep_open_count,
            "tsp_hole_events": len(tsp_events),
            "tsp_hole_detail": tsp_events,
            "components": planner.component_sizes,
            "nodes": [[p[0], p[1], n.state, n.kind, n.reason]
                      for p, n in sorted(graph_nodes.items())],
        },
        "public_map": {
            "published_free_cells": len(request.free),
            "published_blocked_targets": len(set(request.published_targets) - set(request.free)),
            "sampled_cells": len(sampled),
            "sampled_interior_cells": len(interior),
            "unsampled_free_cells": len(unsampled),
            "unsampled_free_sample": [list(p) for p in unsampled[:16]],
            "boundary_ring_only": len(sampled) > 0 and not interior,
            "graph_columns": sorted({p[0] for p in sampled}),
            "rcg_connected": cstatus != "rcg_disconnected",
        },
        "coverage": {"pending": len(pending), "omitted": [list(p) for p in pending_left],
                     "complete": not pending_left},
        "completion_tsp": {"enabled": bool(options["completion_tsp"]),
                           "steps": completion_steps, "detail": completion_summary},
        "route": {"cstar_steps": cstar_steps, "completion_steps": completion_steps,
                  "base_return_steps": base_return_steps, "total_steps": steps},
        "trace": planner.iterations_trace,
    }

    reason = f"cstar_{cstatus}"
    if completion_steps:
        reason += "+completion_tsp"
    if base_return_steps:
        reason += "+base_return"
    if pending_left:
        reason += "+coverage_incomplete"

    meta["adaptation_class"] = ADAPTATION_CLASS
    meta["history"] = _history_dataflow(request)
    meta["terminal_facts"] = terminal_facts
    meta["resource_facts"] = {"limit": limit, "used": steps,
                              "cstar_steps": cstar_steps,
                              "completion_steps": completion_steps,
                              "base_return_steps": base_return_steps}

    if completion_steps:
        # the added mechanism is disclosed, never attributed to C*
        meta["completion_tsp"]["attribution"] = (
            "ADDED mechanism, NOT part of the C* result; excluded from the graded row")
    if pending_left:
        failure_status = "coverage_incomplete"
    elif limit is not None and steps > limit:
        failure_status = "resource_exceeded"
    elif cstatus in ("rcg_disconnected", "invariant_failure"):
        failure_status = "no_legal_route_within_resource"
    elif cstatus == "iteration_limit":
        failure_status = "safety_limit_before_complete_route"
    elif cstatus == "wall_clock_cap":
        failure_status = "deadline_before_complete_route"
    else:
        failure_status = "no_legal_route_within_resource"

    natural = cstatus == "graph_exhausted"
    outcome = finalize(
        request, route, natural=natural, reason=reason,
        failure_status=failure_status, success_status="finished",
        errors=errors, meta=meta)
    return _assemble(version, outcome, route, clock,
                     fallback_used=fallback_used, fallback_steps=fallback_steps,
                     best=("cstar_rcg" if cstar_steps > 0 else "cstar_start_only"),
                     final=final_source)
