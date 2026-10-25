"""Seal a fixed bounded correctness protocol, zero solver calls."""
import json,hashlib
from pathlib import Path
from audit_inputs import check_case,check_history,pts
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
HIST=ALGO/'continuous_history_diagnostics'
PP=ROOT/'基线复现准备_20261019/独立版_v0.2'
CSTAR=ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(exist_ok=True,parents=True)
    with p.open('xb') as f:f.write(json.dumps(obj,ensure_ascii=False,indent=2).encode())
def main():
    if (HERE/'protocol.json').exists():raise RuntimeError('Already sealed; do not overwrite')
    # Verify candidate and both predecessor deliveries plus archived input
    # provenance. Witness routes remain auditor-only, never solver candidates.
    for folder in (CSTAR,CSTAR.parent/'修正版_v0.2',CSTAR.parent):
        for name,digest in read(folder/'delivery_manifest.json')['files'].items():assert sha(folder/name)==digest
    hist_path=HIST/'preparation_verification_v0.1_20261016/checks.json'
    histories={r['map_id']:r for r in read(hist_path)}
    pp_jobs=read(PP/'comparison/protocol.json')['jobs']
    paths=sorted((PP/'oarp_remote/inputs').glob('*.json'),key=lambda p:({'small':0,'medium':1,'large':2}[p.stem.split('_')[0]],p.stem))
    assert len(paths)==10
    cases=[];provenance=[];checks=[];sources={str(hist_path.relative_to(ROOT)):sha(hist_path)}
    for source in paths:
        event=read(source);mid=source.stem;assert event['metadata']['split']=='development'
        init_path=HIST/'preflight_v0.1_20261016/initial_cases'/(mid+'.json');initial=read(init_path)
        h=histories[mid]['history'];hc=check_history(initial,h)
        for key in ('current','covered','old_route'):assert event[key]==h[key],(mid,key)
        assert event['distance_budget']==h['remaining_budget']
        job=next(j for j in pp_jobs if j['map_id']==mid and j['method']=='PPCPP' and j['seed']==20261018 and j['budget']==1)
        assert sha(source)==job['input_sha256'] and sha(init_path)==job['initial_input_sha256']
        witness_path=PP/'comparison/runs'/(job['run_id']+'.json');wr=read(witness_path)
        assert wr['job']==job and wr['input_sha256']==sha(source) and wr['timely']
        for kind in ('control','event'):
            active=initial if kind=='control' else event
            published=initial['targets'] if kind=='control' else event['metadata']['published_targets']
            c=dict(name=mid+'__'+kind,map_id=mid,scale=mid.split('_')[0],state=kind,
                   event='none' if kind=='control' else event['metadata']['event'],split='development',radius=0,
                   free=active['free'],targets=active['targets'],covered=h['covered'],current=h['current'],base=active['base'],
                   published_targets=published,deferred_targets=sorted(pts(published)-pts(active['free'])-pts(h['covered'])),distance_budget=h['remaining_budget'])
            witness=h['old_route'] if kind=='control' else wr['route']
            if kind=='event':assert pts(c['deferred_targets'])==pts(event['metadata']['deferred_targets'])
            facts=check_case(c,witness)
            write(HERE/'inputs'/(c['name']+'.json'),c);write(HERE/'witnesses'/(c['name']+'.json'),dict(route=witness,source='saved_actual_tail' if kind=='control' else str(witness_path.relative_to(ROOT))))
            checks.append(dict(name=c['name'],history=hc,**facts))
            cases.append(dict(name=c['name'],scale=c['scale'],state=kind,event=c['event'],input='inputs/'+c['name']+'.json',input_sha256=sha(HERE/'inputs'/(c['name']+'.json'))))
        for p in (source,init_path,witness_path):sources[str(p.relative_to(ROOT))]=sha(p)
        provenance.append(dict(map_id=mid,event_source=str(source.relative_to(ROOT)),initial_source=str(init_path.relative_to(ROOT)),history_source=str(hist_path.relative_to(ROOT)),witness_source=str(witness_path.relative_to(ROOT))))
    write(HERE/'input_checks.json',checks);write(HERE/'provenance.json',provenance)
    jobs=[]
    for c in cases:
        for seed in (20261018,20261019):jobs.append(dict(c,seed=seed,budget_seconds=20,max_iterations=20000,run_id=c['name']+'__s'+str(seed)))
    protocol=dict(version='road_correctness_v0.1_20261019',status='SEALED_NOT_RUN',algorithm='CSTAR_history_v0.3',algorithm_source=str((CSTAR/'runtime').relative_to(ROOT)),cases=cases,jobs=jobs,
        scope='10 existing development maps, 20 event/control states, 40 calls; correctness only',seeds=[20261018,20261019],budget_seconds=20,max_iterations=20000,watchdog_seconds=35,serial=True,
        core_input_whitelist=['free','targets','covered','current','base','published_targets','distance_budget'],
        count_bootstrap_separately=True,include_solver_input_conversion_and_trace_materialization_in_budget=True,
        max_algorithm_budget_seconds=800,max_watchdog_envelope_seconds=1400,holdout_used=False,new_initial_plans=0,
        source_files=sources,stop_rules=['Stop before a job if any frozen hash changes','Keep logical coverage/resource/deadline/iteration failures and finish the fixed list without retries','Abort after two consecutive worker exceptions or watchdog timeouts; unstarted jobs remain unstarted','Do not change input, seed, max_iterations or budget after observing outcomes','Any feasible-state failed call blocks correctness acceptance; no dropping cases or global completion'],
        acceptance='All 40 return complete legal timely coverage-and-return routes, all independent checks pass; no speed/length ranking',
        withheld_from_solver=['witnesses','old_route','initial_targets','executed_prefix','event_type','map_id','future_events','other_method_results'])
    assert len(cases)==20 and len(jobs)==40
    write(HERE/'protocol.json',protocol)
    protected={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='freeze_manifest.json' and p.suffix!='.log'}
    protected_sources={str(p.relative_to(ROOT)):sha(p) for p in sorted((CSTAR/'runtime').rglob('*.py'))}
    for p in (CSTAR/'audit_special.py',CSTAR/'audit_micro.py'):protected_sources[str(p.relative_to(ROOT))]=sha(p)
    write(HERE/'freeze_manifest.json',dict(local_files=protected,external_runtime=protected_sources,prior_sources=sources,scope='Pre-run protocol/input/runtime freeze only; no road solve executed'))
    print(json.dumps(dict(status='SEALED_NOT_RUN',base_maps=10,states=20,jobs=40,physical_witness_checks=20,new_solver_calls=0),ensure_ascii=False))
if __name__=='__main__':main()
