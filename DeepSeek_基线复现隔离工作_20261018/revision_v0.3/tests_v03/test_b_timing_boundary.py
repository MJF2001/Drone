"""B: the pre-return legality check must be inside the measured cost.

The reviewer's diagnostic was: add 50 ms inside ``finalize`` without changing the
algorithm or the route; a real call then takes ~51 ms while ``adapter_call`` stays
~0.04 ms.  That proved the mandatory result validation was outside the timing.

Here the same 50 ms is injected into ``audit_independent.audit_route`` (which
``finalize`` calls) and the test requires every method's ``adapter_call`` to have
grown accordingly, i.e. all methods share one entry/exit boundary.
"""
import time
import unittest

import conftest_v03 as cf
from adapters import registry
import audit_independent

INJECTED = 0.05
FLOOR = 0.04          # generous lower bound for a 50 ms sleep


class ValidationInsideTiming(unittest.TestCase):
    def setUp(self):
        self._audit = audit_independent.audit_route

    def tearDown(self):
        audit_independent.audit_route = self._audit

    def _slow_audit(self):
        original = self._audit

        def wrapper(request, route, radius=0):
            time.sleep(INJECTED)
            return original(request, route, radius)

        audit_independent.audit_route = wrapper

    def test_injected_validation_delay_appears_in_adapter_call(self):
        request = cf.request("m05_no_change")
        self._slow_audit()
        for method in cf.METHODS:
            with self.subTest(method=method):
                result = registry.run(method, request)
                stages = result.stage_seconds
                self.assertGreaterEqual(
                    stages["adapter_call"], FLOOR,
                    f"{method}: the pre-return validation is outside the measured cost")
                self.assertTrue(stages["_stopped"])

    def test_delay_is_visible_against_the_unslept_baseline(self):
        request = cf.request("m05_no_change")
        for method in cf.METHODS:                    # warm up: drop first-call overhead
            registry.run(method, request)
        baseline = {m: registry.run(m, request).stage_seconds["adapter_call"]
                    for m in cf.METHODS}
        self._slow_audit()
        slept = {m: registry.run(m, request).stage_seconds["adapter_call"]
                 for m in cf.METHODS}
        for method in cf.METHODS:
            with self.subTest(method=method):
                growth = slept[method] - baseline[method]
                self.assertGreaterEqual(
                    growth, FLOOR,
                    f"{method}: measured cost grew by only {growth:.4f}s "
                    f"despite a {INJECTED}s validation delay")

    def test_no_method_publishes_a_zero_total(self):
        request = cf.request("m02_extension_only")
        for method in cf.METHODS:
            stages = registry.run(method, request).stage_seconds
            self.assertGreater(stages["adapter_call"], 0.0, method)
            self.assertEqual(stages["_total"], stages["adapter_call"])
            internal = [k for k in stages
                        if not k.startswith("_") and k != "adapter_call"]
            self.assertLessEqual(sum(stages[k] for k in internal),
                                 stages["adapter_call"] + 1e-9, method)


if __name__ == "__main__":
    unittest.main(verbosity=2)
