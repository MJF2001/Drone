"""Independent saved-input/route checks and map-cluster descriptive statistics.
No planner calls. Inputs: --inputs; results: default.
"""
from pathlib import Path
from collections import Counter,deque
from types import SimpleNamespace
import argparse,hashlib,importlib.util,itertools,json,statistics

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
INPUT=ALGO/'scale_inputs/matched_history_v2_20261015'
SOURCE=ALGO/'development_preflights/matched_history_v2_20261015'
OUT=ALGO/'development_preflights/matched_history_v2_20261015_verification'
METHODS=('P2_MULTI','OARP_CORE2','TREE_MST','PPCPP_CORE4')
VARIANTS=('H25','H50','H75','V50')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def pts(o,k):return set(map(tuple,o[k]))
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def hashes(root):
    assert all(sha(root/n)==h for n,h in read(root/'sha256.json').items())
def reachable(free,current):
    seen={current} if current in free else set();q=deque(seen)
    while q:
        x,y=q.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in free and p not in seen:seen.add(p);q.append(p)
    return seen
def route_check(route,free,targets,covered,current,base,limit):
    assert route and route[0]==current and route[-1]==base
    assert set(route)<=free and not targets-covered-set(route)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
    assert len(route)-1<=limit

def verify_inputs(save=True):
    hashes(INPUT);p=read(INPUT/'protocol.json');complete=read(INPUT/'completion.json')
    assert all(sha(Path(n))==h for n,h in p['source_hashes'].items())
    ledger=read(INPUT/'generation_ledger.json');assert len(ledger)==48
    assert len({r['state_id'] for r in ledger})==48
    groups={};cases={};failures=[]
    for entry in ledger:
        sid=entry['state_id'];ap=ALGO/'development_preflights/v1_20261014/cases'/(entry['anchor_id']+'.json')
        anchor=read(ap);am=anchor['metadata'];mp=read(ALGO/'scale_inputs/development_v0.1_20261014'/(am['map_id']+'.json'))
        assert am['split']==mp['parameters']['split']=='development'
        history=entry['variant'][0];progress=int(entry['variant'][1:]);initial=pts(mp,'initial_targets')
        full=tuple(map(tuple,mp['routes'][history]));seen=set();index=None
        for i,q in enumerate(full):
            if q in initial:seen.add(q)
            if 100*len(seen)>=progress*len(initial):index=i;break
        assert index is not None
        prefix=full[:index+1];suffix=full[index:];current=full[index];covered=initial&set(prefix)
        free=pts(anchor,'free');targets=pts(anchor,'targets');blocked=pts(am,'obstacles');published=pts(am,'published_targets')
        assert free==pts(mp,'domain')-blocked and targets==published-blocked
        reached=reachable(free,current)
        feasible=current in free and tuple(anchor['base']) in reached and not targets-covered-reached
        assert feasible==(entry['status']=='generated')
        groups.setdefault(am['map_id'],[]).append(entry['variant'])
        if not feasible:
            saved=read(INPUT/'cases'/(sid+'_infeasible.json'))
            assert tuple(saved['current'])==current and pts(saved,'covered')==covered
            assert tuple(map(tuple,saved['prefix']))==prefix and tuple(map(tuple,saved['old_route']))==suffix
            failures.append(entry);continue
        c=read(INPUT/'cases'/(sid+'.json'));m=c['metadata'];cases[sid]=c
        assert c['name']==sid and m['variant']==entry['variant'] and m['map_id']==am['map_id']
        assert pts(c,'covered')==covered and tuple(c['current'])==current and c['radius']==0
        assert tuple(map(tuple,c['old_route']))==suffix and tuple(map(tuple,m['prefix']))==prefix
        assert m['actual_progress']==len(covered)/len(initial)
        assert pts(m,'deferred_targets')==(published-covered)&blocked
        assert pts(m,'initial_targets')==initial and m['repeat_seed_0']==am['repeat_seed_0']
        for key in ('free','targets','base'):assert c[key]==anchor[key]
        assert m['published_targets']==am['published_targets'] and m['obstacles']==am['obstacles']
        assert m['extension']==am['extension']
        witness=tuple(map(tuple,read(INPUT/'witnesses'/(sid+'.json'))['route']))
        route_check(witness,free,targets,covered,current,tuple(c['base']),c['distance_budget'])
        canonical=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
        assert canonical(c)==entry['snapshot_sha256'] and canonical(witness)==entry['witness_sha256']
        assert len(witness)-1==m['witness_steps']
    assert len(groups)==12 and all(sorted(v)==sorted(VARIANTS) for v in groups.values())
    assert len(cases)==complete['feasible'] and set(cases)==set(complete['case_ids'])
    for mid in groups:
        family=[c for c in cases.values() if c['metadata']['map_id']==mid]
        limit=max([1]+[2*c['metadata']['witness_steps'] for c in family])
        assert all(c['distance_budget']==limit for c in family)
        hp={c['metadata']['variant']:pts(c,'covered') for c in family if c['metadata']['history']=='H'}
        if len(hp)==3:assert hp['H25']<=hp['H50']<=hp['H75']
    result=dict(valid=True,attempted=48,feasible=len(cases),infeasible=len(failures),failures=failures,
        base_maps=12,hashes_verified=True,solver_called=False,holdout_used=False,verifier_sha256=sha(Path(__file__)))
    if save:write(INPUT/'independent_input_verification.json',result)
    return result,cases

