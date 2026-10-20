"""Independent strip and GTSP subproblem verification.

Two separate budgets, both logged:

``strip``   10 frozen inputs x cap 0/1/2/6 with the normal certification pipeline
            (40 items), plus 2 strict diagnostics with the repair switched off.
            The model is the frozen one (it is the object under test); the
            *reference* is an independent enumeration written here, which does not
            call ``enumerate_oracle`` or the production decoder.
``gtsp``    4 small service-block sets, solved exactly by the frozen DP and checked
            against an independent enumeration of every order and direction,
            including expansion of the resulting route.

Every item records: model kind and status, objective, whether an incumbent existed,
the decoded strips, the independent reference value, and whether they agree.
"""
import itertools
import json
import math
import sys
import time
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from oarp_replan.ranks import Rank, metrics, rank_replan  # noqa: E402

ART = NEW / "artifacts"
PROBE = NEW / "sources" / "probe" / "planned_inputs.json"
SOFT = 5.0
STRIP_CAP = 56
GTSP_CAP = 8


# --------------------------------------------------------------- enumeration
def enumerate_partitions(cells):
    """Every legal strip partition: an orientation per cell plus a cut per
    adjacent same-axis pair.

    The frozen model can keep two adjacent strips of the same axis apart (its
    `matches` variables decide where a strip ends), so enumerating only the
    maximal runs per orientation would miss those partitions -- which is exactly
    how a retained old block survives.  All partitions here are exact covers.
    """
    cells = sorted(cells)
    cell_set = set(cells)
    for bits in range(1 << len(cells)):
        directions = {p: ("H" if bits >> i & 1 else "V") for i, p in enumerate(cells)}
        pairs = []
        for p in cells:
            for axis, step in (("H", (1, 0)), ("V", (0, 1))):
                q = (p[0] + step[0], p[1] + step[1])
                if q in cell_set and directions[p] == axis and directions[q] == axis:
                    pairs.append((p, q))
        for cut_bits in range(1 << len(pairs)):
            cuts = {pairs[i] for i in range(len(pairs)) if cut_bits >> i & 1}
            ranks = _runs(cells, directions, cuts)
            if ranks is not None:
                yield directions, ranks


def _runs(cells, directions, cuts):
    """Assemble strips, cutting at the chosen adjacent pairs; None if illegal."""
    assigned = set()
    out = []
    for p in cells:
        if p in assigned:
            continue
        axis = directions[p]
        dx, dy = (1, 0) if axis == "H" else (0, 1)
        previous = (p[0] - dx, p[1] - dy)
        if directions.get(previous) == axis and (previous, p) not in cuts:
            continue
        run, q = [], p
        while True:
            if q in assigned:
                return None
            run.append(q)
            assigned.add(q)
            following = (q[0] + dx, q[1] + dy)
            if following in cells and directions.get(following) == axis and (q, following) not in cuts:
                q = following
                continue
            break
        out.append(Rank(axis, tuple(run)))
    if assigned != set(cells):
        return None
    return tuple(out)


def _agrees(value, reference, status):
    """Compare the model result with the enumeration, including the infeasible case.

    A model that reports no solution agrees with the enumeration exactly when the
    enumeration also found no partition inside the change budget.
    """
    if value is None:
        return (reference["feasible_within_cap"] is False
                and status in ("infeasible", "invalid_original_model_solution",
                               "fractional_lp", "timeout"))
    return (reference["best_within_cap"] is not None
            and abs(value - reference["best_within_cap"]) < 1e-6)


def reference_best(cells, old, cap, variant):
    """Best legal strip count and the best change-bounded objective by enumeration."""
    best_any, best_feasible = None, None
    feasible_exists = False
    for directions, ranks in enumerate_partitions(cells):
        m = metrics(ranks, old, directions)
        value = m["rank_count"] + (0 if variant == 0 else m["endpoint_bound"] / (cap + 1))
        counted = 0 if variant == 0 else m["endpoint_bound"]
        if best_any is None or value < best_any:
            best_any = value
        if counted <= cap + 1e-9:
            feasible_exists = True
            if best_feasible is None or value < best_feasible:
                best_feasible = value
    return {"best_overall": best_any, "best_within_cap": best_feasible,
            "feasible_within_cap": feasible_exists}


def strips_match(ranks, decoded):
    return ([ (r.axis, tuple(r.cells)) for r in ranks ]
            == [ (r.axis, tuple(r.cells)) for r in decoded ])


