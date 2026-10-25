"""Read-only second-algorithm replay of all sealed exact requests."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / "PPCPP小图最优差距诊断_v0.2_20261020"
spec = importlib.util.spec_from_file_location("review_independent", SOURCE / "independent.py")
independent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(independent)

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

rows = []
for path in sorted((SOURCE / "exact").glob("*/*.request.json")):
    request = read(path)["request"]
    result_path = path.with_name(path.name.replace(".request.json", ".json"))
    result = read(result_path)
    case = read(SOURCE / "inputs" / (path.parent.name + ".json"))
    assert request["base"] == case["base"]
    assert set(map(tuple, request["free"])) == set(map(tuple, case["free"]))
    length = independent.oracle(
        set(map(tuple, request["free"])),
        tuple(request["start"]),
        tuple(request["base"]),
        set(map(tuple, request["targets"])),
        tuple(request["last"]) if request["last"] is not None else None,
    )
    assert result["status"] == "optimal" and length == result["length"], path
    rows.append(dict(case=path.parent.name, query=result_path.stem,
                     independently_recomputed_length=length,
                     source_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest()))
    print(path.parent.name, result_path.stem, length, flush=True)

assert len(rows) == 64
output = dict(
    verified=True, exact_rechecks=64,
    method="Existing independent frozenset-state Dijkstra, newly executed on every formal query",
    scope="Reviewer replay only; not additional formal samples or performance runs",
    rows=rows,
)
(HERE / "recheck_results.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("ALL 64 INDEPENDENT RECHECKS PASSED", flush=True)
