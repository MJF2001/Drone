"""C: call recording must be complete, durable and tamper-evident.

Four concrete requirements from the review:

1. no test/development path may bypass the registered entry (the fake clock is
   passed through the registry, not by calling the adapter directly);
2. a failure to write the ``start`` row must abort the call, and a failure on the
   ``end`` row must be reported - never swallowed;
3. the sealed ledger prefix must be immutable while appends stay legal;
4. the formal ledger, the task manifest, the saved routes and the summary must
   join by ``run_id``, and deletion/duplication/tampering must be detected.
"""
import csv
import hashlib
import subprocess
import sys
import unittest

import conftest_v03 as cf
from adapters import registry


class RegisteredEntry(unittest.TestCase):
    def test_no_test_calls_the_adapter_directly(self):
        """Guard: every planner call in tests_v03 goes through the registry."""
        offenders = []
        for path in sorted((cf.V03 / "tests_v03").glob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern in ("epsilon_star" ".run(", "cstar" ".run(",
                                "reference_methods" ".run_reference("):
                    if pattern in stripped:
                        offenders.append(f"{path.name}:{number}: {stripped[:80]}")
        self.assertEqual(offenders, [], "a test bypassed the registered entry point")

    def test_fake_clock_goes_through_the_registry_and_is_registered(self):
        clock = cf.ManualClock()
        before = len(_ledger_rows())
        result = registry.run("EPSILON_STAR", cf.free_grid(size=3), deadline_clock=clock)
        self.assertIn(result.status, ("finished", "planned"))
        rows = _ledger_rows()[before:]
        self.assertEqual([row["phase"] for row in rows], ["start", "end"])
        self.assertEqual(rows[0]["run_id"], rows[1]["run_id"])
        self.assertEqual(rows[1]["kind"], "test")
        self.assertGreater(clock.calls, 0, "the injected clock was not used")


class WriteFailures(unittest.TestCase):
    def setUp(self):
        self._append = registry._append
        self._ledger = registry.LEDGER
        self._failures = list(registry.LEDGER_FAILURES)
        # keep the real ledger clean: these probes deliberately leave an
        # unserialisable state (a start without an end), which is a property of
        # the detector, not of the delivered evidence
        cf.SCRATCH.mkdir(parents=True, exist_ok=True)
        registry.LEDGER = cf.SCRATCH / "probe_ledger.csv"
        if registry.LEDGER.exists():
            registry.LEDGER.unlink()

    def tearDown(self):
        registry._append = self._append
        registry.LEDGER = self._ledger
        registry.LEDGER_FAILURES[:] = self._failures
        probe = cf.SCRATCH / "probe_ledger.csv"
        if probe.exists():
            probe.unlink()

    def test_start_write_failure_aborts_before_planning(self):
        calls = {"adapter": 0}
        original_adapter = registry.METHODS["EPSILON_STAR"]["adapter"]

        def counting_adapter(request, clock=None, **kwargs):
            calls["adapter"] += 1
            return original_adapter(request, clock, **kwargs)

        registry.METHODS["EPSILON_STAR"]["adapter"] = counting_adapter

        def failing(row):
            raise OSError("simulated disk failure")

        registry._append = failing
        try:
            with self.assertRaises(registry.LedgerWriteError):
                registry.run("EPSILON_STAR", cf.free_grid(size=3))
            self.assertEqual(calls["adapter"], 0,
                             "the planner ran even though its start row was not written")
            self.assertTrue(registry.LEDGER_FAILURES, "the failure was not recorded")
            self.assertEqual(registry.LEDGER_FAILURES[-1]["phase"], "start")
        finally:
            registry.METHODS["EPSILON_STAR"]["adapter"] = original_adapter

    def test_end_write_failure_is_reported_not_swallowed(self):
        state = {"count": 0}

        def flaky(row):
            state["count"] += 1
            if state["count"] == 2:          # the start row succeeded
                raise OSError("simulated disk failure on end")
            return self._append(row)

        registry._append = flaky
        result = registry.run("EPSILON_STAR", cf.free_grid(size=3))
        self.assertIn(result.status, ("finished", "planned"))
        self.assertIn("ledger_write_error", result.meta,
                      "the end-row write failure was swallowed")
        self.assertTrue(any(item["phase"] == "end" for item in registry.LEDGER_FAILURES),
                        "the end-row failure was not recorded for the batch")


class SealedPrefix(unittest.TestCase):
    def test_prefix_survives_an_append_and_detects_a_rewrite(self):
        from verify_v03 import prefix_ok
        target = cf.SCRATCH / "_seal_unit.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"one\ntwo\n")
        raw = target.read_bytes()
        seal = {"bytes": len(raw), "lines": raw.count(b"\n"),
                "sha256_of_prefix": hashlib.sha256(raw).hexdigest()}
        self.assertTrue(prefix_ok(target, seal)[0])
        with open(target, "ab") as handle:
            handle.write(b"three\n")
        self.assertTrue(prefix_ok(target, seal)[0], "a legal append was rejected")
        target.write_bytes(b"one\nTWO\nthree\n")
        self.assertFalse(prefix_ok(target, seal)[0], "a rewritten prefix was not detected")
        target.unlink()

    def test_the_real_ledger_prefix_matches_its_seal(self):
        from verify_v03 import prefix_ok, MANIFESTS, LEDGER
        import json
        seal_path = MANIFESTS / "ledger_seal.json"
        if not seal_path.is_file():
            self.skipTest("no formal batch sealed yet")
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        ok, message = prefix_ok(LEDGER, seal)
        self.assertTrue(ok, message)


class LedgerAuditNegative(unittest.TestCase):
    def setUp(self):
        from verify_v03 import audit_ledger, join_routes
        self.audit = audit_ledger
        self.join = join_routes
        self.start = {"run_id": "r", "phase": "start", "kind": "formal",
                      "plan_id": "c::m", "batch": "b", "case_id": "c",
                      "method_id": "m", "seed": "1"}
        self.end = dict(self.start, phase="end", status="finished", route_steps="5")

    def test_clean_pair_is_accepted(self):
        self.assertEqual(self.audit([self.start, self.end]), [])

    def test_deleted_end_row_is_detected(self):
        self.assertTrue(any("start without end" in p for p in self.audit([self.start])))

    def test_duplicated_run_id_is_detected(self):
        problems = self.audit([self.start, self.end, self.start, self.end])
        self.assertTrue(any("repeated" in p for p in problems))

    def test_unregistered_row_is_detected(self):
        problems = self.audit([dict(self.start, kind="unregistered"), self.end])
        self.assertTrue(any("unregistered" in p for p in problems))

    def test_join_detects_missing_route_and_tampering(self):
        rows = [self.end]
        saved = {"r": {"case_id": "c", "method_id": "m", "status": "finished",
                       "route_steps": 5, "seed": 1}}
        self.assertEqual(self.join(rows, saved), [])
        self.assertTrue(any("no saved route" in p for p in self.join(rows, {})))
        tampered = {"r": dict(saved["r"], route_steps=99)}
        self.assertTrue(any("route_steps differs" in p
                            for p in self.join(rows, tampered)))


class KilledProcess(unittest.TestCase):
    """A process killed in the middle of a call leaves a start without an end."""

    CHILD = (
        "import sys, time\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, {src!r})\n"
        "import bootstrap_v03\n"
        "from adapters import registry\n"
        "registry.CONTEXT['kind'] = 'test'\n"
        "registry.LEDGER = Path({ledger!r})\n"
        "registry._append({{'run_id': 'orphan', 'phase': 'start', 'batch': 'killed',\n"
        "                   'kind': 'test', 'plan_id': 'orphan::EPSILON_STAR'}})\n"
        "time.sleep(30)\n"
    )

    def test_orphan_start_row_is_reported(self):
        from verify_v03 import audit_ledger, read_ledger
        src = str(cf.V03 / "src_v03")
        ledger = cf.SCRATCH / "orphan_ledger.csv"
        cf.SCRATCH.mkdir(parents=True, exist_ok=True)
        if ledger.exists():
            ledger.unlink()
        proc = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-c",
                                 self.CHILD.format(src=src, ledger=str(ledger))])
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        rows = read_ledger(ledger)
        self.assertTrue(any(row.get("run_id") == "orphan" for row in rows),
                        "the pre-call start row was not durable")
        problems = audit_ledger(rows)
        self.assertTrue(any("start without end" in p for p in problems),
                        "an orphan start row was not reported")
        ledger.unlink()


def _ledger_rows():
    if not registry.LEDGER.is_file():
        return []
    with open(registry.LEDGER, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main(verbosity=2)
