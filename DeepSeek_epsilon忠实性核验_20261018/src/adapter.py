"""Adapter: run the revised epsilon-star through the unified request/result shapes.

This keeps the deliverable comparable with the other methods without touching them:
``problem.PlanRequest`` in, a result row out, with the independent audit of
``audit_independent`` applied to the produced route.

The adapter records, in one place, which parts are the *original mechanism* and
which parts are the *scenario adaptation*, so a reader does not have to guess:

original mechanism
    multiscale tiling and levels, Eq. (2)/(3) potentials, Algorithm 1,
    CP0/CP1..CPL/WT/FN, Eq. (5) waypoint choice, FN halting.

scenario adaptation (this project's user model)
    * four-neighbour unit steps, so the connector is the common grid BFS and the
      executed motion is one cell per step;
    * "passing over a cell covers it" is enforced by the *auditor* on the route,
      while the ETM's control ledger only changes at tasking (credit="task");
    * the tiled area is the bounding box of the currently published region, since
      the map beyond it is unknown;
    * the forbidden buffer around obstacles is empty (footprint radius 0, no
      inertia);
    * a return-to-base leg is appended after FN, which the paper does not model.
"""
import time

from common_geometry import GridMetric
from etm_faithful import ETM
from maps_faithful import MAPS
from audit_independent import audit_route
from problem import PlanRequest
from result import PlanResult, StageClock


METHOD_VERSION = "epsilon_star_faithful_v1_20261018"
ADAPTER_VERSION = "epsilon_faithful_adapter_20261018"


def run(request, mode="task", seed=None, turn_cost=1.0, travel_cost=1.0,
        max_steps=20000, build_clock=None):
    """Run one epsilon-star call.  ``mode`` selects the credit rule."""
    clock = build_clock or StageClock()
    seed = request.seed if seed is None else seed
    clock.start("maps_build")
    maps = MAPS(request.free, request.published_targets, request.covered)
    clock.stop()

    clock.start("etm_run")
    engine = ETM(maps, request.current, seed=seed, credit=mode,
                 travel_cost=travel_cost, turn_cost=turn_cost,
                 metric=GridMetric(request.free))
    engine.run(max_steps=max_steps)
    clock.stop()

    clock.start("return")
    engine.return_to_base(request.base)
    clock.stop()

    route = tuple(engine.route)
    clock.start("audit")
    audit = audit_route(request, route)
    resource = audit.get("resource", {})
    clock.stop()

    summary = engine.summary()
    status = "finished" if summary["terminal"].startswith("FN") else "planned_at_timeout"
    natural = summary["terminal"] == "FN_no_positive_potential"
    result = PlanResult(
        method_id="EPSILON_STAR", method_version=METHOD_VERSION, route=route,
        status=status, audit=audit, resource_check=resource,
        fallback_used=False, stage_seconds=clock.as_dict(),
        termination={"natural": natural, "reason": summary["terminal"]},
        errors=[] if audit["valid"] else list(audit["errors"]),
        meta={"engine": summary, "credit_mode": mode, "adapter_version": ADAPTER_VERSION,
              "maps": maps.describe(), "turn_cost": turn_cost,
              "travel_cost": travel_cost},
    )
    result.meta["route"] = {"completion_steps": audit["route_steps"]}
    return result


def _unused(request):                     # pragma: no cover - keeps the import meaningful
    return isinstance(request, PlanRequest)
