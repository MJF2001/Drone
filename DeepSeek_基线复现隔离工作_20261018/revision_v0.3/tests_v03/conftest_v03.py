"""Shared helpers for the v0.3 revision tests."""
import os
import sys
from pathlib import Path

# R5 / C1: test calls must be registered, and distinguishable from formal ones.
os.environ.setdefault("DSH_RUN_KIND", "test")

V03 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V03))            # so tests can import verify_v03 / tools
sys.path.insert(0, str(V03 / "src_v03"))

import bootstrap_v03  # noqa: E402,F401  must come first

from problem import PlanRequest, Termination  # noqa: E402,F401

OUT = bootstrap_v03.OUT
CASES = OUT / "tests" / "fixtures" / "cases"
SCRATCH = V03 / "scratch"
METHODS = ("P2_MULTI", "OARP_CORE2", "TREE_MST", "PPCPP_CORE4", "EPSILON_STAR", "CSTAR")


class ManualClock:
    """A clock the test drives explicitly (no dependence on real time)."""

    def __init__(self, start=0.0):
        self.value = float(start)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


def request(case_id, **overrides):
    import json
    payload = json.loads((CASES / f"{case_id}.json").read_text(encoding="utf-8"))
    grid = payload["grid"]
    base = dict(
        case_id=case_id,
        free=frozenset(map(tuple, grid["free"])),
        published_targets=frozenset(map(tuple, grid["published_targets"])),
        covered=frozenset(map(tuple, grid["covered"])),
        current=tuple(grid["current"]),
        base=tuple(grid["base"]),
        old_route=tuple(map(tuple, grid["old_route"])),
        remaining_resource=grid["remaining_resource"],
        initial_targets=frozenset(map(tuple, grid["initial_targets"])),
        seed=20261018,
        termination=Termination(time_limit_seconds=30.0),
    )
    base.update(overrides)
    return PlanRequest(**base)


def line_request(seconds=1.0, resource=1):
    """Empty task on a three-cell line: the return needs two steps."""
    cells = {(0, 0), (1, 0), (2, 0)}
    return PlanRequest(
        case_id="a_line", free=frozenset(cells), published_targets=frozenset(cells),
        covered=frozenset(cells), current=(0, 0), base=(2, 0), old_route=(),
        remaining_resource=resource, seed=1,
        termination=Termination(time_limit_seconds=seconds),
    )


def free_grid(size=4, seconds=30.0):
    cells = frozenset((x, y) for x in range(size) for y in range(size))
    return PlanRequest(
        case_id=f"a_grid_{size}", free=cells, published_targets=cells,
        covered=frozenset(), current=(0, 0), base=(0, 0), old_route=(),
        remaining_resource=None, seed=3,
        termination=Termination(time_limit_seconds=seconds),
    )
