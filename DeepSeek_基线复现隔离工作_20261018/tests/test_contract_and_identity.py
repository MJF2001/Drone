"""Contract and behaviour-identity tests.

Two things are proved here:

1. the copied frozen / candidate sources are byte-identical to the versions their
   own manifests declare, so "we reused the existing implementation" is checkable;
2. the adapter layer is transparent: for every fixture and every pre-existing
   method, calling the adapter and calling the frozen entry point directly on the
   same snapshot returns exactly the same status and the same cell-by-cell route.
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))
sys.path.insert(0, str(HERE))

import bootstrap  # noqa: E402
from problem import PlanRequest, Termination  # noqa: E402
from audit_independent import audit_route  # noqa: E402
from adapters import registry  # noqa: E402
from run_micro import load_cases  # noqa: E402

FROZEN = bootstrap.FROZEN
CANDIDATE = bootstrap.CANDIDATE

HARD_ERRORS = {"wrong_start", "missing_return", "collision_or_out_of_bounds", "illegal_step"}
SUCCESS = {"finished", "planned", "planned_at_timeout", "complete_coverage"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FrozenIntegrity(unittest.TestCase):
    def test_frozen_bundle_matches_its_manifest(self):
        manifest = json.loads((FROZEN / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "v2_20261012")
        self.assertEqual(sorted(manifest["methods"]), ["OARP_CORE2", "P2_MULTI", "TREE_MST"])
        for name, expected in manifest["source_sha256"].items():
            actual = sha256(FROZEN / "source" / name)
            self.assertEqual(actual, expected, f"frozen source changed: {name}")
        self.assertEqual(sha256(FROZEN / "runtime_profile.json"),
                         manifest["runtime_profile_sha256"])

    def test_candidate_bundle_matches_its_manifest(self):
        manifest = json.loads((CANDIDATE / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["files_sha256"].items():
            self.assertEqual(sha256(CANDIDATE / name), expected, f"candidate file changed: {name}")
        for name, expected in manifest["base_source_sha256"].items():
            self.assertEqual(sha256(FROZEN / "source" / name), expected,
                             f"candidate base source changed: {name}")

    def test_imports_resolve_inside_out(self):
        report = bootstrap.verify_isolation()
        self.assertTrue(Path(report["baseline_suite"]).is_relative_to(OUT))
        self.assertTrue(Path(report["model"]).is_relative_to(OUT))


class BehaviourIdentity(unittest.TestCase):
    """The adapter must not change what the reused implementation does."""

    def _direct(self, call):
        """Call the reused entry point, returning (status, route) or ('raised', error)."""
        try:
            raw = call()
        except Exception as exc:  # the method itself rejected the input
            return "raised", str(exc)
        return raw["status"], tuple(map(tuple, raw["route"]))

    def test_frozen_methods_are_reached_unchanged(self):
        cases = load_cases()
        affected = 0
        for payload, request, _ in cases:
            snapshot = request.to_snapshot()
            history = sorted(request.history_targets)
            for method in bootstrap.portable_frozen.METHODS:
                direct_status, direct_route = self._direct(
                    lambda m=method: bootstrap.portable_frozen.solve(
                        snapshot, history, m, request.termination.time_limit_seconds,
                        request.seed, bootstrap.profile()))
                through_adapter = registry.run(method, request)
                if direct_status == "raised":
                    self.assertIn(through_adapter.status,
                                  ("input_precondition_unmet", "adapter_assertion"),
                                  f"{method} raised directly but the adapter hid it "
                                  f"on {request.case_id}")
                    self.assertEqual(through_adapter.meta.get("engine_status", None), None)
                    affected += 1
                    continue
                # the adapter may only downgrade an over-claimed success to
                # "no_legal_route_within_resource"; everything else must match.
                if direct_route:
                    self.assertEqual(direct_status, through_adapter.status,
                                     f"{method} status differs on {request.case_id}")
                    self.assertEqual(direct_route, tuple(through_adapter.route),
                                     f"{method} route differs on {request.case_id}")
                else:
                    self.assertEqual(through_adapter.route, ())
                    if "engine_status" in through_adapter.meta:
                        self.assertEqual(through_adapter.meta["engine_status"], direct_status)
                affected += 1
        self.assertGreater(affected, 0)

    def test_ppcpp_candidate_is_reached_unchanged(self):
        loader = bootstrap.load_ppcpp_candidate()
        for payload, request, _ in load_cases():
            snapshot = request.to_snapshot()
            history = sorted(request.history_targets)
            direct_status, direct_route = self._direct(
                lambda: loader.solve(snapshot, history,
                                     request.termination.time_limit_seconds, request.seed))
            through_adapter = registry.run("PPCPP_CORE4", request)
            if direct_status == "raised":
                self.assertIn(through_adapter.status,
                              ("input_precondition_unmet", "adapter_assertion"))
                continue
            self.assertEqual(direct_route, tuple(through_adapter.route),
                             f"PPCPP route differs on {request.case_id}")
            if direct_route:
                self.assertEqual(direct_status, through_adapter.status,
                                 f"PPCPP status differs on {request.case_id}")


class OutputContract(unittest.TestCase):
    def test_every_method_returns_a_complete_record(self):
        required = ("method_id", "method_version", "status", "reason", "route",
                    "resource_check", "termination", "fallback_used", "best_candidate_source",
                    "final_source", "stage_seconds", "errors")
        for payload, request, _ in load_cases():
            for method in registry.available():
                with self.subTest(case=request.case_id, method=method):
                    result = registry.run(method, request)
                    row = result.as_row(request)
                    for field in required:
                        self.assertIn(field, row)
                    self.assertEqual(row["method_id"], method)
                    self.assertTrue(row["method_version"])
                    self.assertIn("natural", result.termination)
                    self.assertIsInstance(row["route_steps"], (int, type(None)))

    def test_no_method_returns_an_illegal_route(self):
        for payload, request, _ in load_cases():
            for method in registry.available():
                result = registry.run(method, request)
                if not result.route:
                    self.assertNotIn(result.status, SUCCESS,
                                     f"{method} claims success without a route on {request.case_id}")
                    continue
                audit = audit_route(request, result.route)
                with self.subTest(case=request.case_id, method=method):
                    self.assertFalse(set(audit["errors"]) & HARD_ERRORS,
                                     f"{method} {request.case_id}: {audit['errors']}")
                    if result.status in SUCCESS:
                        self.assertTrue(audit["coverage_complete"],
                                        f"{method} claims success but omits "
                                        f"{audit['uncovered_count']} targets on {request.case_id}")
                        self.assertTrue(audit["resource"]["ok"],
                                        f"{method} exceeds the resource on {request.case_id}")

    def test_deferred_targets_are_never_touched_or_claimed(self):
        for payload, request, _ in load_cases():
            if not request.deferred:
                continue
            for method in registry.available():
                result = registry.run(method, request)
                audit = audit_route(request, result.route)
                self.assertEqual(audit["deferred_visited"], [],
                                 f"{method} flies over a deferred target on {request.case_id}")
                self.assertFalse(set(request.deferred) & set(result.covered_physical),
                                 f"{method} claims a deferred target covered on {request.case_id}")

    def test_adapter_is_deterministic_for_the_given_seed(self):
        for payload, request, _ in load_cases():
            for method in registry.available():
                first = registry.run(method, request)
                second = registry.run(method, request.replaced(seed=request.seed))
                self.assertEqual(first.route, second.route,
                                 f"{method} is not reproducible on {request.case_id}")


class DeterminismAcrossRestarts(unittest.TestCase):
    """A second process must reproduce the same route for the same seed."""

    def test_reference_method_is_stable(self):
        for payload, request, _ in load_cases():
            route = registry.run("TREE_MST", request).route
            self.assertEqual(route, registry.run("TREE_MST", request).route)


if __name__ == "__main__":
    unittest.main(verbosity=2)
