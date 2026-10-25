"""Read-only reconstruction of saved calls. No planner or diagnostic-native import."""
from analyze import *
import sys,csv,ast,difflib
def checkcsv(name,rows):
    with (H/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(dict,list,tuple)) else '' if r.get(k) is None else str(r.get(k)) for k in keys} for r in rows];assert actual==expected,name
def verify():
    seal=read(H/'preseal.json');assert seal['complete'] and sha(sys.executable)==seal['python_executable_sha256']
    for p,h in seal['files'].items():assert sha(p)==h,p
    if (H/'manifest.json').exists():
        for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    assert read(H/'stub_results.json')['passed'] and len(read(H/'stub_results.json')['tests'])==8 and read(H/'stub_results.json')['real_core_calls']==0
    # Structural audit: one pre-loop hook, original while loop and scoring untouched.
    old=(R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_text(encoding='utf8');new=(H/'native_probe.py').read_text(encoding='utf8')
    def loop(code):return next(n for n in ast.walk(ast.parse(code)) if isinstance(n,ast.While))
    assert ast.dump(loop(old),include_attributes=False)==ast.dump(loop(new),include_attributes=False)
    calls=[n for n in ast.walk(ast.parse(new)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='force_history_step'];assert len(calls)==1 and calls[0].lineno<loop(new).lineno
    assert (H/'candidate.py').read_bytes()==(P/'candidate.py').read_bytes()
    a=compute();assert a==read(H/'analysis.json') and a['audits']==read(H/'all_decision_audits.json');assert compute('gate')==read(H/'gate_analysis.json')
    order=read(H/'fixed_order.json');actual=[json.loads(line) for line in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert [j['id'] for j in order]==[j['id'] for j in actual] and len(actual)==24
    assert len(a['equivalence'])==6 and len(a['pairs'])==6 and len(a['rows'])==24 and not (H/'STOP.json').exists()
    for j in order:
        x=read(H/'outputs'/f'{j["id"]}.json');rec=read(H/'logs'/f'{j["id"]}.receipt.json');assert rec['output_sha256']==sha(H/'outputs'/f'{j["id"]}.json') and rec['exit_code']==0
        assert len(x['actual_core_calls'])==1 and x['actual_core_calls'][0]['end']>=x['actual_core_calls'][0]['begin'];assert x['result']['budget']==20 and set(x['result']['raw']['branches'])=={'P0'}
        for p,h in x['imports'].items():assert seal['files'][p]==h==sha(p)
        allowed={str(H/j['input']),str(H/'actions.json')};assert set(x['runtime_reads'])<=allowed
    for case in CASES:
        assert sha(H/'inputs'/f'{case}.json')==sha(S/'inputs'/f'{case}.json');action=read(H/'actions.json')[case];assert action['current']==[5,2] and action['previous']==[4,2] and action['next']==[5,1] and action['max_trigger']==1
    checkcsv('24调用完整指标.csv',a['rows']);checkcsv('6正式配对.csv',a['pairs']);checkcsv('2状态三种子原值均值范围.csv',a['states'])
    print('PASS pre-run source/input/action/environment hashes and untouched frozen sources; exactly24 ordered entries/24 cores, no retries',flush=True)
    print('PASS 8 saved stub checks, 12 OFF gate calls identical to frozen/history except seven explicit timing fields; 12 fresh formal calls and no control drift',flush=True)
    print('PASS all saved decisions independently: local rewards/tie, recovery closest graph-distance targets, literal recovery/return shortestness, one forced history step, pending/direction/resource, full-route dual metrics',flush=True)
    print('PASS all JSON/CSV, seed means/ranges, signed cost identity, state-rejoin facts and fixed stop criterion; no planner invoked by verify',flush=True)
    print(json.dumps(dict(status='ALL PASS',ordinary_BFS_full_analysis=a['ordinary_BFS_total'],ordinary_BFS_gate_recheck=read(H/'gate_analysis.json')['ordinary_BFS_total'],ordinary_BFS_this_verify=a['ordinary_BFS_total']+read(H/'gate_analysis.json')['ordinary_BFS_total'],new_planner_calls=0,new_coverage_exact=0,verdict=a['stop_verdict']),ensure_ascii=False),flush=True)
if __name__=='__main__':verify()
