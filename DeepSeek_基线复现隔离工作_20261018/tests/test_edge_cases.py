"""Edge cases required by the execution draft, checked on every method.

Each test names the boundary it covers so a reader can see that the six required
families (pure obstacle / pure extension / overlay / two events / no change /
illegal input) and the additional boundaries of section 6 are actually exercised.
"""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))
sys.path.insert(0, str(HERE))

import bootstrap  # noqa: E402,F401
from audit_independent import audit_route  # noqa: E402
from adapters import registry  # noqa: E402
from problem import environment_status, validate_inputs  # noqa: E402
from run_micro import load_cases  # noqa: E402

SUCCESS = {"finished", "planned", "planned_at_timeout", "complete_coverage"}


def case(case_id):
    for payload, request, path in load_cases():
        if request.case_id == case_id:
            return request
    raise KeyError(case_id)


def every_method():
    return registry.available()


class EventFamilies(unittest.TestCase):
    """One test per required event family, so a missing fixture is visible."""

    def _run(self, case_id):
        request = case(case_id)
        rows = []
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            rows.append((method, result, audit))
        return request, rows

    def test_pure_obstacle(self):
        request, rows = self._run("m01_pure_obstacle")
        notes = [code for code, _ in validate_inputs(request)]
        self.assertIn("old_route_crosses_blocked", notes,
                      "this fixture is supposed to exercise an old route cut by a new obstacle")
        for method, result, audit in rows:
            if result.route:
                self.assertFalse({"wrong_start", "missing_return", "illegal_step",
                                  "collision_or_out_of_bounds"} & set(audit["errors"]))

    def test_pure_extension(self):
        request, rows = self._run("m02_extension_only")
        self.assertGreater(len(request.pending), 0)
        self.assertEqual(len(request.deferred), 0)

    def test_overlay(self):
        request, rows = self._run("m03_corner_extension_and_obstacle")
        self.assertGreater(len(request.deferred), 0)
        for method, result, audit in rows:
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], (method, audit["uncovered"]))

    def test_two_events(self):
        request, rows = self._run("m04_two_events")
        self.assertGreater(len(request.deferred), 0)
        for method, result, audit in rows:
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], method)

    def test_no_change(self):
        request, rows = self._run("m05_no_change")
        self.assertEqual(len(request.deferred), 0)
        for method, result, audit in rows:
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], method)


class ModelBoundaries(unittest.TestCase):
    def test_empty_pending_returns_straight_home(self):
        request = case("m06_empty_pending")
        self.assertEqual(len(request.pending), 0)
        from common_geometry import GridMetric
        direct = GridMetric(request.free).path(tuple(request.current), tuple(request.base))
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            self.assertTrue(audit["valid"], (method, audit["errors"]))
            self.assertEqual(audit["route_steps"], len(direct) - 1,
                             f"{method} did not take the direct return")

    def test_start_equals_base(self):
        request = case("m07_start_equals_base")
        self.assertEqual(tuple(request.current), tuple(request.base))
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if result.route:
                self.assertTrue(audit["valid"], (method, audit["errors"]))
                self.assertGreater(audit["route_steps"], 0,
                                   f"{method} returned a zero-length route while targets remain")

    def test_base_belongs_to_pending(self):
        request = case("m08_base_pending")
        self.assertIn(tuple(request.base), request.pending)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            self.assertTrue(audit["valid"], (method, audit["errors"]))
            # the final cell is the base, so the base target is covered on arrival
            self.assertIn(list(request.base), audit["covered_physical"],
                          f"{method} does not credit the base cell")

    def test_start_belongs_to_pending(self):
        request = case("m17_start_pending")
        self.assertIn(tuple(request.current), request.pending)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if not result.route:
                continue
            self.assertIn(list(request.current), audit["covered_physical"],
                          f"{method} does not credit the start cell")

    def test_passing_the_base_early_does_not_end_the_run(self):
        request = case("m09_pass_base_early")
        self.assertIn(tuple(request.base), request.free)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], method)

    def test_transit_coverage_is_credited(self):
        request = case("m10_transit_coverage")
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if not result.route:
                continue
            visited_targets = [p for p in request.pending if tuple(p) in set(result.route)]
            for p in visited_targets:
                self.assertIn(list(p), audit["covered_physical"],
                              f"{method} passes over {p} without crediting it")
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], method)

    def test_covered_corridor_stays_passable(self):
        request = case("m11_covered_corridor_blocks")
        self.assertGreater(len(request.covered), 0)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if result.status in SUCCESS:
                self.assertTrue(audit["coverage_complete"], method)

    def test_insufficient_resource_is_reported_not_trimmed(self):
        request = case("m12_resource_tight")
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if result.route and audit["coverage_complete"]:
                if not audit["resource"]["ok"]:
                    # a complete route may be delivered only when the overrun is stated
                    self.assertEqual(result.status, "resource_exceeded",
                                     f"{method} returned a complete route over the resource "
                                     f"limit without saying so")
                continue
            if result.route:
                # an incomplete route must be labelled, never presented as a completion
                self.assertNotIn(result.status, SUCCESS,
                                 f"{method} claims success but does not complete the task")
            else:
                self.assertIn(result.status,
                              ("no_legal_route_within_resource", "resource_exceeded",
                               "input_precondition_unmet", "adapter_assertion",
                               "planning_failure", "timeout", "coverage_incomplete",
                               "no_legal_candidate"),
                              f"{method} produced unexpected status {result.status}")

    def test_deferred_target_is_not_deleted(self):
        request = case("m13_deferred_target")
        self.assertGreater(len(request.deferred), 0)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            self.assertEqual(len(audit["deferred_untouched"]), len(request.deferred))
            for p in request.deferred:
                self.assertNotIn(list(p), audit["covered_physical"], method)

    def test_unreachable_base_is_reported(self):
        request = case("m14_base_unreachable")
        self.assertEqual(environment_status(request)["code"], "base_unreachable")
        for method in every_method():
            result = registry.run(method, request)
            self.assertEqual(result.status, "environment_infeasible",
                             f"{method} did not report the unreachable base")
            self.assertEqual(result.route, ())

    def test_unreachable_target_is_reported(self):
        request = case("m15_target_sealed")
        self.assertEqual(environment_status(request)["code"], "target_unreachable")
        for method in every_method():
            result = registry.run(method, request)
            self.assertEqual(result.status, "environment_infeasible", method)
            self.assertEqual(result.route, ())

    def test_missing_old_route_is_accepted(self):
        request = case("m16_no_old_route")
        self.assertEqual(len(request.old_route), 0)
        for method in every_method():
            result = registry.run(method, request)
            audit = audit_route(request, result.route)
            if result.route:
                self.assertFalse({"wrong_start", "missing_return", "illegal_step",
                                  "collision_or_out_of_bounds"} & set(audit["errors"]))


class InputContradictions(unittest.TestCase):
    def test_covered_outside_published_is_rejected_for_every_caller(self):
        from problem import InputError
        request = case("m05_no_change")
        bad = replace(request, covered=request.covered | {(42, 42)})
        with self.assertRaises(InputError):
            validate_inputs(bad)

    def test_environment_infeasible_never_comes_back_as_a_route(self):
        for case_id in ("m14_base_unreachable", "m15_target_sealed"):
            request = case(case_id)
            for method in every_method():
                result = registry.run(method, request)
                self.assertEqual(result.route, ())
                self.assertEqual(result.status, "environment_infeasible")


if __name__ == "__main__":
    unittest.main(verbosity=2)
