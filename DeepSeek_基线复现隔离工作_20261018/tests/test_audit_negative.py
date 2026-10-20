"""Negative tests for the independent auditor.

The auditor is only useful if it actually rejects bad routes.  Each case starts
from a real, legal route produced by a planner and corrupts exactly one aspect.
"""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))
sys.path.insert(0, str(HERE))

from problem import InputError, PlanRequest, validate_inputs  # noqa: E402
from audit_independent import audit_route  # noqa: E402
from adapters import registry  # noqa: E402
from run_micro import load_cases  # noqa: E402


def case(case_id):
    for payload, request, path in load_cases():
        if request.case_id == case_id:
            return request
    raise KeyError(case_id)


def legal_route(request, method="P2_MULTI"):
    result = registry.run(method, request)
    audit = audit_route(request, result.route)
    assert audit["valid"], (method, request.case_id, audit["errors"])
    return result.route


class NegativeAudit(unittest.TestCase):
    def setUp(self):
        self.request = case("m10_transit_coverage")
        self.route = legal_route(self.request)

    def test_baseline_route_is_accepted(self):
        self.assertTrue(audit_route(self.request, self.route)["valid"])

    def test_empty_route_rejected(self):
        audit = audit_route(self.request, ())
        self.assertFalse(audit["valid"])
        self.assertIn("empty_route", audit["errors"])

    def test_diagonal_jump_rejected(self):
        route = list(self.route)
        # splice out one corner so two consecutive cells differ in both axes
        for index in range(1, len(route) - 2):
            a, b = route[index - 1], route[index + 1]
            if a[0] != b[0] and a[1] != b[1]:
                del route[index]
                audit = audit_route(self.request, route)
                self.assertIn("illegal_step", audit["errors"])
                self.assertFalse(audit["valid"])
                return
        self.skipTest("fixture produced no bend to cut")

    def test_non_free_step_rejected(self):
        blocked = sorted(set(self.request.free) - set(self.route))
        self.assertTrue(blocked, "fixture should contain unvisited free cells")
        route = list(self.route)
        # replace the middle of the route by a cell that is not free at all
        outside = (max(p[0] for p in self.request.free) + 3, 0)
        route.insert(1, outside)
        route.insert(2, route[0])
        audit = audit_route(self.request, tuple(route))
        self.assertIn("collision_or_out_of_bounds", audit["errors"])

    def test_dropped_coverage_rejected(self):
        counts = {}
        for p in self.route:
            counts[p] = counts.get(p, 0) + 1
        target = None
        for p in sorted(self.request.pending):
            if counts.get(p, 0) == 1 and 0 < self.route.index(p) < len(self.route) - 1:
                target = p
                break
        if target is None:
            self.skipTest("no singly-visited pending target")
        route = tuple(p for p in self.route if p != target)
        audit = audit_route(self.request, route)
        self.assertIn("coverage_omission", audit["errors"])

    def test_wrong_return_rejected(self):
        route = tuple(self.route[:-1]) + (tuple(self.request.current),)
        audit = audit_route(self.request, route)
        self.assertIn("missing_return", audit["errors"])

    def test_wrong_start_rejected(self):
        route = (tuple(self.request.base),) + tuple(self.route)
        audit = audit_route(self.request, route)
        self.assertIn("wrong_start", audit["errors"])

    def test_resource_overrun_rejected(self):
        tight = replace(self.request, remaining_resource=1)
        audit = audit_route(tight, self.route)
        self.assertIn("distance_budget_exceeded", audit["errors"])
        self.assertFalse(audit["resource"]["ok"])

    def test_self_reported_coverage_is_ignored(self):
        """A planner cannot claim a target by editing its own bookkeeping."""
        counts = {}
        for p in self.route:
            counts[p] = counts.get(p, 0) + 1
        target = None
        for p in sorted(self.request.pending):
            if counts.get(p, 0) == 0:
                target = p
                break
        if target is None:
            self.skipTest("route visits every pending target")
        route = tuple(p for p in self.route if p != target)
        audit = audit_route(self.request, route)
        self.assertIn("coverage_omission", audit["errors"])
        self.assertEqual(audit["coverage_complete"], False)
        # even if the caller now pretends the ledger already had it
        inflated = replace(self.request, covered=self.request.covered | {target})
        still = audit_route(inflated, route)
        self.assertTrue(still["coverage_complete"])
        # the auditor recomputes the physical set from the route, so a ledger
        # entry alone never appears as physically covered
        self.assertNotIn(list(target), still["covered_physical"])

    def test_deferred_targets_are_reported_and_never_credited(self):
        """A blocked published target is deferred: not deleted, not completed."""
        request = case("m13_deferred_target")
        if not request.deferred:
            self.skipTest("no deferred target in fixture")
        route = legal_route(request)
        audit = audit_route(request, route)
        self.assertTrue(audit["valid"], audit["errors"])
        deferred = sorted(request.deferred)
        self.assertEqual(audit["deferred_untouched"], [list(p) for p in deferred])
        for p in deferred:
            self.assertNotIn(list(p), audit["covered_physical"])
            self.assertNotIn(list(p), [list(q) for q in request.pending])
        # a deferred cell is not free, so any route that enters it must also be
        # rejected as a collision; the auditor must not accept it as coverage
        target = deferred[0]
        neighbours = [(target[0] + 1, target[1]), (target[0] - 1, target[1]),
                      (target[0], target[1] + 1), (target[0], target[1] - 1)]
        usable = [q for q in neighbours if q in request.free]
        if not usable:
            self.skipTest("deferred target has no free neighbour")
        nxt = usable[0]
        head = route[:route.index(nxt) + 1] if nxt in route else ()
        if not head or head[-1] != nxt:
            self.skipTest("neighbour of the deferred target is not on the route")
        corrupted = head + (target,) + (nxt,) + route[route.index(nxt) + 1:]
        bad = audit_route(request, corrupted)
        self.assertIn("collision_or_out_of_bounds", bad["errors"])
        self.assertFalse(bad["valid"])


