"""Interface boundary tests.  Each real run adds one ledger row.

Real calls (6): connector-crossing deadline, audit-crossing deadline, an accepted
in-time candidate for the second method, a 50 ms audit injection (baseline +
injected), and the empty-task-at-base case.

Mock-only: start-write failure, end-write failure, orphan-start detection.  Those
replace the entry with a stub, so no solver runs.
"""
import json
import os
import sys
import time
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import common_geometry  # noqa: E402
import audit_independent  # noqa: E402
import entry  # noqa: E402
import methods  # noqa: E402
from adapters import registry  # noqa: E402
from problem import PlanRequest, Termination  # noqa: E402

ATTEMPT = os.environ.get("OARP_TEST_BATCH", "b1")


class ManualClock:
    def __init__(self, start=0.0):
        self.value = start
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


def rect(cells, current=(0, 0), base=(0, 0), resource=1000, seed=20261018, seconds=5.0):
    cells = frozenset(map(tuple, cells))
    return PlanRequest(case_id="boundary", free=cells, published_targets=cells,
                       covered=frozenset(), current=tuple(current), base=tuple(base),
                       old_route=(), remaining_resource=resource, seed=seed,
                       termination=Termination(time_limit_seconds=seconds))


def run(request, method, tag, **kwargs):
    registry.CONTEXT.update({"kind": "interface", "batch": f"IFACE_{ATTEMPT}",
                             "run_id": f"IFACE:{ATTEMPT}:{tag}",
                             "plan_id": f"IFACE:{ATTEMPT}:{tag}",
                             "case_id": request.case_id})
    seconds = kwargs.pop("seconds", request.termination.time_limit_seconds)
    return registry.run(method, request, seconds=seconds, seed=20261018, **kwargs)


class DeadlineEdges(unittest.TestCase):
    def test_connector_crossing_the_deadline(self):
        original = common_geometry.GridMetric.path
        clock = ManualClock()

        def wrapper(metric, a, b):
            route = original(metric, a, b)
            clock.advance(2.0)
            return route

        common_geometry.GridMetric.path = wrapper
        try:
            result = run(rect([[x, y] for x in range(4) for y in range(3)]),
                         methods.METHOD_RANK0, "connector_cross",
                         seconds=1.0, deadline_clock=clock)
        finally:
            common_geometry.GridMetric.path = original
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertFalse(result.meta["flags"]["candidate_accepted_in_time"])

    def test_audit_crossing_the_deadline(self):
        original = audit_independent.audit_route
        clock = ManualClock()

        def wrapper(request, route, radius=0):
            out = original(request, route, radius)
            clock.advance(2.0)
            return out

        audit_independent.audit_route = wrapper
        try:
            result = run(rect([[x, y] for x in range(3) for y in range(2)]),
                         methods.METHOD_RANK0, "audit_cross",
                         seconds=1.0, deadline_clock=clock)
        finally:
            audit_independent.audit_route = original
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertIn("diagnostic_route", result.meta)
        self.assertFalse(result.meta["candidate"]["accepted"])

    def test_candidate_accepted_before_the_deadline(self):
        result = run(rect([[x, 0] for x in range(4)]), methods.METHOD_RANK0,
                     "candidate_ok")
        self.assertEqual(result.status, "finished")
        flags = result.meta["flags"]
        self.assertTrue(flags["candidate_accepted_in_time"])
        self.assertTrue(flags["call_within_budget"])
        self.assertTrue(result.audit["valid"])
        self.assertGreater(result.meta["deadline"]["soft_deadline_checks"], 1)


class AuditTiming(unittest.TestCase):
    def test_audit_time_is_inside_the_call(self):
        cells = [[x, 0] for x in range(4)]
        baseline = run(rect(cells), methods.METHOD_RANK0, "inject_base")
        original = audit_independent.audit_route

        def slow(request, route, radius=0):
            time.sleep(0.05)
            return original(request, route, radius)

        audit_independent.audit_route = slow
        try:
            injected = run(rect(cells), methods.METHOD_RANK0, "inject_slow")
        finally:
            audit_independent.audit_route = original
        growth = injected.stage_seconds["_sum"] - baseline.stage_seconds["_sum"]
        self.assertGreaterEqual(growth, 0.04, f"audit outside the measured cost ({growth:.3f}s)")


