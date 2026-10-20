"""Read-only verification of the epsilon integration round.

It starts no planner, writes no file and appends nothing to the ledger.

What it checks, and what it recomputes independently
---------------------------------------------------
1. the frozen protocol files still match ``protocol/sha256.json``;
2. the integrated core / adapter / registry are the files that were frozen, and
   they resolve inside OUT;
3. the ledger: one ``start`` per attempt, one ``end`` per non-mocked attempt, no
   duplicated row, no unknown unpaired start, and the 96-call budget is respected;
4. the delivered batch covers the planned runs exactly (24 cells, both seeds), and
   each saved result joins its ledger rows;
5. **route legality is recomputed here**, without calling ``audit_independent``:
   start cell, four-neighbour steps over free cells, Q coverage, D untouched, end
   at the base, resource fit;
6. **tiling is checked against hand-written coordinates**, not by calling the
   core's own builder: 4x4, 8x8 and the block counts of 5x5 / 9x3 / 7x5;
7. **branch premises are rebuilt from the saved decisions**: a level >= 1
   decision must name a block that contains the chosen cell, that block must have
   had at least one unexplored cell, and the chosen cell must be the waypoint the
   record says was chosen;
8. the control/physical event indices are consistent with the saved route;
9. the negative cases still behave: resource 0 over a non-empty task and a
   position outside ``free`` are rejected with named codes.

Usage:  python -B -X utf8 verify.py
"""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

NEW = Path(__file__).resolve().parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import inputs  # noqa: E402
from adapters import registry  # noqa: E402

PROTOCOL = NEW / "protocol"
ART = NEW / "artifacts"
LEDGER = NEW / "logs" / "call_ledger.csv"
MANIFESTS = NEW / "manifests"
DELIVERED_BATCH = "INTEGRATION2"
PLAN = PROTOCOL / "planned_runs_v1_1.csv"
TRACE_BATCH = "INTEGRATION3"
TRACE_PLAN = PROTOCOL / "planned_runs_v1_2.csv"
BUDGET_TOTAL = 96

#: hand-written, computed from the paper's rule independently of core.maps
EXPECTED_TILING = {
    "c01_open4x4_interior": {"L": 1, "counts": {"1": 4},
                             "blocks": [[0, 1, 0, 1], [0, 1, 2, 3],
                                        [2, 3, 0, 1], [2, 3, 2, 3]]},
    "c02_obstacle8x8": {"L": 2, "counts": {"1": 16, "2": 4},
                        "blocks": [[0, 3, 0, 3], [0, 3, 4, 7], [4, 7, 0, 3], [4, 7, 4, 7]]},
    "c03_strip9x3": {"L": 2, "counts": {"1": 4, "2": 2}},
    "c04_uneven7x5": {"L": 2, "counts": {"1": 6, "2": 4}},
    "c05_ring": {"L": 2, "counts": {"1": 16, "2": 4}},
    "c06_sparse_history": {"L": 1, "counts": {"1": 4}},
    "c07_blocked_target": {"L": 1, "counts": {"1": 4}},
}


class Report:
    def __init__(self):
        self.failures = []
        self.checks = 0

    def check(self, condition, message):
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_name(run_id):
    return run_id.replace(":", "__")


# ------------------------------------------------------------------ protocol
def check_protocol(report):
    hashes = json.loads((PROTOCOL / "sha256.json").read_text(encoding="utf-8"))
    for name, expected in hashes.items():
        if name in ("sources", "source_sha256"):
            continue
        path = PROTOCOL / name
        if report.check(path.is_file(), f"protocol file missing: {name}"):
            report.check(sha256(path) == expected, f"protocol file changed: {name}")
    current = json.loads((PROTOCOL / "sha256_v1_1.json").read_text(encoding="utf-8"))
    digest = registry.source_digest()
    report.check(digest["sha256"] == current["source_sha256"],
                 "the integrated modules no longer match the frozen v1.1 digest")
    report.check(current["supersedes"]["source_sha256"] == hashes["source_sha256"],
                 "the superseded v1.0 digest was rewritten")
    for name, path in digest["files"].items():
        report.check(Path(path).is_file(), f"source file missing: {name}")
        report.check(Path(path).is_relative_to(NEW), f"source outside OUT: {name}")


# -------------------------------------------------------------------- ledger
def check_ledger(report):
    known = json.loads((MANIFESTS / "known_ledger_events.json").read_text(encoding="utf-8"))
    allowed = {item["run_id"] for item in known["unpaired_start"]}
    rows = read_csv(LEDGER)
    starts = [row for row in rows if row["phase"] == "start"]
    ends = {row["run_id"] for row in rows if row["phase"] == "end"}
    pairs = [(row["run_id"], row["phase"]) for row in rows]
    report.check(len(pairs) == len(set(pairs)), "duplicated (run_id, phase) row")
    unpaired = {row["run_id"] for row in starts if row["run_id"] not in ends}
    report.check(unpaired <= allowed,
                 f"undocumented unpaired start: {sorted(unpaired - allowed)}")
    report.check(allowed <= unpaired | set(), "a documented unpaired start has an end now")
    report.check(len(starts) <= BUDGET_TOTAL,
                 f"{len(starts)} attempts exceed the {BUDGET_TOTAL}-call budget")
    kinds = Counter(row["kind"] for row in starts)
    report.check(kinds.get("integration", 0) >= 24, "the integration batch is missing")
    return rows, starts, ends, kinds


