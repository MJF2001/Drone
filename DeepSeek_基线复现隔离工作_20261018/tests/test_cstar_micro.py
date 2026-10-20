"""Micro tests for the adapted C* port (``CSTAR``).

What is proven here (and what is not)
-------------------------------------
* every fixture in ``tests/fixtures/cases`` is run in both adapter modes with a
  10 s hard cap, and every returned route is re-checked by the *independent*
  auditor ``src/audit_independent.py`` -- the adapter is never asked whether it
  succeeded;
* the deferred ledger is untouched, the empty-pending fixture returns exactly
  the ``GridMetric`` shortest return, and two runs with the same seed return the
  identical route;
* the graded route is the C* route plus the fixed base return **only**: no
  post-processing pass is appended and none is attributed to C*.  A test drives
  the wall-clock cap so that the C* route covers nothing, checks
  ``status="coverage_incomplete"`` / ``errors=["coverage_omitted:<n>"]``, and
  separately checks that the opt-in ``completion_tsp=True`` variant (a different
  ``method_version`` suffix and ``final_source``) is the only way any completion
  TSP ever appears;
* the RCG keeps the paper's graph metric (a ``sqrt(2)`` cross-lap edge and a
  long same-lap edge are present on a public-map micro case) while every edge is
  realisable by a four-neighbour ``GridMetric`` path;
* Algorithm 1's fixed Left -> Up -> Down -> Right order, Algorithm 2's leftward
  link-node insertion at distance w, and the three Algorithm-3 TSP end cases are
  exercised directly;
* the public-map degeneration is measured and written to
  ``artifacts/cstar_trace/degeneration_public_map.json``: the sampler yields the
  boundary ring only, and a free pocket two cells behind an obstacle ring makes
  the RCG disconnected, which the historical invariant rejects and the adapter
  answers with its labelled ledger-completion fallback;
* hand-traceable decision traces are written, one Algorithm-4 record per
  iteration, to ``artifacts/cstar_trace/``.

This is not a proof that the paper's continuous-area coverage theorem holds under
footprint radius 0, and it is not a performance comparison.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))

from adapters.cstar import METHOD_ID, METHOD_VERSION, run  # noqa: E402
from audit_independent import audit_route  # noqa: E402
from common_geometry import GridMetric  # noqa: E402
from problem import PlanRequest, Termination, environment_status  # noqa: E402

from cstar_core.planner import CStar, optimize_tsp  # noqa: E402
from cstar_core.public_map import (PublicMap, published_observation,  # noqa: E402
                                   dist)
from cstar_core.rcg import RCG  # noqa: E402

CASES = OUT / "tests" / "fixtures" / "cases"
TRACE_DIR = OUT / "artifacts" / "cstar_trace"
MODES = ("public_map", "sensed")
SENSOR_RADIUS = 2.0
TIME_LIMIT = 10.0
SUCCESS = ("finished",)

TRACE_LEGEND = {
    "iteration": "Algorithm 4 iteration index i",
    "step": "index of the last executed cell in the four-neighbour route at that point",
    "node_count/edge_count": "RCG size after sampling and pruning, before goal selection",
    "why.group": ("which Algorithm 1 rule fired: fixed order left -> up -> down -> right, "
                  "then 'retreat' (dead end), then 'exhausted' (no open node and no retreat)"),
    "why.options": "sorted open candidates in that group; the seeded RNG picks one",
    "why.chosen": "goal node selected in that group",
    "state_update": "Algorithm 2 result: current closed/kept open, vertical neighbours, link nodes inserted",
    "holes": "coverage-hole node set detected by the flood fill (Algorithm 3 input)",
    "tsp": "Algorithm 3 event: end case (1 goal / 2 start / 3 free end), NN and 2-opt lengths, order",
    "retreat_used": "True when Algorithm 1 escaped a dead end through a retreat node",
    "move": "executed mode (sweep/retreat/tsp) and the number of unit cells appended",
    "nodes/edges": "full RCG snapshot for this iteration (x, y, state, kind, reason) and edge list",
}


# ---------------------------------------------------------------- helpers
def load_payloads():
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(CASES.glob("*.json"))]


def build_request(payload, mode, seed=0, time_limit=TIME_LIMIT, extra=None, **overrides):
    grid = payload["grid"]
    fields = dict(
        case_id=payload["case_id"],
        free=frozenset(map(tuple, grid["free"])),
        published_targets=frozenset(map(tuple, grid["published_targets"])),
        covered=frozenset(map(tuple, grid["covered"])),
        current=tuple(grid["current"]),
        base=tuple(grid["base"]),
        old_route=tuple(map(tuple, grid["old_route"])),
        remaining_resource=grid["remaining_resource"],
        seed=seed,
        termination=Termination(time_limit_seconds=time_limit, extra=dict(extra or {})),
        initial_targets=frozenset(map(tuple, grid["initial_targets"])),
        meta={"mode": mode, "sensor_radius": SENSOR_RADIUS},
    )
    fields.update(overrides)
    return PlanRequest(**fields)


def synthetic_request(case_id, free, targets, current, base, mode="public_map",
                      resource=None):
    return PlanRequest(
        case_id=case_id, free=frozenset(free), published_targets=frozenset(targets),
        covered=frozenset(), current=tuple(current), base=tuple(base),
        remaining_resource=resource if resource is not None else 8 * len(free),
        seed=0, termination=Termination(time_limit_seconds=TIME_LIMIT),
        initial_targets=frozenset(targets),
        meta={"mode": mode, "sensor_radius": SENSOR_RADIUS})


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def trace_payload(payload, request, result):
    meta = result.meta
    cstar = meta.get("cstar") or {}
    keep = ("status", "error", "iterations", "initial_samples", "known_free_end",
            "observed_cells_end", "nodes_end", "edges_end", "frontier_added",
            "link_count", "tsp_nodes", "total_pruned", "start_anchor",
            "retreat_events", "keep_open_count", "tsp_hole_events", "components")
    return {
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "case_id": payload["case_id"],
        "mode": meta["mode"],
        "seed": request.seed,
        "time_limit_seconds": request.termination.time_limit_seconds,
        "how_to_read": TRACE_LEGEND,
        "input": {
            "free_cells": len(request.free),
            "published_targets": sorted(list(p) for p in request.published_targets),
            "covered": sorted(list(p) for p in request.covered),
            "pending": sorted(list(p) for p in request.pending),
            "deferred": sorted(list(p) for p in request.deferred),
            "current": list(request.current),
            "base": list(request.base),
            "remaining_resource": request.remaining_resource,
        },
        "result": {
            "status": result.status,
            "reason": result.reason,
            "termination": result.termination,
            "route_steps": result.route_steps,
            "fallback_used": result.fallback_used,
            "fallback_steps": result.fallback_steps,
            "best_candidate_source": result.best_candidate_source,
            "final_source": result.final_source,
            "resource_check": result.resource_check,
            "errors": result.errors,
            "route": [list(p) for p in result.route],
            "route_split": meta.get("route"),
        },
        "public_map": meta.get("public_map"),
        "coverage": meta.get("coverage"),
        "cstar_summary": {key: cstar.get(key) for key in keep},
        "cstar_nodes": cstar.get("nodes"),
        "completion_tsp": meta.get("completion_tsp"),
        "iterations": meta.get("trace"),
    }


def rcg_for(request):
    known = PublicMap()
    known.update(published_observation(request.free, request.published_targets))
    graph = RCG(known)
    graph.sample_front(request.current)
    return known, graph


# ---------------------------------------------------------------- tests
class AdaptedCStarFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = load_payloads()
        cls.by_id = {payload["case_id"]: payload for payload in cls.payloads}

    def test_every_fixture_both_modes_audited(self):
        self.assertTrue(self.payloads, "no fixtures found")
        for payload in self.payloads:
            for mode in MODES:
                with self.subTest(case=payload["case_id"], mode=mode):
                    request = build_request(payload, mode)
                    env = environment_status(request)
                    result = run(request)
                    audit = audit_route(request, result.route)

                    self.assertEqual(result.method_id, METHOD_ID)
                    self.assertEqual(result.method_version, METHOD_VERSION)
                    self.assertIn("mode", result.meta)
                    self.assertEqual(result.meta["mode"], mode)

                    # deferred targets are kept, never deleted, never visited
                    self.assertEqual(set(map(tuple, audit["deferred_untouched"])),
                                     set(request.deferred))
                    self.assertEqual(audit["deferred_visited"], [])
                    self.assertFalse(set(result.route) & set(request.deferred))

                    if not env["ok"]:
                        self.assertEqual(result.status, "environment_infeasible")
                        self.assertEqual(result.reason, env["code"])
                        self.assertEqual(result.route, ())
                        self.assertFalse(result.termination["natural"])
                        self.assertTrue(result.errors)
                        self.assertIn(env["code"], result.errors[0])
                        continue

                    # movement contract
                    self.assertTrue(result.route, "no route on a solvable request")
                    self.assertEqual(result.route[0], tuple(request.current))
                    self.assertEqual(result.route[-1], tuple(request.base))
                    self.assertTrue(audit["starts_at_current"])
                    self.assertTrue(audit["ends_at_base"])
                    self.assertEqual(audit["collisions"], [])
                    self.assertEqual(audit["illegal_steps"], [])
                    self.assertEqual(audit["coverage_claimed_without_visit"], [])
                    self.assertEqual(audit["route_steps"], result.route_steps)

                    if not request.pending:
                        self.assertEqual(result.status, "finished")
                        expected = GridMetric(request.free).path(tuple(request.current),
                                                                 tuple(request.base))
                        self.assertEqual(result.route, expected)
                        self.assertTrue(result.termination.get("natural"))
                        continue

                    self.assertIn(result.status,
                                  ("finished", "coverage_incomplete", "resource_exceeded"))
                    self.assertFalse(result.termination.get("natural") is None)
                    self.assertTrue(result.resource_check.get("source"))
                    # the graded route never contains a completion post-processing pass
                    self.assertFalse(result.meta["options"]["completion_tsp"])
                    self.assertEqual(result.meta["route"]["completion_steps"], 0)

                    if result.status in SUCCESS:
                        # a success claim must survive the independent audit
                        self.assertTrue(audit["valid"], audit["errors"])
                        self.assertTrue(audit["coverage_complete"])
                        self.assertTrue(result.termination["natural"])
                        self.assertEqual(result.termination["reason"], "graph_exhausted")
                        self.assertFalse(result.fallback_used)
                        self.assertFalse(result.final_source.startswith("completion_tsp"))

                    if result.status == "coverage_incomplete":
                        # task-definition mismatch, reported honestly, route saved
                        omitted = [e for e in result.errors if e.startswith("coverage_omitted:")]
                        self.assertEqual(len(omitted), 1, result.errors)
                        self.assertEqual(omitted[0],
                                         f"coverage_omitted:{audit['uncovered_count']}")
                        self.assertFalse(audit["coverage_complete"])
                        self.assertFalse(result.fallback_used)
                        self.assertEqual(result.meta["coverage"]["omitted"],
                                         audit["uncovered"])

                    if result.status == "resource_exceeded":
                        self.assertIsNotNone(request.resource_limit())
                        self.assertGreater(result.route_steps, request.resource_limit())
                        self.assertFalse(result.resource_check["ok"])
                        self.assertTrue(audit["coverage_complete"])
                        self.assertIn("resource_exceeded", " ".join(result.errors))

                    # determinism: same seed -> identical route
                    again = run(build_request(payload, mode))
                    self.assertEqual(again.status, result.status)
                    self.assertEqual(again.route, result.route)
                    self.assertEqual(again.meta["cstar"].get("iterations")
                                     if "cstar" in again.meta else None,
                                     result.meta["cstar"].get("iterations")
                                     if "cstar" in result.meta else None)

    def test_empty_pending_returns_direct(self):
        payload = self.by_id["m06_empty_pending"]
        for mode in MODES:
            with self.subTest(mode=mode):
                request = build_request(payload, mode)
                self.assertEqual(request.pending, frozenset())
                result = run(request)
                expected = GridMetric(request.free).path(tuple(request.current),
                                                         tuple(request.base))
                self.assertEqual(result.route, expected)
                self.assertEqual(result.status, "finished")
                self.assertEqual(result.reason, "empty_pending_direct_return")
                self.assertTrue(result.termination["natural"])
                self.assertFalse(result.fallback_used)
                self.assertEqual(result.best_candidate_source, "direct_return")
                self.assertEqual(result.meta["trace"], [])
                audit = audit_route(request, result.route)
                self.assertTrue(audit["valid"], audit["errors"])

    def test_environment_infeasible_has_no_route(self):
        for case_id, code in (("m14_base_unreachable", "base_unreachable"),
                              ("m15_target_sealed", "target_unreachable")):
            for mode in MODES:
                with self.subTest(case=case_id, mode=mode):
                    request = build_request(self.by_id[case_id], mode)
                    self.assertFalse(environment_status(request)["ok"])
                    result = run(request)
                    self.assertEqual(result.status, "environment_infeasible")
                    self.assertEqual(result.reason, code)
                    self.assertEqual(result.route, ())
                    self.assertEqual(result.termination["reason"], "environment_infeasible")
                    self.assertFalse(result.termination["natural"])

    def test_resource_tight_is_exceeded_but_route_recorded(self):
        payload = self.by_id["m12_resource_tight"]
        for mode in MODES:
            with self.subTest(mode=mode):
                request = build_request(payload, mode)
                result = run(request)
                self.assertEqual(result.status, "resource_exceeded")
                self.assertGreater(result.route_steps, 3)
                self.assertEqual(result.route[0], tuple(request.current))
                self.assertEqual(result.route[-1], tuple(request.base))
                audit = audit_route(request, result.route)
                self.assertTrue(audit["coverage_complete"])
                self.assertEqual(audit["errors"], ["distance_budget_exceeded"])

    def test_wall_clock_cap_reports_coverage_incomplete_without_post_processing(self):
        """The cap truncates C*; the graded route is only C* + base return."""
        payload = self.by_id["m05_no_change"]
        request = build_request(payload, "public_map", time_limit=1e-9)
        result = run(request)
        self.assertEqual(result.termination["reason"], "wall_clock_cap_triggered")
        self.assertFalse(result.termination["natural"])
        self.assertEqual(result.meta["cstar"]["status"], "wall_clock_cap")
        self.assertEqual(result.meta["route"]["cstar_steps"], 0)
        self.assertEqual(result.meta["route"]["completion_steps"], 0)
        self.assertEqual(result.status, "coverage_incomplete")
        self.assertEqual(result.method_version, METHOD_VERSION)
        self.assertFalse(result.fallback_used)
        self.assertTrue(result.final_source.startswith("cstar_start_only"))
        audit = audit_route(request, result.route)
        self.assertEqual(audit["uncovered_count"], len(request.pending))
        self.assertIn(f"coverage_omitted:{audit['uncovered_count']}", result.errors)
        self.assertEqual(result.route[0], tuple(request.current))
        self.assertEqual(result.route[-1], tuple(request.base))

    def test_completion_tsp_variant_is_opt_in_and_labelled(self):
        """The added completion pass is a different method row, never the default."""
        payload = self.by_id["m05_no_change"]
        request = build_request(payload, "public_map", time_limit=1e-9,
                                extra={"completion_tsp": True})
        result = run(request)
        self.assertEqual(result.method_version, METHOD_VERSION + "+completion")
        self.assertEqual(result.meta["adaptation_label"], METHOD_VERSION + "+completion")
        self.assertTrue(result.meta["options"]["completion_tsp"])
        self.assertEqual(result.status, "finished")
        self.assertGreater(result.meta["route"]["completion_steps"], 0)
        self.assertEqual(result.meta["route"]["cstar_steps"], 0)
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_steps,
                         result.meta["route"]["completion_steps"])
        self.assertEqual(result.final_source, "completion_tsp_after_rcg_failure")
        self.assertEqual(result.meta["completion_tsp"]["detail"]["mechanism"],
                         "added_completion_tsp")
        audit = audit_route(request, result.route)
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertTrue(audit["coverage_complete"])

        # the graded row of the same request stays C*-only
        graded = run(build_request(payload, "public_map", time_limit=1e-9))
        self.assertEqual(graded.method_version, METHOD_VERSION)
        self.assertNotEqual(graded.route, result.route)
        self.assertEqual(graded.meta["route"]["completion_steps"], 0)


class RCGMechanisms(unittest.TestCase):
    def setUp(self):
        self.payloads = {p["case_id"]: p for p in load_payloads()}

    def test_graph_metric_keeps_lap_geometry_but_edges_are_four_neighbour_realisable(self):
        request = build_request(self.payloads["m01_pure_obstacle"], "public_map")
        known, graph = rcg_for(request)
        metric = GridMetric(known.free)
        graph.validate(request.current)  # P3 holds on this fixture

        diagonal, long_vertical = [], []
        for a in sorted(graph.edges):
            for b, weight in sorted(graph.edges[a].items()):
                if a > b:
                    continue
                self.assertAlmostEqual(weight, dist(a, b), places=9)
                if abs(a[0] - b[0]) == 1 and abs(a[1] - b[1]) == 1:
                    diagonal.append((a, b, weight))
                if a[0] == b[0] and abs(a[1] - b[1]) > 1:
                    long_vertical.append((a, b, weight))
                path = metric.path(a, b)
                self.assertEqual(path[0], a)
                self.assertEqual(path[-1], b)
                self.assertEqual(len(path) - 1,
                                 abs(a[0] - b[0]) + abs(a[1] - b[1]))
        self.assertTrue(diagonal, "no sqrt(2) cross-lap edge on m01")
        self.assertAlmostEqual(diagonal[0][2], 2 ** 0.5, places=9)
        self.assertTrue(long_vertical, "no same-lap long edge on m01")
        self.assertGreater(long_vertical[0][2], 1.5)

    def test_algorithm1_fixed_order_then_dead_end(self):
        free = rect(-3, -3, 7, 7)
        known = PublicMap()
        known.update({p: True for p in free})
        planner = CStar(start=(0, 0), known=known, seed=3)
        graph = planner.graph
        graph.nodes.clear()
        graph.edges.clear()
        graph.sampled.clear()
        core, left, up, down, right = (0, 0), (-1, 0), (0, 1), (0, -1), (1, 0)
        for p in (core, left, up, down, right):
            graph.insert(p)
        for p in (left, up, down, right):
            graph.connect(core, p)
        planner.current = core

        total = 0
        for expected_group, node in (("left", left), ("up", up),
                                     ("down", down), ("right", right)):
            goal, route, is_retreat, why = planner.select_goal()
            self.assertEqual(why["group"], expected_group)
            self.assertEqual(goal, node)
            self.assertEqual(why["order"], ["left", "up", "down", "right"])
            self.assertFalse(is_retreat)
            self.assertEqual(route, [core, node])
            graph.nodes[node].state = "Cl"
            total += 1
        self.assertEqual(total, 4)

        goal, route, is_retreat, why = planner.select_goal()
        self.assertIsNone(goal)
        self.assertEqual(why["group"], "exhausted")
        self.assertEqual(graph.nodes[core].state, "Cl")

    def test_algorithm1_seeded_choice_inside_a_group(self):
        free = rect(-3, -3, 7, 7)
        goals = []
        for _ in range(2):
            known = PublicMap()
            known.update({p: True for p in free})
            planner = CStar(start=(0, 0), known=known, seed=7)
            graph = planner.graph
            graph.nodes.clear()
            graph.edges.clear()
            graph.sampled.clear()
            for p in ((0, 0), (-1, -1), (-1, 1), (1, 0)):
                graph.insert(p)
            graph.connect((0, 0), (-1, -1))
            graph.connect((0, 0), (-1, 1))
            graph.connect((0, 0), (1, 0))
            planner.current = (0, 0)
            goal, _, _, why = planner.select_goal()
            self.assertEqual(why["group"], "left")
            self.assertEqual(why["options"], [[-1, -1], [-1, 1]])
            self.assertIn(goal, ((-1, -1), (-1, 1)))
            goals.append(goal)
        self.assertEqual(goals[0], goals[1], "seeded choice is not deterministic")

    def test_algorithm1_retreat_when_no_open_neighbour(self):
        free = rect(-3, -3, 7, 7)
        known = PublicMap()
        known.update({p: True for p in free})
        planner = CStar(start=(0, 0), known=known, seed=0)
        graph = planner.graph
        graph.nodes.clear()
        graph.edges.clear()
        graph.sampled.clear()
        for p in ((0, 0), (0, 1), (0, 2), (0, 3)):
            graph.insert(p)
        for a, b in (((0, 0), (0, 1)), ((0, 1), (0, 2)), ((0, 2), (0, 3))):
            graph.connect(a, b)
        # the robot walked 0,0 -> 0,1 -> 0,2; (0,0) is an Open retreat node on
        # that trajectory but is not a neighbour of the current node
        planner.path = [(0, 0), (0, 1), (0, 2)]
        planner.current = (0, 2)
        planner.refresh_retreat((0, 0), (0, 1))
        planner.refresh_retreat((0, 1), (0, 2))
        graph.nodes[(0, 1)].state = "Cl"
        graph.nodes[(0, 3)].state = "Cl"
        self.assertIn((0, 0), planner.retreat)

        goal, route, is_retreat, why = planner.select_goal()
        self.assertTrue(is_retreat)
        self.assertEqual(why["group"], "retreat")
        self.assertEqual(goal, (0, 0))
        self.assertEqual(route, [(0, 2), (0, 1), (0, 0)])
        self.assertAlmostEqual(why["rcg_path_cost"], 2.0, places=9)

    def test_algorithm2_leftward_link_insertion_at_distance_w(self):
        free = rect(0, 0, 5, 5)
        known = PublicMap()
        known.update({p: True for p in free})
        planner = CStar(start=(0, 1), known=known, seed=0)
        graph = planner.graph
        graph.nodes.clear()
        graph.edges.clear()
        graph.sampled.clear()
        graph.insert((0, 1))
        graph.insert((0, 3))
        graph.connect((0, 1), (0, 3))
        info = graph.update_state((0, 1), (-1, 1))
        self.assertEqual(graph.nodes[(0, 1)].state, "Cl")
        self.assertIn([0, 2], info["link_inserted"])
        self.assertIn((0, 2), graph.nodes)
        self.assertEqual(graph.nodes[(0, 2)].kind, "link")
        self.assertIn((0, 2), graph.edges[(0, 1)])
        self.assertIn((0, 2), graph.edges[(0, 3)])

        # the existing sample at exactly distance w becomes the same link anchor
        planner2 = CStar(start=(0, 1), known=known, seed=0)
        graph2 = planner2.graph
        graph2.nodes.clear()
        graph2.edges.clear()
        graph2.sampled.clear()
        graph2.insert((0, 1))
        graph2.insert((0, 2))
        graph2.connect((0, 1), (0, 2))
        info2 = graph2.update_state((0, 1), (-1, 1))
        self.assertEqual(info2["link_inserted"], [])
        self.assertEqual(graph2.nodes[(0, 2)].kind, "link")

    def test_algorithm3_tsp_three_end_cases(self):
        free = rect(0, 0, 5, 5)
        metric = GridMetric(free)
        points = {(0, 0), (2, 0), (2, 2), (0, 3)}
        cost = {}
        for a in sorted(points):
            for b in sorted(points):
                if a != b:
                    cost[(a, b)] = metric.distance(a, b)

        # case 1: fixed goal end
        order, before, after = optimize_tsp(points, (0, 0), (2, 2), cost)
        self.assertEqual(order[0], (0, 0))
        self.assertEqual(order[-1], (2, 2))
        self.assertEqual(set(order), points)
        self.assertLessEqual(after, before + 1e-9)

        # case 2: end == start (closed loop through the hole)
        order, before, after = optimize_tsp(points, (0, 0), (0, 0), cost)
        self.assertEqual(order[0], (0, 0))
        self.assertEqual(order[-1], (0, 0))
        self.assertEqual(set(order), points)
        self.assertLessEqual(after, before + 1e-9)

        # case 3: free end
        order, before, after = optimize_tsp(points, (0, 0), None, cost)
        self.assertEqual(order[0], (0, 0))
        self.assertEqual(set(order), points)
        self.assertLessEqual(after, before + 1e-9)

    def test_start_sample_anchor_in_public_map_mode(self):
        """p0 is always a sample; when the whole map is observed it may be interior."""
        request = build_request(self.payloads["m02_extension_only"], "public_map")
        known, graph = rcg_for(request)
        self.assertTrue(graph.start_anchor)
        self.assertIn(tuple(request.current), graph.nodes)
        rcg_for(request)[1].validate(request.current)


class PublicMapDegeneration(unittest.TestCase):
    """Concrete evidence for the public-map mode finding; written as an artifact."""

    @classmethod
    def setUpClass(cls):
        cls.payloads = load_payloads()
        cls.rows = []
        for payload in cls.payloads:
            request = build_request(payload, "public_map")
            if not environment_status(request)["ok"]:
                continue
            result = run(request)
            meta = result.meta
            if "public_map" not in meta:
                continue
            pm = meta["public_map"]
            audit = audit_route(request, result.route)
            cls.rows.append({
                "case_id": payload["case_id"],
                "free_cells": pm["published_free_cells"],
                "sampled_cells": pm["sampled_cells"],
                "sampled_interior_cells": pm["sampled_interior_cells"],
                "unsampled_free_cells": pm["unsampled_free_cells"],
                "boundary_ring_only": pm["boundary_ring_only"],
                "rcg_connected": pm["rcg_connected"],
                "rcg_nodes": meta["cstar"]["nodes_end"],
                "rcg_edges": meta["cstar"]["edges_end"],
                "iterations": meta["cstar"]["iterations"],
                "cstar_steps": meta["route"]["cstar_steps"],
                "completion_steps": meta["route"]["completion_steps"],
                "coverage_complete": audit["coverage_complete"],
            })

    def test_public_map_samples_only_the_boundary_ring(self):
        self.assertTrue(self.rows)
        for row in self.rows:
            self.assertTrue(row["rcg_connected"],
                            f"{row['case_id']}: public-map RCG unexpectedly disconnected")
        ring_only = [row for row in self.rows if row["boundary_ring_only"]]
        self.assertTrue(ring_only, "no fixture shows the ring-only sampling limit")
        self.assertTrue(all(row["sampled_interior_cells"] == 0 for row in self.rows))
        self.assertTrue(any(row["unsampled_free_cells"] > 0 for row in self.rows))
        # the long same-lap edges still sweep the unsampled interior, so coverage
        # is complete without the ledger-completion fallback on these fixtures
        self.assertTrue(all(row["coverage_complete"] for row in self.rows))

    def test_public_map_deep_interior_is_swept_by_long_lap_edges(self):
        request = synthetic_request("deep_lap_probe", rect(0, 0, 9, 9), {(4, 4)},
                                    (0, 0), (0, 8))
        result = run(request)
        meta = result.meta
        self.assertEqual(meta["cstar"]["status"], "graph_exhausted")
        self.assertEqual(meta["cstar"]["initial_samples"], 32)   # 9x9 boundary ring
        self.assertEqual(meta["public_map"]["sampled_interior_cells"], 0)
        self.assertEqual(meta["public_map"]["unsampled_free_cells"], 49)  # 81 - 32
        self.assertEqual(meta["cstar"]["nodes_end"], 32)
        self.assertEqual(meta["cstar"]["edges_end"], 39)
        self.assertEqual(meta["route"]["completion_steps"], 0)
        self.assertGreater(meta["route"]["cstar_steps"], 0)
        audit = audit_route(request, result.route)
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertTrue(audit["coverage_complete"])

    def test_public_map_free_pocket_disconnects_the_rcg(self):
        # a free cell two cells behind a blocked ring is published-free but
        # unreachable and cannot be sampled into the lap system
        blocked = {(x, y) for x in range(9) for y in range(9)
                   if max(abs(x - 4), abs(y - 4)) <= 2 and (x, y) != (4, 4)}
        free = rect(0, 0, 9, 9) - blocked
        request = synthetic_request("free_pocket_probe", free, {(1, 1), (7, 7), (1, 7)},
                                    (0, 0), (0, 8))
        self.assertTrue(environment_status(request)["ok"])  # the pocket is not a task
        result = run(request)
        meta = result.meta
        self.assertEqual(meta["cstar"]["status"], "rcg_disconnected")
        components = sorted(meta["cstar"]["components"])
        self.assertEqual(len(components), 2)
        self.assertEqual(components[0], 1)              # the unreachable pocket (4,4)
        self.assertGreater(components[1], 40)
        self.assertEqual(sum(components), meta["cstar"]["nodes_end"])
        self.assertEqual(meta["route"]["cstar_steps"], 0)
        self.assertEqual(meta["route"]["completion_steps"], 0)
        self.assertEqual(result.status, "coverage_incomplete")
        self.assertEqual(result.errors[0], "coverage_omitted:3")
        self.assertFalse(result.fallback_used)
        self.assertTrue(result.final_source.startswith("cstar_start_only"))
        audit = audit_route(request, result.route)
        self.assertEqual(audit["uncovered_count"], 3)
        self.assertFalse(audit["coverage_complete"])
        self.assertEqual(result.route[0], tuple(request.current))
        self.assertEqual(result.route[-1], tuple(request.base))
        self.assertEqual(len(result.route) - 1, meta["route"]["base_return_steps"])

    def test_zz_write_degeneration_and_trace_artifacts(self):
        """Runs last (name sorts last) and writes the human-traceable evidence."""
        self.assertTrue(self.rows)
        deep = synthetic_request("deep_lap_probe", rect(0, 0, 9, 9), {(4, 4)},
                                 (0, 0), (0, 8))
        deep_result = run(deep)
        blocked = {(x, y) for x in range(9) for y in range(9)
                   if max(abs(x - 4), abs(y - 4)) <= 2 and (x, y) != (4, 4)}
        pocket_free = rect(0, 0, 9, 9) - blocked
        pocket = synthetic_request("free_pocket_probe", pocket_free,
                                   {(1, 1), (7, 7), (1, 7)}, (0, 0), (0, 8))
        pocket_result = run(pocket)

        def probe_summary(request, result):
            meta = result.meta
            audit = audit_route(request, result.route)
            return {
                "free_cells": meta["public_map"]["published_free_cells"],
                "sampled_cells": meta["public_map"]["sampled_cells"],
                "sampled_interior_cells": meta["public_map"]["sampled_interior_cells"],
                "unsampled_free_cells": meta["public_map"]["unsampled_free_cells"],
                "rcg_connected": meta["public_map"]["rcg_connected"],
                "rcg_status": meta["cstar"]["status"],
                "components": meta["cstar"]["components"],
                "rcg_nodes": meta["cstar"]["nodes_end"],
                "rcg_edges": meta["cstar"]["edges_end"],
                "iterations": meta["cstar"]["iterations"],
                "cstar_steps": meta["route"]["cstar_steps"],
                "completion_steps": meta["route"]["completion_steps"],
                "base_return_steps": meta["route"]["base_return_steps"],
                "status": result.status,
                "errors": result.errors,
                "method_version": result.method_version,
                "fallback_used": result.fallback_used,
                "final_source": result.final_source,
                "coverage_complete": audit["coverage_complete"],
                "coverage_omitted": audit["uncovered_count"],
                "route": [list(p) for p in result.route],
                "route_steps": result.route_steps,
            }

        write_json(TRACE_DIR / "degeneration_public_map.json", {
            "generated_by": "tests/test_cstar_micro.py",
            "default_mode": "public_map",
            "what": "public_map mode: frontier sampling limit on the micro fixtures",
            "graded_route": (
                "C* route + fixed base return only. completion_tsp is False by default; "
                "any completion pass is an added mechanism under method_version "
                "'cstar_adapt_v0.1_20261018+completion' and is never part of this evidence."),
            "finding_1_ring_only": (
                "With the whole published map observed at k=0, no free cell is adjacent to "
                "unknown inside the published region, so sample_front() returns only the "
                "boundary ring (plus the rings around blocked cells). The interior is never "
                "sampled: 0 interior samples on all 15 solvable fixtures. It is still swept, "
                "because Def. III.8 keeps both lap ends and expansion re-creates one long "
                "same-lap edge per column; the executed C* route therefore becomes a "
                "boustrophedon over the published region. This is a full-area sweep, so under "
                "a target-only task it over-covers; a longer route is a task-definition "
                "mismatch, not evidence that C* is weak."),
            "finding_2_disconnected": (
                "A free pocket two cells behind a blocked ring is published-free, is a "
                "frontier sample, and cannot be connected to any lap: the RCG loses P3 and "
                "validate() raises. The historical outer loop cannot run. The graded answer "
                "is the honest one: C* route = [current], base return only, "
                "status=coverage_incomplete, errors=[coverage_omitted:3]. No post-processing "
                "is appended to the graded route."),
            "fixture_table": self.rows,
            "probe_deep_lap_sweep": probe_summary(deep, deep_result),
            "probe_free_pocket": probe_summary(pocket, pocket_result),
        })

        for case_id, mode in (("m01_pure_obstacle", "public_map"),
                              ("m01_pure_obstacle", "sensed"),
                              ("m03_corner_extension_and_obstacle", "public_map"),
                              ("m04_two_events", "sensed")):
            payload = next(p for p in self.payloads if p["case_id"] == case_id)
            request = build_request(payload, mode)
            result = run(request)
            audit = audit_route(request, result.route)
            self.assertTrue(audit["valid"], audit["errors"])
            write_json(TRACE_DIR / f"{case_id}__{mode}.json",
                       trace_payload(payload, request, result))
            self.assertTrue((TRACE_DIR / f"{case_id}__{mode}.json").is_file())


if __name__ == "__main__":
    unittest.main()
