"""Frozen crossed development diagnosis, not final held-out validation."""
from pathlib import Path
import json,time,hashlib
import oarp_replan
from scenarios import deserialize
from model import Geometry
from bfs_metric_geometry import BFSMetricGeometry
from unified_geometry import UnifiedGeometry
from unified_candidates import solve_candidate,metric_tree,preorder
from structure_candidates import solve_candidate as historical
from planners import candidates,nearest,two_opt,sequence_cost
from audit import audit

D=Path(__file__).parent;O=D/'results'/'run_28_rank_ablation_20261012'
M=['P2_SHARED','STRIP_HV','TREE_MST']
def write(n,o): (O/n).write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    O.mkdir(exist_ok=False,parents=True)
    inputs={'old':D/'results/run_20_new_structure_comparison/snapshots.json',
            'new':D/'results/run_26_unified_new_maps/snapshots.json'}
    batches={b:[deserialize(r.get('snapshot',r)) for r in json.loads(p.read_text(encoding='utf-8'))] for b,p in inputs.items()}
    sources=['run_rank_ablation.py','unified_candidates.py','structure_candidates.py','model.py',
             'bfs_metric_geometry.py','unified_geometry.py','planners.py','audit.py','oarp_replan/tour.py']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(inputs.values())+[D/x for x in sources]}
    write('protocol.json',{'hashes':hashes,'batches':{b:len(ss) for b,ss in batches.items()},
        'cross':'48 states x 2 connector policies x 3 methods x 2 budgets (.1,5) x 2 repeats = 1152',
        'distance':'48 states x P2 x 2 metrics (A*, BFS) x 5s x 1 repeat = 96',
        'anchor':'old 24 states x original 3 methods x 5s x 1 repeat = 72',
        'initialization':'48 states x 5 seeds (H,V,NN,two tree orders), before/after same 8-pass 2opt; no deadline',
        'restrictions':'batch comparison bundles size, obstacle, progress, scan axis; cannot attribute one geometric factor',
        'seed':'same 28000+case_index*10+repeat for all connector variants; serial rotated execution',
        'validation':'independent audit every route; no parameter tuning; developmental post-hoc causal diagnosis'})
    rows=[];begin=time.perf_counter()
    for i,(batch,s) in enumerate((b,s) for b,ss in batches.items() for s in ss):
        for repeat in (0,1):
            for budget in ((.1,5) if repeat==0 else (5,.1)):
                order=[('legacy_ties',BFSMetricGeometry),('canonical_ties',UnifiedGeometry)]
                if (i+repeat)%2:order.reverse()
                for label,cls in order:
                    methods=M[(i+repeat)%3:]+M[:(i+repeat)%3]
                    for method in methods:
                        r=solve_candidate(s,method,budget,28000+i*10+repeat,geometry_class=cls)
                        r.update(batch=batch,case=s.name,repeat=repeat,budget=budget,variant=label,phase='cross')
                        r['independent_audit']=audit(s,r['route']);rows.append(r)
        # Shared validation/algorithm; only metric implementation changes. Ties preserved.
        for label,cls in [('astar_metric',Geometry),('bfs_metric',BFSMetricGeometry)]:
            r=solve_candidate(s,'P2_SHARED',5,28000+i*10,geometry_class=cls)
            r.update(batch=batch,case=s.name,repeat=0,budget=5,variant=label,phase='distance')
            r['independent_audit']=audit(s,r['route']);rows.append(r)
        if batch=='old':
            for method in M:
                r=historical(s,method,5,3000+i)
                r.update(batch=batch,case=s.name,repeat=0,budget=5,variant='original_code',phase='anchor')
                r['independent_audit']=audit(s,r['route']);rows.append(r)
        write('runs.json',rows)
        print(f'case {i+1}/48; {len(rows)} runs; elapsed {time.perf_counter()-begin:.1f}s; invalid {sum(not r["independent_audit"]["valid"] for r in rows)}',flush=True)
    seeds=[]
    for i,(batch,s) in enumerate((b,s) for b,ss in batches.items() for s in ss):
        for label in ('H_scan','V_scan','nearest','tree_forward','tree_reverse'):
            start=time.perf_counter();g=UnifiedGeometry(s)
            demand=s.targets-s.covered-g.views[s.current]
            if label in ('H_scan','V_scan'):points=candidates(g,demand,label[0])
            elif label=='nearest':points=nearest(g,sorted(demand))
            else:
                children,_=metric_tree(g);points=preorder(children,s.current,label=='tree_reverse')
            preparation=time.perf_counter()-start
            for stage in ('before','after'):
                t=time.perf_counter();visits=points if stage=='before' else two_opt(g,points,max_passes=8)
                route=g.expand(visits);check=audit(s,route)
                seeds.append(dict(batch=batch,case=s.name,seed=label,stage=stage,route=route,
                    preparation_seconds=preparation,stage_seconds=time.perf_counter()-t,
                    sequence_cost=sequence_cost(g,visits),independent_audit=check))
        write('initializations.json',seeds)
        print(f'initialization {i+1}/48',flush=True)
    assert hashes=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in hashes}
    write('completion.json',{'runs':len(rows),'initialization_routes':len(seeds),
        'valid_runs':sum(r['independent_audit']['valid'] for r in rows),
        'valid_initializations':sum(r['independent_audit']['valid'] for r in seeds),'hashes_unchanged':True})
if __name__=='__main__':main()
