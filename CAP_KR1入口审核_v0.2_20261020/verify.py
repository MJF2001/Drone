"""Read-only source, deadline eligibility, ledger and saved-result checks."""
import json,hashlib
from pathlib import Path
from audit import audit
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(Path(f))==h,f
    prior=Path(p['prior_failed_version'])
    for f in (H/'runtime').glob('*.py'):
        assert sha(f)==sha(prior/'runtime'/f.name)==sha(H.parent/'CAP完整接续候选_v0.1_20261020/runtime'/f.name)
    assert sha(H/'entry.py')==sha(prior/'entry.py')
    gates=read(H/'gates.json');assert len(gates)==28
    invalid={x['name'] for x in p['invalid']};assert len(invalid)==19
    calls=0
    def check(x):
        nonlocal calls
        e=x['entry'];calls+=int(e['solver_called']);r=e['result']
        if r is not None:assert audit(x['input'],r)==x['check']
        assert bool(e['accepted_route'])==bool(e['eligible'])
        if e['eligible']:
            assert e['entry_status']=='returned' and e['entry_seconds']<e['budget'] and r['status']=='complete'
            assert e['accepted_route']==r['route']
        else:assert e['accepted_route']==[]
    for x in gates:
        check(x);e=x['entry'];name=x['name']
        if name in invalid or name.startswith('bad_budget_'):assert e['entry_status']=='invalid_input' and not e['solver_called']
        elif name.startswith('outer_deadline_'):
            assert not e['eligible']
            if name.endswith(('after_solve','after_serialize')):assert e['result']['status']=='complete' and e['entry_status']=='entry_late'
            else:assert e['entry_status']=='entry_deadline_before_solve' and not e['solver_called']
        elif name=='solver_interrupt_after_actual_move':assert e['result']['status']=='deadline' and e['result']['distance']==1 and not e['eligible']
        elif name=='distance_limit_zero':assert e['result']['status']=='resource_exceeded' and not e['eligible']
        else:assert name=='normal_entry' and e['eligible']
    roads=read(H/'roads.json');assert len(roads)==20
    jobs={j['case_id']:j for j in p['roads']};assert {x['case_id'] for x in roads}==set(jobs)
    for x in roads:
        check(x);j=jobs[x['case_id']]
        assert x['input']==read(Path(j['input']))
        old=read(Path(j['old_result']))[j['old_index']]['result'];new=x['entry']['result']
        assert {k:v for k,v in old.items() if k!='seconds'}=={k:v for k,v in new.items() if k!='seconds'}
        assert x['same_except_seconds'] and x['entry']['eligible'] and x['independent_call_seconds']<20
        assert x['independent_call_seconds']>=x['entry']['entry_seconds']
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,entry_gate_calls=28,invalid_requests=19,road_calls=20,solver_calls=calls,semantic_clearance='adapted variant only; not original CAP',sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
