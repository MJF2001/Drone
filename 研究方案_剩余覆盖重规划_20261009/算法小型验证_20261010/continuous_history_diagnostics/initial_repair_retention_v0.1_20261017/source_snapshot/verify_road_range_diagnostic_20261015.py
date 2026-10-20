"""Independent structural/reference and saved-route verification; no solve calls."""
from pathlib import Path
from collections import deque,Counter
from types import SimpleNamespace
import argparse,hashlib,importlib.util,itertools,json,math,statistics
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
INPUT=ALGO/'range_diagnostics/inputs_v0.1_20261015'
SOURCE=ALGO/'range_diagnostics/run_v0.1_20261015'
OUT=ALGO/'range_diagnostics/verification_v0.1_20261015'
METHODS=('R_SEED','R_PLUS1','R_PLUS2','R_ALL','P2_MULTI')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def norm(o):return json.loads(json.dumps(o))
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def ps(o,k):return set(map(tuple,o[k]))
def adj(p):
    x,y=p;return ((x,y+1),(x+1,y),(x,y-1),(x-1,y))
def check_manifest(folder):assert all(sha(folder/n)==h for n,h in read(folder/'sha256.json').items())

def independent_plan(c):
    old=tuple(map(tuple,c['old_route']));initial=ps(c['metadata'],'initial_targets');covered=ps(c,'covered');free=ps(c,'free');targets=ps(c,'targets')
    pending=initial-covered-{tuple(c['current'])};first={}
    for i,p in enumerate(old):
        if p in pending and p not in first:first[p]=i
    assert set(first)==pending
    blocks=[];group=[];vec=None
    for i,p in sorted((i,p) for p,i in first.items()):
        v=(p[0]-group[-1][1][0],p[1]-group[-1][1][1]) if group else None
        if group and (i!=group[-1][0]+1 or vec is not None and vec!=v):
            blocks.append(dict(start=group[0][0],end=group[-1][0],cells=[q for _,q in group]));group=[];vec=None
        if group:vec=v
        group.append((i,p))
    if group:blocks.append(dict(start=group[0][0],end=group[-1][0],cells=[q for _,q in group]))
    N=len(old)-1;bounds=sorted({0,N}|{b['start'] for b in blocks});legal=[i for i in bounds if old[i] in free]
    bad=[i for i,p in enumerate(old) if p not in free];spans=[]
    if bad:spans.append((max(i for i in legal if i<min(bad)),min(i for i in legal if i>max(bad))))
    new=targets-initial-covered-set(old);components=[]
    while new:
        root=min(new);todo=[root];component=set();new.remove(root)
        while todo:
            p=todo.pop();component.add(p)
            for q in adj(p):
                if q in new:new.remove(q);todo.append(q)
        distances={p:0 for p in component};queue=deque(sorted(component))
        while queue:
            p=queue.popleft()
            for q in adj(p):
                if q in free and q not in distances:distances[q]=distances[p]+1;queue.append(q)
        anchor=min((i for i in legal if old[i] in distances),key=lambda i:(distances[old[i]],i))
        k=bounds.index(anchor);a=bounds[max(0,k-1)];b=bounds[min(len(bounds)-1,k+1)]
        a=max(i for i in legal if i<=a);b=min(i for i in legal if i>=b);spans.append((a,b))
        components.append(dict(cells=sorted(component),anchor_index=anchor,distance=distances[old[anchor]]))
    left=min((x for x,y in spans),default=0);right=max((y for x,y in spans),default=0)
    li=bounds.index(left);ri=bounds.index(right);plans={}
    for m,steps in zip(METHODS[:4],(0,1,2,None)):
        if steps is None:a,b=0,N
        else:
            a=max(i for i in legal if i<=bounds[max(0,li-steps)])
            b=min(i for i in legal if i>=bounds[min(len(bounds)-1,ri+steps)])
        prefix=old[:a+1];suffix=old[b:];done=covered|(set(prefix)&targets)
        required=((targets-done)&set(old[a:b])) | (targets-done-set(suffix))
        assert set(prefix)|set(suffix)<=free
        assert targets<=covered|set(prefix)|set(suffix)|required
        plans[m]=dict(left=a,right=b,start=old[a],join=old[b],required=sorted(required),prefix_steps=a,suffix_steps=N-b,
            pending_count=len(targets-covered-{tuple(c['current'])}),required_count=len(required),
            modifiable_blocks=sum(a<=z['start']<b for z in blocks),block_count=len(blocks),
            prefix_sha256=digest(prefix),suffix_sha256=digest(suffix))
    for x,y in zip(METHODS[:3],METHODS[1:4]):
        assert plans[y]['left']<=plans[x]['left'] and plans[y]['right']>=plans[x]['right']
        assert set(map(tuple,plans[x]['required']))<=set(map(tuple,plans[y]['required']))
    return norm(dict(blocks=blocks,boundaries=bounds,old_collision_indices=bad,new_components=components,
        seed_span=(left,right),plans=plans,
        limitation='One enclosing route interval; nearest-graph-distance insertion anchor; fixed literal prefix/suffix.'))

