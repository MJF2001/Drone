"""Freeze inputs before sequential runs; independently audit every delivered route."""
from pathlib import Path
import json,time,hashlib,sys
from dataclasses import replace
from collections import defaultdict
from scenarios import serialize,deserialize
from scenarios_unified import cases
from unified_geometry import UnifiedGeometry,single_cell_audit
from unified_candidates import solve_candidate
from model import Geometry
from audit import audit

D=Path(__file__).parent
OUT=D/'results'/'run_26_unified_new_maps'
METHODS=['P2_SHARED','STRIP_HV','TREE_MST']
BUDGETS=[.1,.5,5.0]

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def tests(items):
    s=items[0][0]
    a,b=s.current,s.base
    g=UnifiedGeometry(s);h=UnifiedGeometry(s)
    g.distance(a,b);h.distance(b,a)
    assert g.path(a,b)==h.path(a,b)
    assert g.path(a,b)==tuple(reversed(g.path(b,a))) or list(g.path(a,b))==list(reversed(g.path(b,a)))
    legacy=Geometry(s)
    for p in sorted(s.targets-s.covered)[::17]:
        assert g.distance(a,p)==len(legacy.path(a,p))-1
    for case,_ in items:
        route=UnifiedGeometry(case).expand(sorted(case.targets-case.covered))
        for test in (route,route[:-1],(case.current,case.base)):
            assert single_cell_audit(case,test)['valid']==audit(case,test)['valid']
    tiny=replace(s,targets=frozenset(sorted(s.targets-s.covered)[:8]),covered=frozenset(),old_route=())
    for method in METHODS:
        result=solve_candidate(tiny,method,.5,seed=42)
        assert audit(tiny,result['route'])['valid'],result
    assert len(items)==24 and len({s.name for s,_ in items})==24
    print('PASS canonical connectors, metric equivalence, 72 validator comparisons, 3 solver smoke tests, 24 scenarios',flush=True)

def main():
    items=list(cases());tests(items)
    if '--test-only' in sys.argv:return
    OUT.mkdir(parents=True,exist_ok=False)
    frozen=[{'snapshot':serialize(s,meta)} for s,meta in items]
    # serialize carries metadata; store separate metadata as well for explicit report use.
    for row,(_,meta) in zip(frozen,items):row['metadata']=meta
    write(OUT/'snapshots.json',frozen)
    sources=['unified_geometry.py','unified_candidates.py','scenarios_unified.py','run_unified.py',
             'bfs_metric_geometry.py','model.py','planners.py','audit.py','oarp_replan/tour.py','oarp_replan/ranks.py']
    hashes={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in sources}
    write(OUT/'protocol.json',{'budgets':BUDGETS,'repeats':2,'methods':METHODS,'cases':24,
        'executions':432,'reference':'P2_SHARED 20 seconds once per case; heuristic, not optimum',
        'source_sha256':hashes,'snapshot_sha256':hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest(),
        'timing':'cold cache; setup, common fallback, metric, search, candidate validation inside budget; external audit outside',
        'deadline':'cooperative soft deadline; report actual elapsed and >10ms overruns',
        'connector':'canonical unordered-pair A* tie policy, shared BFS metric',
        'scope':'new development parameters, not final held-out benchmark; 8 shared initial histories',
        'selection':'all cases retained; no tuning on this batch; algorithms unchanged except shared geometry and validation'})
    rows=[];begin=time.perf_counter()
    for i,(s,meta) in enumerate(items):
        for repeat in range(2):
            budgets=BUDGETS[repeat:]+BUDGETS[:repeat]
            for budget in budgets:
                offset=(i+repeat)%3
                methods=METHODS[offset:]+METHODS[:offset]
                if repeat:methods=list(reversed(methods))
                for method in methods:
                    r=solve_candidate(s,method,budget,seed=26000+10*i+repeat)
                    r.update(case=s.name,budget=budget,repeat=repeat,metadata=meta)
                    r['independent_audit']=audit(s,r['route'])
                    rows.append(r)
        write(OUT/'runs.json',rows)
        print(f'{i+1}/24 cases; {len(rows)}/432 runs; elapsed {time.perf_counter()-begin:.1f}s; invalid {sum(not r["independent_audit"]["valid"] for r in rows)}',flush=True)
    refs=[]
    for i,(s,meta) in enumerate(items):
        r=solve_candidate(s,'P2_SHARED',20,seed=26000+10*i)
        r.update(case=s.name,budget=20,metadata=meta,independent_audit=audit(s,r['route']))
        refs.append(r);write(OUT/'references.json',refs)
        print(f'reference {i+1}/24',flush=True)
    groups=defaultdict(list)
    for r in rows:groups[(r['budget'],r['algorithm'])].append(r)
    summary=[]
    lookup={(r['case'],r['repeat'],r['budget']):r for r in rows if r['algorithm']=='P2_SHARED'}
    for (budget,method),rs in sorted(groups.items()):
        diffs=[r['independent_audit']['length']-lookup[r['case'],r['repeat'],budget]['independent_audit']['length'] for r in rs]
        summary.append({'budget':budget,'method':method,'n':len(rs),
            'valid':sum(r['independent_audit']['valid'] for r in rs),
            'total_steps':sum(r['independent_audit']['length'] for r in rs),
            'total_seconds':sum(r['seconds'] for r in rs),'overruns':sum(r['overrun_gt_10ms'] for r in rs),
            'win_tie_loss_vs_P2':[sum(d<0 for d in diffs),sum(d==0 for d in diffs),sum(d>0 for d in diffs)]})
    write(OUT/'summary.json',summary)
    assert hashes=={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in sources}
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
