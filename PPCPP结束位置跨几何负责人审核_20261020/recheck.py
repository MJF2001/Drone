"""Reviewer replay: all exact queries plus separately coded D4 shape grouping."""
import hashlib
import importlib.util
import json
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parent
S = R / "PPCPP结束位置跨几何验证_v0.1_20261020"
spec = importlib.util.spec_from_file_location("independent_review", S / "independent.py")
solver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solver)

def read(p):
    return json.loads(p.read_text(encoding="utf-8"))

def shape(c):
    targets = set(map(tuple, c["published_targets"]))
    blocked = targets - set(map(tuple, c["free"]))
    variants = []
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                def transform(points):
                    return {(sx * (y if swap else x), sy * (x if swap else y)) for x, y in points}
                t, b = transform(targets), transform(blocked)
                ax, ay = min(x for x, y in t), min(y for x, y in t)
                variants.append((tuple(sorted((x-ax, y-ay) for x, y in t)),
                                 tuple(sorted((x-ax, y-ay) for x, y in b))))
    return min(variants)

rows = []
for p in sorted((S / "exact").glob("*/*.request.json")):
    q = read(p)["request"]
    result_path = p.with_name(p.name.replace(".request.json", ".json"))
    result = read(result_path)
    value = solver.oracle(set(map(tuple, q["free"])), tuple(q["start"]),
                          tuple(q["base"]), set(map(tuple, q["targets"])),
                          tuple(q["last"]) if q["last"] is not None else None)
    assert result["status"] == "optimal" and value == result["length"]
    rows.append(dict(case=p.parent.name, query=result_path.stem, length=value,
                     result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest()))
assert len(rows) == 93
cases = {p.stem: read(p) for p in (S / "inputs").glob("*.json")}
analysis = read(S / "analysis.json")["states"]
keys = {name: shape(c) for name, c in cases.items()}
for a in analysis:
    for b in analysis:
        assert (keys[a["id"]] == keys[b["id"]]) == (a["shape_group"] == b["shape_group"])
old_keys = {shape(read(p)) for p in (R / "PPCPP小图最优差距诊断_v0.2_20261020/inputs").glob("*.json")}
positive = [r for r in analysis if r.get("E", 0) > 0]
assert len(positive) == 8
assert len({keys[r["id"]] for r in positive}) == 4
assert {r["family"] for r in positive} == {"L", "Z"}
assert all(keys[r["id"]] not in old_keys for r in positive)
bad = [r for r in analysis if r.get("near_minus_L0", 0) > 0]
assert len(bad) == 5 and all(r["d_emin"] < r["d_e0"] for r in bad)
assert sum(r["G"] for r in analysis) == 28
assert sum(r.get("E", 0) for r in analysis) == 26
assert sum(r.get("R", 0) for r in analysis) == 2
out = dict(verified=True, reviewer_exact_replays=93, independent_shape_groups=len(set(keys.values())),
           positive_states=8, positive_shape_groups=4, positive_families=["L", "Z"],
           strictly_nearer_but_worse=5, queries=rows,
           scope="Reviewer replay, not new formal samples or performance data")
(H / "recheck_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k != "queries"}, ensure_ascii=False))
