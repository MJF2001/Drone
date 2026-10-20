"""R1: the empty-task branch must obey the same legality and resource checks.

Review counterexample: three free cells in a row, Q empty, current (0,0), base
(2,0), remaining resource 1.  The return needs 2 steps.  v0.1 returned
``finished``; v0.2 must report ``resource_exceeded``.
"""
import unittest

import conftest_v02 as cf
from problem import InputError, validate_inputs
from adapters import registry
from finalize import SUCCESS_STATUSES


class EmptyPendingResource(unittest.TestCase):
    def test_reviewer_counterexample(self):
        request = cf.line_request(resource=1)
        self.assertEqual(len(request.pending), 0)
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                self.assertNotIn(result.status, SUCCESS_STATUSES,
                                 f"{method} still calls an over-budget return a success")
                # a method that returns a route says resource_exceeded; a frozen
                # engine that refuses to emit any route says so explicitly
                self.assertIn(result.status,
                              ("resource_exceeded", "no_legal_route_within_resource"), method)
                self.assertIn("resource", result.reason + str(result.errors), method)
                # a method that does emit a route must emit the direct return;
                # a frozen engine that refuses to emit one stays empty
                if result.route:
                    self.assertEqual(result.route, ((0, 0), (1, 0), (2, 0)), method)
                    self.assertEqual(result.route_steps, 2, method)
                self.assertFalse(result.audit["resource"]["ok"])
                if result.route:
                    self.assertIn("distance_budget_exceeded", result.audit["errors"], method)
                else:
                    self.assertEqual(result.status, "no_legal_route_within_resource", method)
                    self.assertIn("resource", result.reason, method)
                self.assertFalse(result.termination["natural"])

    def test_exact_resource_is_enough(self):
        request = cf.line_request(resource=2)
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                self.assertIn(result.status, SUCCESS_STATUSES, method)
                self.assertTrue(result.audit["valid"], result.audit["errors"])
                self.assertTrue(result.termination["natural"])

    def test_zero_resource_at_base_is_legal_and_finishes(self):
        request = cf.line_request(current=(2, 0), base=(2, 0), resource=0)
        notes = validate_inputs(request)          # must not raise
        self.assertIsInstance(notes, list)
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                self.assertIn(result.status, SUCCESS_STATUSES, method)
                self.assertEqual(result.route_steps, 0, method)
                self.assertTrue(result.audit["valid"], result.audit["errors"])
                self.assertTrue(result.audit["resource"]["ok"])

    def test_zero_resource_away_from_base_is_reported(self):
        request = cf.line_request(current=(0, 0), base=(2, 0), resource=0)
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                self.assertIn(result.status,
                              ("resource_exceeded", "no_legal_route_within_resource"), method)
                self.assertFalse(result.audit["resource"]["ok"])

    def test_negative_resource_is_still_rejected(self):
        request = cf.line_request(resource=-1)
        with self.assertRaises(InputError) as context:
            validate_inputs(request)
        self.assertEqual(context.exception.code, "negative_resource")

    def test_empty_task_route_is_only_the_return(self):
        """Q empty means "cover nothing"; no detour to free cells may be added."""
        request = cf.line_request(resource=5)
        direct = ((0, 0), (1, 0), (2, 0))
        for method in cf.METHODS:
            result = registry.run(method, request)
            self.assertEqual(result.route, direct, method)
            self.assertEqual(result.route_steps, 2, method)


class CompleteButOverBudget(unittest.TestCase):
    def test_full_coverage_over_budget_is_never_success(self):
        """The other half of R1/R5: complete coverage does not excuse the budget."""
        request = cf.request("m10_transit_coverage", remaining_resource=4)
        saw_over_budget = False
        for method in cf.METHODS:
            result = registry.run(method, request)
            audit = result.audit
            if audit["coverage_complete"] and not audit["resource"]["ok"]:
                saw_over_budget = True
                self.assertEqual(result.status, "resource_exceeded",
                                 f"{method} hid an over-budget completion")
                self.assertNotIn(result.status, SUCCESS_STATUSES)
        self.assertTrue(saw_over_budget, "fixture no longer produces the over-budget case")


if __name__ == "__main__":
    unittest.main(verbosity=2)