def inputs(save):
    check_manifest(INPUT);ip=read(INPUT/'protocol.json')
    assert sha(Path(ip['origin_snapshot_file']))==ip['origin_sha256']
    assert all(sha(Path(p))==h for p,h in ip['source_hashes'].items())
    original={c['name']:c for c in [json.loads(l) for l in Path(ip['origin_snapshot_file']).open(encoding='utf-8')]}
    anchors=read(Path(ip['anchor_protocol']))['case_ids'];families=read(INPUT/'families.json');complete=read(INPUT/'completion.json')
    assert [f['anchor'] for f in families]==anchors and len(families)==12
    refs=read(INPUT/'structural_references.json');cases={};stats=[];expectedids=[]
    for f in families:
        expected=list(dict.fromkeys((f['anchor'],f['map_id']+'_H_p50_no_change')));assert f['case_ids']==expected
        expectedids+=expected
        assert f['distance_budget']==max(original[sid]['distance_budget'] for sid in expected)
        assert f['seed']==original[f['anchor']]['metadata']['repeat_seed_0']
        for sid in expected:
            c=read(INPUT/'cases'/(sid+'.json'));o=original[sid];cases[sid]=c
            for k in ('name','free','targets','covered','current','base','old_route','radius'):assert c[k]==o[k]
            assert c['distance_budget']==f['distance_budget'] and c['metadata']['repeat_seed_0']==f['seed']
            assert c['metadata']['split']=='development' and c['metadata']['map_id']==f['map_id']
            for k,v in o['metadata'].items():
                if k!='repeat_seed_0':assert c['metadata'][k]==v
            provenance=c['metadata']['range_diagnostic'];assert provenance['paired_seed']==f['seed']
            assert provenance['original_repeat_seed_0']==o['metadata']['repeat_seed_0']
            assert provenance['original_distance_budget']==o['distance_budget']
            assert provenance['source_snapshot_sha256']==hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()
            assert ps(c,'targets')==ps(c['metadata'],'published_targets')-ps(c['metadata'],'obstacles')
            assert ps(c['metadata'],'deferred_targets')==(ps(c['metadata'],'published_targets')-ps(c,'covered'))&ps(c['metadata'],'obstacles')
            plan=independent_plan(c);assert plan==refs[sid]['plan']
            seen={};aliases={}
            for m in METHODS[:4]:
                cfg=plan['plans'][m];aliases[m]=seen.setdefault((cfg['left'],cfg['right']),m)
            assert aliases==refs[sid]['aliases']
            stats.append(dict(case=sid,map_id=f['map_id'],event=c['metadata']['event'],block_count=len(plan['blocks']),
                scope_cuts={m:[p['left'],p['right']] for m,p in plan['plans'].items()},
                scope_required_counts={m:p['required_count'] for m,p in plan['plans'].items()},
                duplicate_settings=4-len(set(aliases.values()))))
        for k in ('current','base','covered','old_route'):assert original[expected[0]][k]==original[expected[-1]][k]
    assert expectedids==complete['case_ids'] and len(cases)==22 and set(cases)==set(refs)
    result=dict(valid=True,states=22,base_maps=12,event_states=10,control_states=12,
        unique_range_settings=sum(4-s['duplicate_settings'] for s in stats),structural_checks=stats,
        solver_called=False,holdout_used=False,verifier_sha256=sha(Path(__file__)))
    if save:write(INPUT/'independent_input_check.json',result)
    return result,cases,refs,families

