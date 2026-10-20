"""R5: the checker's own semantics, and the ledger's completeness.

The point of this module is that the *gate* is tested, not only the routes: v0.1
accepted a success status when coverage was complete, even if the same record
also said ``distance_budget_exceeded``.  R5 asks for that exact negative case.
"""
import csv
import json
import unittest

import conftest_v02 as cf

V02 = cf.V02
import sys
sys.path.insert(0, str(V02))
import verify_v02


class GateSemantics(unittest.TestCase):
    def test_over_budget_complete_route_is_rejected_as_success(self):
        record = {"valid": False, "coverage_complete": True,
                  "errors": ["distance_budget_exceeded"],
                  "resource": {"limit": 3, "used": 10, "ok": False},
                  "route_steps": 10}
        problems = verify_v02.grade("finished", record, {"natural": True})
        self.assertIn("success_status_over_resource", problems)
        self.assertIn("success_status_with_invalid_audit", problems)

    def test_coverage_omission_is_rejected_as_success(self):
        record = {"valid": False, "coverage_complete": False,
                  "errors": ["coverage_omission"], "resource": {"ok": True},
                  "route_steps": 5}
        self.assertIn("success_status_without_full_coverage",
                      verify_v02.grade("finished", record, {}))

    def test_illegal_movement_is_rejected_as_success(self):
        record = {"valid": False, "coverage_complete": True, "errors": ["illegal_step"],
                  "resource": {"ok": True}, "route_steps": 5}
        problems = verify_v02.grade("planned", record, {})
        self.assertIn("success_status_with_illegal_movement", problems)

    def test_environment_infeasible_with_a_route_is_rejected(self):
        record = {"valid": True, "coverage_complete": True, "errors": [],
                  "resource": {"ok": True}, "route_steps": 4}
        self.assertIn("environment_infeasible_with_a_route",
                      verify_v02.grade("environment_infeasible", record, {}))

    def test_truncated_status_must_not_be_natural(self):
        record = {"valid": False, "coverage_complete": False, "errors": [],
                  "resource": {"ok": True}, "route_steps": None}
        self.assertIn("truncated_status_marked_natural",
                      verify_v02.grade("timeout", record, {"natural": True}))

    def test_valid_record_passes(self):
        record = {"valid": True, "coverage_complete": True, "errors": [],
                  "resource": {"limit": 9, "used": 8, "ok": True}, "route_steps": 8}
        self.assertEqual(verify_v02.grade("finished", record, {"natural": True}), [])

    def test_unknown_status_is_rejected(self):
        record = {"valid": True, "coverage_complete": True, "errors": [],
                  "resource": {"ok": True}, "route_steps": 1}
        self.assertTrue(any(problem.startswith("unknown_status")
                            for problem in verify_v02.grade("looks_good", record, {})))


class SavedRecords(unittest.TestCase):
    """The real saved routes must satisfy the gate, not just the synthetic ones."""

    def test_every_saved_route_passes_the_gate(self):
        root = V02 / "artifacts_v02" / "routes"
        files = sorted(root.glob("*/*.json"))
        if not files:
            self.skipTest("no v0.2 formal run yet")
        from audit_independent import audit_route
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            request = verify_v02.load_request(payload["case_id"])
            route = tuple(map(tuple, payload["route"])) if payload.get("route") else ()
            audit = audit_route(request, route)
            with self.subTest(file=path.name, case=payload["case_id"]):
                self.assertEqual(verify_v02.grade(payload["status"], audit,
                                                  payload.get("termination")), [])


class Ledger(unittest.TestCase):
    def test_ledger_has_unique_run_ids_and_no_duplicate_plan_cells(self):
        ledger = V02 / "logs_v02" / "call_ledger_v02.csv"
        if not ledger.is_file():
            self.skipTest("no v0.2 ledger yet")
        with open(ledger, encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        ids = [row["run_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate run_id")
        formal = [row for row in rows if row["kind"] == "formal"]
        if not formal:
            self.skipTest("no formal rows yet")
        batch = max(row["batch"] for row in formal)
        cells = [row["plan_id"] for row in formal if row["batch"] == batch]
        self.assertEqual(len(cells), len(set(cells)),
                         "a (case, method) cell was registered twice in one batch")
        self.assertTrue(all(row["task_set_sha256"] for row in formal))


if __name__ == "__main__":
    unittest.main(verbosity=2)
