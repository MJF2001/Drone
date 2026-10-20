"""Post-hoc, tiny-fixture regressions for the sealed P2 warm candidate.

This file is deliberately separate from the formal development-map runner.
It runs only hand-built micro snapshots and records planner-call counts.
"""
from pathlib import Path
import json, sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
ALGO = ROOT / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ALGO / "frozen_baselines" / "v2_20261012" / "source"))
sys.path.insert(0, str(ALGO / "candidate_baselines" / "P2_WARM_GLOBAL" / "v0.1_20261017"))
import portable_frozen
import baseline_suite
from model import Snapshot, DeadlineExceeded
import p2_search_audit_warm as warm
from audit import audit

calls = {"frozen_P2": 0, "warm_module": 0}


def snapshot(name="micro_loop", targets=True, current=(0, 0), base=(0, 0), free=None,
             old_route=None, radius=0):
    free = set(free or {(0, 0), (1, 0), (1, 1), (0, 1)})
    goals = {(0, 0), (1, 0), (1, 1), (0, 1)} if targets else set()
    if old_route is None:
        old_route = ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))
    return Snapshot(name, frozenset(free), frozenset(goals), frozenset(),
                    tuple(current), tuple(base), tuple(old_route), radius, 10000)


def call(s, variant="warm_multi", budget=30.0):
    calls["warm_module"] += 1
    baseline_suite.p2_solve = lambda ss, bb, vv, sd: warm.solve(ss, bb, variant, sd)
    return baseline_suite.solve(s, set(s.targets), "P2_MULTI", budget, 17017,
                                portable_frozen.PROFILE)


results = []

# Off-mode equivalence: same micro input, fixed seed, and generous budget.
s = snapshot()
calls["frozen_P2"] += 1
baseline_suite.p2_solve = portable_frozen.solve.__globals__["p2_solve"]
frozen = baseline_suite.solve(s, set(s.targets), "P2_MULTI", 30.0, 17017,
                              portable_frozen.PROFILE)
off = call(s, variant="multi", budget=30.0)
assert tuple(frozen["route"]) == tuple(off["route"]), "warm-off route differs from frozen P2"
assert audit(s, tuple(off["route"]))["valid"]
results.append({"case": "warm_off_frozen_P2_equivalence", "planner_calls": 2,
                "frozen_steps": len(frozen["route"])-1,
                "warm_module_multi_steps": len(off["route"])-1,
                "route_equal": True, "valid": True, "budget_seconds": 30.0})

# Empty target set still returns from current to base.
empty = Snapshot("micro_empty", frozenset({(0, 0), (1, 0), (2, 0)}),
                 frozenset(), frozenset(), (0, 0), (2, 0),
                 ((0, 0), (1, 0), (2, 0)), 0, 100)
out = call(empty)
assert out["route"][0] == empty.current and out["route"][-1] == empty.base
assert audit(empty, tuple(out["route"]))["valid"]
assert any(e.get("stage") == "warm_sequence_audit" and e.get("sequence") == []
           for e in out["events"])
results.append({"case": "empty_targets_returns_to_base", "planner_calls": 1,
                "steps": len(out["route"])-1, "source": out["source"],
                "valid": True, "sequence_empty": True})

# A disconnected base is rejected as environment-infeasible with no fabricated route.
bad = Snapshot("micro_disconnected", frozenset({(0, 0), (2, 0)}), frozenset(),
               frozenset(), (0, 0), (2, 0), ((0, 0), (2, 0)), 0, 100)
out = call(bad)
assert out["status"] == "environment_infeasible" and not out["route"]
results.append({"case": "disconnected_base_rejected", "planner_calls": 1,
                "status": out["status"], "route_empty": True,
                "reason": out.get("reason")})

# Contract-invalid footprint is rejected before invoking the P2 planner.
invalid = snapshot(name="micro_invalid_radius", radius=1)
try:
    baseline_suite.check_contract(invalid, set(invalid.targets), 30.0)
    raise AssertionError("invalid radius unexpectedly passed the contract")
except ValueError as exc:
    assert str(exc) == "one-cell downward footprint required"
results.append({"case": "invalid_radius_rejected_before_planner", "planner_calls": 0,
                "exception": "ValueError", "reason": "one-cell downward footprint required"})

# Deterministic deadline injection at the first warm 2-opt distance check.
geometry = warm.UnifiedGeometry


class InterruptAtWarmDistance(geometry):
    def distance(self, a, b):
        raise DeadlineExceeded("injected deadline at warm 2-opt distance")


with patch.object(warm, "UnifiedGeometry", InterruptAtWarmDistance):
    out = call(snapshot(name="micro_deadline"), variant="warm_multi", budget=30.0)
assert out["status"] == "deadline"
assert out["route"] and audit(s, tuple(out["route"]))["valid"]
assert out["source"] in ("old_suffix", "common_fallback")
assert any(e.get("stage") == "warm_2opt" and e.get("termination") == "deadline"
           for e in out["events"])
results.append({"case": "deadline_keeps_accepted_legal_fallback", "planner_calls": 1,
                "status": out["status"], "source": out["source"],
                "steps": len(out["route"])-1, "valid": True,
                "injection": "DeadlineExceeded at first warm 2-opt distance check"})

summary = {"status": "PASS", "posthoc": True, "formal_map_calls": 0,
           "candidate_planner_calls": calls["warm_module"],
           "frozen_P2_planner_calls": calls["frozen_P2"],
           "total_planner_calls": calls["warm_module"] + calls["frozen_P2"],
           "results": results,
           "limitations": [
               "All fixtures are synthetic micro snapshots; no development-map performance job was run.",
               "Deadline behavior is deterministic exception injection at a solver boundary, not a wall-clock timing claim.",
               "The warm-off comparison is one tiny fixed-seed case and supplements, rather than reconstructs, the missing historical multi-case log."
           ]}
dest = Path(__file__).with_name("posthoc_warm_regressions_20261017.json")
dest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
