"""Boundary tests.  Every test that runs the core adds one ledger row.

Classification (see ``protocol/test_plan.md``):

* tests 1-7 and 9 run the integrated adapter and are counted as *boundary* calls;
* tests 8 and 10-12 use mocks or saved evidence only and add no planner call.

Run:  python -B -X utf8 -m unittest test_boundaries -v
"""
import csv
import json
import os
import sys
import time
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import audit_independent  # noqa: E402
import common_geometry  # noqa: E402
import inputs  # noqa: E402
from adapters import epsilon_star, registry  # noqa: E402
from result import PlanResult  # noqa: E402


class ManualClock:
    def __init__(self, start=0.0):
        self.value = float(start)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


class TickClock:
    """Advances on every read; the deadline is crossed *inside* a stage."""

    def __init__(self, step):
        self.step = float(step)
        self.value = 0.0

    def __call__(self):
        self.value += self.step
        return self.value


def fresh(case_id, seed=20261018, soft=10.0, resource=None):
    request = inputs.load_case(case_id, seed, soft)
    if resource is not None:
        request = request.replaced(remaining_resource=resource)
    return request


ATTEMPT = os.environ.get("EPS_TEST_BATCH", "b1")


def run(request, tag, **kwargs):
    registry.CONTEXT.update({"kind": "boundary", "batch": f"BOUNDARY_{ATTEMPT}",
                             "plan_id": f"BOUNDARY:{ATTEMPT}:{tag}",
                             "run_id": f"BOUNDARY:{ATTEMPT}:{tag}",
                             "soft_limit": request.termination.time_limit_seconds})
    return registry.run(registry.METHOD_ID, request, **kwargs)


class DeadlineBoundaries(unittest.TestCase):
    def test_deadline_crossed_inside_maps(self):
        result = run(fresh("c01_open4x4_interior", soft=2.0), "maps_cross",
                     deadline_clock=TickClock(0.6))
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])
        self.assertFalse(result.termination["natural"])

    def test_deadline_crossed_after_the_connector(self):
        original = common_geometry.GridMetric.path
        clock = ManualClock()

        def wrapper(metric, a, b):
            route = original(metric, a, b)
            clock.advance(2.0)      # the connector returns only after the jump
            return route

        common_geometry.GridMetric.path = wrapper
        try:
            result = run(fresh("c02_obstacle8x8", soft=1.0), "connector_cross",
                         deadline_clock=clock)
        finally:
            common_geometry.GridMetric.path = original
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])

    def test_deadline_crossed_by_the_audit(self):
        original = audit_independent.audit_route
        clock = ManualClock()

        def wrapper(request, route, radius=0):
            out = original(request, route, radius)
            clock.advance(2.0)
            return out

        audit_independent.audit_route = wrapper
        try:
            result = run(fresh("c01_open4x4_interior", soft=1.0), "audit_cross",
                         deadline_clock=clock)
        finally:
            audit_independent.audit_route = original
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, (), "a late audit must not be graded")
        self.assertTrue(result.meta["candidate"]["post_deadline"])
        self.assertFalse(result.meta["candidate"]["accepted"])
        self.assertIn("post_deadline_candidate_excluded", result.meta["errors"])
        self.assertIn("diagnostic_route", result.meta)

    def test_candidate_accepted_before_the_deadline(self):
        result = run(fresh("c01_open4x4_interior", soft=10.0), "candidate_ok")
        self.assertEqual(result.status, "finished")
        self.assertTrue(result.meta["candidate"]["accepted"])
        self.assertFalse(result.meta["candidate"]["post_deadline"])
        self.assertTrue(result.audit["valid"])
        self.assertGreater(result.meta["deadline"]["soft_deadline_checks"], 1)

    def test_a_real_tiny_budget_still_takes_the_deadline_path(self):
        request = inputs.load_case("c01_open4x4_interior", 20261018, 1e-9)
        result = run(request, "tiny_real")
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])
        self.assertEqual(result.route, ())


