"""Independent saved-input mathematics and isolated mock regressions.
run writes supplemental evidence; --check is read-only and imports no planner.
No SCIP/GLNS/coverage planner call is made by either mode.
"""
import ast, collections, copy, hashlib, itertools, json, math, os
from pathlib import Path
import subprocess, sys, tempfile, time

ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def qset(req):return (set(map(tuple,req['P']))-set(map(tuple,req['C'])))&set(map(tuple,req['F']))
def endkeys(strips):
    return {(s['axis'],side,tuple(s['cells'][i])) for s in strips for side,i in (('L',0),('R',-1))}

def rank_frontier(points,old):
    # Enumerate exact disjoint straight-segment covers. Singleton H and V are
    # distinct; adjacent collinear segments may retain an intentional old cut.
    previous={e for e in endkeys(old) if e[2] in points};best={};covers=0
    def visit(left,segments):
        nonlocal covers
        if not left:
            covers+=1;now=endkeys(segments)
            directions={tuple(p):s['axis'] for s in segments for p in s['cells']}
            added=len(now-previous)
            extended=sum(directions[p]==axis for axis,side,p in previous-now)
            twice=2*added+extended;n=len(segments)
            if twice not in best or n<best[twice]['rank_count']:
                best[twice]={'rank_count':n,'segments':segments}
            return
        p=min(left)
        for axis,(dx,dy) in (('H',(1,0)),('V',(0,1))):
            run=[];z=p
            while z in left:
                run.append(z)
                visit(left-set(run),segments+[{'axis':axis,'cells':run[:]}])
                z=z[0]+dx,z[1]+dy
    visit(set(points),[])
    return {'covers_enumerated':covers,'frontier':{str(k):v for k,v in sorted(best.items())}}

def distances(free,start):
    queue=collections.deque([start]);d={start:0}
    while queue:
        x,y=queue.popleft()
        for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if p in free and p not in d:d[p]=d[x,y]+1;queue.append(p)
    return d

def matrix_check(result):
    detail=result['core_detail'];tour=detail.get('tour')
    if not tour:return None
    states=[]
    for b in detail['blocks']:
        p=list(map(tuple,b['path']));states.extend((p,p[::-1]))
    start=len(states);end=start+1
    states.extend(([tuple(result['request']['current'])],[tuple(result['request']['base'])]))
    free=set(map(tuple,result['request']['F']));rows={}
    def dist(a,b):
        if a not in rows:rows[a]=distances(free,a)
        return rows[a][b]
    edges={(i,j):len(states[i])-1+dist(states[i][-1],states[j][0])
           for i in range(start+1) for j in range(end+1) if i!=j and j!=start}
    penalty=(len(states)+1)*(max(edges.values(),default=0)+1)
    matrix=[[edges.get((i,j),penalty) for j in range(len(states))] for i in range(len(states))]
    matrix[end][start]=0
    assert matrix==tour['matrix']
    groups=[[i,i+1] for i in range(0,start,2)]+[[start],[end]]
    assert groups==tour['sets']
    order=tour['order'];assert order[0]==start and order[-1]==end
    assert len(order)==len(groups) and all(sum(n in g for n in order)==1 for g in groups)
    cost=sum(matrix[a][b] for a,b in zip(order,order[1:]+order[:1]))
    assert cost==tour['cost']==len(result['core_plan']['route'])-1
    return matrix,groups,start,end

def exact_saved_tour(result):
    matrix,groups,start,end=matrix_check(result);service=groups[:-2];best=None;trials=0
    # Full permutations and orientations, no use of the production Held-Karp.
    for perm in itertools.permutations(service):
        for choices in itertools.product(*perm):
            trials+=1;order=(start,)+choices+(end,)
            cost=sum(matrix[a][b] for a,b in zip(order,order[1:]))
            if best is None or cost<best[0]:best=(cost,order)
    return {'enumerated_tours':trials,'exact_cost':best[0],'witness':best[1],
            'saved_cost':result['core_detail']['tour']['cost'],
            'saved_gap':result['core_detail']['tour']['cost']-best[0]}