class IllegalInputs(unittest.TestCase):
    def setUp(self):
        self.request = case("m05_no_change")

    def test_covered_outside_published_is_rejected(self):
        bad = replace(self.request, covered=self.request.covered | {(99, 99)})
        with self.assertRaises(InputError) as context:
            validate_inputs(bad)
        self.assertEqual(context.exception.code, "covered_not_published")

    def test_current_not_free_is_rejected(self):
        bad = replace(self.request, current=(-5, -5))
        with self.assertRaises(InputError) as context:
            validate_inputs(bad)
        self.assertEqual(context.exception.code, "current_not_free")

    def test_base_not_free_is_rejected(self):
        bad = replace(self.request, base=(-5, -5))
        with self.assertRaises(InputError) as context:
            validate_inputs(bad)
        self.assertEqual(context.exception.code, "base_not_free")

    def test_nonpositive_resource_is_rejected(self):
        bad = replace(self.request, remaining_resource=0)
        with self.assertRaises(InputError) as context:
            validate_inputs(bad)
        self.assertEqual(context.exception.code, "nonpositive_resource")

    def test_nonpositive_time_limit_is_rejected(self):
        bad = replace(self.request, termination=replace(self.request.termination,
                                                       time_limit_seconds=0))
        with self.assertRaises(InputError) as context:
            validate_inputs(bad)
        self.assertEqual(context.exception.code, "nonpositive_time_limit")

    def test_old_route_crossing_a_new_obstacle_is_a_note_not_an_error(self):
        request = case("m01_pure_obstacle")
        notes = validate_inputs(request)
        self.assertIn("old_route_crosses_blocked", [code for code, _ in notes])


if __name__ == "__main__":
    unittest.main(verbosity=2)
