from pathlib import Path
import json,hashlib,time
from scenarios import deserialize
from audit import audit
from unified_candidates import solve_candidate
from p2_search_audit import solve

D=Path(__file__).parent;O=D/'results/run_29b_p2_search_audit_20261012'
def write(n,o):(O/n).write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    old=D/'results/run_20_new_structure_comparison/snapshots.json';new=D/'results/run_26_unified_new_maps/snapshots.json'
    batches={k:[deserialize(r.get('snapshot',r)) for r in json.loads(p.read_text(encoding='utf-8'))] for k,p in [('old',old),('new',new)]}
    # Regression under generous time: instrumentation preserves base route behaviour.
    for s in batches['old'][:1]+batches['new'][::11]:
        a=solve(s,20,'base8',0);b=solve_candidate(s,'P2_SHARED',20,0)
        assert a['route']==b['route'],s.name
    O.mkdir(parents=True,exist_ok=False)
    files=[old,new]+[D/p for p in ['p2_search_audit.py','run_p2_search_audit.py','unified_geometry.py','bfs_metric_geometry.py','model.py','planners.py','unified_candidates.py']]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    write('protocol.json',dict(hashes=hashes,new='24 states x budgets 5/10/20 x 2 repeats x base8/deep128/multi/TREE =576',
        old='24 states x 5s x base8/deep128 once=48',regression='4 exact-route equality checks at 20s',
        multi='complete base8 first and retain all incumbents; 120 additional passes per core seed; then reverse H/V, four segment reversals H/V, two random permutations; 32 passes each',
        supersedes='run_29 interrupted after protocol review: deeper replacement could lose original baseline incumbent; partial data excluded',
        limitations='extra search is a conventional stronger baseline, not innovation; two repeats not independent maps',
        timing='cold cache, all setup and validation inside cooperative deadline, independent audit outside',
        partial='only completed optimization sequences expanded, no free post-deadline candidate accepted'))
    rows=[];begin=time.perf_counter()
    for batch,ss in batches.items():
        for i,s in enumerate(ss):
            repeats=range(2) if batch=='new' else range(1)
            budgets=[5,10,20] if batch=='new' else [5]
            methods=['base8','deep128','multi','TREE'] if batch=='new' else ['base8','deep128']
            for repeat in repeats:
                order=budgets[repeat:]+budgets[:repeat]
                for budget in order:
                    offset=(i+repeat)%len(methods)
                    for method in methods[offset:]+methods[:offset]:
                        r=(solve_candidate(s,'TREE_MST',budget,29000+10*i+repeat)
                            if method=='TREE' else solve(s,budget,method,29000+10*i+repeat))
                        r.update(batch=batch,case=s.name,budget=budget,repeat=repeat,variant=method)
                        r['independent_audit']=audit(s,r['route']);rows.append(r)
            write('runs.json',rows)
            print(f'{batch} {i+1}/24; {len(rows)}/624 runs; {time.perf_counter()-begin:.1f}s; invalid {sum(not r["independent_audit"]["valid"] for r in rows)}',flush=True)
    assert hashes=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in hashes}
    write('completion.json',dict(runs=len(rows),valid=sum(r['independent_audit']['valid'] for r in rows),hashes_unchanged=True))
if __name__=='__main__':main()
