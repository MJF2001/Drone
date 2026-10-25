"""Locate exact existing coverage-induced CAP split, no planning calls."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def points(x):return set(map(tuple,x))
def components(cells):
    left=set(cells);out=[]
    while left:
        p=min(left);left.remove(p);part={p};q=[p]
        while q:
            x,y=q.pop()
            for v in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if v in left:left.remove(v);part.add(v);q.append(v)
        out.append(part)
    return out
def main():
    protocol=read(HERE/'protocol.json')
    for f,h in protocol['files'].items():assert sha(Path(f))==h,f
    jobs=protocol['saved_CAP_jobs'];batch=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';missing=[];splits=[]
    for j in jobs:
        c=read(Path(j['input']));missing.append(dict(run_id=j['run_id'],case=j['case_id'],has_resume_target=any(k in c for k in ('tau_target','resume_target','cap_state'))))
        if j['case_id']!='case10':continue
        r=read(batch/'execution/results'/(j['run_id']+'.json'))['raw'];first=r['plans'][0];second=r['plans'][1];path=list(map(tuple,r['diagnostic_route']))
        before_nodes={n['id']:n for n in first['structure_before']['nodes']};remaining=points(before_nodes[second['region_id']]['R']);initial_size=len(remaining)
        prior=components(remaining);assert len(prior)==1
        critical=[]
        for index in range(first['path_start']+1,first['path_end']+1):
            v=path[index]
            if v not in remaining:continue
            a=len(components(remaining));remaining.remove(v);after=components(remaining)
            if len(after)>a:
                critical.append(dict(path_index=index,actual_cell=v,components_before=a,components_after=len(after),component_sizes=sorted(map(len,after))))
        assert remaining==points(second['required']) and len(remaining)==139 and len(components(remaining))==2 and critical
        splits.append(dict(run_id=j['run_id'],initial_region_size=initial_size,initial_components=1,required_size_at_second_plan=len(remaining),required_components=2,first_plan_region=first['region_id'],affected_later_region=second['region_id'],critical_cells=critical,second_plan_tau=second['end'],second_plan_end_source=second['end_source']))
    assert len(missing)==40 and not any(r['has_resume_target'] for r in missing)
    assert len({r['case'] for r in missing})==20 and len(splits)==2
    out=dict(full_CAP_solver_calls=0,saved_input_jobs=40,unique_inputs=20,missing_explicit_resume_target_jobs=40,missing_records=missing,split_replays=splits,
        inference='The cut is caused by actual incidental acquisition on first-region motion, not discovery of unknown cells. Repartition/reorder policy is not chosen by this replay.')
    (HERE/'saved_replay.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='missing_records'},ensure_ascii=False))
if __name__=='__main__':main()
