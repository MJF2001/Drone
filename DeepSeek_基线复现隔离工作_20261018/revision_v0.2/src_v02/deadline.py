"""Cooperative deadline used by the v0.2 adapters.

Two different things are kept apart on purpose:

``soft deadline``
    an absolute monotonic instant computed once at the public entry point.
    Every expensive stage calls :meth:`Deadline.check`; crossing it raises
    :class:`DeadlineExceeded`.  It is cooperative: one BFS row or one route
    expansion can still overrun it slightly, and the overrun is reported.

``hard watchdog``
    an external process-level cap (``subprocess`` timeout in the tests, or the
    runner's own process cap).  It is not implemented here because a library
    cannot kill its own caller; the tests prove it works from outside.

The clock is injectable so a test can use a controllable fake clock instead of
asserting on real nanosecond thresholds.
"""
import time


class DeadlineExceeded(TimeoutError):
    """Raised when the cooperative soft deadline is crossed."""


class Deadline:
    def __init__(self, seconds, clock=None):
        self.clock = clock or time.perf_counter
        self.limit = float(seconds)
        if self.limit <= 0:
            raise ValueError("nonpositive time limit")
        self.started = self.clock()
        self.at = self.started + self.limit
        self.hit = False
        self.checks = 0

    # -- state -----------------------------------------------------------
    def check(self):
        self.checks += 1
        if self.clock() > self.at:
            self.hit = True
            raise DeadlineExceeded(f"soft deadline crossed after {self.elapsed():.6f}s")

    @property
    def remaining(self):
        return self.at - self.clock()

    def elapsed(self):
        return self.clock() - self.started

    def report(self):
        return {"soft_deadline_seconds": self.limit, "soft_deadline_hit": self.hit,
                "soft_deadline_checks": self.checks,
                "soft_deadline_elapsed_seconds": self.elapsed(),
                "semantics": "cooperative; one stage may overrun slightly and is reported"}
