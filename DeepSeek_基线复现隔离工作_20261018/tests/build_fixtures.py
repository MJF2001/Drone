"""Deterministic micro fixtures for this round.

Each fixture is a *current state* built the way the research problem builds one:
an initial boustrophedon scan over the pre-event targets is executed up to some
progress, then an event is published (extension, obstacle, both, or nothing).
The executed prefix becomes the real coverage ledger and the real current
position; the unexecuted suffix becomes the old remaining route.

No fixture reads a future event, and the old remaining route may cross cells the
event has since blocked: that is history, not an input contradiction.

Two fixtures (m08, m17) are *ledger-boundary* states declared directly rather
than derived from an executed prefix, because the derived form cannot reach the
intended boundary (a start position that is published but not yet credited).
Their ``explicit_state.why`` string records the reason inside the fixture.

Output: tests/fixtures/cases/<case_id>.json (written once, then never edited;
``verify_delivery.py`` checks their hashes).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))

from common_geometry import GridMetric, chain  # noqa: E402

CASES = OUT / "tests" / "fixtures" / "cases"


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


def boustrophedon(points):
    rows = {}
    for x, y in points:
        rows.setdefault(y, []).append(x)
    order = []
    for index, y in enumerate(sorted(rows)):
        xs = sorted(rows[y], reverse=bool(index % 2))
        order.extend((x, y) for x in xs)
    return order


def build(case_id, free, pre_targets, progress, extension=(), blocked=(), base=(0, 0),
          notes="", event="none", resource=None, start=None, drop_old_route=False,
          explicit=None):
    metric = GridMetric(free)
    origin = tuple(start) if start is not None else tuple(base)
    order = boustrophedon(pre_targets)
    route = chain(metric, [origin] + order + [tuple(base)])
    k = max(0, min(len(route) - 2, int(round(progress * (len(route) - 1)))))
    current = route[k]
    covered = frozenset(set(route[:k + 1]) & set(pre_targets))
    old_route = () if drop_old_route else route[k:]
    if explicit:
        current = tuple(explicit["current"])
        covered = frozenset(map(tuple, explicit["covered"]))
        old_route = tuple(map(tuple, explicit.get("old_route", ())))
        k = explicit.get("executed_steps", 0)

    published = frozenset(set(pre_targets) | set(extension))
    free_after = frozenset(set(free) - set(blocked))
    pending = frozenset((published - covered) & free_after)
    deferred = frozenset((published - covered) - free_after)
    return {
        "case_id": case_id,
        "notes": notes,
        "event": event,
        "explicit_state": None if not explicit else {
            "why": explicit["why"],
            "executed_steps": k,
            "class": "ledger_boundary_declared_state",
        },
        "grid": {
            "free": sorted([list(p) for p in free_after]),
            "published_targets": sorted([list(p) for p in published]),
            "covered": sorted([list(p) for p in covered]),
            "current": list(current),
            "base": list(base),
            "old_route": [list(p) for p in old_route],
            "initial_targets": sorted([list(p) for p in pre_targets]),
            "remaining_resource": resource if resource is not None else 4 * len(free_after),
        },
        "expected": {
            "pending": [list(p) for p in sorted(pending)],
            "deferred": [list(p) for p in sorted(deferred)],
            "pending_count": len(pending),
            "deferred_count": len(deferred),
            "old_route_crosses_blocked": any(tuple(p) not in free_after for p in old_route),
            "executed_steps": k,
            "has_old_route": bool(old_route),
            "base_pending": tuple(base) in pending,
            "start_pending": current in pending,
        },
    }


def specs():
    out = []

    out.append(dict(case_id="m01_pure_obstacle", free=rect(0, 0, 6, 4),
                    pre_targets=rect(1, 1, 4, 3) - {(4, 3)}, progress=0.45,
                    blocked={(3, 2)},
                    notes="blocked cell sits on the old route, mid-residual",
                    event="obstacle"))

    out.append(dict(case_id="m02_extension_only", free=rect(0, 0, 7, 4),
                    pre_targets=rect(1, 1, 3, 3), progress=0.4,
                    extension=rect(5, 1, 2, 3),
                    notes="straight extension of the inspection area",
                    event="extension"))

    out.append(dict(case_id="m03_corner_extension_and_obstacle", free=rect(0, 0, 8, 5),
                    pre_targets=rect(1, 1, 4, 3), progress=0.5,
                    extension=rect(6, 1, 2, 4), blocked={(4, 2), (4, 3)},
                    notes="corner extension plus a two-cell obstacle inside the old area",
                    event="overlay"))

    out.append(dict(case_id="m04_two_events", free=rect(0, 0, 8, 4),
                    pre_targets=rect(1, 1, 3, 3), progress=0.55,
                    extension=rect(5, 1, 3, 3), blocked={(6, 2)},
                    notes="the second event removes a cell the first event had just published",
                    event="extension_then_obstacle"))

    out.append(dict(case_id="m05_no_change", free=rect(0, 0, 5, 4),
                    pre_targets=rect(1, 1, 3, 3), progress=0.5,
                    notes="history-invariant control: no new target, no new obstacle",
                    event="none"))

    out.append(dict(case_id="m06_empty_pending", free=rect(0, 0, 5, 4),
                    pre_targets=rect(1, 1, 3, 2), progress=1.0,
                    notes="Q is empty; the only legal answer is the direct return from current to base",
                    event="none"))

    out.append(dict(case_id="m07_start_equals_base", free=rect(0, 0, 5, 4),
                    pre_targets=rect(1, 1, 3, 2), progress=0.0,
                    notes="start == base with a non-empty remaining task",
                    event="none"))

    # the drone was launched from (0,0); its home base is the target (3,1), which
    # the executed prefix never reached, so the base cell is still outstanding.
    out.append(dict(case_id="m08_base_pending", free=rect(0, 0, 4, 2),
                    pre_targets=rect(0, 0, 4, 2), progress=0.0,
                    start=(0, 0), base=(3, 1),
                    notes="the base cell is itself an outstanding target",
                    event="none"))

    out.append(dict(case_id="m09_pass_base_early", free=rect(0, 0, 6, 4),
                    pre_targets=rect(1, 2, 4, 2), progress=0.3, base=(3, 3),
                    notes="base is inside the residual region; passing it early must not end the run",
                    event="none"))

    out.append(dict(case_id="m10_transit_coverage", free=rect(0, 0, 7, 3),
                    pre_targets=rect(1, 1, 5, 1), progress=0.25,
                    notes="single-row corridor: transit to the base crosses further targets",
                    event="none"))

    out.append(dict(case_id="m11_covered_corridor_blocks", free=rect(0, 0, 7, 5),
                    pre_targets=rect(0, 0, 7, 5), progress=0.5,
                    blocked={(3, 1), (3, 3)},
                    notes="covered cells stay passable; the blocked pair splits the residual task",
                    event="obstacle"))

    out.append(dict(case_id="m12_resource_tight", free=rect(0, 0, 6, 4),
                    pre_targets=rect(1, 1, 4, 3), progress=0.4, resource=3,
                    notes="remaining_resource far below the shortest legal completion",
                    event="none"))

    out.append(dict(case_id="m13_deferred_target", free=rect(0, 0, 7, 3),
                    pre_targets=rect(1, 1, 5, 1), progress=0.2, blocked={(3, 1)},
                    notes="a published target cell becomes blocked: deferred, not deleted, not completed",
                    event="obstacle"))

    out.append(dict(case_id="m14_base_unreachable", free=rect(0, 0, 6, 3),
                    pre_targets=rect(2, 1, 3, 1), progress=0.4,
                    blocked={(1, 0), (1, 1), (1, 2)},
                    notes="a full column of obstacles separates current from base",
                    event="obstacle"))

    ring = {(4, 1), (4, 2), (5, 0), (6, 0), (6, 1), (6, 2), (5, 3), (6, 3), (4, 3)}
    out.append(dict(case_id="m15_target_sealed", free=rect(0, 0, 8, 4),
                    pre_targets=rect(1, 1, 7, 1) | {(5, 2)}, progress=0.15, blocked=ring,
                    notes="remaining targets (5,1) and (5,2) are enclosed by a ring of blocked cells",
                    event="obstacle"))

    out.append(dict(case_id="m16_no_old_route", free=rect(0, 0, 5, 4),
                    pre_targets=rect(1, 1, 3, 2), progress=0.5, drop_old_route=True,
                    notes="old remaining route absent: the interface must accept it",
                    event="none"))

    out.append(dict(case_id="m17_start_pending", free=rect(0, 0, 4, 3),
                    pre_targets=rect(0, 0, 4, 3), progress=0.0, base=(0, 0),
                    explicit={"current": (1, 1), "covered": [(0, 0), (0, 1), (1, 0)],
                              "old_route": [(1, 1), (2, 0), (3, 0), (3, 1), (0, 0)],
                              "executed_steps": 3,
                              "why": "a target published at the current position at the moment of "
                                     "the event has not been credited to the ledger yet; a route "
                                     "that starts there must still count it as covered"},
                    notes="the start cell itself is an outstanding target",
                    event="obstacle"))

    return out


def main():
    payloads = [build(**spec) for spec in specs()]
    CASES.mkdir(parents=True, exist_ok=True)
    for payload in payloads:
        path = CASES / f"{payload['case_id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    from problem import PlanRequest, environment_status
    print(f"wrote {len(payloads)} fixtures to {CASES}")
    for payload in payloads:
        grid = payload["grid"]
        request = PlanRequest(
            case_id=payload["case_id"], free=frozenset(map(tuple, grid["free"])),
            published_targets=frozenset(map(tuple, grid["published_targets"])),
            covered=frozenset(map(tuple, grid["covered"])), current=tuple(grid["current"]),
            base=tuple(grid["base"]), old_route=tuple(map(tuple, grid["old_route"])),
            remaining_resource=grid["remaining_resource"])
        env = environment_status(request)
        exp = payload["expected"]
        print(f"  {payload['case_id']:34s} pending={exp['pending_count']:3d} "
              f"deferred={exp['deferred_count']:2d} old_blk={int(exp['old_route_crosses_blocked'])} "
              f"base_pend={int(exp['base_pending'])} start_pend={int(exp['start_pending'])} "
              f"env={env['code']}")


if __name__ == "__main__":
    main()
