"""Negative self-tests for the read-only verifier and the shared semantics.

The draft requires the self-tests to live in the test suite rather than inside the
verifier, so that ``verify.py`` stays strictly read-only.  Every test here is
pure or writes only under ``tmp/``.

Run:  python -B -X utf8 -m unittest discover -s tests -p "test_*.py"
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))
sys.path.insert(0, str(NEW))

import bootstrap  # noqa: E402,F401

from classify import BUCKETS, classify, in_budget_success  # noqa: E402
from grading import grade  # noqa: E402
import verify  # noqa: E402


class SemanticGate(unittest.TestCase):
    def test_over_budget_complete_route_is_not_success(self):
        record = {"valid": False, "coverage_complete": True,
                  "errors": ["distance_budget_exceeded"],
                  "resource": {"limit": 3, "used": 10, "ok": False}, "route_steps": 10}
        problems = grade("finished", record, {"natural": True})
        self.assertIn("success_status_over_resource", problems)
        self.assertIn("success_status_with_invalid_audit", problems)

    def test_coverage_omission_is_not_success(self):
        record = {"valid": False, "coverage_complete": False,
                  "errors": ["coverage_omission"], "resource": {"ok": True},
                  "route_steps": 5}
        self.assertIn("success_status_without_full_coverage",
                      grade("finished", record, {}))

    def test_illegal_movement_is_not_success(self):
        record = {"valid": False, "coverage_complete": True,
                  "errors": ["illegal_step"], "resource": {"ok": True}, "route_steps": 5}
        self.assertIn("success_status_with_illegal_movement", grade("planned", record, {}))

    def test_valid_record_passes(self):
        record = {"valid": True, "coverage_complete": True, "errors": [],
                  "resource": {"limit": 9, "used": 8, "ok": True}, "route_steps": 8}
        self.assertEqual(grade("finished", record, {"natural": True}), [])


class Classification(unittest.TestCase):
    def _row(self, **overrides):
        base = {"status": "finished", "route": [[0, 0]], "route_steps": 0,
                "audit": {"valid": True}, "termination": {"natural": True},
                "within_budget": True}
        base.update(overrides)
        return base

    def test_natural_complete(self):
        self.assertEqual(classify(self._row())[0], "natural_complete_valid")

    def test_truncated_with_candidate(self):
        row = self._row(termination={"natural": False, "reason": "deadline"})
        self.assertEqual(classify(row)[0], "truncated_with_valid_candidate")

    def test_no_route(self):
        row = self._row(route=[], audit={"valid": False, "errors": ["empty_route"]})
        self.assertEqual(classify(row)[0], "no_valid_route")

    def test_rejected_and_infeasible(self):
        self.assertEqual(classify(self._row(status="input_precondition_unmet"))[0],
                         "input_precondition_rejected")
        self.assertEqual(classify(self._row(status="environment_infeasible", route=[]))[0],
                         "environment_infeasible")

    def test_out_of_budget_is_not_an_in_budget_success(self):
        row = self._row(within_budget=False)
        self.assertFalse(in_budget_success(row))
        self.assertEqual(classify(row)[0], "natural_complete_valid")

    def test_every_bucket_is_reachable(self):
        seen = set()
        for row in (self._row(),
                    self._row(termination={"natural": False}),
                    self._row(route=[], audit={"valid": False}),
                    self._row(status="input_precondition_unmet"),
                    self._row(status="environment_infeasible", route=[])):
            seen.add(classify(row)[0])
        self.assertEqual(seen, set(BUCKETS))


class LedgerAuditor(unittest.TestCase):
    def test_duplicate_phase_pair_is_detected(self):
        rows = [{"run_id": "a", "phase": "start"}, {"run_id": "a", "phase": "end"},
                {"run_id": "a", "phase": "end"}]
        pairs = [(row["run_id"], row["phase"]) for row in rows]
        self.assertNotEqual(len(pairs), len(set(pairs)))

    def test_prefix_detects_append_and_rewrite(self):
        target = NEW / "tmp" / "selftest_seal.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"one\ntwo\n")
        raw = target.read_bytes()
        seal = {"bytes": len(raw), "lines": raw.count(b"\n"),
                "sha256_of_prefix": hashlib.sha256(raw).hexdigest()}
        self.assertTrue(verify.prefix_ok(target, seal)[0])
        target.write_bytes(raw + b"three\n")
        self.assertTrue(verify.prefix_ok(target, seal)[0])
        target.write_bytes(b"one\nTWO\nthree\n")
        self.assertFalse(verify.prefix_ok(target, seal)[0])
        target.unlink()

    def test_join_detects_field_tampering(self):
        rows = [{"run_id": "r", "phase": "end", "kind": "development",
                 "case_id": "c", "method_id": "m", "status": "finished",
                 "route_steps": "5", "seed": "1"}]
        saved = {"r": {"case_id": "c", "method_id": "m", "status": "finished",
                       "route_steps": 5, "seed": 1}}
        self.assertEqual(verify.join_routes(rows, saved), [])
        tampered = {"r": dict(saved["r"], route_steps=99)}
        self.assertTrue(any("route_steps differs" in p
                            for p in verify.join_routes(rows, tampered)))


class VerifierIsReadOnly(unittest.TestCase):
    """A static check: verify.py must contain no write operation."""

    FORBIDDEN = ("write_text(", "write_bytes(", ".mkdir(", "DictWriter",
                 "shutil.", "os.remove", ".unlink(", '"w"', "'w'", '"a"', "'a'",
                 '"w+"', "'w+'", '"a+"', "'a+'")

    def test_no_write_calls_in_the_verifier(self):
        source = (NEW / "verify.py").read_text(encoding="utf-8")
        offenders = [token for token in self.FORBIDDEN if token in source]
        self.assertEqual(offenders, [], f"verify.py contains write operations: {offenders}")

    def test_self_tests_are_the_only_writers(self):
        for name in ("tools/run_batch.py", "tools/report.py"):
            self.assertTrue((NEW / name).is_file(), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
