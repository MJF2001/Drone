"""Isolated OARP repair. python -B -X utf8 revision.py prepare|test|freeze|run|verify.
No original delivery file is written. No developer maps or holdouts are used.
"""
import argparse, collections, copy, hashlib, itertools, json, math, os
from pathlib import Path
import shutil, subprocess, sys, time, uuid
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'DeepSeek_OARP原生参照核验_20261018'
DEPS=ROOT.parent/'DeepSeek_底层算法开发比较_20261018/sources/reference_tree/研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps'
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'sources'),str(DEPS)]
ACTIVE=None

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=ROOT/p; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def emit(v):
    with (ROOT/'calls.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n'); f.flush(); os.fsync(f.fileno())
def finite(v):
    try: return float(v) if math.isfinite(float(v)) and abs(float(v))<1e50 else None
    except (TypeError,ValueError): return None

class Expired(TimeoutError): pass
class Budget:
    def __init__(self,seconds=5,clock=None):
        self.clock=clock or time.perf_counter; self.start=self.clock(); self.at=self.start+seconds; self.limit=seconds
    def elapsed(self): return self.clock()-self.start
    def check(self):
        if self.clock()>=self.at: raise Expired('public deadline')
    def remaining(self): self.check(); return self.at-self.clock()

class Grid:
    def __init__(self,free,current,base,budget):
        self.free=set(map(tuple,free)); self.s=SimpleNamespace(current=tuple(current),base=tuple(base)); self.budget=budget
        self.deadline=budget.at; self.rows={}
    def check_time(self): self.budget.check()
    def row(self,a):
        self.check_time()
        if a not in self.rows:
            queue=collections.deque([a]); prev={a:None}
            while queue:
                self.check_time(); x,y=queue.popleft()
                for q in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
                    if q in self.free and q not in prev: prev[q]=(x,y); queue.append(q)
            self.rows[a]=prev
        return self.rows[a]
    def path(self,a,b):
        a,b=tuple(a),tuple(b); prev=self.row(a)
        if b not in prev: raise ValueError('unreachable')
        out=[]; q=b
        while q is not None: out.append(q); q=prev[q]
        self.check_time(); return tuple(reversed(out))
    def distance(self,a,b): return len(self.path(a,b))-1

def sets(req):
    P,F,C=(set(map(tuple,req[k])) for k in ('P','F','C'))
    return P,F,C,(P-C)&F,(P-C)-F

def audit(req,route):
    P,F,C,Q,D=sets(req); route=list(map(tuple,route)); errors=[]
    if not C<=P: errors.append('ledger_not_published')
    if not route: errors.append('empty')
    else:
        if route[0]!=tuple(req['current']): errors.append('start')
        if route[-1]!=tuple(req['base']): errors.append('base')
        if not set(route)<=F: errors.append('collision')
        if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(route,route[1:])): errors.append('step')
        if not Q<=set(route): errors.append('coverage')
        if len(route)-1>req['resource']: errors.append('resource')
    return {'valid':not errors,'errors':errors,'steps':len(route)-1 if route else None,'Q':sorted(Q),'D':sorted(D)}

def validate_plan(plan):
    route=list(map(tuple,plan['route'])); ids=set(); cells=[]
    for s in plan['strips']:
        assert s['rank_id'] not in ids; ids.add(s['rank_id'])
        pts=list(map(tuple,s['cells'])); axis=s['axis']; assert axis in ('H','V') and pts
        dx,dy=(1,0) if axis=='H' else (0,1)
        assert all((b[0]-a[0],b[1]-a[1])==(dx,dy) for a,b in zip(pts,pts[1:]))
        ordered=pts[::-1] if s['reversed_direction'] else pts
        assert route[s['service_start']:s['service_end']+1]==ordered
        assert s['connector_start']<=s['service_start']<=s['service_end']
        cells.extend(pts)
    assert len(cells)==len(set(cells))
    if 'service_targets' in plan: assert set(cells)==set(map(tuple,plan['service_targets']))
    for packet in plan.get('packets',[]):
        assert route[packet['start']:packet['end']+1]==list(map(tuple,packet['path']))
    return True