def summary_group(group):
    valid=[r for r in group if r['valid']];times=[r['solver_seconds'] for r in group if r['solver_seconds'] is not None]
    arrivals=sum(r['metrics']['steps']-r['metrics']['non_target'] for r in valid)
    repeats=sum(r['metrics']['historical_repeat']+r['metrics']['current_repeat'] for r in valid)
    return dict(runs=len(group),valid=len(valid),failures=len(group)-len(valid),
        sum_steps_valid_only=sum(r['metrics']['steps'] for r in valid),
        overlap_pooled=repeats/arrivals if arrivals else None,
        turns90=sum(r['metrics']['turns90'] for r in valid),
        solver_seconds_mean=statistics.mean(times) if times else None,
        solver_seconds_median=statistics.median(times) if times else None,
        solver_seconds_max=max(times) if times else None,
        fallback=sum(bool(r['fallback_selected']) for r in group),
        core_obtained=sum(bool(r['core_tour_obtained'] or r['core_valid_before_deadline']) for r in group),
        overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in group),
        max_overrun_seconds=max([0]+[r['solver_seconds']-r['budget'] for r in group if r['solver_seconds'] is not None]),
        solver_status_counts=dict(Counter(r['solver_status'] for r in group)))

def verify_results():
    inp,cases=verify_inputs(False);hashes(SOURCE);protocol=read(SOURCE/'protocol.json')
    assert all(sha(Path(p))==h for p,h in protocol['hashes'].items())
    assert protocol['budgets']==[1,20] and protocol['repeats']==1
    rows=[json.loads(l) for l in (SOURCE/'execution_ledger.jsonl').open(encoding='utf-8')]
    assert len(rows)==protocol['expected_runs']==len(cases)*8
    assert [r['run_id'] for r in rows]==[j['run_id'] for j in protocol['jobs']]
    assert len({r['run_id'] for r in rows})==len(rows)
    spec=importlib.util.spec_from_file_location('_matched_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    checks=[];cores=0;lookup={};resource_margins=[]
    for r in rows:
        c=cases[r['case']];m=c['metadata'];r.update(map_id=m['map_id'],variant=m['variant'],scale=m['scale'],event=m['event'])
        path=SOURCE/'runs'/(r['run_id']+'.json')
        if not path.exists() or r['worker_status']!='returned':assert not r['valid']
        else:
            payload=read(path);raw=payload['raw']
            assert payload['method']==raw['method']==r['method'] and payload['case']==c['name']
            assert raw['budget']==r['budget'] and raw['seed']==m['repeat_seed_0'] and r['repeat']==0
            assert raw['seconds']==r['solver_seconds'] and payload['metrics']==r['metrics']
            assert bool(raw['overrun_gt_10ms'])==(raw['seconds']-r['budget']>0.01)
            s=SimpleNamespace(free=frozenset(pts(c,'free')),targets=frozenset(pts(c,'targets')),
                covered=frozenset(pts(c,'covered')),current=tuple(c['current']),base=tuple(c['base']),radius=0,distance_budget=c['distance_budget'])
            if raw['route']:
                route=tuple(map(tuple,raw['route']));checked=audit.audit(s,route)
                assert checked==raw['independent_audit'] and r['valid']==(checked['valid'] and not r['watchdog_timeout'])
                assert checked['valid'];route_check(route,s.free,s.targets,s.covered,s.current,s.base,s.distance_budget)
                mt=payload['metrics'];counts=[0,0,0,0];seen=set(s.covered)|({route[0]}&s.targets)
                pending=set(s.targets)-seen;completion=0 if not pending else None
                for i,p in enumerate(route[1:],1):
                    k=3 if p not in s.targets else 1 if p in s.covered else 2 if p in seen else 0
                    counts[k]+=1;seen.add(p);pending.discard(p)
                    if not pending and completion is None:completion=i
                assert counts==[mt[k] for k in ('fresh','historical_repeat','current_repeat','non_target')]
                assert sum(counts)==mt['steps']==checked['length']
                denom=sum(counts[:3]);assert mt['overlap_ratio']==((counts[1]+counts[2])/denom if denom else None)
                vectors=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
                assert mt['turns90']==sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vectors,vectors[1:]))
                assert mt['turns180']==sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vectors,vectors[1:]))
                assert mt['completion_step']==completion and mt['return_tail_steps']==len(route)-1-completion
                assert raw['seconds']<=payload['solve_plus_audits_seconds']+.000001
                resource_margins.append(s.distance_budget-mt['steps'])
                checks.append(dict(run_id=r['run_id'],valid=True,steps=mt['steps']))
            else:assert not r['valid']
            if r['method']=='PPCPP_CORE4' and raw['detail']['core_route']:
                core=audit.audit(s,tuple(map(tuple,raw['detail']['core_route'])))
                assert core==raw['core_independent_audit'];cores+=1
                if raw['detail']['core_valid_before_deadline']:assert core['valid']
        lookup[r['case'],r['budget'],r['method']]=r
    summaries=[];pairs=[]
    # New states and tuned anchors separated. No independent-state inference or p-values.
    subsets={'all':set(VARIANTS),'new_states':{'H25','H75','V50'},**{v:{v} for v in VARIANTS}}
    for subset,variants in subsets.items():
        for budget in (1,20):
            for method in METHODS:
                group=[r for r in rows if r['variant'] in variants and r['budget']==budget and r['method']==method]
                summaries.append(dict(subset=subset,budget=budget,method=method,**summary_group(group)))
            for a,b in itertools.combinations(METHODS,2):
                differences=[];by_map={};state_values=[];a_only=b_only=both_fail=0
                for sid,c in cases.items():
                    if c['metadata']['variant'] not in variants:continue
                    x=lookup[sid,budget,a];y=lookup[sid,budget,b]
                    if x['valid'] and y['valid']:
                        lx=x['metrics']['steps'];ly=y['metrics']['steps'];d=lx-ly;differences.append(d)
                        rel=lx/ly-1 if ly else None
                        state_values.append(dict(case=sid,map_id=x['map_id'],variant=x['variant'],difference=d,relative_difference=rel))
                        if rel is not None:by_map.setdefault(x['map_id'],[]).append(rel)
                    elif x['valid']:a_only+=1
                    elif y['valid']:b_only+=1
                    else:both_fail+=1
                pairs.append(dict(subset=subset,budget=budget,a=a,b=b,paired_states=len(differences),
                    a_only_success=a_only,b_only_success=b_only,both_fail=both_fail,
                    a_shorter_states=sum(d<0 for d in differences),equal_states=sum(d==0 for d in differences),
                    a_longer_states=sum(d>0 for d in differences),step_difference_sum_paired=sum(differences),
                    relative_difference_map_equal=statistics.mean([statistics.mean(v) for v in by_map.values()]) if by_map else None,
                    maps_with_pairs=len(by_map),per_state=state_values,
                    per_map_mean_relative={k:statistics.mean(v) for k,v in by_map.items()}))
    scales=[dict(scale=scale,budget=budget,method=method,**summary_group([
        r for r in rows if r['scale']==scale and r['budget']==budget and r['method']==method and r['variant']!='H50']))
        for scale in ('small','medium','large') for budget in (1,20) for method in METHODS]
    result=dict(status='verified_matched_development',runs=len(rows),selected_route_audits=len(checks),ppcpp_core_audits=cores,
        attempted_input_states=48,feasible_input_states=len(cases),infeasible_input_states=inp['infeasible'],
        development_base_maps=12,new_history_states=sum(c['metadata']['variant']!='H50' for c in cases.values()),
        min_selected_route_resource_margin=min(resource_margins) if resource_margins else None,
        hashes_verified=True,solver_called=False,holdout_used=False,verifier_sha256=sha(Path(__file__)),
        caveat='New states remain on tuning-development maps. One run per method/state/budget. No independent test or timing stability claim.')
    OUT.mkdir(parents=True,exist_ok=False)
    for name,o in (('summary.json',result),('method_budget_summary.json',summaries),('paired_comparisons.json',pairs),
        ('new_states_scale_summary.json',scales),('per_run_audits.json',checks),('enriched_ledger.json',rows)):
        write(OUT/name,o)
    write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',action='store_true');args=parser.parse_args()
    if args.inputs:print(json.dumps(verify_inputs()[0],ensure_ascii=False))
    else:verify_results()