def raw_vector_check(result,record):
    if not record['has_incumbent']:
        assert record['status']=='infeasible';return {'status':'infeasible_no_primal_vector'}
    vals=record['values'];mapping=record['mapping']
    o={ast.literal_eval(k):vals[v] for k,v in mapping['orientation'].items()}
    y={ast.literal_eval(k):vals[v] for k,v in mapping['endpoint'].items()}
    points=qset(result['request']);eps=1e-6
    assert set(o)=={(a,p) for p in points for a in ('H','V')}
    assert set(y)=={(a,s,p) for p in points for a in ('H','V') for s in ('L','R')}
    assert all(v is not None and -eps<=v<=1+eps for v in vals.values())
    for p in points:
        assert abs(o['H',p]+o['V',p]-1)<eps
        for axis,(dx,dy) in (('H',(1,0)),('V',(0,1))):
            for side,sign in (('L',-1),('R',1)):
                neighbor=p[0]+sign*dx,p[1]+sign*dy
                assert y[axis,side,p]+eps>=o[axis,p]-o.get((axis,neighbor),0)
    added=extensions=0
    if result['method']=='REPLAN2':
        old=read('events/'+result['request']['case_id']+'.json')['reference']
        previous=endkeys(old)
        # _build appends one beta for every endpoint in insertion order. Names
        # are actual SCIP variable names, not labels reconstructed from values.
        endpoint_order=[(a,s,p) for p in sorted(points) for a in ('H','V') for s in ('L','R')]
        beta_names=mapping['auxiliary_beta_names'];assert len(beta_names)==len(endpoint_order)
        assert [int(n[1:]) for n in beta_names]==sorted(int(n[1:]) for n in beta_names)
        for k,name in zip(endpoint_order,beta_names):
            axis,side,p=k;lower=(1-y[k] if k in previous else 0)+o[axis,p]-1
            assert vals[name]+eps>=lower
        added=sum(v for k,v in y.items() if k not in previous)
        extensions=sum(vals[n] for n in beta_names)
        assert added+extensions/2<=result['cap']+eps
    else:assert not mapping['auxiliary_beta_names']
    objective=sum(y.values())/2+(added+extensions/2)/(result['cap']+1) if result['method']=='REPLAN2' else sum(y.values())/2
    assert abs(objective-record['objective'])<eps
    assert record['dual_bound']<=objective+eps
    assert abs(objective-result['core_detail']['objective'])<eps
    return {'status':record['status'],'primal_objective':objective,
            'all_values_integral':all(abs(v-round(v))<eps for v in vals.values()),
            'beta_mapping':'endpoint insertion order; actual variable names recorded'}

def mathematics():
    jobs=read('protocol.json')['planned'];results={j['plan_id']:read('results/'+j['plan_id']+'.json') for j in jobs}
    ledger=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    starts={e['attempt_id']:e for e in ledger if e['event']=='start'}
    rankrecords=[e for e in ledger if e['event']=='end' and e['kind']=='SCIP']
    byid={r['attempt_id']:r for r in results.values()};raw=[]
    for e in rankrecords:
        r=byid[e['parent']];x=raw_vector_check(r,e);x.update(plan_id=r['plan_id'],attempt_id=e['attempt_id']);raw.append(x)
    frontiers={};comparisons=[]
    for n in (1,2,4,5,6,7,8):
        case=read(f'events/N{n}.json');f=rank_frontier(qset(case['request']),case['reference']);frontiers[f'N{n}']=f
        for slot in ('rank0','cap0','cap2','capmax'):
            result=results[f'N{n}_{slot}'];cap=result['cap'];best=None
            for twice,w in f['frontier'].items():
                bound=int(twice)/2
                if slot!='rank0' and bound>cap:continue
                value=w['rank_count']+(bound/(cap+1) if slot!='rank0' else 0)
                if best is None or value<best:best=value
            detail=result['core_detail']
            if best is None:assert detail['status']=='infeasible'
            else:assert detail['status']=='optimal' and abs(detail['objective']-best)<1e-6
            comparisons.append({'plan_id':result['plan_id'],'independent_optimum':best,'saved_status':detail['status'],
                                'saved_objective':detail.get('objective')})
    matrices=[]
    for name,r in results.items():
        m=matrix_check(r)
        if m is not None:
            # Cross-check actual GLNS call inputs/output against saved core.
            logs=[e for e in ledger if e.get('parent')==r['attempt_id'] and e['kind']=='GLNS']
            assert len(logs)==2;st=next(e for e in logs if e['event']=='start');en=next(e for e in logs if e['event']=='end')
            assert st['matrix']==m[0] and st['sets']==m[1] and st['params']==r['core_detail']['tour']['params']
            tour=en['tour'];assert len(tour)==len(m[1]) and all(sum(v in g for v in tour)==1 for g in m[1])
            assert en['cost']==sum(m[0][a][b] for a,b in zip(tour,tour[1:]+tour[:1]))==r['core_detail']['tour']['cost']
            matrices.append(name)
    exact={name:exact_saved_tour(results[name]) for name in read('supplement_protocol.json')['exact_saved_gtsp']}
    assert all(v['saved_gap']>=0 for v in exact.values())
    return {'rank_enumerations':frontiers,'rank_comparisons':comparisons,'raw_SCIP_vectors':raw,
            'independent_matrix_checks':matrices,'exact_saved_gtsp':exact,
            'new_SCIP_calls':0,'new_GLNS_calls':0,'new_coverage_planner_calls':0}

