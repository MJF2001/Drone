"""Independent read-only verification: no planner imports, no solver, no writes."""
import collections,hashlib,itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def check_route(req,route):
    P,F,C=(set(map(tuple,req[k])) for k in ('P','F','C'));Q=(P-C)&F
    route=list(map(tuple,route));e=[]
    if not route:return ['empty']
    if route[0]!=tuple(req['current']):e.append('start')
    if route[-1]!=tuple(req['base']):e.append('base')
    if not set(route)<=F:e.append('collision')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(route,route[1:])):e.append('step')
    if not Q<=set(route):e.append('coverage')
    if len(route)-1>req['resource']:e.append('resource')
    return e

def check_plan(plan,targets):
    route=list(map(tuple,plan['route']));seen=[];ids=[]
    for s in plan['strips']:
        cells=list(map(tuple,s['cells']));assert cells and s['axis'] in ('H','V')
        step=(1,0) if s['axis']=='H' else (0,1)
        assert all((b[0]-a[0],b[1]-a[1])==step for a,b in zip(cells,cells[1:]))
        ordered=cells[::-1] if s['reversed_direction'] else cells
        assert route[s['service_start']:s['service_end']+1]==ordered
        ids.append(s['rank_id']);seen.extend(cells)
    assert len(ids)==len(set(ids)) and len(seen)==len(set(seen))
    assert set(seen)==set(map(tuple,targets))
    for packet in plan.get('packets',[]):
        assert route[packet['start']:packet['end']+1]==list(map(tuple,packet['path']))

def main():
    assert all(sha(ROOT/p)==h for p,h in read('seal.json').items())
    old=ROOT.parent/'DeepSeek_OARP原生参照核验_20261018'
    assert all(sha(old/p)==h for p,h in read('source_protection.json').items())
    events=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    starts={};ends={};active=set()
    for e in events:
        ident=e['attempt_id'];table=starts if e['event']=='start' else ends
        assert ident not in table;table[ident]=e
        if e['event']=='start':
            if e.get('parent'):assert e['parent'] in active
            active.add(ident)
        else:
            assert ident in active;active.remove(ident);assert 'error' not in e
    assert not active and starts.keys()==ends.keys()
    kinds=collections.Counter(e['kind'] for e in starts.values())
    assert sum(kinds[k] for k in ('preparation','event','boundary'))<=48
    assert kinds['SCIP']<=250 and kinds['GLNS']<=64
    planned=read('protocol.json')['planned'];expected={j['plan_id'] for j in planned}
    actual=[e['plan_id'] for e in starts.values() if e['kind'] in ('preparation','event','boundary')]
    assert len(actual)==len(set(actual)) and set(actual)==expected
    responses=[]
    for j in planned:
        result=read('results/'+j['plan_id']+'.json');req=result['request'];ident=result['attempt_id']
        assert ends[ident]['result_sha256']==sha(ROOT/('results/'+j['plan_id']+'.json'))
        assert starts[ident]['plan_id']==j['plan_id']
        assert result['flags']['call_within_budget']==(result['public_seconds']<5)
        if result['flags']['route_valid']:
            assert not check_route(req,result['route'])
        else:assert check_route(req,result['route'])
        accepted=[c for c in result['candidates'] if c['accepted'] is not None]
        for c in accepted:assert not check_route(req,c['route']) and c['audited']<5
        if accepted:
            winner=min(accepted,key=lambda c:(len(c['route']),c['accepted']))
            assert result['source']==winner['source'] and result['route']==winner['route']
        if result['core_plan'] is not None:
            targets=(set(map(tuple,req['P']))-set(map(tuple,req['C'])))&set(map(tuple,req['F']))
            check_plan(result['core_plan'],targets)
            tour=result['core_detail'].get('tour')
            if tour:assert tour['cost']==len(result['core_plan']['route'])-1
        assert not (result['flags']['fallback_selected'] and result['flags']['natural'])
        if j['kind']=='event':responses.append(result)
    preparations=read('inputs/preparations.json')
    for n in (1,2,3,4,5,6,7,8):
        case=read(f'events/N{n}.json');ex=case['execution'];req=case['request'];plan=case['initial_plan']
        prep=preparations[0 if n<7 else n-6]
        prefix=plan['route'][:ex['index']+1]
        covered=set(map(tuple,prefix))&set(map(tuple,prep['published']))
        assert covered==set(map(tuple,req['C'])) and ex['current']==prefix[-1]
        assert req['resource']==1000-(len(prefix)-1)
        assert len(covered)>=prep['prefix_targets']
        if len(prefix)>1:assert len(set(map(tuple,prefix[:-1]))&set(map(tuple,prep['published'])))<prep['prefix_targets']
        original={s['rank_id']:s for s in plan['strips']}
        for f in case['reference']:
            source=original[f['parent_rank_id']];assert f['axis']==source['axis']
            for p,i in zip(f['cells'],f['indices']):assert plan['route'][i]==p
            assert not set(map(tuple,f['cells']))&covered
        if n in (2,6):assert case['event']['blocked']==[[1,1]]
        if n==3:assert not case['applicable'] and not any(r['request']['case_id']=='N3' for r in responses)
        if n in (1,2,4,5,6):assert case['reference']==read('events/N1.json')['reference']
    n1=[r for r in responses if r['request']['case_id']=='N1']
    assert all(r['flags']['core_candidate_valid'] for r in n1)
    assert all(len(r['core_plan']['route'])-1==8 for r in n1)
    n2zero=read('results/N2_cap0.json');assert n2zero['core_detail']['status']=='infeasible'
    assert read('plans/prep_sparse.json')['start']==[2,0]
    assert read('events/N8.json')['execution']['steps']==2
    for method in ('RANK0','REPLAN2'):
        assert read(f'results/boundary_{method}_zero_at_base.json')['status']=='finished'
        assert not read(f'results/boundary_{method}_empty_away_short.json')['flags']['route_valid']
        assert not read(f'results/boundary_{method}_nonempty_over_resource.json')['flags']['route_valid']
        a=read(f'results/boundary_{method}_audit_baseline.json')['public_seconds']
        b=read(f'results/boundary_{method}_audit_slow.json')['public_seconds']
        assert b-a>=.09,(method,a,b)
    # Negative checks test the verifier, without a planner or file mutation.
    first=responses[0];req=first['request'];route=first['route']
    bad=dict(req,resource=0);assert 'resource' in check_route(bad,route)
    assert check_route(req,route[:-1]) and check_route(req,[[999,999]]+route[1:])
    badplan=json.loads(json.dumps(read('plans/prep_rect.json')));badplan['strips'][0]['axis']='V'
    try:check_plan(badplan,badplan['service_targets'])
    except AssertionError:pass
    else:raise AssertionError('negative wrong-axis accepted')
    if (ROOT/'manifest.json').exists():assert all(sha(ROOT/p)==h for p,h in read('manifest.json').items())
    print(json.dumps({'verification':'PASS','complete_entry_calls':len(actual),'nested':dict(kinds),
        'event_routes_valid':sum(r['flags']['route_valid'] for r in responses),'event_responses':len(responses),
        'core_candidates':sum(r['flags']['core_candidate_valid'] for r in responses),
        'N1_core_steps':[len(r['core_plan']['route'])-1 for r in n1],
        'N3':'not_applicable','old_files_unchanged':len(read('source_protection.json')),'new_solver_calls':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
