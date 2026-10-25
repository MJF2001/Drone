"""Reviewer read-only semantic and timing recomputation; no solver imports."""
import json
import statistics
from collections import defaultdict, Counter
from pathlib import Path

H = Path(__file__).resolve().parent
S = H.parent / "PPCPP_LAST距离查询等价提速_v0.2_20261020"
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
def semantic(raw):
    r = json.loads(json.dumps(raw))
    r.pop("version", None)
    for k in ("seconds", "accepted_seconds", "budget", "overrun_gt_10ms"):
        r["branches"]["P0"].pop(k, None)
    if "P1" in r["branches"]:
        r["branches"]["P1"].pop("accepted_seconds", None)
    return r
groups = defaultdict(dict)
times = defaultdict(list)
hashes = defaultdict(set)
for p in sorted((S/"execution").glob("*.json")):
    x = read(p)
    j = x["job"]
    assert x["eligible"] and x["raw"]["status"] == "core_complete" and x["entry_seconds"] < 20
    groups[j["case_id"], j["repetition"]][j["method"]] = x
    times[j["method"]].append(x["entry_seconds"])
    for file, digest in x["production_sources"].items():
        hashes[file].add(digest)
assert len(groups) == 270 and all(len(v) == 1 for v in hashes.values())
totals = Counter()
paired_faster = 0
for (case, rep), pair in groups.items():
    assert set(pair) == {"PPCPP", "LAST_V1", "LAST_V2"}
    a, b = pair["LAST_V1"], pair["LAST_V2"]
    assert semantic(a["raw"]) == semantic(b["raw"])
    paired_faster += b["entry_seconds"] < a["entry_seconds"]
    for label in ("LAST_V1", "LAST_V2"):
        for field in ("route", "trace"):
            assert pair[label]["raw"]["branches"]["P0"][field] == pair["PPCPP"]["raw"]["branches"]["P0"][field]
    if rep == 0:
        for label, x in pair.items():
            totals[label] += len(x["raw"]["route"])-1
        totals["improved"] += len(b["raw"]["route"]) < len(pair["PPCPP"]["raw"]["route"])
assert totals == Counter(PPCPP=5530, LAST_V1=5476, LAST_V2=5476, improved=27)
assert paired_faster == 266
inventory = read(S/"imported_dependency_inventory.json")
missing = inventory["optional_package_files_without_individual_preseal"]
assert len(missing) == 90
v1 = (S/"candidate_v1.py").read_text(encoding="utf-8")
v2 = (S/"candidate_v2.py").read_text(encoding="utf-8")
assert v2 == v1.replace("PPCPP_LAST_RESERVE_v0.1", "PPCPP_LAST_RESERVE_v0.2").replace("full.distance(q,s.base)", "full.distance(s.base,q)")
means = {k: statistics.mean(v)*1000 for k,v in times.items()}
out = dict(verified=True, calls=sum(map(len,times.values())), semantic_pairs=270,
           p0_pairs=540, mean_ms=means, v1_over_v2=means["LAST_V1"]/means["LAST_V2"],
           v2_over_ppcpp=means["LAST_V2"]/means["PPCPP"],
           v2_faster_pairs=paired_faster, totals=dict(totals),
           critical_file_hashes_consistent=True, optional_files_missing_preseal=90,
           optional_package_paths=sorted(set(str(Path(p).parent) for p in missing)),
           new_solver_calls=0)
(H/"recheck_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k!="optional_package_paths"},ensure_ascii=False))
