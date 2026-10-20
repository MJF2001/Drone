"""Independent read-only audit. Does not import kernel or call any planner."""
import collections,hashlib,json,sys
from pathlib import Path
import independent as ind
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def membership(expected,actual):assert len(actual)==len(set(actual)) and len(expected)==len(set(expected)) and set(actual)==set(expected)
def prefix(data,seal):assert len(data)>=seal['bytes'] and hashlib.sha256(data[:seal['bytes']]).hexdigest()==seal['sha256_of_prefix']
def ledger(rows):
    active=set();starts={};ends={}
    for e in rows:
        ident=e['attempt_id'];table=starts if e['event']=='start' else ends
        assert ident not in table and 'error' not in e;table[ident]=e
        if e['event']=='start':
            if e.get('parent'):assert e['parent'] in active
            active.add(ident)
        else:
            assert ident in active and e['kind']==starts[ident]['kind'];active.remove(ident)
    assert not active and starts.keys()==ends.keys()
    return starts,ends
def main():
    protocol=read('protocol.json');assert all(sha(ROOT/p)==h for p,h in read('freeze.json').items())
    prior=ROOT.parent/'OARP原生参照修订_v0.2_20261018'
    assert all(sha(prior/p)==h for p,h in read('previous_protection.json').items())
    assert all(sha(p)==h for p,h in read('dependency_lock_before_execution.json')['files'].items())
    data=(ROOT/'calls.jsonl').read_bytes();records=[json.loads(s) for s in data.decode('utf-8').splitlines()]
    starts,ends=ledger(records);counts=collections.Counter(e['kind'] for e in starts.values())
    assert counts['preparation']==3 and counts['response']==72
    assert counts['SCIP']<=protocol['SCIP_limit'] and counts['GLNS']<=protocol['GLNS_limit']
    jobs=protocol['planned'];expected=[j['plan_id'] for j in jobs]
    actual=[e['plan_id'] for e in starts.values() if e['kind'] in ('preparation','response')]
    membership(expected,actual);membership(expected,[p.stem for p in (ROOT/'results').glob('*.json')])
    results={j['plan_id']:read('results/'+j['plan_id']+'.json') for j in jobs};valid=complete=0
    for j in jobs:
        r=results[j['plan_id']];req=r['request'];ident=r['attempt_id'];d=r['core_detail']
        assert starts[ident]['plan_id']==j['plan_id']==ends[ident]['plan_id']
        assert starts[ident]['freeze_sha256']==sha(ROOT/'freeze.json')
        assert ends[ident]['result_sha256']==sha(ROOT/'results'/f"{j['plan_id']}.json")
        assert r['arm']==j['arm'] and req['seed']==j['seed'] and req['case_id']==j['case']
        assert r['method']==('RANK0' if j['arm']=='FULL' else 'REPLAN2')
        assert r['cap']==(None if j['arm']=='FULL' else 2*len(ind.targets(req)))
        assert r['flags']['route_valid']==(not ind.audit(req,r['route']))
        assert r['flags']['call_within_budget']==(r['public_seconds']<30)
        assert 'error' not in d
        if r['core_plan']:
            assert not ind.audit(req,r['core_plan']['route']);ind.check_strips(r['core_plan'],ind.targets(req))
        assert r['core_complete']==bool(r['flags']['core_candidate_valid'] and d.get('core_natural') and r['flags']['call_within_budget'])
        assert r['flags']['core_candidate_valid']==any(c['source']=='core' and c['accepted'] is not None for c in r['candidates'])
        for c in r['candidates']:
            assert not ind.audit(req,c['route']) and c['generated']<=c['audited']<30 and c['accepted']==c['audited']
        if r['candidates']:
            winner=min(r['candidates'],key=lambda c:(len(c['route']),c['accepted']))
            assert r['route']==winner['route'] and r['source']==winner['source']
        assert not (r['flags']['fallback_selected'] and r['flags']['natural'])
        assert sum(r['phase_seconds'].values())<=r['public_seconds']+1e-5
        sup=read('supervisor/'+r['plan_id']+'.json');assert sup['returncode']==0
        assert sup['process_wall_seconds']>=r['public_seconds']+r['bootstrap_seconds']
        assert Path(r['imported_modules']['rank']).resolve()==(ROOT/'sources/oarp_replan/ranks.py').resolve()
        assert Path(r['imported_modules']['tour']).resolve()==(ROOT/'sources/oarp_replan/tour.py').resolve()
        assert r['imported_modules']['glns'] in read('dependency_lock_before_execution.json')['files']
        if j['kind']=='preparation':
            assert req==read('inputs/'+j['case']+'.json') and r['core_complete']
        else:
            case=read('events/'+j['case']+'.json');expected_req=dict(case['request'],seed=j['seed'])
            assert req==expected_req and r['event_sha256']==sha(ROOT/'events'/f"{j['case']}.json")
            if j['arm']=='ATOMIC':assert all(b['kind']=='rank' for b in d.get('blocks',[]))
            valid+=r['flags']['route_valid'];complete+=r['core_complete']
        glog=[e for e in records if e.get('parent')==ident and e['kind']=='GLNS']
        if 'tour' in d:
            assert len(glog)==2;st=next(e for e in glog if e['event']=='start');en=next(e for e in glog if e['event']=='end')
            assert st['params']==d['tour']['params'] and st['matrix']==d['tour']['matrix'] and st['sets']==d['tour']['sets']
            assert all(st['params'][k]==protocol['GLNS'][k] for k in ('mode','trials','restarts'))
            assert st['params']['seed']==req['seed'] and 0<st['params']['max_time']<30
            tour=en['tour'];groups=st['sets'];matrix=st['matrix']
            assert len(tour)==len(groups) and all(sum(v in g for v in tour)==1 for g in groups)
            assert en['cost']==sum(matrix[a][b] for a,b in zip(tour,tour[1:]+tour[:1]))==len(r['core_plan']['route'])-1
    for name in ('rect6x3','rect12x4','rect24x5'):
        prep=results['prep_'+name];old=prep['request'];plan=prep['core_plan'];P=set(map(tuple,old['P']));route=list(map(tuple,plan['route']))
        seen=set();threshold=(len(P)+1)//2
        for index,p in enumerate(route):
            seen|={p}&P
            if len(seen)>=threshold:break
        references=[]
        for kind in ('unchanged','obstacle','straight','corner_obstacle'):
            case=read('events/'+name+'_'+kind+'.json');req=case['request'];ex=case['execution'];ev=case['event']
            assert case['preparation_attempt_id']==prep['attempt_id'] and case['preparation_sha256']==sha(ROOT/'results'/('prep_'+name+'.json'))
            assert ex['index']==index==ex['steps'] and ex['prefix']==plan['route'][:index+1]
            assert set(map(tuple,req['C']))==seen and req['current']==list(route[index])
            assert req['resource']==10000-index and req['base']==[-2,0]
            added=set(map(tuple,ev['added']));blocked=set(map(tuple,ev['blocked']));L,W=old['length'],old['width']
            expected_added={(x,y) for x in range(L,L+2) for y in range(W)} if kind in ('straight','corner_obstacle') else set()
            if kind=='corner_obstacle':expected_added|={(x,y) for x in range(L,L+4) for y in range(W,W+2)}
            assert added==expected_added and set(map(tuple,req['P']))==P|added
            free_before=set(map(tuple,old['F']));newfree=free_before|{(x+dx,y+dy) for x,y in added for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1))}
            assert set(map(tuple,req['F']))==newfree-blocked
            if kind in ('obstacle','corner_obstacle'):
                assert len(blocked)==1 and blocked<=P-seen-{route[index],tuple(old['base'])}
                for p in sorted(P-seen-{route[index],tuple(old['base'])},key=lambda p:(p[1],p[0])):
                    geo=ind.Geometry({'F':sorted(newfree-{p})});geo.path(route[index],tuple(old['base']))
                    if ((P-seen)|added)-{p}<=set(geo.rows[route[index]]):assert blocked=={p};break
            else:assert not blocked
            references.append(case['reference'])
            for f in case['reference']:
                parent=next(s for s in plan['strips'] if s['rank_id']==f['parent_rank_id'])
                assert f['axis']==parent['axis'] and set(map(tuple,f['cells']))<=set(map(tuple,parent['cells']))
                assert not set(map(tuple,f['cells']))&seen
                assert len(f['cells'])==len(f['indices'])
                assert all(plan['route'][i]==p for p,i in zip(f['cells'],f['indices']))
        assert all(x==references[0] for x in references)
    # Deliberately corrupted in-memory evidence must fail; no files are changed.
    negatives=0
    for ids in (actual[:-1],actual+['extra'],actual+[actual[0]]):
        try:membership(expected,ids)
        except AssertionError:negatives+=1
        else:raise AssertionError('plan negative accepted')
    for rows in (records[:-1],records+[records[0]]):
        try:ledger(rows)
        except AssertionError:negatives+=1
        else:raise AssertionError('ledger negative accepted')
    assert ind.selftest()['passed']
    if (ROOT/'analysis.json').exists():
        # Recompute all exact results in a read-only path, no saved booleans trusted.
        import analyze
        prior_args=sys.argv[:]
        try:sys.argv=['analyze.py','--check'];analyze.main()
        finally:sys.argv=prior_args
    if (ROOT/'ledger_seal.json').exists():prefix(data,read('ledger_seal.json'))
    if (ROOT/'manifest.json').exists():
        m=read('manifest.json');assert all(sha(ROOT/p)==h for p,h in m.items())
        membership(list(m),[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='manifest.json'])
    print(json.dumps({'verification':'PASS','complete_entries':len(actual),'calls_by_kind':dict(counts),
        'response_final_routes_valid':valid,'response_core_complete':complete,'negative_plan_and_ledger_tests':negatives,
        'old_files_unchanged':len(read('previous_protection.json')),'new_solver_calls':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
