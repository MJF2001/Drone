"""Closed loop: native initial plan -> real prefix -> event -> remaining-task responses.

Three preparations (rectangle, vertical line, sparse line) are planned once each with
``OARP_RANK0_FULLTOUR_SCENE``.  The prefix is flown for real and the physical ledger
is rebuilt from the executed cells.  Each of the eight events is then published on
its own preparation state, and for an applicable event four responses run on exactly
the same snapshot: rank0 once and replan2 with cap 0, 2 and 2*|Q|.

Outputs (all inside OUT):

``artifacts/plans/<prep>.json``        the native initial plan (strips + indices)
``artifacts/executions/<prep>.json``   the real prefix and the physical ledger
``artifacts/events/<case>.json``       the published P/F/Q/D and the chosen cells
``artifacts/responses/<plan_id>.json`` every response, with flags and core detail
``artifacts/requests/<plan_id>.json``  the exact request a response consumed
"""
import json
import os
import sys
import time
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import native  # noqa: E402
import methods  # noqa: E402
from adapters import registry  # noqa: E402
from common_geometry import GridMetric  # noqa: E402
from problem import PlanRequest, Termination  # noqa: E402

PROTOCOL = NEW / "protocol"
ART = NEW / "artifacts"
SEED = 20261018
SOFT = 5.0
RESOURCE = 1000
PREFIX = os.environ.get("OARP_PREFIX", "")
ONLY = os.environ.get("OARP_ONLY", "")


def load_cases():
    return json.loads((PROTOCOL / "cases.json").read_text(encoding="utf-8"))


def request_from(case, free, published, covered, current, base, old_route=(),
                 resource=RESOURCE, seconds=SOFT):
    free = frozenset(tuple(p) if not isinstance(p, tuple) else p for p in free)
    published = frozenset(tuple(p) for p in published)
    covered = frozenset(tuple(p) for p in covered)
    return PlanRequest(
        case_id=case, free=free, published_targets=published,
        covered=covered, current=tuple(current), base=tuple(base),
        old_route=tuple(tuple(p) for p in old_route),
        remaining_resource=resource, seed=SEED,
        termination=Termination(time_limit_seconds=seconds))


def prefix_length(plan, targets, count):
    """Smallest route length whose first-visit set covers ``count`` targets."""
    wanted = {tuple(p) for p in targets}
    seen = set()
    for index, cell in enumerate(plan.route):
        if cell in wanted:
            seen.add(cell)
        if len(seen) >= count:
            return index
    return len(plan.route) - 1