# --------------------------------------------------------------- strip block
def run_strip_items():
    inputs = json.loads(PROBE.read_text(encoding="utf-8"))
    items = []
    for entry in inputs:
        cells = frozenset(tuple(p) for p in entry["cells"])
        old = tuple(Rank(axis, tuple(tuple(p) for p in cells_))
                    for axis, cells_ in entry["old"])
        for cap in (0, 1, 2, 6):
            begin = time.perf_counter()
            deadline = begin + SOFT
            result = rank_replan(cells, old=old, cap=cap, variant=2,
                                 deadline=deadline, integer_fallback=True,
                                 allow_certification_repair=True)
            reference = reference_best(cells, old, cap, 2)
            ranks = result.get("ranks") or ()
            value = result.get("objective")
            items.append({
                "kind": "strip", "case_id": entry["case_id"], "cap": cap,
                "variant": 2, "certification_repair": result.get("certification_repair"),
                "status": result.get("status"),
                "objective": value,
                "rank_count": len(ranks) if ranks else None,
                "attempts": result.get("attempts"),
                "reference": reference,
                "objective_matches_reference": _agrees(value, reference, result.get("status")),
                "ranking_matches_enumeration": (
                    ranks and None not in (value,)
                    and abs(value - min(reference["best_overall"],
                                        reference["best_within_cap"]
                                        if reference["best_within_cap"] is not None
                                        else math.inf)) < 1e-6),
                "seconds": round(time.perf_counter() - begin, 4),
            })
        if len(items) >= STRIP_CAP - 2:
            break

    # two strict diagnostics: the repair is switched off on purpose
    diagnostics = [
        {"case_id": "diag_three_to_four_cap1",
         "cells": [[0, 0], [1, 0], [2, 0], [3, 0]],
         "old": [["H", [[0, 0], [1, 0], [2, 0]]]], "cap": 1,
         "expect": "may be rejected; the recorded value is whatever the solver returns"},
        {"case_id": "diag_unchanged_line_cap0",
         "cells": [[0, 0], [1, 0], [2, 0], [3, 0]],
         "old": [["H", [[0, 0], [1, 0], [2, 0], [3, 0]]]], "cap": 0,
         "expect": "should be feasible with zero change"},
    ]
    for item in diagnostics:
        cells = frozenset(tuple(p) for p in item["cells"])
        old = tuple(Rank(axis, tuple(tuple(p) for p in cells_)) for axis, cells_ in item["old"])
        begin = time.perf_counter()
        result = rank_replan(cells, old=old, cap=item["cap"], variant=2,
                             deadline=begin + SOFT, integer_fallback=True,
                             allow_certification_repair=False)
        reference = reference_best(cells, old, item["cap"], 2)
        items.append({
            "kind": "strip_diagnostic", "case_id": item["case_id"], "cap": item["cap"],
            "variant": 2, "certification_repair": False,
            "status": result.get("status"), "objective": result.get("objective"),
            "attempts": result.get("attempts"), "rejected": result.get("rejected"),
            "reference": reference,
            "expect": item["expect"],
            "objective_matches_reference": _agrees(result.get("objective"), reference,
                                                    result.get("status")),
            "seconds": round(time.perf_counter() - begin, 4),
        })
    return items


# ---------------------------------------------------------------- GTSP block
def run_gtsp_items():
    from oarp_replan.tour import gtsp_instance, tour_replan, decode_tour
    from model import Geometry, Snapshot

    specs = [
        {"case_id": "gtsp_two_groups",
         "blocks": [[(0, 0), (1, 0)], [(3, 0), (3, 1)]]},
        {"case_id": "gtsp_three_groups",
         "blocks": [[(0, 0)], [(2, 0), (3, 0)], [(2, 2)]]},
        {"case_id": "gtsp_four_groups",
         "blocks": [[(0, 0), (1, 0)], [(0, 2)], [(3, 0)], [(3, 2), (3, 3)]]},
        {"case_id": "gtsp_single_group",
         "blocks": [[(0, 0), (1, 0), (2, 0)]]},
    ]
    free = frozenset((x, y) for x in range(5) for y in range(4))
    start, base = (0, 3), (0, 3)
    out = []
    for spec in specs:
        blocks = [{"kind": "rank", "rank_keys": [(b[0], b)], "path": tuple(b)}
                  for b in spec["blocks"]]
        snapshot = Snapshot(spec["case_id"], free, frozenset(), frozenset(),
                            start, base, (), radius=0)
        g = Geometry(snapshot, time.perf_counter() + SOFT)
        begin = time.perf_counter()
        tour = tour_replan(g, blocks, seconds=SOFT, seed=20261018, exact=True)
        elapsed = time.perf_counter() - begin
        matrix, sets = tour["matrix"], tour["sets"]
        naive = _enumerate_gtsp(tour["states"], sets, matrix)
        out.append({
            "kind": "gtsp", "case_id": spec["case_id"],
            "groups": len(spec["blocks"]),
            "exact_cost": tour["length"], "exact_order": list(tour["order"]),
            "enumerated_cost": naive["cost"], "enumerated_order": naive["order"],
            "agree": naive["cost"] == tour["length"],
            "route_steps": len(tour["route"]) - 1,
            "route_matches_cost": len(tour["route"]) - 1 == tour["length"],
            "seconds": round(elapsed, 4),
        })
        if len(out) >= GTSP_CAP:
            break
    return out


def _enumerate_gtsp(states, sets, matrix):
    """Brute force over service-group orders and directions (no DP reuse).

    `gtsp_instance` appends the start and end states last, so they are
    `len(states)-2` and `len(states)-1`.
    """
    groups = [s for s in sets if len(s) == 2]
    start, end = len(states) - 2, len(states) - 1
    best = (math.inf, ())
    for permutation in itertools.permutations(range(len(groups))):
        for directions in itertools.product((0, 1), repeat=len(groups)):
            tour = [start]
            for group_index, direction in zip(permutation, directions):
                tour.append(groups[group_index][direction])
            tour.append(end)
            cost = sum(matrix[a][b] for a, b in zip(tour, tour[1:]))
            if cost < best[0]:
                best = (cost, tuple(tour))
    return {"cost": best[0], "order": list(best[1])}


def main():
    items = run_strip_items()
    gtsp = run_gtsp_items()
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "strip_math.json").write_text(
        json.dumps({"items": items, "count": len(items),
                    "cap": STRIP_CAP}, ensure_ascii=False, indent=1), encoding="utf-8")
    (ART / "gtsp_math.json").write_text(
        json.dumps({"items": gtsp, "count": len(gtsp), "cap": GTSP_CAP},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    agrees = sum(1 for item in items if item.get("objective_matches_reference"))
    print(f"strip items: {len(items)}  objective agrees with enumeration: {agrees}")
    for item in items:
        if not item.get("objective_matches_reference"):
            print("  MISMATCH", item["case_id"], item["cap"], item["status"],
                  item["objective"], item["reference"])
    print(f"gtsp items: {len(gtsp)}  all agree: {all(g['agree'] for g in gtsp)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
