"""Read-only completed-experiment verification; never import planner/native/runtime."""
from analyze import *
from stage_control import require,require_preseal
import sys,csv,ast
def checkcsv(name,rows):
    with (H/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(dict,list,tuple)) else '' if r.get(k) is None else str(r.get(k)) for k in keys} for r in rows];assert actual==expected,name
def verify():
    seal=require_preseal();assert sha(sys.executable)==seal['python_executable_sha256']
    for path,h in seal['files'].items():assert sha(path)==h,path
    for stage in ('static','prepare_fixtures','preseal','stubs','gate','formal'):require(stage)
    if (H/'manifest.json').exists():
        for path,h in read(H/'manifest.json').items():assert sha(H/path)==h,path
    for copy in read(H/'copy_manifest.json'):
        assert sha(copy['source'])==copy['source_sha256'] and sha(copy['target'])==copy['target_sha256']
        if copy['kind']=='required_exact_binary':assert Path(copy['source']).read_bytes()==Path(copy['target']).read_bytes()
    fixtures=read(H/'prep_fixture_results.json');assert fixtures['passed'] and len(fixtures['tests'])==2
    mismatch,equal=fixtures['tests'];assert mismatch['exit_code']!=0 and not mismatch['preseal_exists'] and not mismatch['sentinel_executed'] and equal['exit_code']==0 and equal['preseal_exists'] and equal['sentinel_executed']
    assert not (H/'fixtures/mismatch/preseal.json').exists() and not (H/'fixtures/mismatch/next_stage_sentinel.txt').exists()
    stubs=read(H/'stub_results.json');assert stubs['passed'] and len(stubs['tests'])==8 and stubs['real_core_calls']==stubs['real_planner_entries']==0
    old=(R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_text(encoding='utf8');new=(H/'native_probe.py').read_text(encoding='utf8')
    loop=lambda s:next(n for n in ast.walk(ast.parse(s)) if isinstance(n,ast.While));assert ast.dump(loop(old),include_attributes=False)==ast.dump(loop(new),include_attributes=False)
    calls=[n for n in ast.walk(ast.parse(new)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='force_history_step'];assert len(calls)==1 and calls[0].lineno<loop(new).lineno
    a=compute();assert a==read(H/'analysis.json') and a['audits']==read(H/'all_decision_audits.json');g=compute('gate');assert g==read(H/'gate_analysis.json')
    order=read(H/'fixed_order.json');actual=[json.loads(line) for line in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert [j['id'] for j in order]==[j['id'] for j in actual] and len(actual)==24
    assert len(a['equivalence'])==6 and len(a['pairs'])==6 and len(a['rows'])==24 and not (H/'STOP.json').exists()
    for j in order:
        x=read(H/'outputs'/f'{j["id"]}.json');rec=read(H/'logs'/f'{j["id"]}.receipt.json');assert rec['output_sha256']==sha(H/'outputs'/f'{j["id"]}.json') and rec['exit_code']==0
        assert len(x['actual_core_calls'])==1 and x['actual_core_calls'][0]['end']>=x['actual_core_calls'][0]['begin'];assert 0<x['actual_core_calls'][0]['native_budget']<=20;assert x['result']['budget']==20 and set(x['result']['raw']['branches'])=={'P0'}
        for path,h in x['imports'].items():assert seal['files'][path]==h==sha(path)
        assert set(x['runtime_reads'])<={str(H/j['input']),str(H/'actions.json')}
        if j['mode']=='ON':
            native=x['result']['raw']['branches']['P0'];z=native['intervention'];assert z['trigger_count']==1 and z['deadline']>x['actual_core_calls'][0]['begin'] and z['deadline']<=x['actual_core_calls'][0]['begin']+20
        else:assert 'intervention' not in x['result']['raw']['branches']['P0'] and all(e['kind']!='forced_history_step' for e in x['result']['raw']['trace'])
    checkcsv('24调用完整指标.csv',a['rows']);checkcsv('6正式配对.csv',a['pairs']);checkcsv('2状态三种子原值均值范围.csv',a['states'])
    print('PASS frozen/v0.1/source/environment/preseal hashes, exact binary copies, intended minimal diff, hash-bound stage receipts',flush=True)
    print('PASS 2 preparation fixtures (expected negative blocked mock seal/sentinel), 8 intervention stubs; no real calls in these tests',flush=True)
    print('PASS exactly24 ordered entries/24 cores: 12 OFF equality gate +12 fresh formal calls; full route/trace/options/scores/non-time fields match frozen historical controls',flush=True)
    print('PASS saved local rewards/tie, recovery nearest graph targets/literal shortest segments, one forced step, pending/previous/distance/deadline, full-route independent dual metrics, rejoin facts, CSV/means/ranges and stop verdict',flush=True)
    print(json.dumps(dict(status='ALL PASS COMPLETED EXPERIMENT',ordinary_BFS_full_analysis=a['ordinary_BFS_total'],ordinary_BFS_gate_recheck=g['ordinary_BFS_total'],ordinary_BFS_this_verify=a['ordinary_BFS_total']+g['ordinary_BFS_total'],new_planner_calls=0,new_coverage_exact=0,verdict=a['stop_verdict']),ensure_ascii=False),flush=True)
if __name__=='__main__':verify()