def choose_obstacle(event, free, pending, covered, current, base, plan, execution):
    """Deterministic obstacle pick for N2/N3/N6; returns (cell, reason)."""
    free = set(map(tuple, free))
    pending = set(map(tuple, pending))
    covered = set(map(tuple, covered))
    current, base = tuple(current), tuple(base)

    def reachable_after(blocked):
        metric = GridMetric(free - {blocked})
        try:
            seen = metric.reachable(current)
        except Exception:                                  # noqa: BLE001
            return False
        return base in seen and pending <= seen

    if event["new_obstacles"] in ("select", "select_n2"):
        # the rule allows a pending target to become the obstacle; it then enters D
        # and is not counted as completed
        candidates = sorted((p for p in free - covered if p not in (current, base)),
                            key=lambda p: (p[1], p[0]))
        for cell in candidates:
            rest = pending - {cell}
            metric = GridMetric(free - {cell})
            try:
                seen = metric.reachable(current)
            except Exception:                              # noqa: BLE001
                continue
            if base in seen and rest <= seen:
                return cell, ("N2 order: first (y,x) uncovered cell whose removal keeps "
                              "the remaining Q and the base reachable")
        return None, "no candidate satisfied the N2 rule"

    # N3: connectors of the remaining native strips, in route-index order
    remaining = [s for s in plan.strips
                 if any(cell in pending for cell in s.cells)]
    indices = []
    for strip in remaining:
        for index in range(strip.connector_start, strip.service_start):
            indices.append(index)
    for index in sorted(set(indices)):
        if index >= len(plan.route):
            continue
        cell = plan.route[index]
        if cell in (current, base) or cell in pending or cell in covered:
            continue
        if not reachable_after(cell):
            continue
        if cell not in free:
            continue
        return cell, (f"N3 order: first connector cell at route index {index} that is "
                      f"not a pending service cell and keeps Q completable")
    return None, "no connector cell satisfied the N3 rule"


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    data = load_cases()
    prepared = {}
    for prep in data["preparations"]:
        name = prep["name"]
        free = frozenset(map(tuple, prep["free"]))
        request = request_from(name, free, prep["published"], prep["covered"],
                               prep["current"], prep["base"])
        registry.CONTEXT.update({"kind": "initial", "batch": "INIT",
                                 "run_id": f"INIT:{name}", "plan_id": f"INIT:{name}",
                                 "case_id": name})
        begin = time.perf_counter()
        result = registry.run(methods.METHOD_RANK0, request, seconds=SOFT, seed=SEED)
        elapsed = time.perf_counter() - begin
        plan_payload = (result.meta or {}).get("core_plan")
        if plan_payload is None:
            raise SystemExit(f"{name}: the initial plan failed: {result.status}")
        plan = native.NativePlan.from_dict(plan_payload)
        length = prefix_length(plan, prep["published"], prep["prefix_targets"])
        execution = native.execute_prefix(plan, length, prep["covered"])
        prepared[name] = {"request": request, "plan": plan, "execution": execution,
                          "prep": prep, "seconds": elapsed,
                          "status": result.status}
        save(ART / "plans" / f"{name}.json", plan.as_dict())
        save(ART / "executions" / f"{name}.json", execution.as_dict())
        save(ART / "initial" / f"{name}.json", {
            "prep": name, "status": result.status, "route_steps": result.route_steps,
            "seconds": round(elapsed, 4), "prefix_steps": execution.steps_used,
            "flags": (result.meta or {}).get("flags"),
            "core_detail": {k: v for k, v in ((result.meta or {}).get("core_detail") or {}).items()
                            if k != "rank_attempts"}})
        print(f"[init] {name}: {result.status} steps={result.route_steps} "
              f"prefix={execution.steps_used}")

    summary = []
    for event in data["events"]:
        case_id = event["case_id"]
        if ONLY and case_id != ONLY:
            continue
        prep = prepared[event["prep"]]
        plan, execution, spec = prep["plan"], prep["execution"], prep["prep"]
        free = set(map(tuple, spec["free"])) | set(map(tuple, event["new_free"]))
        published = set(map(tuple, spec["published"])) | set(map(tuple, event["new_targets"]))
        covered = set(execution.covered_physical)
        current = execution.current
        base = tuple(spec["base"])
        pending_now = sorted((p for p in published - covered if p in free))
        obstacle, reason = (None, "no obstacle in this event")
        if event["new_obstacles"]:
            obstacle, reason = choose_obstacle(event, free, pending_now, covered,
                                               current, base, plan, execution)
        blocked = {obstacle} if obstacle else set()
        state = native.event_state(case_id, published, free - blocked, covered,
                                   new_obstacles=blocked,
                                   new_targets=event["new_targets"])
        remnants = native.normalize(plan, execution, state.covered, state.free,
                                    targets_after=set(state.pending) | set(state.deferred))
        save(ART / "events" / f"{case_id}.json",
             {"event": event, "state": state.as_dict(), "obstacle_choice": reason,
              "remnants": [r.as_dict() for r in remnants]})
        applicable = bool(state.pending) or True
        rows = []
        for slot, method, cap in (("rank0", methods.METHOD_RANK0, None),
                                  ("cap0", methods.METHOD_REPLAN2, 0),
                                  ("cap2", methods.METHOD_REPLAN2, 2),
                                  ("capmax", methods.METHOD_REPLAN2,
                                   len(state.pending) * 2)):
            if method == methods.METHOD_REPLAN2 and not remnants:
                rows.append({"method_id": method, "cap": cap,
                             "status": "not_applicable", "reason": "no remnant"})
                continue
            suffix = "" if method == methods.METHOD_RANK0 else f":{slot}"
            plan_id = f"{PREFIX}{case_id}:{method}{suffix}"
            request = request_from(case_id, state.free, state.published, state.covered,
                                   current, base, old_route=plan.route)
            registry.CONTEXT.update({"kind": "event", "batch": "EVENT",
                                     "run_id": plan_id, "plan_id": plan_id,
                                     "case_id": case_id})
            kwargs = {}
            if method == methods.METHOD_REPLAN2:
                kwargs = {"remnants": remnants, "cap_override": int(cap)}
            result = registry.run(method, request, seconds=SOFT, seed=SEED, **kwargs)
            payload = {"plan_id": plan_id, "case_id": case_id, "method_id": method,
                       "cap_override": cap, "status": result.status,
                       "route": [list(p) for p in result.route],
                       "route_steps": result.route_steps,
                       "audit": result.audit, "termination": result.termination,
                       "flags": (result.meta or {}).get("flags"),
                       "core_detail": {k: v for k, v in ((result.meta or {}).get("core_detail") or {}).items()
                                       if k != "rank_attempts"},
                       "stage_seconds": result.stage_seconds,
                       "pending": [list(p) for p in sorted(state.pending)],
                       "deferred": [list(p) for p in sorted(state.deferred)]}
            save(ART / "responses" / f"{plan_id.replace(':', '__')}.json", payload)
            save(ART / "requests" / f"{plan_id.replace(':', '__')}.json",
                 request.describe())
            rows.append({"method_id": method, "cap": cap, "status": result.status,
                         "steps": result.route_steps,
                         "fallback": (result.meta or {}).get("flags", {}).get("fallback_selected"),
                         "valid": result.audit["valid"]})
        summary.append({"case_id": case_id, "kind": event["kind"],
                        "pending": len(state.pending), "deferred": len(state.deferred),
                        "remnants": len(remnants), "responses": rows})
        print(f"[event] {case_id}: pending={len(state.pending)} deferred={len(state.deferred)} "
              f"remnants={len(remnants)} -> " +
              ", ".join(f"{r['method_id'].split('_')[1]}{r['cap'] if r['cap'] is not None else ''}"
                        f"={r['status']}({r.get('steps')})" for r in rows))

    save(ART / "closed_loop_summary.json",
         {"preparations": {k: {"steps": v["plan"].as_dict()["route_steps"],
                               "prefix": v["execution"].steps_used,
                               "seconds": round(v["seconds"], 4)}
                           for k, v in prepared.items()},
          "events": summary})
    return 0


if __name__ == "__main__":
    sys.exit(main())