def mocks():
    import revision as r
    evidence={};original_hash=sha(ROOT/'calls.jsonl');old_sources=dict(read('seal.json'))
    # Both methods: final mandatory audit crosses a shared absolute deadline.
    for method in ('RANK0','REPLAN2'):
        clock={'now':0,'audits':0,'engines':0}
        req={'F':[(0,0)],'P':[],'C':[],'current':(0,0),'base':(0,0),'resource':0,'seed':0,'old_route':[]}
        def engine(*a):clock['engines']+=1;return None,{}
        def auditor(req,route):
            clock['audits']+=1
            if clock['audits']==2:clock['now']=2
            return r.audit(req,route)
        out=r.entry(req,method,0,[],'supplement_mock',seconds=1,clock=lambda:clock['now'],auditor=auditor,engine=engine)
        assert out['public_seconds']==2 and not out['flags']['call_within_budget'] and out['flags']['candidate_accepted_in_time']
        evidence[method+'_final_deadline']={'elapsed':out['public_seconds'],'call_within_budget':False,'timely_candidate_retained':True,'real_solver_calls':0}
    # Future connector obstruction splits packets and never fabricates a bent rank.
    from types import SimpleNamespace
    route=[(0,0),(1,0),(2,0),(2,1),(1,1),(0,1),(0,2),(1,2),(2,2)]
    fragments=[{'rank_id':'a','parent_rank_id':'a','axis':'H','cells':[(0,0),(1,0)],'indices':[0,1]},
               {'rank_id':'b','parent_rank_id':'b','axis':'H','cells':[(1,2),(2,2)],'indices':[7,8]}]
    ranks=[SimpleNamespace(key=r.key(f['axis'],f['cells']),axis=f['axis'],cells=f['cells']) for f in fragments]
    whole=r.packets(ranks,fragments,route,set(route));split=r.packets(ranks,fragments,route,set(route)-{(1,1)})
    assert len(whole)==1 and len(split)==2 and sum(len(b['members']) for b in split)==2
    evidence['blocked_connector_fixture']={'whole_packets':1,'blocked_packets':2,'preserved_atomic_members':2,'solver_calls':0}
    # Inject failure before start persistence in the real worker. The entry is a
    # spy, so even a regression cannot invoke a real planner or change results.
    original_emit,original_entry,original_write=r.emit,r.entry,r.write
    spy={'entries':0,'writes':0}
    def spyentry(*a,**k):spy['entries']+=1;return {'status':'finished'}
    def spywrite(*a,**k):spy['writes']+=1
    def failstart(e):raise OSError('injected start fsync failure')
    r.entry=spyentry;r.write=spywrite;r.emit=failstart
    try:
        try:r.worker('boundary_RANK0_zero_at_base')
        except OSError:pass
        else:raise AssertionError('start failure swallowed')
        assert spy=={'entries':0,'writes':0}
        evidence['start_write_failure']={'entries':0,'result_writes':0,'raised':True}
        events=[]
        def failend(e):
            if e['event']=='end':raise OSError('injected end fsync failure')
            events.append(e)
        r.emit=failend
        try:r.worker('boundary_RANK0_zero_at_base')
        except OSError:pass
        else:raise AssertionError('end failure swallowed')
        assert spy['entries']==1 and spy['writes']==1 and len(events)==1
        evidence['end_write_failure']={'mock_entries':1,'start_without_end':True,'raised':True,'no_real_result_written':True}
    finally:r.emit,r.entry,r.write=original_emit,original_entry,original_write
    # Actual child starts and sleeps; timeout kills it. This is a process-control
    # test, explicitly not a killed planner or a simulated successful end.
    with tempfile.TemporaryDirectory(prefix='oarp_watchdog_') as tmp:
        ready=Path(tmp)/'started';script='import pathlib,time,sys;pathlib.Path(sys.argv[1]).write_text("start");time.sleep(30)'
        began=time.perf_counter()
        try:subprocess.run([sys.executable,'-B','-c',script,str(ready)],timeout=.5,check=True,capture_output=True)
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('sleeping mock was not killed')
        assert ready.read_text()=='start'
        evidence['actual_process_watchdog']={'child_really_started':True,'timeout_seconds':.5,'wall_seconds':time.perf_counter()-began,
            'planner_calls':0,'end_fabricated':False,'scope':'mock sleep child only; production planner hard termination not observed'}
    assert sha(ROOT/'calls.jsonl')==original_hash and all(sha(ROOT/p)==h for p,h in old_sources.items())
    return evidence