def normalize(plan,covered):
    """Only pre-event coverage is removed; no post-event free map is read."""
    covered=set(map(tuple,covered)); fragments=[]
    for strip in plan['strips']:
        run=[]
        def flush():
            nonlocal run
            if run:
                fragments.append({'rank_id':strip['rank_id']+f'/fragment{len(fragments)}',
                    'parent_rank_id':strip['rank_id'],'axis':strip['axis'],
                    'cells':[p for p,i in run],'indices':[i for p,i in run]})
            run=[]
        for offset,p in enumerate(map(tuple,strip['cells'])):
            i=strip['service_end']-offset if strip['reversed_direction'] else strip['service_start']+offset
            if p in covered: flush()
            else: run.append((p,i))
        flush()
    return sorted(fragments,key=lambda f:min(f['indices']))

def key(axis,cells): return axis,tuple(cells[0]),tuple(cells[-1])

def packets(ranks,fragments,old_route,free):
    """A packet is a path with multiple atomic straight ranks, never a fake rank."""
    route=tuple(map(tuple,old_route)); free=set(map(tuple,free)); remaining={r.key:r for r in ranks}; out=[]; group=[]
    def flush():
        nonlocal group
        if not group:return
        start=min(group[0]['indices']); end=max(group[-1]['indices']); path=route[start:end+1]
        assert path and set(path)<=free
        members=[]
        for f in group:
            lo,hi=min(f['indices']),max(f['indices'])
            members.append({'rank_id':f['rank_id'],'parent_rank_id':f['parent_rank_id'],
                'axis':f['axis'],'cells':f['cells'],'start':lo-start,'end':hi-start,
                'reverse':f['indices'][0]>f['indices'][-1]})
        out.append({'kind':'path','path':path,'members':members,'rank_keys':[key(f['axis'],f['cells']) for f in group]}); group=[]
    for f in fragments:
        k=key(f['axis'],f['cells'])
        if k not in remaining:flush();continue
        lo,hi=min(f['indices']),max(f['indices'])
        if not set(route[lo:hi+1])<=free:raise ValueError('unchanged rank crosses obstacle')
        if group:
            a=max(group[-1]['indices'])
            if not set(route[a:lo+1])<=free:flush()
        group.append(f); remaining.pop(k)
    flush()
    for i,r in enumerate(sorted(remaining.values(),key=lambda r:r.key)):
        out.append({'kind':'rank','path':r.cells,'rank_keys':[r.key],
                    'members':[{'rank_id':'new:'+hashlib.sha256(repr(r.key).encode()).hexdigest()[:12],
                    'parent_rank_id':None,'axis':r.axis,'cells':r.cells,'start':0,'end':len(r.cells)-1,'reverse':False}]})
    assert {k for b in out for k in b['rank_keys']}=={r.key for r in ranks}
    for b in out:
        assert {tuple(p) for m in b['members'] for p in m['cells']}<=set(b['path'])
    return out

