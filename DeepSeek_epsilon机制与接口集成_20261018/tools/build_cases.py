"""The 12 synthetic micro cases, with explicit coordinates and expected properties.

Every case is at most 9x9 and fully specified here (no randomness).  ``expected``
records what the round must verify, not what the method must achieve: a case that
may legitimately be truncated says so.

Run:  python -B -X utf8 tools/build_cases.py   -> protocol/cases.json
"""
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

PROTOCOL = NEW / "protocol"
SEEDS = [20261018, 20261019]


def rect(x0, y0, w, h):
    return [(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)]


def cells(points):
    return sorted([list(p) for p in points])


def case(case_id, free, published, covered, current, base, resource, expected, note,
         old_route=None):
    return {
        "case_id": case_id,
        "free": cells(free),
        "published_targets": cells(published),
        "covered": cells(covered),
        "current": list(current),
        "base": list(base),
        "old_route": cells(old_route or []),
        "remaining_resource": resource,
        "expected": expected,
        "note": note,
    }


def build():
    cases = []

    # 1. 4x4 open, start on an interior cell that has pending cells above and below
    free = rect(0, 0, 4, 4)
    cases.append(case(
        "c01_open4x4_interior", free, free, [], (1, 1), (0, 0), 200,
        {"status": "success", "coverage_complete": True,
         "min_line5_or_line6": 1, "min_tasks": 1,
         "must_show_tasking": True},
        "interior start with pending cells on both sides; the paper's L5/L6 and the "
        "control/physical split must both be visible"))

    # 2. 8x8 with an obstacle, free stays connected
    free = [p for p in rect(0, 0, 8, 8) if p not in {(3, 3), (4, 3)}]
    cases.append(case(
        "c02_obstacle8x8", free, free, [], (0, 0), (0, 0), 400,
        {"status": "success", "coverage_complete": True,
         "note_escape": "a high-level escape is NOT required; record the actual count"},
        "two blocked cells inside an 8x8 free square; multi-scale tiling and detour"))

    # 3. 9x3 strip: only one axis splits
    free = rect(0, 0, 9, 3)
    cases.append(case(
        "c03_strip9x3", free, free, [], (0, 0), (0, 0), 200,
        {"status": "success", "coverage_complete": True},
        "single-axis split: an implementation interpretation of the paper's rule"))

    # 4. 7x5 uneven tiling: two 3-wide blocks cannot split further
    free = rect(0, 0, 7, 5)
    cases.append(case(
        "c04_uneven7x5", free, free, [], (0, 0), (0, 0), 250,
        {"status": "success", "coverage_complete": True},
        "blocks stop at different depths; each tiling must still be a partition"))

    # 5. ring corridor: the case that exposed the turn-cost oscillation
    outer = set(rect(0, 0, 9, 9))
    ring = set(rect(3, 3, 5, 5)) - set(rect(4, 4, 3, 3))
    free = sorted(outer - ring | {(5, 3)})      # one opening into the 3x3 room
    cases.append(case(
        "c05_ring", free, free, [], (0, 0), (0, 0), 400,
        {"status": "success_or_artificial_stop",
         "note": "if an artificial stop happens, it must be reported as such"},
        "ring corridor with a narrow entry; risk case for control oscillation"))

    # 6. sparse Q with a non-empty real history and passable non-target cells
    free = rect(0, 0, 6, 5)
    targets = [(0, 0), (2, 1), (4, 2), (5, 4), (1, 3), (3, 0), (5, 0), (2, 4)]
    covered = [(1, 1), (3, 3), (0, 2)]
    cases.append(case(
        "c06_sparse_history", free, targets + covered, covered, (2, 2), (0, 0), 120,
        {"status": "success", "coverage_complete": True,
         "covered_must_stay": True},
        "real coverage history C is kept; non-target free cells stay passable"))

    # 7. a published target that is blocked and not covered -> deferred, never asked
    free = [p for p in rect(0, 0, 6, 4) if p[0] != 3]
    free += [(3, 0), (3, 3)]
    published = free + [(3, 1)]          # (3,1) is published but blocked
    cases.append(case(
        "c07_blocked_target", free, published, [], (0, 0), (0, 0), 250,
        {"status": "success", "coverage_complete": True, "deferred_min": 1},
        "one published target is inside the wall: it becomes deferred, never completed"))

    # 8. a pending target in another free component -> environment infeasible
    free = [p for p in rect(0, 0, 7, 3) if p[0] != 3]   # a full wall splits the map
    published = list(free)                             # targets exist on both sides
    cases.append(case(
        "c08_unreachable", free, published, [], (0, 0), (0, 0), 200,
        {"status": "environment_infeasible", "coverage_complete": False},
        "the right component is reachable only through one cell; the left component's "
        "targets are unreachable from the start"))

    # 9. empty Q at the base with zero resource
    free = rect(0, 0, 3, 3)
    covered = [(0, 1), (2, 2)]
    cases.append(case(
        "c09_empty_at_base", free, covered, covered, (0, 0), (0, 0), 0,
        {"status": "success", "route_steps": 0, "coverage_complete": True},
        "nothing to do, already at the base, no resource: a legal zero-step success"))

    # 10/11. empty Q, two steps from the base, resource 1 then 2
    for case_id, resource, expected in (
            ("c10_empty_far_resource1", 1, {"status": "resource_exceeded",
                                            "coverage_complete": True}),
            ("c11_empty_far_resource2", 2, {"status": "success", "route_steps": 2,
                                            "coverage_complete": True})):
        cases.append(case(
            case_id, free, covered, covered, (2, 0), (0, 0), resource, expected,
            "the return leg is charged even when the task is empty"))

    # 12. the current position is not free
    cases.append(case(
        "c12_bad_input", free, covered, covered, (5, 5), (0, 0), 50,
        {"status": "input_precondition_unmet", "coverage_complete": False},
        "current outside free must be rejected with a named reason, not crash"))

    return cases


def main():
    PROTOCOL.mkdir(parents=True, exist_ok=True)
    cases = build()
    payload = {
        "seeds": SEEDS,
        "count": len(cases),
        "note": "coordinates are Cartesian (x, y); every case is <= 9x9; two seeds give "
                "24 planned runs",
        "cases": cases,
    }
    path = PROTOCOL / "cases.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path}")
    for item in cases:
        print(f"  {item['case_id']:26s} free={len(item['free']):3d} "
              f"P={len(item['published_targets']):3d} C={len(item['covered']):3d} "
              f"resource={item['remaining_resource']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
