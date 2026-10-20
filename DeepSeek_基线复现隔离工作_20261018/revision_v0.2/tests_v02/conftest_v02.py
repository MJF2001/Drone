"""Shared helpers for the v0.2 revision tests.

Every test module imports this first so that ``bootstrap_v02`` fixes module
resolution before anything imports ``problem``/``adapters``.
"""
import sys
from pathlib import Path

# R5: test calls must be registered too, distinguished from formal runs.
import os
os.environ.setdefault("DSH_RUN_KIND", "test")

V02 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V02 / "src_v02"))

import bootstrap_v02  # noqa: E402,F401  must be imported before the patched modules

from problem import PlanRequest, Termination  # noqa: E402,F401

OUT = bootstrap_v02.OUT
CASES = OUT / "tests" / "fixtures" / "cases"
SCRATCH = V02 / "scratch"


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


def line_request(current=(0, 0), base=(2, 0), resource=1, free=None, covered=None):
    """The reviewer's R1 counterexample: three free cells in a row, no task left.

    ``covered`` defaults to every cell, so ``Q`` is empty and the only remaining
    work is the return flight.
    """
    cells = free if free is not None else {(0, 0), (1, 0), (2, 0)}
    covered = frozenset(cells) if covered is None else frozenset(covered)
    return PlanRequest(
        case_id="r1_line", free=frozenset(cells),
        published_targets=frozenset(cells), covered=covered,
        current=current, base=base, old_route=(),
        remaining_resource=resource, seed=1,
        termination=Termination(time_limit_seconds=30.0),
    )


METHODS = ("P2_MULTI", "OARP_CORE2", "TREE_MST", "PPCPP_CORE4", "EPSILON_STAR", "CSTAR")
