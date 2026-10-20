"""Offline supplementary counts and protected-source archive; no new solve calls."""
from pathlib import Path
import hashlib,json,shutil,statistics
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'range_diagnostics/run_v0.1_20261015'
OUT=ALGO/'range_diagnostics/verification_v0.1_20261015'
INPUT=ALGO/'range_diagnostics/inputs_v0.1_20261015'
METHODS=('R_SEED','R_PLUS1','R_PLUS2','R_ALL','P2_MULTI')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def main():
    assert read(OUT/'summary.json')['valid_physical_runs']==200
    rows=read(OUT/'logical_ledger.json');lookup={(r['case'],r['budget'],r['method']):r for r in rows}
    refs=read(INPUT/'structural_references.json');case_ids=read(INPUT/'completion.json')['case_ids']
    stages=[];plateaus=[];extents=[];resource=[];full_equal=[]
    for sid in case_ids:
        c=read(INPUT/'cases'/(sid+'.json'));role=c['metadata']['range_diagnostic']['role'];mid=c['metadata']['map_id']
        cfg=refs[sid]['plan']['plans']['R_SEED'];pending=cfg['pending_count']
        extents.append(dict(case=sid,map_id=mid,role=role,event=c['metadata']['event'],
            required_fraction=cfg['required_count']/pending if pending else 0,
            block_fraction=cfg['modifiable_blocks']/cfg['block_count'] if cfg['block_count'] else 0,
            required=cfg['required_count'],pending=pending,block_count=cfg['block_count'],modifiable_blocks=cfg['modifiable_blocks']))
        for budget in (1,20):
            group=[lookup[sid,budget,m] for m in METHODS]
            assert all(r['valid'] for r in group)
            a,b=group[-2:];assert a['metrics']['steps']==b['metrics']['steps']
            full_equal.append(dict(case=sid,budget=budget,steps=a['metrics']['steps']))
            values=[r['metrics']['steps'] for r in group[:4]]
            if values[1]>=values[0] and values[3]<values[0]:
                plateaus.append(dict(case=sid,budget=budget,role=role,steps=values,
                    observation='First expansion did not improve, yet ALL is shorter; not a proven online stopping rule.'))
            for r in group:resource.append(c['distance_budget']-r['metrics']['steps'])
    for role in ('all','event','control'):
        for budget in (1,20):
            for a,b in zip(METHODS[:3],METHODS[1:4]):
                ds=[]
                for sid in case_ids:
                    x=lookup[sid,budget,a];y=lookup[sid,budget,b]
                    if role!='all' and x['role']!=role:continue
                    ds.append(y['metrics']['steps']-x['metrics']['steps'])
                stages.append(dict(subset=role,budget=budget,from_method=a,to_method=b,
                    shorter=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),longer=sum(d>0 for d in ds),sum_difference=sum(ds)))
    oracle=[]
    for budget in (1,20):
        for role in ('all','event','control'):
            group=[r for r in read(OUT/'posthoc_scope_oracle.json') if r['budget']==budget and (role=='all' or r['role']==role)]
            oracle.append(dict(subset=role,budget=budget,states=len(group),
                shorter=sum(r['minus_P2']<0 for r in group),equal=sum(r['minus_P2']==0 for r in group),
                sum_minus_P2=sum(r['minus_P2'] for r in group),online_selector=False))
    data=dict(all_vs_P2_equal_length_pairs=len(full_equal),min_selected_resource_margin=min(resource),
        logical_overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),
        physical_overrun_gt_10ms=read(OUT/'summary.json')['overrun_gt_10ms_physical'],
        extents=extents,scope_expansion_comparisons=stages,first_expansion_non_improvement_but_full_better=plateaus,
        posthoc_oracle_summary=oracle,solver_called=False,holdout_used=False,
        supplementary_analysis='Descriptive post-processing; does not change predeclared primary statistics or fit a threshold.')
    write(OUT/'supplementary_counts.json',data)
    protected=read(SOURCE/'protocol.json')['protected_hashes'];snap=OUT/'source_snapshot';snap.mkdir(exist_ok=False);records=[]
    for name,h in protected.items():
        p=Path(name);assert sha(p)==h
        if p.parent==ROOT or p.name.startswith('57_'):
            dest=snap/p.name;shutil.copyfile(p,dest);assert sha(dest)==h
            records.append(dict(original_path=str(p),snapshot_path=str(dest),sha256=h))
    write(OUT/'source_snapshot_manifest.json',dict(status='end_of_run_bytes_match_pre_run_protected_hashes',files=records,
        note='Restore to original workspace paths to replay; source copies are not a self-contained runtime.'))
    paths=[Path(__file__),ROOT/'render_road_range_diagnostic_20261015.py',OUT/'supplementary_counts.json',
        OUT/'source_snapshot_manifest.json',OUT/'input_clean_replay.json',OUT/'figure_sha256.json',OUT/'event_range_vs_P2.png']
    paths+=list(snap.iterdir())
    paths+=list((ALGO/'range_diagnostics/preflight_v0.1_20261015').iterdir())
    write(OUT/'supplement_sha256.json',{str(p):sha(p) for p in paths})
    print(json.dumps(dict(all_vs_P2_equal_length_pairs=len(full_equal),min_resource_margin=min(resource),
        plateau_counterexamples=len(plateaus),oracle_summary=oracle,source_snapshots=len(records)),ensure_ascii=False))
if __name__=='__main__':main()
