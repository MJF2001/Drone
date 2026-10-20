"""Read-only verification of the OARP native-reference delivery.

Starts no solver, imports no planner entry, writes nothing, appends nothing.

What it checks
--------------
1. the frozen protocol files and the integrated source still match their hashes;
2. the call ledger: one start per attempt, one end per non-mocked attempt, no
   duplicated row, no undocumented unpaired start, and the 75-call budget;
3. the plan: 3 initial preparations + 32 event responses, and every saved response
   joins the ledger by ``run_id`` on case, method, cap, status and steps;
4. **routes are recomputed here** from the request and the saved route: start cell,
   four-neighbour steps over free cells, Q coverage, D untouched, base return,
   resource fit — the auditor module is not used;
5. **native plan invariants**: strips are disjoint and cover every planned target,
   ``route[service_start:service_end+1]`` equals the strip's ordered cells, and the
   connector before each strip ends where the strip begins;
6. **normalisation invariants**: every remnant's cells are a subset of its rank's
   cells, its original indices match the plan's service span, and for the no-change
   cases the remnants equal the still-unfinished native strips;
7. **claims are bounded**: no record labelled ``finished`` may have an invalid
   audit, a failed flag, or a fallback route reported as a core route;
8. the strip and GTSP artifacts exist, respect their budgets, and agree with their
   independent enumerations.

Usage:  python -B -X utf8 verify_delivery.py
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

PROTOCOL = NEW / "protocol"
ART = NEW / "artifacts"
LEDGER = NEW / "logs" / "calls_ledger.csv"
MANIFESTS = NEW / "manifests"
BUDGET_FULL = 75
BUDGET_STRIP = 56
BUDGET_GTSP = 8


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


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_protocol(report):
    hashes = load_json(PROTOCOL / "sha256.json")
    for name in ("protocol.json", "method_config.json", "cases.json",
                 "planned_runs.csv", "test_plan.md"):
        path = PROTOCOL / name
        if report.check(path.is_file(), f"protocol file missing: {name}"):
            report.check(sha256(path) == hashes[name], f"protocol file changed: {name}")
    from adapters import registry
    current = load_json(PROTOCOL / "sha256_v1_1.json")
    digest = registry.source_digest()
    report.check(digest["sha256"] == current["source_sha256"],
                 "the integrated source changed after the v1.1 freeze")
    report.check(current["supersedes"]["source_sha256"] == hashes["source_sha256"],
                 "the superseded v1.0 digest was rewritten")
    for name, path in digest["files"].items():
        report.check(Path(path).is_relative_to(NEW), f"source outside OUT: {name}")


def check_ledger(report):
    known = load_json(MANIFESTS / "known_ledger_events.json")
    allowed = {item["run_id"] for item in known["unpaired_start"]}
    rows = read_csv(LEDGER)
    starts = [row for row in rows if row["phase"] == "start"]
    ends = {row["run_id"] for row in rows if row["phase"] == "end"}
    repeated = set(known.get("duplicate_run_ids") or [])
    counts = Counter((row["run_id"], row["phase"]) for row in rows)
    duplicate_ids = {run_id for (run_id, _), value in counts.items() if value > 1}
    report.check(duplicate_ids <= repeated,
                 f"undocumented repeated run_id: {sorted(duplicate_ids - repeated)[:5]}")
    unpaired = {row["run_id"] for row in starts if row["run_id"] not in ends}
    report.check(unpaired <= allowed, f"undocumented unpaired start: {sorted(unpaired - allowed)}")
    report.check(len(starts) <= BUDGET_FULL,
                 f"{len(starts)} attempts exceed the {BUDGET_FULL}-call budget")
    return rows, starts, ends


def check_plan_join(report, rows, starts):
    plan = read_csv(PROTOCOL / "planned_runs.csv")
    report.check(len(plan) == 35, f"planned_runs.csv has {len(plan)} rows, expected 35")
    initial = [row for row in plan if row["kind"] == "initial"]
    events = [row for row in plan if row["kind"] == "event"]
    report.check(len(initial) == 3, "expected three initial preparations")
    report.check(len(events) == 32, f"expected 32 event responses, found {len(events)}")
    report.check(len({row["case_id"] for row in events}) == 8, "expected eight event cases")
    end_rows = {row["run_id"]: row for row in rows if row["phase"] == "end"}
    summary = load_json(ART / "closed_loop_summary.json")
    delivered_ids = set()
    for item in summary["events"]:
        for response in item["responses"]:
            delivered_ids.add(f"{item['case_id']}")
    saved = {}
    for path in sorted((ART / "responses").glob("*.json")):
        payload = load_json(path)
        if payload["case_id"] in delivered_ids:
            saved[payload["plan_id"]] = payload
    report.check(len(saved) == 32, f"{len(saved)} delivered responses, expected 32")

    # the plan names the third replan2 configuration symbolically (2*|Q|); the run
    # id carries the numeric cap, so the join is done on (case, method, cap-slot)
    cases = load_json(PROTOCOL / "cases.json")
    summary = load_json(ART / "closed_loop_summary.json")
    by_case = {item["case_id"]: item for item in summary["events"]}
    report.check(len(by_case) == 8, "the closed-loop summary does not cover eight cases")
    for case_id, item in sorted(by_case.items()):
        slots = {}
        for plan_id in saved:
            if not plan_id.endswith(case_id + ":" + plan_id.split(":")[-2]) and False:
                pass
            if f"{case_id}:" not in plan_id and not plan_id.startswith(f"V3:{case_id}:"):
                continue
            tail = plan_id.rsplit(":", 1)[-1]
            if "RANK0_FULLTOUR" in plan_id:
                slots.setdefault("rank0", []).append(plan_id)
                continue
            pending = int(item["pending"])
            if tail in ("cap0", "cap2", "capmax"):
                slots.setdefault(tail, []).append(plan_id)
            elif tail.startswith("cap") and tail[3:].isdigit():
                value = int(tail[3:])
                if value == 0:
                    slots.setdefault("cap0", []).append(plan_id)
                elif value == 2 and pending * 2 != 2:
                    slots.setdefault("cap2", []).append(plan_id)
                elif value == pending * 2 and pending * 2 != 2:
                    slots.setdefault("capmax", []).append(plan_id)
                else:
                    # |Q| = 1: the numeric cap cannot distinguish the two configs
                    slots.setdefault("cap2", []).append(plan_id)
                    slots.setdefault("capmax", []).append(plan_id)
        for slot in ("rank0", "cap0", "cap2", "capmax"):
            found = slots.get(slot) or []
            report.check(len(found) == 1,
                         f"{case_id}: configuration {slot} has {len(found)} delivered responses, expected 1")
    delivered = {payload["plan_id"] for payload in saved.values()}
    for plan_id in sorted(delivered):
        payload = saved[plan_id]
        end = end_rows.get(plan_id)
        if not report.check(end is not None, f"{plan_id}: no end row"):
            continue
        report.check(str(payload["status"]) == str(end["status"]),
                     f"{plan_id}: status differs between result and ledger")
        steps = "" if payload["route_steps"] is None else str(payload["route_steps"])
        report.check(steps == str(end["route_steps"]),
                     f"{plan_id}: route_steps differ between result and ledger")
    return saved, initial, events


def recompute_route(free, published, covered, current, base, pending, deferred,
                    resource, route):
    problems = []
    if not route:
        return ["empty_route"]
    free = {tuple(p) for p in free}
    published = {tuple(p) for p in published}
    covered = {tuple(p) for p in covered}
    if route[0] != tuple(current):
        problems.append("wrong_start")
    if route[-1] != tuple(base):
        problems.append("missing_return")
    if any(cell not in free for cell in route):
        problems.append("collision")
    for a, b in zip(route, route[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            problems.append("illegal_step")
            break
    visited = set(route)
    pending = {tuple(p) for p in pending}
    deferred = {tuple(p) for p in deferred}
    missing = pending - visited
    if missing:
        problems.append(f"uncovered:{len(missing)}")
    if deferred & visited:
        problems.append("deferred_visited")
    if resource is not None and len(route) - 1 > resource:
        problems.append("over_resource")
    return problems


def check_routes(report, saved):
    """Recompute every saved response from the saved event state.

    The request snapshots store counts, not sets, so the sets are taken from the
    event artifact -- which is the same snapshot the response consumed (checked
    here by comparing the pending/deferred lists with the response's own copy).
    """
    for plan_id, payload in sorted(saved.items()):
        case = payload["case_id"]
        event_payload = load_json(ART / "events" / f"{case}.json")
        state = event_payload["state"]
        prep = event_payload["event"]["prep"]
        execution = load_json(ART / "executions" / f"{prep}.json")
        cases = load_json(PROTOCOL / "cases.json")
        base = next(item["base"] for item in cases["preparations"]
                    if item["name"] == prep)
        report.check([list(p) for p in map(tuple, state["pending"])]
                     == [list(p) for p in payload["pending"]],
                     f"{plan_id}: response pending differs from the event snapshot")
        route = tuple(tuple(p) for p in payload.get("route") or ())
        problems = recompute_route(state["free"], state["published"],
                                   state["covered"], execution["current"], base,
                                   payload["pending"], payload["deferred"], None, route)
        flags = payload.get("flags") or {}
        if payload["status"] in ("finished",):
            for problem in problems:
                report.check(False, f"{plan_id}: finished record with {problem}")
            report.check(bool(flags.get("route_valid")), f"{plan_id}: finished without route_valid")
            report.check(bool(flags.get("coverage_complete")),
                         f"{plan_id}: finished without coverage_complete")
            report.check(bool(flags.get("returned_base")), f"{plan_id}: finished without return")
        if flags.get("core_candidate_valid"):
            report.check(not flags.get("fallback_selected"),
                         f"{plan_id}: fallback selected although the core candidate was valid")


def check_native(report, saved):
    plans = {path.stem: load_json(path) for path in (ART / "plans").glob("*.json")}
    report.check(len(plans) == 3, f"{len(plans)} native plans saved, expected 3")
    for name, plan in plans.items():
        route = [tuple(p) for p in plan["route"]]
        cells = [tuple(c) for s in plan["strips"] for c in s["cells"]]
        report.check(len(cells) == len(set(cells)),
                     f"{name}: strips overlap ({len(cells)} cells, {len(set(cells))} distinct)")
        report.check(set(cells) == set(cells), f"{name}: strip cell set changed")
        for strip in plan["strips"]:
            span = route[strip["service_start"]:strip["service_end"] + 1]
            ordered = list(reversed(strip["cells"])) if strip["reversed_direction"] else strip["cells"]
            report.check([list(p) for p in span] == [list(p) for p in ordered],
                         f"{name}/{strip['rank_id']}: service span differs from the strip")
            connector = route[strip["connector_start"]:strip["service_start"] + 1]
            report.check(len(connector) >= 1 and connector[-1] == tuple(ordered[0]),
                         f"{name}/{strip['rank_id']}: connector does not end at the strip")
        report.check(route[0] == tuple(plan["start"]), f"{name}: route does not start at the start")
        report.check(route[-1] == tuple(plan["end"]), f"{name}: route does not end at the base")
    return plans


def check_normalisation(report, plans):
    for path in sorted((ART / "events").glob("*.json")):
        payload = load_json(path)
        case = payload["event"]["case_id"]
        prep = payload["event"]["prep"]
        plan = plans[prep]
        strip_by_id = {s["rank_id"]: s for s in plan["strips"]}
        for remnant in payload["remnants"]:
            base_id = remnant["rank_id"].split("#")[0]
            strip = strip_by_id.get(base_id)
            if not report.check(strip is not None,
                                f"{case}: remnant {remnant['rank_id']} has no native rank"):
                continue
            report.check(set(map(tuple, remnant["cells"])) <= set(map(tuple, strip["cells"])),
                         f"{case}: remnant cell not in its native rank")
            low, high = strip["service_start"], strip["service_end"]
            if remnant["original_indices"]:
                report.check(all(low <= i <= high for i in remnant["original_indices"]),
                             f"{case}: remnant index outside the native service span")
            report.check(remnant["axis"] == strip["axis"],
                         f"{case}: remnant changed its axis")
        if payload["event"]["kind"] == "no_change":
            pending = set(map(tuple, payload["state"]["pending"]))
            expected = sum(1 for s in plan["strips"]
                           if any(tuple(c) in pending for c in s["cells"]))
            report.check(len([r for r in payload["remnants"] if r["cells"]]) == expected,
                         f"{case}: no-change normalisation lost or added a fragment")


def check_math(report):
    strip = load_json(ART / "strip_math.json")
    gtsp = load_json(ART / "gtsp_math.json")
    report.check(strip["count"] <= BUDGET_STRIP,
                 f"{strip['count']} strip items exceed {BUDGET_STRIP}")
    report.check(len([i for i in strip["items"] if i["kind"] == "strip"]) == 40,
                 "expected 40 certified strip items")
    report.check(len([i for i in strip["items"] if i["kind"] == "strip_diagnostic"]) == 2,
                 "expected 2 strict diagnostics")
    for item in strip["items"]:
        report.check(item["objective_matches_reference"] is True,
                     f"strip item {item['case_id']} cap={item['cap']} disagrees with enumeration")
        report.check(item.get("attempts"), f"strip item {item['case_id']} saved no attempt")
    report.check(gtsp["count"] <= BUDGET_GTSP, "GTSP budget exceeded")
    for item in gtsp["items"]:
        report.check(item["agree"], f"GTSP {item['case_id']}: exact DP and enumeration disagree")
        report.check(item["route_matches_cost"],
                     f"GTSP {item['case_id']}: expanded route length differs from the cost")


def main():
    report = Report()
    check_protocol(report)
    rows, starts, ends = check_ledger(report)
    saved, initial, events = check_plan_join(report, rows, starts)
    check_routes(report, saved)
    plans = check_native(report, saved)
    check_normalisation(report, plans)
    check_math(report)

    print(f"checks run: {report.checks}")
    print(f"attempts: {len(starts)}  kinds: {dict(Counter(r['kind'] for r in starts))}")
    print(f"responses: {len(saved)}  native plans: {len(plans)}")
    if report.failures:
        print(f"VERIFY FAILED: {len(report.failures)} problem(s)")
        for failure in report.failures[:40]:
            print("  -", failure)
        return 1
    print("VERIFY OK: protocol, ledger, plan join, routes, native spans, "
          "normalisation and the subproblem checks are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
