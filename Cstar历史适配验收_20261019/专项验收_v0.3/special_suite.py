"""Fixed, bounded correctness protocol. No timing or route-quality ranking."""
import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
from history_adapter import solve
def hole_cases():
    f={(-1,0),(0,0),(1,0),(0,-1)};ring={(x,y) for x in range(-2,3) for y in range(-2,2)}-f
    rows=[]
    for name,omitted,expected in [('goal',{(-2,1)},1),('start',{(-1,-2)},2),('free',set(),3)]:
        rows.append(dict(name='hole_'+name,free=sorted(f),targets=sorted(f),covered=[],current=(0,0),base=(0,0),published_targets=sorted(f),known_blocked=sorted(ring-omitted),distance_budget=100,expected_hole_case=expected))
    return rows
def boundary_specs():
    h=hole_cases()[2]
    simple=dict(name='line_boundary',free=[(0,0),(1,0),(2,0)],targets=[(1,0),(2,0)],covered=[],current=(0,0),base=(0,0),distance_budget=100)
    empty=dict(name='return_boundary',free=[(0,0),(1,0),(2,0)],targets=[],covered=[],current=(2,0),base=(0,0),distance_budget=100)
    specs=[]
    for phase in ['rcg_sample','rcg_expand','task_protection','rcg_search','rcg_essential','rcg_prune_edges','bfs_path','bfs_expand','bfs_reconstruct','move_before','move_after','densify','tsp_costs','tsp_nn','tsp_2opt','return_before','return_bfs','final_audit','result_ready']:
        c=h if phase in ['densify','tsp_costs','tsp_nn','tsp_2opt'] else empty if phase in ['return_bfs','final_audit','result_ready'] else simple
        for relation,instant in [('before',2-1e-6),('exact',2),('after',2+1e-6)]:specs.append(dict(phase=phase,relation=relation,instant=instant,input=c))
    return specs
def execute_boundary(spec):
    value=[0.0];hits=[];armed=[False]
    def hook(stage):
        if stage=='return_before':armed[0]=True
        match=stage==spec['phase'] or (spec['phase']=='return_bfs' and stage=='bfs_expand' and armed[0])
        if match:value[0]=spec['instant'];hits.append(stage)
    result=solve(spec['input'],2,7,clock=lambda:value[0],checkpoint_hook=hook)
    return dict(phase=spec['phase'],relation=spec['relation'],hits=hits,result=result)
def main():
    out=ROOT/'evidence';out.mkdir(exist_ok=True)
    if (out/'results.json').exists():raise RuntimeError('Do not overwrite evidence')
    old=ROOT.parent/'修正版_v0.2'
    base=[]
    for path in ('micro_evidence/inputs.json','regression_evidence/inputs.json'):
        base+=json.loads((old/path).read_text(encoding='utf8'))
    holes=hole_cases();boundaries=boundary_specs()
    protocol=dict(base_inputs=base,hole_inputs=holes,boundary_specs=boundaries,seed=7,budget=2,max_iterations=400,ranking=False,holdout=False)
    (out/'protocol.json').write_bytes(json.dumps(protocol,ensure_ascii=False,indent=2).encode())
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime').rglob('*.py')}
    for p in (Path(__file__),out/'protocol.json'):files[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'pre_run_manifest.json').write_bytes(json.dumps(dict(files=files,scope='29 real-clock fixtures + 57 deterministic boundary calls; no performance ranking'),ensure_ascii=False,indent=2).encode())
    rows=[]
    for c in base+holes:
        result=solve(c,2,7);rows.append(dict(kind='functional',input=c,result=result));print(c['name'],result['status'],flush=True)
    for spec in boundaries:
        row=execute_boundary(spec);rows.append(dict(kind='boundary',input=spec['input'],**row));print(spec['phase'],spec['relation'],row['result']['status'],len(row['hits']),flush=True)
    (out/'results.json').write_bytes(json.dumps(rows,ensure_ascii=False,indent=2).encode())
if __name__=='__main__':main()
