"""Post-hoc completion check of ALL multi runs censored at 20s; no tuning."""
from pathlib import Path
import json,hashlib
from scenarios import deserialize
from p2_search_audit import solve
from unified_candidates import solve_candidate
from audit import audit
D=Path(__file__).parent;O=D/'results/run_29b_p2_search_audit_20261012'
rs=json.loads((O/'runs.json').read_text(encoding='utf-8'))
selected=[r for r in rs if r['batch']=='new' and r['variant']=='multi' and r['budget']==20 and r['status']=='deadline']
frozen=json.loads((D/'results/run_26_unified_new_maps/snapshots.json').read_text(encoding='utf-8'))
snaps={r['snapshot']['name']:(i,deserialize(r['snapshot'])) for i,r in enumerate(frozen)}
target=O/'followup60.json';assert not target.exists()
(O/'followup60_protocol.json').write_text(json.dumps(dict(reason='all four 20s multi timeouts, selected after main results; completion diagnosis only',
    budget=60,selected=[(r['case'],r['repeat']) for r in selected],runs_sha256=hashlib.sha256((O/'runs.json').read_bytes()).hexdigest()),ensure_ascii=False,indent=2),encoding='utf-8')
out=[]
for k,r in enumerate(selected):
    i,s=snaps[r['case']]
    for method in ('multi','TREE'):
        a=solve(s,60,method,29000+10*i+r['repeat']) if method=='multi' else solve_candidate(s,'TREE_MST',60,29000+10*i+r['repeat'])
        a.update(case=s.name,repeat=r['repeat'],budget=60,variant=method,independent_audit=audit(s,a['route']))
        out.append(a)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'followup {k+1}/{len(selected)} '+str([(a['variant'],a['status'],a['independent_audit']['length'],round(a['seconds'],2)) for a in out[-2:]]),flush=True)
