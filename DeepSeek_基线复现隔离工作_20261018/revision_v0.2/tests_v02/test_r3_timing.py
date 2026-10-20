"""R3: the end-to-end time must be measured, not copied before the clock stops.

v0.1 built the result (and copied ``clock.stages``) inside the ``try`` block and
only called ``clock.stop()`` in ``finally``, so ``adapter_call`` was reported as
``0.0`` for real, non-zero calls.  v0.2 stops the clock first and then attaches
the snapshot; a snapshot taken before the stop raises instead of reporting zero.
"""
import unittest

import conftest_v02 as cf
from result import StageClock
from adapters import registry


class StageClockUnit(unittest.TestCase):
    def test_snapshot_before_stop_is_refused(self):
        clock = StageClock()
        clock.add("work", 0.01)
        with self.assertRaises(RuntimeError):
            clock.snapshot()

    def test_total_is_fixed_after_stop_and_equals_adapter_call(self):
        clock = StageClock()
        clock.add("work", 0.01)
        total = clock.stop_total()
        snapshot = clock.snapshot()
        self.assertEqual(snapshot["adapter_call"], total)
        self.assertEqual(snapshot["_total"], total)
        self.assertTrue(snapshot["_stopped"])
        self.assertGreater(total, 0.0)

    def test_missing_instrumentation_is_declared_not_zero(self):
        clock = StageClock()
        clock.declare_missing("internal_stage_split")
        clock.stop_total()
        snapshot = clock.snapshot()
        self.assertIn("internal_stage_split", snapshot["_missing"])
        self.assertNotIn("internal_stage_split", snapshot)
        self.assertNotIn("engine_stage_split", snapshot)


class AdapterTiming(unittest.TestCase):
    def test_every_method_reports_a_positive_end_to_end_time(self):
        request = cf.request("m02_extension_only")
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                stages = result.stage_seconds
                self.assertTrue(stages.get("_stopped"), f"{method} snapshot not closed")
                self.assertIn("adapter_call", stages)
                self.assertGreater(stages["adapter_call"], 0.0,
                                   f"{method} reported a zero end-to-end time")
                self.assertEqual(stages["_total"], stages["adapter_call"])
                self.assertIn("adapter_call", stages["_instrumented"])

    def test_no_stage_is_summed_into_the_total(self):
        """Disjoint internal stages may not be added up to imitate the total."""
        request = cf.request("m02_extension_only")
        for method in cf.METHODS:
            result = registry.run(method, request)
            stages = result.stage_seconds
            internal = [key for key in stages
                        if not key.startswith("_") and key != "adapter_call"]
            summed = sum(stages[key] for key in internal)
            self.assertLessEqual(summed, stages["adapter_call"] + 1e-6,
                                 f"{method} internal stages exceed the end-to-end time")

    def test_missing_instrumentation_is_declared_per_method(self):
        request = cf.request("m05_no_change")
        expectations = {
            "P2_MULTI": False,       # P2 records its own stage events
            "EPSILON_STAR": False,   # v0.2 instruments MAPS / ETM / return
            "CSTAR": False,          # v0.2 instruments the loop stages
            "OARP_CORE2": True,
            "TREE_MST": True,
            "PPCPP_CORE4": True,
        }
        for method, should_miss in expectations.items():
            with self.subTest(method=method):
                result = registry.run(method, request)
                missing = result.stage_seconds.get("_missing", [])
                if should_miss:
                    self.assertIn("internal_stage_split", missing,
                                  f"{method} does not measure internal stages but claims to")
                else:
                    self.assertNotEqual(result.stage_seconds["_instrumented"],
                                        ["adapter_call"],
                                        f"{method} has no real internal instrumented stage")

    def test_empty_task_branch_also_reports_time(self):
        request = cf.line_request()
        for method in cf.METHODS:
            result = registry.run(method, request)
            self.assertTrue(result.stage_seconds.get("_stopped"), method)
            self.assertGreater(result.stage_seconds["adapter_call"], 0.0, method)


if __name__ == "__main__":
    unittest.main(verbosity=2)
