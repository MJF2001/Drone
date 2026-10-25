"""Deterministic synthetic clock boundary tests, separate from wall-clock roads."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'))
from planners import solve
from audit import audit
f={(x,y) for x in range(5) for y in range(4)};h={(2,y) for y in range(4)}
c=dict(name='deadline_split_history',free=sorted(f),targets=sorted(f),covered=sorted(h),current=[0,0],base=[0,0],published_targets=sorted(f),distance_budget=1000)
out=HERE/'deadline_evidence';assert not out.exists();out.mkdir()
rows=[]
for method in ('TRACE','CAP'):
    seen=[]
    base=solve(c,method,1,clock=lambda:0,checkpoint_hook=lambda s:seen.append(s))
    assert base['status']=='complete';audit(c,base)
    stages=sorted(set(seen))
    for stage in stages:
        for relation,value in [('before',1-1e-6),('equal',1),('after',1+1e-6)]:
            state={'time':0,'hit':False}
            def hook(s):
                if s==stage and not state['hit']:state.update(time=value,hit=True)
            r=solve(c,method,1,clock=lambda:state['time'],checkpoint_hook=hook)
            assert state['hit'];assert r['status']==('complete' if relation=='before' else 'deadline')
            check=audit(c,r);name=f'{method}__{stage}__{relation}'
            (out/(name+'.json')).write_text(json.dumps(r,ensure_ascii=False),encoding='utf-8')
            rows.append(dict(name=name,stage=stage,relation=relation,**check))
    (out/(method+'_stage_coverage.json')).write_text(json.dumps(stages),encoding='utf-8')
(out/'input.json').write_text(json.dumps(c),encoding='utf-8')
(out/'checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'manifest.json').write_text(json.dumps({str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'deadline_gates.py',HERE/'audit.py',*sorted((HERE/'runtime').glob('*.py'))]},indent=2),encoding='utf-8')
print(json.dumps(dict(total=len(rows),all_pass=True,by_method={m:sum(x['name'].startswith(m) for x in rows) for m in ('TRACE','CAP')})))
