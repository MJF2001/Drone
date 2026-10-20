"""22 development inputs and untimed structural references; no algorithm solves."""
from pathlib import Path
import copy,hashlib,json
import portable_frozen
from model import Snapshot
from road_range_candidate_20261015 import range_plan,RANGES
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
OUT=ALGO/'range_diagnostics/inputs_v0.1_20261015'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def snapshot(c):
    ps=lambda k:frozenset(map(tuple,c[k]))
    return Snapshot(c['name'],ps('free'),ps('targets'),ps('covered'),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
def main():
    original=ALGO/'scale_inputs/development_v0.1_20261014'
    manifest=read(original/'sha256.json')['artifacts'];assert all(sha(original/n)==h for n,h in manifest.items())
    allcases={c['name']:c for c in [json.loads(l) for l in (original/'snapshots.jsonl').open(encoding='utf-8')]}
    anchor_ids=read(ALGO/'development_preflights/v1_20261014/protocol.json')['case_ids']
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'cases').mkdir();families=[];references={};caseids=[]
    for aid in anchor_ids:
        anchor=allcases[aid];mid=anchor['metadata']['map_id'];control_id=mid+'_H_p50_no_change'
        ids=list(dict.fromkeys((aid,control_id)));limit=max(allcases[sid]['distance_budget'] for sid in ids)
        family=dict(map_id=mid,anchor=aid,control=control_id,case_ids=ids,seed=anchor['metadata']['repeat_seed_0'],distance_budget=limit)
        families.append(family)
        for sid in ids:
            c=copy.deepcopy(allcases[sid]);assert c['metadata']['split']=='development'
            c['metadata']['range_diagnostic']=dict(source_snapshot_sha256=hashlib.sha256(json.dumps(allcases[sid],sort_keys=True).encode()).hexdigest(),
                original_distance_budget=c['distance_budget'],original_repeat_seed_0=c['metadata']['repeat_seed_0'],
                family_anchor=aid,paired_seed=family['seed'],role='control' if sid==control_id else 'event')
            c['metadata']['repeat_seed_0']=family['seed']
            c['distance_budget']=limit;write(OUT/'cases'/(sid+'.json'),c);caseids.append(sid)
            plan=range_plan(snapshot(c),set(map(tuple,c['metadata']['initial_targets'])));aliases={};seen={}
            for method in RANGES:
                cfg=plan['plans'][method];key=(cfg['left'],cfg['right'])
                aliases[method]=seen.setdefault(key,method)
            references[sid]=dict(plan=plan,aliases=aliases)
        a=allcases[aid];b=allcases[control_id]
        for k in ('covered','current','old_route','base'):assert a[k]==b[k]
    assert len(caseids)==22 and len(set(caseids))==22 and len(families)==12
    write(OUT/'families.json',families);write(OUT/'structural_references.json',references)
    write(OUT/'protocol.json',dict(version='road_range_inputs_v0.1_20261015',
        origin_snapshot_file=str(original/'snapshots.jsonl'),origin_sha256=sha(original/'snapshots.jsonl'),
        anchor_protocol=str(ALGO/'development_preflights/v1_20261014/protocol.json'),
        source_hashes={str(p):sha(p) for p in (Path(__file__),ROOT/'road_range_candidate_20261015.py',ROOT/'range_p2_engine_20261015.py')},
        holdout_used=False,solver_called=False))
    write(OUT/'completion.json',dict(status='prepared_road_range_development_inputs',case_ids=caseids,states=22,base_maps=12,
        paired_event_maps=10,no_change_only_maps=2,holdout_used=False,solver_called=False,
        normalization='Family-shared maximum original geometric resource cap and anchor seed; no geometry changed.',
        reference_use='Workers must recompute plan inside timing, never receive these references as solver input.'))
    write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(dict(states=len(caseids),families=len(families),unique_range_settings=sum(len(set(v['aliases'].values())) for v in references.values()),
        max_jobs_with_P2_and_two_budgets=2*sum(len(set(v['aliases'].values()))+1 for v in references.values()))))
if __name__=='__main__':main()