class TimingBoundary(unittest.TestCase):
    def test_audit_time_is_inside_the_call(self):
        baseline = run(fresh("c03_strip9x3"), "inject_baseline")
        original = audit_independent.audit_route

        def slow(request, route, radius=0):
            time.sleep(0.05)
            return original(request, route, radius)

        audit_independent.audit_route = slow
        try:
            injected = run(fresh("c03_strip9x3"), "inject_audit")
        finally:
            audit_independent.audit_route = original
        growth = (injected.stage_seconds["_sum"] - baseline.stage_seconds["_sum"])
        self.assertGreaterEqual(growth, 0.04,
                                f"the audit is outside the measured cost (grew {growth:.3f}s)")
        self.assertEqual(set(baseline.stage_seconds) - {"_sum"},
                         set(injected.stage_seconds) - {"_sum"})


class ArtificialStop(unittest.TestCase):
    def test_step_limit_is_not_a_natural_fn(self):
        result = run(fresh("c02_obstacle8x8"), "step_limit", max_steps=3)
        self.assertEqual(result.meta["engine"]["terminal"], "step_limit")
        self.assertFalse(result.termination["natural"])
        self.assertNotEqual(result.status, "finished")
        self.assertTrue(result.errors)


class LedgerProtection(unittest.TestCase):
    def setUp(self):
        self._append = registry._append
        self._run = epsilon_star.run
        self._failures = list(registry.LEDGER_FAILURES)

    def tearDown(self):
        registry._append = self._append
        epsilon_star.run = self._run
        registry.LEDGER_FAILURES[:] = self._failures

    def _stub(self, status="finished"):
        def stub(request, clock=None, **kwargs):
            return PlanResult(method_id="EPSILON_STAR", method_version="stub",
                              route=((0, 0),), status=status,
                              audit={"valid": True, "coverage_complete": True,
                                     "route_steps": 0, "errors": []},
                              termination={"natural": True, "reason": "stub"},
                              meta={"engine": {"terminal": "stub"}, "events": {}})
        return stub

    def test_start_write_failure_aborts_before_any_planner_call(self):
        epsilon_star.run = self._stub()

        def failing(row):
            raise OSError("simulated ledger failure")

        registry._append = failing
        with self.assertRaises(registry.LedgerWriteError):
            run(fresh("c01_open4x4_interior"), "ledger_start_fail")
        self.assertTrue(registry.LEDGER_FAILURES)
        self.assertEqual(registry.LEDGER_FAILURES[-1]["phase"], "start")

    def test_end_write_failure_is_reported(self):
        epsilon_star.run = self._stub()
        state = {"n": 0}

        def flaky(row):
            state["n"] += 1
            if state["n"] == 2:
                raise OSError("simulated ledger failure on end")
            return self._append(row)

        registry._append = flaky
        result = run(fresh("c01_open4x4_interior"), "ledger_end_fail")
        self.assertIn("ledger_write_error", result.meta)
        self.assertTrue(any(item["phase"] == "end" for item in registry.LEDGER_FAILURES))


class SavedEvidence(unittest.TestCase):
    """Checks over the saved integration batch: no planner call."""

    def _results(self):
        out = {}
        for path in sorted((NEW / "artifacts" / "runs").glob("INT__*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            out[payload["case_id"]] = payload
        return out

    def test_empty_task_cases(self):
        results = self._results()
        if not results:
            self.skipTest("integration batch not run")
        zero = results["c09_empty_at_base"]
        self.assertEqual(zero["status"], "finished")
        self.assertEqual(zero["route_steps"], 0)
        self.assertEqual(zero["meta"]["events"]["index_first_physical_complete"], 0)
        short = results["c10_empty_far_resource1"]
        self.assertEqual(short["status"], "resource_exceeded")
        exact = results["c11_empty_far_resource2"]
        self.assertEqual(exact["status"], "finished")
        self.assertEqual(exact["route_steps"], 2)

    def test_control_and_physical_indices_are_recorded(self):
        results = self._results()
        if not results:
            self.skipTest("integration batch not run")
        for case_id, payload in results.items():
            events = payload["meta"].get("events") or {}
            if payload["status"] not in ("finished", "finished_with_safety_limit"):
                continue
            self.assertIsNotNone(events["index_first_physical_complete"], case_id)
            self.assertIsNotNone(events["index_control_fn"], case_id)
            self.assertIsNotNone(events["index_return_end"], case_id)
            self.assertGreaterEqual(events["index_control_fn"],
                                    events["index_first_physical_complete"], case_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
