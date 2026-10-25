"""Read-only reviewer recomputation from raw routes, without candidate/audit imports."""
import json
from collections import deque, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
S = H.parent / "PPCPP保留末采集格候选_v0.1_20261020"
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
def points(a):
    return set(map(tuple, a))
def distance(f, start):
    d = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in f and p not in d:
                d[p] = d[x,y] + 1
                q.append(p)
    return d

groups = defaultdict(dict)
branch_count = 0
for p in sorted((S / "execution").glob("*.json")):
    x = read(p)
    j, r = x["job"], x["raw"]
    c = read(Path(j["input"]))
    f, t, h = points(c["free"]), points(c["targets"]), points(c["covered"])
    start, base = tuple(c["current"]), tuple(c["base"])
    u = t - h - {start}
    assert x["eligible"] and x["entry_seconds"] < x["budget"]
    for label, b in r["branches"].items():
        assert b["status"] == "core_complete"
        route = list(map(tuple, b["route"]))
        assert route[0] == start and route[-1] == base and set(route) <= f
        assert all(abs(a[0]-z[0])+abs(a[1]-z[1]) == 1 for a,z in zip(route,route[1:]))
        assert t <= h | set(route)
        if label == "P1":
            branch_count += 1
            ds = distance(f, base)
            e = min(u, key=lambda v: (ds[v], v))
            assert list(e) == r["e"]
            end = b["phase1_end"]
            assert e not in route[:end+1] and u-{e} <= set(route[:end+1])
            left = set(u)
            last = None
            for v in route:
                if v in left:
                    left.remove(v)
                    last = v
            assert not left and last == e
    chosen = min(r["branches"], key=lambda k: (len(r["branches"][k]["route"]), k))
    assert r["selected"] == chosen and r["route"] == r["branches"][chosen]["route"]
    groups[(j["batch"], j["case_id"], j["repetition"])][j["method"]] = x

summary = {}
for (batch, case, rep), pair in groups.items():
    assert set(pair) == {"PPCPP", "LAST"}
    a, b = pair["PPCPP"]["raw"], pair["LAST"]["raw"]
    for field in ("route", "trace"):
        assert a["branches"]["P0"][field] == b["branches"]["P0"][field]
    if rep == 0:
        s = summary.setdefault(batch, dict(states=0, original=0, candidate=0, improved=0))
        s["states"] += 1
        s["original"] += len(a["route"])-1
        s["candidate"] += len(b["route"])-1
        s["improved"] += len(b["route"]) < len(a["route"])
assert len(groups) == 180 and branch_count == 174
assert summary["main36"] == dict(states=36, original=430, candidate=414, improved=8)
assert summary["supp24"] == dict(states=24, original=266, candidate=262, improved=2)
out = dict(verified=True, formal_outputs=360, paired_groups=180,
           alternative_routes=branch_count, summary=summary, new_solver_calls=0)
(H / "recheck_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
