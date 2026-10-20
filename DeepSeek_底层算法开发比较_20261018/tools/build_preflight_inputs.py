"""Build the two fixed synthetic preflight maps.

The execution draft fixes them: one obstacle-free small map and one small map with
an obstacle where every remaining target is still reachable.  Both must carry a
realistic old remaining route so that ``OARP_CORE2``'s input precondition (its
rank adapter needs the old route to enumerate every original pending cell) is
satisfied.

Construction (same idea as the earlier micro fixtures): a boustrophedon scan over
the pre-event targets is executed to a fixed fraction, the executed prefix becomes
the real coverage ledger and the real current position, and the unexecuted suffix
becomes the old remaining route.  No planner is called.

These maps are written once and then hashed into the protocol; they are never
used for tuning.
"""
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401
from common_geometry import GridMetric, chain  # noqa: E402

OUT = NEW / "preflight" / "inputs"


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


def build(case_id, free, pre_targets, progress, blocked, base, notes):
    metric = GridMetric(free)
    order = boustrophedon(pre_targets)
    route = chain(metric, [tuple(base)] + order + [tuple(base)])
    k = max(1, min(len(route) - 3, int(round(progress * (len(route) - 1)))))
    covered = frozenset(set(route[:k + 1]) & set(pre_targets))
    old_route = tuple(route[k:])
    published = frozenset(pre_targets)
    free_after = frozenset(set(free) - set(blocked))
    pending = frozenset((published - covered) & free_after)
    deferred = frozenset((published - covered) - free_after)
    return {
        "case_id": case_id,
        "notes": notes,
        "grid": {
            "free": sorted([list(p) for p in free_after]),
            "published_targets": sorted([list(p) for p in published]),
            "covered": sorted([list(p) for p in covered]),
            "current": list(route[k]),
            "base": list(base),
            "old_route": [list(p) for p in old_route],
            "initial_targets": sorted([list(p) for p in pre_targets]),
            "remaining_resource": 4 * len(free_after),
        },
        "expected": {"pending": len(pending), "deferred": len(deferred)},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []

    free_a = rect(0, 0, 6, 4)
    cases.append(build(
        "pf_open_small", free_a, rect(1, 1, 4, 2), 0.4, set(), (0, 0),
        "obstacle-free 6x4 map, 8x2 target band, executed to 40% of a row scan"))

    free_b = rect(0, 0, 6, 4)
    cases.append(build(
        "pf_obstacle_small", free_b, rect(1, 1, 4, 2), 0.35, {(3, 2)}, (0, 0),
        "same size with one blocked cell inside the band; every remaining target "
        "stays reachable through the free row"))

    written = []
    for payload in cases:
        path = OUT / f"{payload['case_id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        written.append({"case_id": payload["case_id"], "path": str(path),
                        "pending": payload["expected"]["pending"],
                        "deferred": payload["expected"]["deferred"],
                        "free": len(payload["grid"]["free"]),
                        "old_route_len": len(payload["grid"]["old_route"])})
    print(json.dumps(written, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
