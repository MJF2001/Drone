"""Read-only audit of this stopped package, not experimental validation."""
from pathlib import Path
import ast, json, hashlib
H = Path(__file__).resolve().parent
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for p, h in read(H / 'old_v02_hashes.json').items(): assert sha(p) == h, p
    for x in read(H / 'source_manifest.json'):
        assert sha(x['source']) == x['source_sha256'], x['source']
        assert sha(x['target']) == x['target_sha256'], x['target']
    structure = read(H / 'worker_structure_check.json')
    assert structure['guard_matches_reviewed_proposal'] and structure['old_body_AST_equal_before_gate']
    old = H.parent / 'PPCPP侧向拓宽开发诊断_v0.2_20261021' / 'worker.py'
    text = old.read_text(encoding='utf8'); prefix = text[:text.index('assert Path(runtime.__file__).resolve()')]
    oldbody = ast.parse(text).body[len(ast.parse(prefix).body):]
    tree = ast.parse((H / 'worker.py').read_text(encoding='utf8'))
    mainnode = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    gate = ast.parse("require('technical')").body[0]
    newbody = list(mainnode.body)
    matches = [i for i, n in enumerate(newbody) if ast.dump(n) == ast.dump(gate)]
    assert len(matches) == 1; newbody.pop(matches[0])
    assert ast.dump(ast.Module(body=oldbody, type_ignores=[])) == ast.dump(ast.Module(body=newbody, type_ignores=[]))
    for x in read(H / 'preflight' / 'active_syntax.json')['active_files']:
        assert sha(x['path']) == x['sha256']; ast.parse(Path(x['path']).read_text(encoding='utf8')); assert x['passed']
    for name in ('runtime.py', 'candidate.py', 'p2_adapter.py'):
        assert (H / 'frozen_source_bytes' / name).read_bytes() == (H.parent / 'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020' / name).read_bytes()
    block = read(H / 'preflight' / 'SEAL_CREATION_CONTRACT_BLOCK.json')
    assert block['production_seal_not_attempted'] and block['real_entries'] == block['real_cores'] == 0
    f = H / 'preflight' / 'SYNTHETIC_NOT_EXPERIMENT_seal_collision'
    assert 'FileExistsError' in (f / 'stderr.log').read_text(encoding='utf8')
    assert read(f / 'synthetic_events.json')[-1]['real_planner_modules_loaded'] == []
    assert not (f / 'seal1.json').exists()
    assert not list((H / 'outputs').iterdir()) and not list((H / 'logs').iterdir()) and not list((H / 'receipts').iterdir())
    for name in ('actual_order.jsonl', 'seal1.json', 'seal2.json', 'states.json', 'stat_stub_results.json', 'binding_files.json'):
        assert not (H / name).exists(), name
    assert len(list((H / 'inputs').glob('*.json'))) == 6
    assert read(H / 'STOP.json')['hypothesis_result'] == 'NOT_TESTED'
    ledger = read(H / 'call_ledger.json')
    assert ledger['real_entries'] == ledger['real_cores'] == ledger['ordinary_graph_searches'] == 0
    slots = read(H / 'unrun_slots.json'); assert len(slots) == 306 and all(x['execution'] == 'NOT_RUN' for x in slots)
    for name, h in read(H / 'manifest.json').items(): assert sha(H / name) == h, name
    print('PASS upstream evidence/source hashes, exact guarded worker task AST after removing the one declared technical gate, syntax records and frozen reference bytes')
    print('PASS isolated actual-seal FileExistsError evidence, no planner imports in fixture, no production PASS/seal/order/results, all306 slots NOT_RUN')
    print('ALL PASS STOP-PACKAGE AUDIT ONLY; hypothesis NOT_TESTED; real entries/cores/graph searches=0', flush=True)
if __name__ == '__main__': main()
