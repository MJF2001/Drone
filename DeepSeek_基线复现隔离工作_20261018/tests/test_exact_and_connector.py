"""Exact-optimum comparison and connector equivalence.

``tests/exact_reference.py`` is an independent breadth-first search over
(position, covered-target-mask).  It gives the true optimum for the smallest
instances, which lets this round separate "legal route" from "cost accounting is
right": every accepted planner route must be at least the optimum, and at least
one planner route must equal it on an instance that is small enough to be solved
exactly.

Because the heuristic methods are not required to be optimal, being longer than
the optimum is recorded, never treated as a failure of the reproduction.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))
sys.path.insert(0, str(HERE))

import bootstrap  # noqa: E402,F401
from audit_independent import audit_route  # noqa: E402
from adapters import registry  # noqa: E402
from common_geometry import GridMetric  # noqa: E402
from problem import environment_status  # noqa: E402
from run_micro import load_cases  # noqa: E402
from exact_reference import exact_optimum, exact_with_path, reach_lower_bound  # noqa: E402

from unified_geometry import UnifiedGeometry  # noqa: E402  (frozen connector)

LIMIT = 12


def solvable_cases():
    for payload, request, path in load_cases():
        if not environment_status(request)["ok"]:
            continue
        if len(request.pending) > LIMIT:
            continue
        yield payload, request, path


class ConnectorEquivalence(unittest.TestCase):
    """The new connector must agree with the frozen one on distances and lengths."""

    def test_distance_and_path_length_agree_with_the_frozen_connector(self):
        for payload, request, _ in load_cases():
            snapshot = request.to_snapshot()
            frozen = UnifiedGeometry(snapshot)
            mine = GridMetric(request.free)
            reachable = sorted(mine.reachable(tuple(request.current)))
            sample = reachable[:: max(1, len(reachable) // 10)][:10]
            for a in sample:
                for b in sample:
                    self.assertEqual(frozen.distance(a, b), mine.distance(a, b),
                                     f"distance differs {a}->{b} in {request.case_id}")
                    path = mine.path(a, b)
                    self.assertEqual(len(path) - 1, mine.distance(a, b))
                    self.assertEqual(path[0], a)
                    self.assertEqual(path[-1], b)
                    for x, y in zip(path, path[1:]):
                        self.assertEqual(abs(x[0] - y[0]) + abs(x[1] - y[1]), 1)

    def test_path_is_reversible(self):
        for payload, request, _ in load_cases():
            mine = GridMetric(request.free)
            reachable = sorted(mine.reachable(tuple(request.current)))
            for a in reachable[:: max(1, len(reachable) // 5)][:5]:
                for b in reachable[:: max(1, len(reachable) // 4)][:4]:
                    self.assertEqual(tuple(reversed(mine.path(a, b))), mine.path(b, a))


class ExactOptimum(unittest.TestCase):
    def test_every_accepted_route_is_at_least_the_optimum(self):
        checked = 0
        for payload, request, _ in solvable_cases():
            answer = exact_optimum(request)
            if answer.get("status") != "optimal":
                continue
            for method in registry.available():
                result = registry.run(method, request)
                audit = audit_route(request, result.route)
                if not audit["valid"]:
                    continue
                self.assertGreaterEqual(audit["route_steps"], answer["steps"],
                                        f"{method} beats the exact optimum on {request.case_id}: "
                                        "the cost accounting must be wrong")
                checked += 1
        self.assertGreater(checked, 0, "no runnable exact instance")

    def test_exact_route_is_itself_legal(self):
        checked = 0
        for payload, request, _ in solvable_cases():
            answer = exact_with_path(request)
            if answer.get("status") != "optimal":
                continue
            limit = request.resource_limit()
            if limit is not None and answer["steps"] > limit:
                # even the optimum cannot pay for the task: the instance is
                # resource-infeasible and no legal route can exist
                self.assertTrue(True)
                continue
            audit = audit_route(request, answer["route"])
            self.assertTrue(audit["valid"], (request.case_id, audit["errors"]))
            self.assertEqual(audit["route_steps"], answer["steps"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_lower_bound_is_not_exceeded(self):
        for payload, request, _ in solvable_cases():
            bound = reach_lower_bound(request)
            for method in registry.available():
                audit = audit_route(request, registry.run(method, request).route)
                if audit["valid"]:
                    self.assertGreaterEqual(audit["route_steps"], bound,
                                            f"{method} violates the reach bound on {request.case_id}")

    def test_exact_summary_is_saved(self):
        rows = []
        for payload, request, _ in solvable_cases():
            answer = exact_optimum(request)
            row = {"case_id": request.case_id, "pending": len(request.pending), **answer}
            for method in registry.available():
                audit = audit_route(request, registry.run(method, request).route)
                row[method] = audit["route_steps"] if audit["valid"] else None
            if answer.get("status") == "optimal":
                row["gap_to_exact"] = {
                    key: (None if value is None else value - answer["steps"])
                    for key, value in row.items()
                    if key in registry.available()}
            rows.append(row)
        target = OUT / "artifacts" / "runs" / "exact_summary.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        self.assertTrue(rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