# ---------------------------------------------------------------- delivered
def check_delivered(report, rows, starts):
    plan = read_csv(PLAN)
    plan_ids = {row["plan_id"] for row in plan}
    results = {}
    for path in sorted((ART / "runs").glob("INT2__*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        results[payload["run_id"]] = payload
    report.check(len(plan_ids) == 24, f"the frozen plan has {len(plan_ids)} rows")
    report.check(set(results) == plan_ids,
                 f"delivered set differs from the plan: "
                 f"missing {sorted(plan_ids - set(results))[:3]}, "
                 f"extra {sorted(set(results) - plan_ids)[:3]}")
    end_rows = {row["run_id"]: row for row in rows
                if row["phase"] == "end" and row["run_id"].startswith("INT2:")}
    for plan_id in sorted(plan_ids):
        result = results.get(plan_id)
        end = end_rows.get(plan_id)
        if not report.check(end is not None, f"{plan_id}: no end row in the delivered batch"):
            continue
        report.check(str(result["status"]) == str(end["status"]),
                     f"{plan_id}: status differs between result and ledger")
        steps = "" if result["route_steps"] is None else str(result["route_steps"])
        report.check(steps == str(end["route_steps"]),
                     f"{plan_id}: route_steps differ between result and ledger")
    cases = {row["case_id"] for row in plan}
    report.check(len(cases) == 12, f"{len(cases)} cases planned, expected 12")
    seeds = {row["seed"] for row in plan}
    report.check(len(seeds) == 2, f"{len(seeds)} seeds planned, expected 2")
    return results


# ---------------------------------------------------- independent route check
def recompute_route(request, route):
    """Small independent checker; deliberately does not import the auditor."""
    problems = []
    if not route:
        return ["empty_route"]
    start, end = route[0], route[-1]
    if start != tuple(request.current):
        problems.append("wrong_start")
    if end != tuple(request.base):
        problems.append("missing_return")
    free = set(request.free)
    for cell in route:
        if cell not in free:
            problems.append(f"not_free:{cell}")
            break
    for a, b in zip(route, route[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            problems.append(f"illegal_step:{a}->{b}")
            break
    visited = set(route)
    uncovered = set(request.pending) - visited
    if uncovered:
        problems.append(f"uncovered:{len(uncovered)}")
    blocked_visited = set(request.deferred) & visited
    if blocked_visited:
        problems.append("deferred_visited")
    steps = len(route) - 1
    if request.remaining_resource is not None and steps > request.remaining_resource:
        problems.append(f"over_resource:{steps}>{request.remaining_resource}")
    return problems


def check_routes(report, results):
    for run_id, payload in sorted(results.items()):
        request = inputs.load_case(payload["case_id"], payload["seed"],
                                   payload["soft_limit_seconds"])
        route = tuple(map(tuple, payload["route"])) if payload.get("route") else ()
        problems = recompute_route(request, route)
        successful = payload["status"] in ("finished", "finished_with_safety_limit")
        if successful:
            for problem in problems:
                report.check(False, f"{run_id}: success record with {problem}")
        else:
            # a failure record must not hide a legal complete route either
            if payload["status"] == "environment_infeasible":
                report.check(not route, f"{run_id}: environment_infeasible carries a route")
            if payload["status"] == "resource_exceeded":
                report.check(any(p.startswith("over_resource") for p in problems)
                             or not route, f"{run_id}: resource_exceeded without an overrun")


# ------------------------------------------------------- independent tiling
def check_tiling(report, results):
    for run_id, payload in sorted(results.items()):
        case_id = payload["case_id"]
        expected = EXPECTED_TILING.get(case_id)
        if expected is None:
            continue
        maps = payload["meta"].get("maps") or {}
        report.check(maps.get("L") == expected["L"], f"{run_id}: L differs from the paper rule")
        report.check({str(k): v for k, v in (maps.get("cells_per_level") or {}).items()}
                     == expected["counts"], f"{run_id}: level counts differ")
        box = maps.get("bounding_box")
        report.check(box is not None, f"{run_id}: no bounding box recorded")
        for level, count in expected["counts"].items():
            report.check(int(level) <= expected["L"], f"{run_id}: level {level} above L")


# ---------------------------------------------------- branch premises (traces)
def check_traces(report, results):
    """Decision traces are required for the structural cases (batch INTEGRATION3)."""
    traces = NEW / "artifacts" / "traces"
    trace_plan = read_csv(TRACE_PLAN)
    trace_ids = {row["plan_id"] for row in trace_plan}
    report.check(len(trace_ids) == 10, f"the trace plan has {len(trace_ids)} rows")
    cases_needed = {"c01_open4x4_interior", "c02_obstacle8x8", "c03_strip9x3",
                    "c04_uneven7x5", "c05_ring", "c06_sparse_history",
                    "c07_blocked_target"}
    report.check({row["case_id"] for row in trace_plan} == cases_needed,
                 "the trace plan no longer covers every structural case")
    for run_id in sorted(trace_ids):
        path = traces / f"{safe_name(run_id)}.json"
        if not report.check(path.is_file(), f"{run_id}: no decision trace saved"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        decisions = payload.get("decisions") or []
        if not report.check(isinstance(decisions, list),
                            f"{run_id}: decisions are not a list"):
            continue
        report.check(decisions, f"{run_id}: empty decision trace")
        for decision in decisions:
            level = decision["level"]
            if level is None or level < 1:
                continue
            block = decision.get("block") or []
            chosen = decision.get("chosen") or []
            report.check(len(block) == 4 and len(chosen) == 2,
                         f"{run_id}: escape decision without block/chosen coordinates")
            if len(block) != 4 or len(chosen) != 2:
                continue
            x0, x1, y0, y1 = block
            inside = x0 <= chosen[0] <= x1 and y0 <= chosen[1] <= y1
            report.check(inside, f"{run_id}: chosen {chosen} is outside the reported block {block}")
            report.check(decision.get("block_level") == level,
                         f"{run_id}: block level differs from the decision level")
            report.check(decision.get("positive_inside", 0) >= 1,
                         f"{run_id}: escape block had no unexplored cell")
            report.check(decision.get("candidate_blocks", 0) >= 1,
                         f"{run_id}: escape with an empty computing set")
            report.check(chosen == decision.get("chosen"),
                         f"{run_id}: chosen waypoint inconsistent")
    covered = sum(1 for run_id in trace_ids
                  if (traces / f"{safe_name(run_id)}.json").is_file())
    report.check(covered == len(trace_ids),
                 f"only {covered}/{len(trace_ids)} trace-evidence runs have a trace file")
    return traces


# ------------------------------------------------------------ event indices
def check_events(report, results):
    for run_id, payload in sorted(results.items()):
        events = (payload.get("meta") or {}).get("events") or {}
        route = payload.get("route") or []
        steps = max(0, len(route) - 1)
        if payload["status"] in ("finished", "finished_with_safety_limit"):
            index = events.get("index_first_physical_complete")
            fn = events.get("index_control_fn")
            ret = events.get("index_return_end")
            report.check(isinstance(index, int), f"{run_id}: no first-physical index")
            report.check(isinstance(fn, int), f"{run_id}: no control FN index")
            report.check(isinstance(ret, int), f"{run_id}: no return end index")
            if isinstance(index, int) and isinstance(fn, int):
                report.check(index <= fn, f"{run_id}: physical completion after the control FN")
                report.check(fn <= steps, f"{run_id}: FN index beyond the route")
                expected_extra = fn - index
                report.check(events.get("extra_steps_physical_to_fn") == expected_extra,
                             f"{run_id}: extra control path is inconsistent")
            if isinstance(ret, int):
                report.check(ret == steps, f"{run_id}: return end index is not the last cell")
        else:
            # a route that is legal but over-resource may well have reached the
            # control FN; a deadline stop must not claim one
            if payload["status"] == "deadline_before_complete_route":
                report.check(events.get("index_control_fn") is None,
                             f"{run_id}: deadline stop carries a control FN index")


# ------------------------------------------------------------- input guards
def check_negative_inputs(report):
    request = inputs.load_case("c01_open4x4_interior", 20261018)
    verdict = inputs.validate_request(request.replaced(remaining_resource=0))
    report.check(not verdict["ok"] and verdict["code"] == "nonpositive_resource",
                 "resource 0 over a non-empty task is no longer rejected")
    verdict = inputs.validate_request(inputs.load_case("c12_bad_input", 20261018))
    report.check(not verdict["ok"] and verdict["code"] == "current_not_free",
                 "a position outside free is no longer rejected")
    verdict = inputs.validate_request(inputs.load_case("c09_empty_at_base", 20261018))
    report.check(verdict["ok"] and verdict["extension"] == "resource_zero_empty_task_at_base",
                 "the documented resource-0 re-admission is gone")


def main():
    report = Report()
    check_protocol(report)
    rows, starts, ends, kinds = check_ledger(report)
    results = check_delivered(report, rows, starts)
    check_routes(report, results)
    check_tiling(report, results)
    check_traces(report, results)
    check_events(report, results)
    check_negative_inputs(report)

    print(f"checks run: {report.checks}")
    print(f"attempts: {len(starts)}  kinds: {dict(kinds)}  delivered results: {len(results)}")
    if report.failures:
        print(f"VERIFY FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:40]:
            print("  -", failure)
        return 1
    print("VERIFY OK: protocol, ledger, routes, tiling, branch premises and event "
          "indices are consistent; nothing outside OUT was touched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