def metrics_independent(c,route):
    targets=ps(c,'targets');covered=ps(c,'covered');seen=covered|({route[0]}&targets);pending=targets-seen
    counts=[0,0,0,0];completion=0 if not pending else None
    for i,p in enumerate(route[1:],1):
        k=3 if p not in targets else 1 if p in covered else 2 if p in seen else 0;counts[k]+=1;seen.add(p);pending.discard(p)
        if not pending and completion is None:completion=i
    d=dict(zip(('fresh','historical_repeat','current_repeat','non_target'),counts));denom=sum(counts[:3])
    vectors=[(q[0]-p[0],q[1]-p[1]) for p,q in zip(route,route[1:])]
    d.update(steps=len(route)-1,overlap_ratio=(counts[1]+counts[2])/denom if denom else None,
        turns90=sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vectors,vectors[1:])),
        turns180=sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vectors,vectors[1:])),
        completion_step=completion,return_tail_steps=len(route)-1-completion if completion is not None else None)
    return d
def mean(values):return statistics.mean(values) if values else None
def mapmean(states,key):
    by={}
    for s in states:
        if s[key] is not None:by.setdefault(s['map_id'],[]).append(s[key])
    return mean([mean(v) for v in by.values()])

def results():
    inp,cases,refs,families=inputs(False);check_manifest(SOURCE);protocol=read(SOURCE/'protocol.json')
    assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    rows=[json.loads(l) for l in (SOURCE/'execution_ledger.jsonl').open(encoding='utf-8')]
    assert [r['run_id'] for r in rows]==[j['run_id'] for j in protocol['jobs']]
    assert len(rows)==protocol['expected_physical_runs'] and len({r['run_id'] for r in rows})==len(rows)
    spec=importlib.util.spec_from_file_location('_road_range_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    physical={};checks=[];corechecks=0;planchecks=0
    for r in rows:
        c=cases[r['case']];path=SOURCE/'runs'/(r['run_id']+'.json');raw=None
        if path.exists() and r['worker_status']=='returned':
            payload=read(path);raw=payload['raw'];assert raw['method']==r['method'] and raw['budget']==r['budget']
            assert raw['seed']==c['metadata']['range_diagnostic']['paired_seed']
            assert payload['metrics']==r['metrics'] and raw['seconds']==r['solver_seconds']
            assert bool(raw['overrun_gt_10ms'])==(raw['seconds']>raw['budget']+.01)
            s=SimpleNamespace(free=ps(c,'free'),targets=ps(c,'targets'),covered=ps(c,'covered'),current=tuple(c['current']),base=tuple(c['base']),radius=0,distance_budget=c['distance_budget'])
            if raw['route']:
                route=tuple(map(tuple,raw['route']));check=auditor.audit(s,route)
                assert check==raw['independent_audit'] and check['valid'] and not r['watchdog_timeout'] and r['valid']
                assert metrics_independent(c,route)==payload['metrics'];checks.append(dict(run_id=r['run_id'],steps=check['length'],valid=True))
                assert raw['seconds']<=payload['solve_plus_audits_seconds']+.000001
            else:assert not r['valid']
            if r['method']!='P2_MULTI':
                detail=raw['detail'];plan=detail['range_plan'];old=tuple(map(tuple,c['old_route']))
                if plan is not None:assert plan==refs[r['case']]['plan'];planchecks+=1
                for kind in ('acceptances','core_acceptances'):
                    events=detail[kind];assert all(0<=e['seconds']<=r['budget'] for e in events)
                    assert all(y['steps']<x['steps'] for x,y in zip(events,events[1:]))
                if raw['route']:
                    assert detail['acceptances'][-1]['route_sha256']==digest(raw['route'])
                    assert detail['acceptances'][-1]['label']==raw['source']
                if raw['core_route']:
                    route=tuple(map(tuple,raw['core_route']));patch=tuple(map(tuple,raw['core_patch']))
                    check=auditor.audit(s,route);assert check['valid'] and check==raw['core_independent_audit'];corechecks+=1
                    cfg=plan['plans'][r['method']];l,rr=cfg['left'],cfg['right']
                    assert route==old[:l]+patch+old[rr+1:]
                    assert patch[0]==old[l] and patch[-1]==old[rr] and ps(cfg,'required')<=set(patch)
                    assert detail['core_acceptances'][-1]['route_sha256']==digest(route)
                    assert detail['core_valid_before_deadline']
                else:assert not detail['core_valid_before_deadline']
        else:assert not r['valid']
        physical[r['run_id']]=dict(r,raw=raw)
    logical=[];lookup={}
    assert len(protocol['logical_settings'])==220
    for item in protocol['logical_settings']:
        p=physical[item['run_id']];c=cases[item['case']]
        assert p['case']==item['case'] and p['budget']==item['budget'] and p['method']==item['canonical_method']
        expected='P2_MULTI' if item['method']=='P2_MULTI' else refs[item['case']]['aliases'][item['method']]
        assert expected==item['canonical_method']
        row={k:v for k,v in p.items() if k!='raw'};row.update(item,map_id=c['metadata']['map_id'],
            role=c['metadata']['range_diagnostic']['role'],event=c['metadata']['event'])
        raw=p['raw'];row['core_valid']=bool(raw and raw.get('detail',{}).get('core_valid_before_deadline'))
        row['core_steps']=len(raw['core_route'])-1 if raw and raw.get('core_route') else None
        row['stages']=raw.get('detail',{}).get('stages',{}) if raw else {}
        row['engine_status']=raw.get('detail',{}).get('engine',{}).get('status') if raw else None
        logical.append(row);lookup[row['case'],row['budget'],row['method']]=row
    method_stats=[];paired=[]
    for subset in ('all','event','control'):
        for budget in (1,20):
            for method in METHODS:
                group=[r for r in logical if r['method']==method and r['budget']==budget and (subset=='all' or r['role']==subset)]
                valid=[r for r in group if r['valid']];times=sorted(r['solver_seconds'] for r in group if r['solver_seconds'] is not None)
                method_stats.append(dict(subset=subset,budget=budget,method=method,logical_settings=len(group),valid=len(valid),
                    sum_steps_valid_only=sum(r['metrics']['steps'] for r in valid),solver_seconds_mean=mean(times),
                    solver_seconds_median=statistics.median(times) if times else None,
                    solver_seconds_p95_nearest_rank=times[math.ceil(.95*len(times))-1] if times else None,
                    solver_seconds_max=max(times) if times else None,fallback=sum(bool(r['fallback_selected']) for r in group),
                    core_valid=sum(r['core_valid'] for r in group) if method!='P2_MULTI' else None,
                    overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in group),
                    engine_status=dict(Counter(r['engine_status'] for r in group))))
            for a,b in itertools.combinations(METHODS,2):
                values=[];aonly=bonly=bothfail=0
                for sid,c in cases.items():
                    if subset!='all' and c['metadata']['range_diagnostic']['role']!=subset:continue
                    x=lookup[sid,budget,a];y=lookup[sid,budget,b]
                    if x['valid'] and y['valid']:
                        lx=x['metrics']['steps'];ly=y['metrics']['steps']
                        values.append(dict(case=sid,map_id=x['map_id'],difference=lx-ly,relative=lx/ly-1 if ly else None))
                    elif x['valid']:aonly+=1
                    elif y['valid']:bonly+=1
                    else:bothfail+=1
                paired.append(dict(subset=subset,budget=budget,a=a,b=b,paired_states=len(values),a_only=aonly,b_only=bonly,both_fail=bothfail,
                    a_shorter=sum(v['difference']<0 for v in values),equal=sum(v['difference']==0 for v in values),
                    a_longer=sum(v['difference']>0 for v in values),sum_difference=sum(v['difference'] for v in values),
                    relative_difference_map_equal=mapmean(values,'relative'),per_state=values))
    oracle=[];contrasts=[];profiles=[]
    for sid,c in cases.items():
        for budget in (1,20):
            scopes=[lookup[sid,budget,m] for m in METHODS[:4]];p2=lookup[sid,budget,'P2_MULTI']
            valid=[x for x in scopes if x['valid']]
            value=min((x['metrics']['steps'] for x in valid),default=None)
            oracle.append(dict(case=sid,map_id=c['metadata']['map_id'],budget=budget,role=c['metadata']['range_diagnostic']['role'],
                posthoc_best_steps=value,methods_tied_best=[x['method'] for x in valid if x['metrics']['steps']==value],
                minus_P2=value-p2['metrics']['steps'] if value is not None and p2['valid'] else None,
                online_selector=False))
            profiles.append(dict(case=sid,budget=budget,event=c['metadata']['event'],map_id=c['metadata']['map_id'],
                scope_details={m:dict(cfg=refs[sid]['plan']['plans'][m],valid=lookup[sid,budget,m]['valid'],
                    final_steps=lookup[sid,budget,m]['metrics']['steps'] if lookup[sid,budget,m]['valid'] else None,
                    core_steps=lookup[sid,budget,m]['core_steps'],canonical=refs[sid]['aliases'][m]) for m in METHODS[:4]}))
    for family in families:
        if family['anchor']==family['control']:continue
        for budget in (1,20):
            for method in METHODS[:4]:
                e=lookup[family['anchor'],budget,method];c=lookup[family['control'],budget,method]
                ep=lookup[family['anchor'],budget,'P2_MULTI'];cp=lookup[family['control'],budget,'P2_MULTI']
                valid=all(x['valid'] for x in (e,c,ep,cp))
                contrasts.append(dict(map_id=family['map_id'],event=e['event'],budget=budget,method=method,valid=valid,
                    event_minus_P2=e['metrics']['steps']-ep['metrics']['steps'] if valid else None,
                    control_minus_P2=c['metrics']['steps']-cp['metrics']['steps'] if valid else None,
                    difference_of_differences=(e['metrics']['steps']-ep['metrics']['steps'])-(c['metrics']['steps']-cp['metrics']['steps']) if valid else None))
    maxrow=max((r for r in rows if r['solver_seconds'] is not None),key=lambda r:r['solver_seconds']-r['budget'])
    summary=dict(status='independently_verified_bounded_road_range_diagnostic',physical_runs=len(rows),logical_settings=220,
        selected_route_audits=len(checks),core_route_audits=corechecks,timed_structural_plan_checks=planchecks,
        input_states=22,base_maps=12,event_states=10,control_states=12,holdout_used=False,solver_called=False,
        valid_physical_runs=sum(r['valid'] for r in rows),overrun_gt_10ms_physical=sum(bool(r['overrun_gt_10ms']) for r in rows),
        max_overrun_seconds=max(0,maxrow['solver_seconds']-maxrow['budget']),max_overrun_run_id=maxrow['run_id'],
        verifier_sha256=sha(Path(__file__)),limitation='One seed, H50 development maps, one enclosing interval, fixed literal tails, no fitted online selector. Aliases are shared executions.')
    OUT.mkdir(parents=True,exist_ok=False)
    for name,o in (('summary.json',summary),('method_summary.json',method_stats),('paired_summary.json',paired),
        ('posthoc_scope_oracle.json',oracle),('event_control_contrasts.json',contrasts),('scope_profiles.json',profiles),
        ('logical_ledger.json',logical),('route_checks.json',checks)):
        write(OUT/name,o)
    write(OUT/'sha256.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');a=p.parse_args()
    if a.inputs:print(json.dumps({k:v for k,v in inputs(True)[0].items() if k!='structural_checks'},ensure_ascii=False))
    else:results()