class EmptyTask(unittest.TestCase):
    def test_empty_task_at_base_with_zero_resource(self):
        cells = [[0, 0], [1, 0], [2, 0]]
        request = PlanRequest(case_id="empty", free=frozenset(map(tuple, cells)),
                              published_targets=frozenset({(0, 0)}),
                              covered=frozenset({(0, 0)}), current=(0, 0),
                              base=(0, 0), old_route=(), remaining_resource=0,
                              seed=20261018,
                              termination=Termination(time_limit_seconds=5.0))
        result = run(request, methods.METHOD_RANK0, "empty_at_base")
        self.assertEqual(result.status, "finished")
        self.assertEqual(result.route_steps, 0)
        self.assertTrue(result.audit["coverage_complete"])


class LedgerProtection(unittest.TestCase):
    def setUp(self):
        self._append = registry._append
        self._entry = entry.run
        self._failures = list(registry.LEDGER_FAILURES)

    def tearDown(self):
        registry._append = self._append
        entry.run = self._entry
        registry.LEDGER_FAILURES[:] = self._failures

    def _stub(self):
        from result import PlanResult

        def stub(request, method_id, **kwargs):
            result = PlanResult(method_id=method_id, method_version="stub",
                                route=((0, 0),), status="finished",
                                audit={"valid": True, "coverage_complete": True,
                                       "route_steps": 0, "errors": []},
                                termination={"natural": True, "reason": "stub"},
                                meta={"flags": {}, "core_detail": {}})
            return result

        return stub

    def test_start_write_failure_runs_no_solver(self):
        entry.run = self._stub()

        def failing(row):
            raise OSError("simulated ledger failure")

        registry._append = failing
        with self.assertRaises(registry.LedgerWriteError):
            run(rect([[0, 0], [1, 0]]), methods.METHOD_RANK0, "ledger_start_fail")
        self.assertEqual(registry.LEDGER_FAILURES[-1]["phase"], "start")

    def test_end_write_failure_is_reported(self):
        entry.run = self._stub()
        state = {"n": 0}

        def flaky(row):
            state["n"] += 1
            if state["n"] == 2:
                raise OSError("simulated ledger failure on end")
            return self._append(row)

        registry._append = flaky
        result = run(rect([[0, 0], [1, 0]]), methods.METHOD_RANK0, "ledger_end_fail")
        self.assertIn("ledger_write_error", result.meta)
        self.assertTrue(any(item["phase"] == "end" for item in registry.LEDGER_FAILURES))


class SavedEvidence(unittest.TestCase):
    """Checks over saved artifacts; no solver call."""

    def test_closed_loop_summary(self):
        path = NEW / "artifacts" / "closed_loop_summary.json"
        if not path.is_file():
            self.skipTest("closed loop not run")
        summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(summary["preparations"]), 3)
        self.assertEqual(len(summary["events"]), 8)
        for event in summary["events"]:
            self.assertEqual(len(event["responses"]), 4, event["case_id"])
            for response in event["responses"]:
                self.assertEqual(response["status"], "finished", event["case_id"])

    def test_native_roundtrip(self):
        import native
        path = NEW / "artifacts" / "plans" / "prep_rect.json"
        if not path.is_file():
            self.skipTest("no saved plan")
        plan = native.NativePlan.from_dict(json.loads(path.read_text(encoding="utf-8")))
        again = native.NativePlan.from_dict(json.loads(native.dumps(plan)))
        self.assertEqual(native.dumps(plan), native.dumps(again))


if __name__ == "__main__":
    unittest.main(verbosity=2)
