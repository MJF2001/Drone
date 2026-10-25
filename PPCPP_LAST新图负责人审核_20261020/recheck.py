"""Reviewer-only route accounting and a bounded distance-query diagnostic."""
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

H = Path(__file__).resolve().parent
S = H.parent / "PPCPP_LAST新开发地图验证_v0.1_20261020"
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
def pts(a):
    return set(map(tuple, a))
groups = defaultdict(dict)
times = defaultdict(list)
candidate_times = []
for p in sorted((S / "execution").glob("*.json")):
    x = read(p)
    j, r = x["job"], x["raw"]
    c = read(Path(j["input"]))
    f, t, h = pts(c["free"]), pts(c["targets"]), pts(c["covered"])
    start, base = tuple(c["current"]), tuple(c["base"])
    u = t-h-{start}
    assert x["eligible"] and x["entry_seconds"] < 20
    for label, b in r["branches"].items():
        assert b["status"] == "core_complete"
        route = list(map(tuple, b["route"]))
        assert route[0] == start and route[-1] == base and set(route) <= f
        assert all(abs(a[0]-z[0])+abs(a[1]-z[1]) == 1 for a,z in zip(route,route[1:]))
        assert t <= h|set(route)
        if label == "P1":
            e = tuple(r["e"])
            end = b["phase1_end"]
            assert e in u and e not in route[:end+1] and u-{e} <= set(route[:end+1])
            remaining = set(u)
            last = None
            for v in route:
                if v in remaining:
                    remaining.remove(v)
                    last = v
            assert not remaining and last == e
    selected = min(r["branches"], key=lambda k: (len(r["branches"][k]["route"]), k))
    assert r["selected"] == selected and r["route"] == r["branches"][selected]["route"]
    groups[j["case_id"], j["repetition"]][j["method"]] = x
    times[j["method"]].append(x["entry_seconds"])
    if j["method"] == "LAST":
        candidate_times.append(x["phase_seconds"]["candidate"])
summary = dict(states=0, original=0, candidate=0, improved=0, savings=[])
for (name, rep), pair in groups.items():
    a, b = pair["PPCPP"]["raw"], pair["LAST"]["raw"]
    for field in ("route", "trace"):
        assert a["branches"]["P0"][field] == b["branches"]["P0"][field]
    if rep == 0:
        saved = len(a["route"])-len(b["route"])
        summary["states"] += 1
        summary["original"] += len(a["route"])-1
        summary["candidate"] += len(b["route"])-1
        summary["improved"] += saved > 0
        summary["savings"].append(saved)
assert len(groups) == 270 and summary["states"] == 54
assert (summary["original"], summary["candidate"], summary["improved"]) == (5530,5476,27)
assert set(summary["savings"]) == {0,2}

# Select by target count, never by observed gain. Do not call a planner.
cases = [read(p) for p in (S/"inputs").glob("*.json")]
c = sorted(cases, key=lambda c: (-len(pts(c["targets"])-pts(c["covered"])-{tuple(c["current"])}), c["name"]))[0]
sys.path.insert(0, str(S))
import runtime
s = runtime.snapshot(c)
u = set(s.targets)-set(s.covered)-{s.current}
original = runtime.native.UnifiedGeometry(s, time.perf_counter()+20)
reversed_query = runtime.native.UnifiedGeometry(s, time.perf_counter()+20)
d1 = {q: original.distance(q,s.base) for q in sorted(u)}
d2 = {q: reversed_query.distance(s.base,q) for q in sorted(u)}
assert d1 == d2
assert original.bfs_rows_built == len(u) and reversed_query.bfs_rows_built == 1
out = dict(
    verified=True, formal_outputs=540, original_pairs=270, summary=summary,
    mean_entry_seconds={m:sum(v)/len(v) for m,v in times.items()},
    mean_candidate_seconds=sum(candidate_times)/len(candidate_times),
    diagnostic=dict(case=c["name"], pending=len(u), original_bfs_rows=original.bfs_rows_built,
                    reversed_query_bfs_rows=reversed_query.bfs_rows_built, distances_equal=True,
                    note="One read-only geometry diagnostic, no planner run or speedup benchmark"),
    new_planner_calls=0,
)
(H/"recheck_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))