def annotate(blocks,order,grid,plan_id):
    route=[grid.s.current]; strips=[]; packet_spans=[]
    for node in order[1:-1]:
        b=blocks[node//2]; rev=bool(node%2); path=tuple(reversed(b['path'])) if rev else tuple(b['path'])
        connector_start=len(route)-1; route.extend(grid.path(route[-1],path[0])[1:]); start=len(route)-1
        route.extend(path[1:]); packet_spans.append({'start':start,'end':len(route)-1,'path':path,'kind':b['kind']})
        members=list(reversed(b['members'])) if rev else b['members']
        prior=connector_start
        for m in members:
            lo,hi=(len(path)-1-m['end'],len(path)-1-m['start']) if rev else (m['start'],m['end'])
            strips.append({'rank_id':m['rank_id'],'parent_rank_id':m['parent_rank_id'],'axis':m['axis'],
                'cells':m['cells'],'visit_order':len(strips),'reversed_direction':bool(m['reverse'])^rev,
                'service_start':start+lo,'service_end':start+hi,'connector_start':prior})
            prior=start+hi
    route.extend(grid.path(route[-1],grid.s.base)[1:])
    plan={'plan_id':plan_id,'route':route,'strips':strips,'packets':packet_spans,
          'start':grid.s.current,'end':grid.s.base,'service_targets':[p for s in strips for p in s['cells']]}
    validate_plan(plan); return plan

def install_trace():
    from oarp_replan import ranks
    if getattr(ranks,'_monitored',False):return
    build=ranks._build
    class ModelProxy:
        def __init__(self,m,orient,endpoint): self.m=m; self.orient=orient; self.endpoint=endpoint
        def __getattr__(self,k):return getattr(self.m,k)
        def optimize(self):
            ident=str(uuid.uuid4()); variables=list(self.m.getVars()); n=self.m.getNVars(); c=self.m.getNConss()
            emit({'event':'start','attempt_id':ident,'parent':ACTIVE,'kind':'SCIP','variables_before':n,'constraints_before':c})
            try:
                self.m.optimize(); sol=self.m.getBestSol() if self.m.getNSols() else None
                vals={v.name:finite(self.m.getSolVal(sol,v)) for v in variables} if sol is not None else {}
                names={'orientation':{repr(k):v.name for k,v in self.orient.items()},'endpoint':{repr(k):v.name for k,v in self.endpoint.items()}}
                named=set(names['orientation'].values())|set(names['endpoint'].values())
                names['auxiliary_beta_names']=[v.name for v in variables if v.name not in named]
                emit({'event':'end','attempt_id':ident,'parent':ACTIVE,'kind':'SCIP','status':str(self.m.getStatus()),
                    'has_incumbent':sol is not None,'objective':finite(self.m.getSolObjVal(sol)) if sol is not None else None,
                    'dual_bound':finite(self.m.getDualbound()),'gap':finite(self.m.getGap()) if sol is not None else None,
                    'values':vals,'mapping':names})
            except BaseException as exc:
                emit({'event':'end','attempt_id':ident,'parent':ACTIVE,'kind':'SCIP','error':repr(exc)});raise
    def wrapped(*a,**kw):
        model,o,e,m=build(*a,**kw);return ModelProxy(model,o,e),o,e,m
    ranks._build=wrapped;ranks._monitored=True

def solve_core(req,method,cap,fragments,budget,grid,ident):
    install_trace()
    from oarp_replan.ranks import Rank,rank_replan
    from oarp_replan.tour import gtsp_instance,decode_tour
    import glns
    Q=sets(req)[3]; old=tuple(Rank(f['axis'],tuple(map(tuple,f['cells']))) for f in fragments) if method=='REPLAN2' else ()
    ranked=rank_replan(Q,old,cap,2 if method=='REPLAN2' else 0,budget.at)
    detail={k:v for k,v in ranked.items() if k!='ranks'}
    if ranked.get('ranks') is None:return None,detail
    rr=ranked['ranks'];detail['ranks']=[{'axis':r.axis,'cells':r.cells} for r in rr]
    if not rr:
        route=grid.path(grid.s.current,grid.s.base)
        return {'route':route,'strips':[],'packets':[],'service_targets':[],'start':grid.s.current,'end':grid.s.base},detail
    blocks=packets(rr,fragments if method=='REPLAN2' else (),req['old_route'],req['F'])
    states,groups,matrix,start,end,penalty=gtsp_instance(grid,blocks); budget.check()
    sid=str(uuid.uuid4()); params={'mode':'default','trials':5,'restarts':3,'seed':req['seed'],'max_time':budget.remaining(),'verbose':0}
    emit({'event':'start','attempt_id':sid,'parent':ACTIVE,'kind':'GLNS','params':params,'sets':groups,'matrix':matrix})
    try:
        sol=glns.solve(matrix,groups,**params)
        emit({'event':'end','attempt_id':sid,'parent':ACTIVE,'kind':'GLNS','cost':sol.cost,'tour':list(sol.tour),'timeout':bool(sol.timeout),'iterations':sol.total_iterations})
    except BaseException as exc:
        emit({'event':'end','attempt_id':sid,'parent':ACTIVE,'kind':'GLNS','error':repr(exc)});raise
    budget.check(); route,cost,order=decode_tour(grid,states,groups,matrix,start,end,sol.tour,penalty)
    plan=annotate(blocks,order,grid,ident)
    assert tuple(plan['route'])==route and len(route)-1==cost
    detail.update(blocks=blocks,tour={'sets':groups,'matrix':matrix,'order':order,'cost':cost,'timeout':bool(sol.timeout),'params':params},
                  core_natural=ranked['status']=='optimal' and not sol.timeout)
    return plan,detail

def entry(req,method,cap,fragments,ident,seconds=5,clock=None,auditor=None,engine=None):
    budget=Budget(seconds,clock); grid=Grid(req['F'],req['current'],req['base'],budget); audit_fn=auditor or audit
    candidates=[]; detail={}; diagnostics=[]; core_plan=None
    def offer(route,label,plan=None):
        generated=budget.elapsed(); a=audit_fn(req,route); checked=budget.elapsed()
        item={'source':label,'route':route,'generated':generated,'audited':checked,'accepted':checked if a['valid'] and checked<seconds else None,'audit':a}
        (candidates if item['accepted'] is not None else diagnostics).append(item)
        return item
    try:
        P,F,C,Q,D=sets(req)
        if not C<=P or req['resource']<0 or grid.s.current not in F or grid.s.base not in F:raise ValueError('invalid input')
        if req.get('old_suffix'):offer(req['old_suffix'],'old_suffix')
        pending=set(Q); route=[grid.s.current]
        while pending:
            budget.check();target=min(pending,key=lambda p:(grid.distance(route[-1],p),p))
            route.extend(grid.path(route[-1],target)[1:]);pending-=set(route)
        route.extend(grid.path(route[-1],grid.s.base)[1:]);offer(tuple(route),'greedy')
        budget.check()
        core_plan,detail=(engine or solve_core)(req,method,cap,fragments,budget,grid,ident)
        if core_plan is not None:offer(core_plan['route'],'core',core_plan)
    except (Expired,TimeoutError) as exc:detail['interruption']=str(exc)
    except Exception as exc:detail['error']=repr(exc)
    chosen=min(candidates,key=lambda x:(len(x['route']),x['accepted'])) if candidates else None
    # The final mandatory audit remains inside the public call and is checked again.
    final_audit=audit_fn(req,chosen['route'] if chosen else ())
    elapsed=budget.elapsed(); within=elapsed<seconds
    valid=bool(chosen and final_audit['valid']); timely=bool(chosen)
    natural=bool(valid and chosen['source']=='core' and detail.get('core_natural'))
    return {'request':req,'method':method,'cap':cap,'route':chosen['route'] if valid else [],
        'status':'finished' if valid else ('deadline' if elapsed>=seconds else 'no_legal_candidate'),
        'audit':final_audit,'candidates':candidates,'diagnostics':diagnostics,'core_plan':core_plan,'core_detail':detail,
        'flags':{'route_valid':valid,'core_candidate_valid':any(c['source']=='core' for c in candidates),
                 'fallback_selected':bool(chosen and chosen['source']!='core'),'natural':natural,
                 'candidate_accepted_in_time':timely,'call_within_budget':within,'within_budget':valid and timely and within},
        'public_seconds':elapsed,'source':chosen['source'] if chosen else None}

def reconstruct_execution(plan,targets,count):
    targets=set(map(tuple,targets));seen=set();route=list(map(tuple,plan['route']))
    for i,p in enumerate(route):
        seen|={p}&targets
        if len(seen)>=count:break
    return {'prefix':route[:i+1],'index':i,'current':route[i],'C':sorted(seen),'steps':i}

def make_case(name,plan,prep):
    ex=reconstruct_execution(plan,prep['published'],prep['prefix_targets']); oldF=set(map(tuple,prep['free']));P=set(map(tuple,prep['published']))
    C=set(ex['C']); F=set(oldF);Q=P-C;current=ex['current'];base=tuple(prep['base']);frags=normalize(plan,C)
    added=[];blocked=[];candidates=[]
    if name in ('N4','N6'):added=[(4,0),(4,1),(4,2)]
    if name=='N5':added=[(4,2),(4,3),(3,3)]
    if name=='N8':added=[(2,1)]
    if name in ('N2','N6'):candidates=sorted(Q-{current,base},key=lambda p:(p[1],p[0]))
    if name=='N3':
        indices=sorted({i for s in plan['strips'] if set(map(tuple,s['cells']))&Q
                        for i in range(max(ex['index'],s['connector_start']),s['service_start'])})
        candidates=[tuple(plan['route'][i]) for i in indices if tuple(plan['route'][i]) not in Q|{current,base}]
    for p in candidates:
        if p not in oldF:continue
        grid=Grid((oldF|set(added))-{p},current,base,Budget())
        try:reachable=set(grid.row(current))
        except ValueError:continue
        if base in reachable and ((Q|set(added))-{p})<=reachable:blocked=[p];break
    applicable=not (name in ('N2','N3','N6') and not blocked)
    F=(F|set(added))-set(blocked);P|=set(added)
    req={'case_id':name,'F':sorted(F),'P':sorted(P),'C':sorted(C),'current':current,'base':base,
         'resource':1000-ex['steps'],'seed':20261018,'old_route':plan['route'],'old_suffix':plan['route'][ex['index']:]}
    return {'case_id':name,'applicable':applicable,'reason':'eligible event' if applicable else 'no future original connector candidate',
            'request':req,'reference':frags,'execution':ex,'event':{'added':added,'blocked':blocked},'initial_plan':plan}

def prepare():
    if (ROOT/'source_protection.json').exists():raise SystemExit('already prepared')
    m=json.loads((OLD/'manifests/delivery_sha256.json').read_text(encoding='utf-8'))
    protected={p:sha(OLD/p) for p in m['files']}; assert protected==m['files']
    write('source_protection.json',protected)
    shutil.copytree(OLD/'sources/frozen/source/oarp_replan',ROOT/'sources/oarp_replan',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    cfg=json.loads((OLD/'protocol/cases.json').read_text(encoding='utf-8'));cfg['preparations'][2]['current']=[2,0]
    write('inputs/preparations.json',cfg['preparations'])
    for prep in ('prep_rect','prep_vline'):
        plan=json.loads((OLD/f'artifacts/plans/{prep}.json').read_text(encoding='utf-8'));validate_plan(plan)
        plan['service_targets']=[p for s in plan['strips'] for p in s['cells']]
        plan['reuse_provenance']={'path':str(OLD/f'artifacts/plans/{prep}.json'),'sha256':sha(OLD/f'artifacts/plans/{prep}.json'),'not_new_solver_call':True}
        write(f'plans/{prep}.json',plan)
    # Preserve the original ledger and derive archival identities, never rewrite it.
    import csv
    rows=list(csv.DictReader((OLD/'logs/calls_ledger.csv').open(encoding='utf-8-sig')))
    write('archive_attempt_map.json',[{'archival_attempt':hashlib.sha256((sha(OLD/'logs/calls_ledger.csv')+':'+str(i)).encode()).hexdigest(),
          'original_row':i+2,'run_id':r['run_id'],'phase':r['phase'],'registered_utc':r['registered_utc'],
          'source_sha256':r['source_sha256'],'historical_compliance_restored':False} for i,r in enumerate(rows)])

def regression():
    rect=read('plans/prep_rect.json');cfg=read('inputs/preparations.json'); n1=make_case('N1',rect,cfg[0]);Q=sets(n1['request'])[3]
    from oarp_replan.ranks import Rank
    ranks=[Rank(f['axis'],tuple(f['cells'])) for f in n1['reference']]
    b=packets(ranks,n1['reference'],rect['route'],n1['request']['F']);assert Q<={p for x in b for p in x['path']}
    grid=Grid(n1['request']['F'],n1['request']['current'],n1['request']['base'],Budget())
    for direction in (0,1):
        p=annotate(b,(2,direction,3),grid,'packet');validate_plan(p);assert len(p['strips'])==2
    for axis in ('H','V'):
        r=Rank(axis,((1,1),));bs=packets([r],[],[],grid.free);p=annotate(bs,(2,0,3),grid,'one');assert p['strips'][0]['axis']==axis
    n2=make_case('N2',rect,cfg[0]);n3=make_case('N3',rect,cfg[0]);n6=make_case('N6',rect,cfg[0])
    assert n2['reference']==n1['reference']==n6['reference'];assert n2['event']['blocked']==[(1,1)]
    assert not n3['applicable'];assert n6['event']['blocked']==[(1,1)]
    assert n1['request']['resource']==992
    # Mock deadline/candidate regressions: no rank or GLNS is run.
    clock=SimpleNamespace(value=0.0,calls=0)
    req={'F':[(0,0)],'P':[],'C':[],'current':(0,0),'base':(0,0),'resource':0,'seed':0,'old_route':[],'old_suffix':[]}
    def engine(*args):return None,{}
    def delayed(req,route):
        clock.calls+=1
        if clock.calls==2:clock.value=2.0
        return audit(req,route)
    out=entry(req,'RANK0',None,[],'mock',seconds=1,clock=lambda:clock.value,auditor=delayed,engine=engine)
    assert not out['flags']['call_within_budget'] and out['flags']['candidate_accepted_in_time']
    assert out['public_seconds']==2
    # Independent validator rejects the formerly invisible curved fake strip.
    bad=copy.deepcopy(rect);bad['strips'][0]['axis']='V'
    try:validate_plan(bad)
    except AssertionError:pass
    else:raise AssertionError('wrong-axis plan accepted')
    write('regression.json',{'passed':True,'pure_structural_and_mock_tests':11,'real_solver_calls':0,
                            'known_old_failure_reproduction':'previous review_evidence.json; N1 missing (1,1),(2,1)',
                            'N3':'not applicable under future original connector annotation'})

def freeze():
    assert read('regression.json')['passed']
    if (ROOT/'seal.json').exists():raise SystemExit('already frozen')
    planned=[{'plan_id':'prepare_sparse','kind':'preparation'}]
    for n in (1,2,4,5,6,7,8):
        for slot in ('rank0','cap0','cap2','capmax'):planned.append({'plan_id':f'N{n}_{slot}','kind':'event'})
    for method in ('RANK0','REPLAN2'):
        for case in ('zero_at_base','empty_away_short','nonempty_over_resource','audit_baseline','audit_slow'):
            planned.append({'plan_id':f'boundary_{method}_{case}','kind':'boundary'})
    write('protocol.json',{'planned':planned,'full_entry_limit':48,'planned_full_entries':39,'soft_seconds':5,'hard_seconds':10,
        'seed':20261018,'N3':'future original connector annotations only; no applicable event, no solver call',
        'reuse':['prep_rect','prep_vline'],'regenerate':['prep_sparse'],'developer_map_calls':0,'holdout_calls':0,
        'rank_only_limit':12,'exact_gtsp_limit':4,'nested_SCIP_limit':250,'nested_GLNS_limit':64,
        'no_successful_task_rerun':True,'changes_are_fidelity_repairs_not_novel_algorithm':True})
    protected={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and (p.suffix=='.py' or 'inputs' in p.parts)}
    protected['protocol.json']=sha(ROOT/'protocol.json');write('seal.json',protected)

def boundary_req(planid):
    case=planid.split('_',2)[2];method=planid.split('_')[1]
    req={'case_id':planid,'F':[(0,0),(1,0),(2,0)],'P':[],'C':[],'current':(0,0),'base':(0,0),
         'resource':0,'seed':20261018,'old_route':[],'old_suffix':[]}
    if case=='empty_away_short':req.update(current=(2,0),resource=1)
    if case=='nonempty_over_resource':req.update(P=[(2,0)],resource=1)
    return method,case,req

def worker(planid):
    global ACTIVE
    assert all(sha(ROOT/p)==h for p,h in read('seal.json').items())
    spec=next(p for p in read('protocol.json')['planned'] if p['plan_id']==planid)
    ACTIVE=str(uuid.uuid4());emit({'event':'start','attempt_id':ACTIVE,'kind':spec['kind'],'plan_id':planid,'source':sha(ROOT/'seal.json')})
    try:
        if planid=='prepare_sparse':
            prep=read('inputs/preparations.json')[2]; req={'case_id':planid,'P':prep['published'],'C':[],'F':prep['free'],
                'current':prep['current'],'base':prep['base'],'resource':1000,'seed':20261018,'old_route':[],'old_suffix':[]}
            result=entry(req,'RANK0',None,[],planid);assert result['core_plan'] and result['flags']['core_candidate_valid']
            write('plans/prep_sparse.json',result['core_plan'])
        elif spec['kind']=='event':
            name,slot=planid.split('_');idx=0 if name not in ('N7','N8') else (1 if name=='N7' else 2)
            prep=read('inputs/preparations.json')[idx];p=read(f"plans/{prep['name']}.json");case=make_case(name,p,prep)
            write(f'events/{name}.json',case); assert case['applicable']
            cap={'rank0':None,'cap0':0,'cap2':2,'capmax':2*len(sets(case['request'])[3])}[slot]
            result=entry(case['request'],'RANK0' if slot=='rank0' else 'REPLAN2',cap,case['reference'],planid)
        else:
            method,case,req=boundary_req(planid)
            def delayed(req,route):time.sleep(.05);return audit(req,route)
            result=entry(req,method,0,[],planid,auditor=delayed if case=='audit_slow' else None)
        result.update(plan_id=planid,attempt_id=ACTIVE,kind=spec['kind']);write(f'results/{planid}.json',result)
        emit({'event':'end','attempt_id':ACTIVE,'kind':spec['kind'],'plan_id':planid,'status':result['status'],
              'result_sha256':sha(ROOT/f'results/{planid}.json')})
    except BaseException as exc:
        emit({'event':'end','attempt_id':ACTIVE,'kind':spec['kind'],'plan_id':planid,'error':repr(exc)});raise

def run():
    for job in read('protocol.json')['planned']:
        name=job['plan_id']
        if (ROOT/f'results/{name}.json').exists():continue
        if (ROOT/'calls.jsonl').exists():
            attempted=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
            if any(r.get('plan_id')==name and r['event']=='start' for r in attempted):raise SystemExit('previous failed attempt requires explicit repair plan: '+name)
        with (ROOT/f'{name}.console.txt').open('w',encoding='utf-8') as f:
            try:r=subprocess.run([sys.executable,'-B','-X','utf8',__file__,'worker','--plan-id',name],stdout=f,stderr=subprocess.STDOUT,timeout=10)
            except subprocess.TimeoutExpired:
                write(f'watchdog/{name}.json',{'plan_id':name,'killed':True,'core_end_not_fabricated':True});raise
        if r.returncode:raise SystemExit('failed '+name)
        result=read(f'results/{name}.json');print(name,result['status'],result['source'],result['audit']['steps'],flush=True)
    # N3 is a real preflight structural rejection, not a synthetic successful solve.
    p=read('plans/prep_rect.json');write('events/N3.json',make_case('N3',p,read('inputs/preparations.json')[0]))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode');ap.add_argument('--plan-id');args=ap.parse_args()
    {'prepare':prepare,'test':regression,'freeze':freeze,'run':run,'worker':lambda:worker(args.plan_id)}[args.mode]()
