"""A: epsilon-star deadline edges, driven by a manual clock.

Three boundaries, as the review asked:

1. the **connector** crosses the deadline (route produced late);
2. the **audit** crosses the deadline (route produced in time, validated late);
3. a legal candidate **exists before** the deadline (must not be degraded).

Plus: the final ``meta.deadline`` must carry the real check count, elapsed time
and hit flag - not the values copied at the start.
"""
import unittest

import conftest_v03 as cf
from adapters import registry
import audit_independent
import common_geometry


class DeadlineEdges(unittest.TestCase):
    def setUp(self):
        self._path = common_geometry.GridMetric.path
        self._audit = audit_independent.audit_route

    def tearDown(self):
        common_geometry.GridMetric.path = self._path
        audit_independent.audit_route = self._audit

    def _slow_connector(self, clock, jump):
        original = self._path

        def wrapper(metric_self, a, b):
            route = original(metric_self, a, b)
            clock.advance(jump)          # the connector returns only after the jump
            return route

        common_geometry.GridMetric.path = wrapper

    def _slow_audit(self, clock, jump):
        original = self._audit

        def wrapper(request, route, radius=0):
            result = original(request, route, radius)
            clock.advance(jump)          # the audit finishes only after the jump
            return result

        audit_independent.audit_route = wrapper

    # -- 1. connector crosses the deadline ---------------------------------
    def test_connector_crossing_the_deadline_is_not_a_candidate(self):
        clock = cf.ManualClock()
        self._slow_connector(clock, 2.0)
        result = registry.run("EPSILON_STAR", cf.line_request(seconds=1.0),
                              deadline_clock=clock)
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertFalse(result.termination["natural"])
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])
        self.assertGreater(result.meta["deadline"]["soft_deadline_checks"], 0)
        self.assertGreaterEqual(result.meta["deadline"]["soft_deadline_elapsed_seconds"], 2.0)
        self.assertFalse(result.meta["candidate"]["accepted"])

    # -- 2. audit crosses the deadline -------------------------------------
    def test_candidate_validated_after_the_deadline_is_only_diagnostic(self):
        clock = cf.ManualClock()
        self._slow_audit(clock, 2.0)
        result = registry.run("EPSILON_STAR", cf.free_grid(size=3, seconds=1.0),
                              deadline_clock=clock)
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, (), "a route validated after the deadline was graded")
        self.assertFalse(result.termination["natural"])
        candidate = result.meta["candidate"]
        self.assertTrue(candidate["post_deadline"])
        self.assertFalse(candidate["accepted"])
        self.assertIsNotNone(candidate["diagnostic_route_steps"])
        self.assertIn("diagnostic_route", result.meta)
        self.assertIn("post_deadline_candidate_excluded", result.errors)
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])

    # -- 3. candidate exists before the deadline ---------------------------
    def test_candidate_validated_in_time_is_accepted(self):
        clock = cf.ManualClock()
        result = registry.run("EPSILON_STAR", cf.free_grid(size=3, seconds=30.0),
                              deadline_clock=clock)
        self.assertEqual(result.status, "finished", result.errors)
        self.assertTrue(result.audit["valid"])
        self.assertTrue(result.termination["natural"])
        self.assertFalse(result.meta["candidate"]["post_deadline"])
        self.assertTrue(result.meta["candidate"]["accepted"])
        self.assertFalse(result.meta["deadline"]["soft_deadline_hit"])
        self.assertGreater(result.meta["deadline"]["soft_deadline_checks"], 0)

    # -- the final metadata is not the initial snapshot --------------------
    def test_final_deadline_metadata_reports_real_activity(self):
        clock = cf.ManualClock()
        result = registry.run("EPSILON_STAR", cf.free_grid(size=4, seconds=30.0),
                              deadline_clock=clock)
        deadline = result.meta["deadline"]
        self.assertGreater(deadline["soft_deadline_checks"], 1,
                           "the check counter was never incremented")
        self.assertGreater(clock.calls, deadline["soft_deadline_checks"],
                           "the clock was read fewer times than the checks reported")
        self.assertAlmostEqual(deadline["soft_deadline_elapsed_seconds"], clock.value,
                               places=9,
                               msg="elapsed is stale: it does not match the final clock value")

    # -- a real clock run still behaves ------------------------------------
    def test_real_clock_tiny_limit_is_still_reported(self):
        result = registry.run("EPSILON_STAR", cf.free_grid(size=5, seconds=1e-9))
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertFalse(result.termination["natural"])
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