def integrity():
    # Stronger joins and evidence-only rejection tests. No mutation of artifacts.
    jobs=read('protocol.json')['planned'];ids=[j['plan_id'] for j in jobs]
    def check_ids(planned,actual):
        assert len(planned)==len(set(planned)) and len(actual)==len(set(actual)) and set(planned)==set(actual)
    actual=[p.stem for p in (ROOT/'results').glob('*.json')];check_ids(ids,actual)
    rejected=0
    for changed in (actual[:-1],actual+['unexpected'],actual+[actual[0]]):
        try:check_ids(ids,changed)
        except AssertionError:rejected+=1
        else:raise AssertionError('invalid plan membership accepted')
    for n in (1,2,4,5,6,7,8):
        case=read(f'events/N{n}.json')
        for slot in ('rank0','cap0','cap2','capmax'):
            result=read(f'results/N{n}_{slot}.json');assert result['request']==case['request']
            assert result['method']==('RANK0' if slot=='rank0' else 'REPLAN2')
            assert result['cap']=={'rank0':None,'cap0':0,'cap2':2,'capmax':2*len(qset(case['request']))}[slot]
            assert result['request']['seed']==20261018
        for f in case['reference']:
            parent=next(s for s in case['initial_plan']['strips'] if s['rank_id']==f['parent_rank_id'])
            assert f['axis']==parent['axis'] and set(map(tuple,f['cells']))<=set(map(tuple,parent['cells']))
    return {'planned_membership_negative_cases_rejected':rejected,'exact_request_method_cap_seed_joins':28,'old_reference_parent_checks':True}

def main():
    check='--check' in sys.argv
    seal=read('supplement_seal.json');assert sha(__file__)==seal['supplement.py'] and sha(ROOT/'supplement_protocol.json')==seal['supplement_protocol.json']
    math_result=mathematics();joins=integrity()
    if check:
        # Compare canonical JSON so tuples and disk lists agree.
        assert json.loads(json.dumps(math_result))==read('supplement_math.json')
        assert joins==read('supplement_integrity.json')
        mock=read('supplement_mocks.json');assert all(mock[m+'_final_deadline']['call_within_budget'] is False for m in ('RANK0','REPLAN2'))
        assert mock['start_write_failure']['entries']==0 and mock['end_write_failure']['raised']
        assert mock['actual_process_watchdog']['child_really_started']
    else:
        assert not (ROOT/'supplement_math.json').exists(),'no repeat of exact computations in execution mode'
        save('supplement_mocks.json',mocks());save('supplement_math.json',math_result);save('supplement_integrity.json',joins)
    print(json.dumps({'supplement_verification':'PASS','rank_state_enumerations':len(math_result['rank_enumerations']),
        'rank_configuration_comparisons':len(math_result['rank_comparisons']),
        'raw_SCIP_checks':len(math_result['raw_SCIP_vectors']),'matrix_checks':len(math_result['independent_matrix_checks']),
        'exact_saved_gtsp':math_result['exact_saved_gtsp'],'new_planner_calls':0,'read_only':check},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
