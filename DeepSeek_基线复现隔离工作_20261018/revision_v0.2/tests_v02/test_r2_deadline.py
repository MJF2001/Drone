"""R2: the public time limit must actually be read and enforced.

v0.1 never consulted ``termination.time_limit_seconds`` inside epsilon-star: a
1e-9 limit still ran to completion and reported ``natural=True``.  v0.2 enforces
it as a cooperative soft deadline and, separately, proves that an external hard
watchdog can stop a runaway child process.

The deadline tests use an injected fake clock, so they do not depend on flaky
real nanosecond thresholds.
"""
import subprocess
import sys
import unittest

import conftest_v02 as cf
from deadline import Deadline, DeadlineExceeded
from adapters import epsilon_star, registry
from finalize import SUCCESS_STATUSES


class FakeClock:
    """A clock the test drives by hand."""

    def __init__(self, step=1e-3, start=0.0):
        self.now = start
        self.step = step
        self.calls = 0

    def __call__(self):
        self.calls += 1
        value = self.now
        self.now += self.step
        return value


def wide_request(seconds, size=5):
    cells = {(x, y) for x in range(size) for y in range(size)}
    from problem import PlanRequest, Termination
    return PlanRequest(
        case_id=f"r2_{size}x{size}", free=frozenset(cells),
        published_targets=frozenset(cells), covered=frozenset(),
        current=(0, 0), base=(0, 0), old_route=(),
        remaining_resource=None, seed=3,
        termination=Termination(time_limit_seconds=seconds),
    )


class DeadlineUnit(unittest.TestCase):
    def test_deadline_raises_when_the_clock_jumps(self):
        clock = FakeClock(step=1.0)
        deadline = Deadline(1e-9, clock=clock)
        with self.assertRaises(DeadlineExceeded):
            deadline.check()
        self.assertTrue(deadline.hit)

    def test_deadline_does_not_raise_within_the_limit(self):
        clock = FakeClock(step=0.0)
        deadline = Deadline(10.0, clock=clock)
        deadline.check()
        self.assertFalse(deadline.hit)

    def test_nonpositive_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            Deadline(0.0)


class EpsilonStarDeadline(unittest.TestCase):
    def test_tiny_limit_on_a_full_grid_is_reported_not_ignored(self):
        """The reviewer's counterexample, with a fake clock that expires at once."""
        request = wide_request(1e-9, size=5)
        clock = FakeClock(step=1.0)
        result = epsilon_star.run(request, deadline_clock=clock)
        self.assertNotIn(result.status, SUCCESS_STATUSES)
        self.assertEqual(result.status, "deadline_before_complete_route")
        self.assertEqual(result.route, ())
        self.assertFalse(result.termination["natural"])
        self.assertTrue(result.meta["deadline"]["soft_deadline_hit"])

    def test_generous_limit_finishes_normally(self):
        request = wide_request(30.0, size=5)
        result = epsilon_star.run(request)
        self.assertEqual(result.status, "finished", result.errors)
        self.assertTrue(result.audit["valid"], result.audit["errors"])
        self.assertFalse(result.meta["deadline"]["soft_deadline_hit"])

    def test_deadline_stop_is_never_reported_as_the_paper_fn(self):
        request = wide_request(1e-9, size=5)
        result = epsilon_star.run(request, deadline_clock=FakeClock(step=1.0))
        self.assertNotEqual(result.reason, "FN_no_unexplored_cell")
        self.assertNotEqual(result.reason, "FN_no_positive_potential")

    def test_partial_route_after_a_deadline_is_never_a_silent_completion(self):
        request = wide_request(1e-9, size=6)
        result = epsilon_star.run(request, deadline_clock=FakeClock(step=0.5))
        if result.route:
            audit = result.audit
            self.assertFalse(audit["valid"],
                             "a route produced at the deadline may not pass the audit")
            self.assertTrue({"coverage_omission", "missing_return"} & set(audit["errors"]))


CHILD = r'''
import sys
sys.path.insert(0, {src!r})
import bootstrap_v02
from adapters import epsilon_star
cells = frozenset((x, y) for x in range(12) for y in range(12))
from problem import PlanRequest, Termination
request = PlanRequest(case_id="watchdog", free=cells, published_targets=cells,
                      covered=frozenset(), current=(0, 0), base=(0, 0), old_route=(),
                      remaining_resource=None, seed=5,
                      termination=Termination(time_limit_seconds=0.002))
result = epsilon_star.run(request)
print(result.status)
'''


class HardWatchdog(unittest.TestCase):
    """The soft deadline is cooperative; a hard cap must come from outside."""

    def test_external_timeout_kills_a_runaway_child(self):
        code = "import time\nwhile True:\n    time.sleep(0.05)\n"
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable, "-c", code], timeout=2.0, check=False)

    def test_soft_deadline_keeps_the_child_within_an_external_cap(self):
        src = str(cf.V02 / "src_v02")
        try:
            completed = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", "-c", CHILD.format(src=src)],
                capture_output=True, text=True, timeout=20.0, check=False)
        except subprocess.TimeoutExpired:
            self.fail("the cooperative deadline did not bring the child back in 20s")
        self.assertEqual(completed.returncode, 0, completed.stderr[-800:])
        self.assertIn(completed.stdout.strip().splitlines()[-1],
                      ("deadline_before_complete_route", "finished"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
