"""Independent public-planning and truth-execution audits. No native imports."""
from fractions import Fraction as R
from collections import Counter
from copy import deepcopy
import json,hashlib,time
from ._common import HERE
from . import _geometry as A
from . import _h1 as h1_audit
from . import _detect as T
from . import region as Z

def load_auditor():
    from . import _post_saved
    return _post_saved

def public_state(raw,c):
    if raw.get('h') is not None:
        assert raw['heading_status']=='KNOWN'
        return A.state(raw,c)
    assert raw['heading_status']=='NO_PRIOR_MOTION'
    s={k:A.cellset(raw[k]) for k in ('F','P','H','D')}
    s.update(S=A.pos(raw['S']),h=None,base=A.pos(raw['base'],True),E=A.load(raw['E']),M=A.load(raw['M']))
    assert s['S']==s['base'] and s['base'] in s['F'] and s['H']<=s['P']
    assert s['D']==s['P']-s['F']-s['H'] and A.sign(s['E'])>=0 and A.sign(s['M'])>=0
    assert 0<len(s['F'])<=25 and len(s['P'])<=12 and A.legal(s['F'],s['S'],s['S'],c)
    return s

def check_state(saved,s):
    assert A.pos(saved['S'])==s['S']
    assert saved['h'] is None if s['h'] is None else A.pos(saved['h'])==s['h']
    for k in ('F','P','H','D'):
        assert A.cellset(saved[k])==s[k],k
    assert A.pos(saved['base'],True)==s['base']
    A.certified(saved['E'],s['E'])
    A.certified(saved['M'],s['M'])

def audit_route(s,saved,c):
    c['independent_route_audits']+=1
    path=[A.pos(p) for p in saved['points']]
    assert path and path[0]==s['S'] and path[-1]==s['base']
    f=deepcopy(s)
    events,total,squares=Z.collect(f,c),{},[]
    for a,b in zip(path,path[1:]):
        assert A.legal(s['F'],a,b,c)
        length,sq=A.metric(a,b,c)
        total=A.add(total,length)
        squares.append(sq)
        events+=Z.service(f,a,b,c)
        if a!=b:
            f['h']=(b[0]-a[0],b[1]-a[1])
    assert not(s['P']&s['F']-f['H']) and A.sign(A.add(s['E'],total,-1))>=0
    f['S'],f['E'],f['M']=s['base'],A.add(s['E'],total,-1),A.add(s['M'],total)
    assert [A.number(v) for v in saved['squared_sources']]==squares and saved['events']==events
    A.certified(saved['length'],total)
    check_state(saved['predicted_final'],f)
    return path,total,f

def audit_one(result,auditor,counts=None,technical=False):
    c=Counter() if counts is None else counts
    begin=time.perf_counter()
    c['independent_pipeline_audits']+=1
    case=result['snapshot']
    s=public_state(case['input'],c)
    check_state(result['actual_before'],s)
    check_state(result['actual_after'],s)
    assert result['actual_before']==result['actual_after']
    q=A.pos(result['q'],True)
    if s['h'] is None:
        assert q==s['S']==s['base'] and len(result['candidates'])==1
        row=result['candidates'][0]
        assert row['initial_zero_entry'] and A.pos(row['q'],True)==q
        assert A.number(row['squared'])==A.number(row['squared_source'])==0 and row['dot'] is None
        assert row['legal'] and row['affordable']
        A.certified(row['length'],{})
    else:
        assert len(result['candidates'])==len(s['F'])
        chosen=None
        candidates=[]
        for row,p in zip(result['candidates'],sorted(s['F'])):
            assert A.pos(row['q'],True)==p
            valid=A.legal(s['F'],s['S'],p,c)
            length,sq=A.metric(s['S'],p,c)
            affordable=A.sign(A.add(s['E'],length,-1))>=0
            dot=sum((p[k]-s['S'][k])*s['h'][k] for k in (0,1))
            assert A.number(row['squared'])==sq==A.number(row['squared_source'])
            assert row['legal']==valid and row['affordable']==affordable and A.number(row['dot'])==dot
            A.certified(row['length'],length)
            if valid and affordable:
                key=(sq,-dot,p)
                candidates.append(key)
                if p==q:
                    chosen=key
        assert chosen is not None
        for key in candidates:
            c['independent_saved_choice_comparisons']+=1
            assert chosen<=key
    gamma,_=A.metric(s['S'],q,c)
    A.certified(result['gamma_length'],gamma)
    assert [A.pos(p) for p in result['gamma']]==[s['S'],q]
    pred=deepcopy(s)
    events=Z.collect(pred,c)+Z.service(pred,s['S'],q,c)
    pred['h']=(q[0]-s['S'][0],q[1]-s['S'][1]) if q!=s['S'] else s['h']
    pred['S'],pred['E'],pred['M']=q,A.add(s['E'],gamma,-1),A.add(s['M'],gamma)
    check_state(result['predicted_entry'],pred)
    assert result['gamma_events']==events
    assert result['h_entry'] is None if pred['h'] is None else A.pos(result['h_entry'])==pred['h']
    req=result['core_request']
    assert A.cellset(req['free'])==s['F'] and A.cellset(req['published_targets'])==s['P']
    assert A.cellset(req['targets'])==s['P']&s['F'] and A.cellset(req['covered'])==pred['H']
    assert A.cellset(req['deferred_targets'])==pred['D'] and pred['H']<=A.cellset(req['initial_targets'])==s['P']
    assert req['old_route']==[] and req['previous'] is None
    assert A.pos(req['current'],True)==q and A.pos(req['base'],True)==s['base']
    assert type(req['distance_budget']) is int and req['distance_budget']==A.floor_exact(pred['E'])
    assert req['predator']==[-3,-3] and req['predator'][0]<min(x for x,y in s['F'])
    heading=req['incoming_heading']
    assert heading==result['heading']
    assert heading['source']['execution_log_tail']==case['metadata']['execution_log_tail']
    if pred['h'] is None:
        assert heading['status']=='NO_PRIOR_MOTION' and heading['vector'] is None
        assert heading['source']['kind']=='initialization_no_motion'
    else:
        assert heading['status']=='KNOWN' and tuple(R(v) for v in heading['vector'])==pred['h']
        assert heading['source']['kind']=='synthetic_direction_fixture'
        assert heading['source']['execution_evidence']==case['metadata']['heading_source']
        assert A.pos(heading['source']['executed_heading'])==s['h']
    assert json.loads(result['core_request_utf8'])==req
    assert hashlib.sha256(result['core_request_utf8'].encode()).hexdigest()==result['core_request_sha256']
    native=result['native_entry']['raw']
    assert not native.get('stub') and result['native_counts']['core_started']==result['native_counts']['core_returned']==result['native_counts']['core_complete']==1
    if result['method']=='H1':
        core=native['branches']['P0']
        assert native['route']==core['route'] and native['selected']=='P0' and not core['fallback_selected']
        audit=h1_audit.audit_output(req,heading,core,True)
        c['independent_H1_decision_audits']+=1
        c['independent_H1_unit_edge_checks']+=audit['route_edge_checks']
    else:
        assert native['status']=='finished' and native['core_finished']
    route=[A.pos(p,True) for p in native['route']]
    assert route[0]==q and route[-1]==s['base'] and len(route)-1<=req['distance_budget']
    assert all(p in s['F'] for p in route)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
    assert result['core_output_used'] and [A.pos(p) for p in result['native_main_audit']['points']]==route
    audit_route(pred,result['native_main_audit'],c)
    post=json.loads(result['post_response_utf8'])
    source=json.loads(result['post_request_utf8'])
    assert source['input']==req and source['raw']==json.loads(json.dumps(native)) and post==result['post']
    n=len(route)-1
    post_receipt=auditor.audit_one({'id':source['id'],'limits':{'candidate_geometry':4096,
        'independent_geometry':n,'independent_service_intersections':n*len(s['P']&s['F']-pred['H'])}},
        result['post_request_utf8'].encode(),result['post_response_utf8'].encode())
    c['independent_frozen_post_audits']+=1
    c['independent_geometry']+=post_receipt['counts']['geometry']
    c['independent_service_intersections']+=post_receipt['counts']['service_intersections']
    for key in ('independent_region_point_tests','independent_region_boundary_parameters'):
        c[key]+=post_receipt['counts'].get(key,0)
    short=[A.pos(p,True) for p in post['vertices']]
    full=([s['S']] if s['S']!=q else [])+short
    assert [A.pos(p) for p in result['full_route']]==full
    assert result['q_locked_index']==(1 if s['S']!=q else 0) and full[result['q_locked_index']]==q
    assert all(a!=b for a,b in zip(full,full[1:]))
    assert [A.pos(p) for p in result['full_main_audit']['points']]==full
    _,total,final=audit_route(s,result['full_main_audit'],c)
    post_length=A.add(total,gamma,-1)
    assert [A.pos(p) for p in result['post_main_audit']['points']]==short
    _,checked_post,checked_final=audit_route(pred,result['post_main_audit'],c)
    assert checked_post==post_length and checked_final==final
    assert A.sign(A.add(A.load(result['native_main_audit']['length']['exact']),post_length,-1))>=0
    assert result['timing']['pipeline_seconds']<30 and result['timing']['core_adapter_seconds']<result['core_budget_passed']<=20
    nc=result['native_counts']
    for key,field in [('candidate','candidate'),('source','source_validation'),('output','output_validation')]:
        assert nc.get('post_'+key+'_geometry',0)==post['counts'][field]
    assert nc.get('post_service_intersections',0)==post['counts']['service_intersections']
    return {'passed':True,'counts':dict(c),'frozen_post_receipt':post_receipt,'seconds':time.perf_counter()-begin,
            'scope':'optimistic_public_map_only_not_unexecuted_truth_safety'}

def ledger_snapshot_check(saved,s,known,last_motion,event_count,nonzero):
    check_state(saved,s)
    assert A.cellset(saved['known'])==known and saved['last_motion']==last_motion
    assert saved['event_count']==event_count and saved['nonzero_segments']==nonzero

def audit_execution(public,private,initial,records,final,plans=None,technical=False,counts=None):
    c=Counter() if counts is None else counts
    c['independent_execution_audits']+=1
    nominal=A.cellset(public['F_nominal'])
    truth=A.cellset(private['O_truth'])
    known=A.cellset(initial['known'])
    s={'S':A.pos(initial['S']),'h':None if initial['h'] is None else A.pos(initial['h']),
       'P':A.cellset(public['P']),'H':A.cellset(initial['H']),'F':nominal-known,'D':A.cellset(initial['D']),
       'base':A.pos(public['base'],True),'E':A.load(initial['E']['exact']),'M':A.load(initial['M']['exact'])}
    if not technical:
        assert s['S']==A.pos(public['start'],True)==s['base'] and s['h'] is None
        assert not known and not s['H'] and s['E']=={1:R(100)} and not s['M']
    last_motion=initial['last_motion']
    event_count=initial['event_count']
    nonzero=initial['nonzero_segments']
    tail='0'*64
    detections=[]
    offcenter=[]
    waits=[]
    for index,record in enumerate(records):
        c['independent_action_log_checks']+=1
        assert record['index']==index and record['previous_hash']==tail
        raw={k:v for k,v in record.items() if k!='record_hash'}
        computed=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        assert computed==record['record_hash']
        ledger_snapshot_check(record['before'],s,known,last_motion,event_count,nonzero)
        if record['kind']=='plan_wait':
            assert record['before']==record['after']
            assert A.pos(record['predicted_route'][0])==s['S']
            if not record['fixed_stub']:
                plan=plans[record['plan_id']]
                assert plan['passed'] and plan['full_route']==record['predicted_route']
                inp=plan['snapshot']['input']
                assert A.pos(inp['S'])==s['S'] and (inp['h'] is None if s['h'] is None else A.pos(inp['h'])==s['h'])
                assert A.cellset(inp['F'])==nominal-known and A.cellset(inp['P'])==s['P']
                assert A.cellset(inp['H'])==s['H'] and A.cellset(inp['D'])==s['D']
                assert A.load(inp['E'])==s['E'] and A.load(inp['M'])==s['M']
                assert plan['snapshot']['metadata']['known_obstacles']==[list(map(int,p)) for p in sorted(known)]
                assert plan['snapshot']['metadata']['heading_source']==(last_motion if last_motion else {'kind':'initialization_no_motion'})
                assert plan['snapshot']['metadata']['execution_log_tail']==tail
                assert set(plan['snapshot'])=={'id','input','metadata'}
                assert set(plan['snapshot']['metadata'])=={'initial_targets','predator','old_route','heading_source','execution_log_tail','known_obstacles','scope'}
            waits.append(record['plan_id'])
            tail=computed
            continue
        if record['kind']=='technical_publish':
            assert technical
            s['P']|=A.cellset(record['targets'])
            new=A.cellset(record['blocked'])
            truth|=new;known|=new
            s['F']=nominal-known;s['D']=s['P']-s['F']-s['H']
            ledger_snapshot_check(record['after'],s,known,last_motion,event_count,nonzero)
            assert record['status']=='published'
            tail=computed
            continue
        c['independent_execution_commits_checked']+=1
        a,b=[A.pos(p) for p in record['proposed']]
        assert a==s['S']
        kind,t,cell=T.probe(a,b,truth,known,c)
        sensor=record['sensor']
        assert sensor['kind']==kind and A.number(sensor['t'])==t
        assert sensor['cell']==(None if cell is None else list(map(int,cell)))
        if kind.startswith('unsafe'):
            assert record['status']==kind and not record['credits']
            A.certified(record['distance'],{})
            ledger_snapshot_check(record['after'],s,known,last_motion,event_count,nonzero)
            tail=computed
            continue
        stop_t=t if kind=='detected' else R(1)
        stop=(a[0]+stop_t*(b[0]-a[0]),a[1]+stop_t*(b[1]-a[1]))
        length,square=A.metric(a,stop,c)
        if A.sign(A.add(s['E'],length,-1))<0:
            assert record['status']=='resource_refused' and not record['credits']
            A.certified(record['distance'],{})
            ledger_snapshot_check(record['after'],s,known,last_motion,event_count,nonzero)
            tail=computed
            continue
        assert A.legal(nominal-truth,a,stop,c),'committed_actual_prefix_not_truth_safe'
        end_open=record['prefix_end_open']
        assert technical or end_open==(kind=='detected')
        if record['kind']=='collect_here':
            assert a==b
            credits=[] if kind=='detected' else Z.collect(s,c)
        else:
            assert record['kind']=='move'
            credits=Z.service(s,a,stop,c,end_open)
        assert credits==record['credits']
        for credit in credits:
            if record['kind']=='move':
                p=tuple(credit['cell'])
                dx,dy=stop[0]-a[0],stop[1]-a[1]
                x,y=p[0]-a[0],p[1]-a[1]
                c['independent_legacy_center_controls']+=1
                center=(dx*y==dy*x and 0<=x*dx+y*dy<=dx*dx+dy*dy)
                if not center and dx and dy:
                    offcenter.append({'action_index':index,'cell':credit['cell'],'evidence':credit['evidence']})
            s['H'].add(tuple(credit['cell']))
        if a!=stop:
            nonzero+=1
            s['h']=(stop[0]-a[0],stop[1]-a[1])
            last_motion={'action_index':index,'a':record['actual'][0],'b':record['actual'][1],
                         'vector':[{'n':v.numerator,'d':v.denominator} for v in s['h']]}
        s['S'],s['E'],s['M']=stop,A.add(s['E'],length,-1),A.add(s['M'],length)
        if kind=='detected':
            assert cell not in known and event_count<1
            known.add(cell)
            event_count+=1
            diagonal=a!=stop and b[0]!=a[0] and b[1]!=a[1] and 0<t<1
            detections.append({'action_index':index,'t':sensor['t'],'S':record['actual'][1],
                               'interior_diagonal':diagonal,'cell':sensor['cell']})
        s['F']=nominal-known
        s['D']=s['P']-s['F']-s['H']
        assert record['status']==('detected' if kind=='detected' else 'committed')
        assert [A.pos(p) for p in record['actual']]==[a,stop] and A.number(record['squared_source'])==square
        A.certified(record['distance'],length)
        ledger_snapshot_check(record['after'],s,known,last_motion,event_count,nonzero)
        tail=computed
    ledger_snapshot_check(final,s,known,last_motion,event_count,nonzero)
    completed=s['S']==s['base'] and not(s['P']&s['F']-s['H'])
    if not technical:
        assert not(s['H']&truth),'blocked_target_credited'
    if completed:
        assert not(s['P']-truth-s['H']),'true_serviceable_coverage_missing'
    return {'passed':True,'counts':dict(c),'completed':completed,'detections':detections,
            'interior_diagonal_detections':sum(x['interior_diagonal'] for x in detections),
            'diagonal_offcenter_credits':offcenter,'covered':len(s['H']),'deferred_known':len(s['D']),'deferred_truth':len(s['P']&truth),
            'pending_known':len(s['P']&s['F']-s['H']),'nonzero_segments':nonzero,
            'actual_length_exact':{'terms':[{'r':r,'c':{'n':v.numerator,'d':v.denominator}}
                                 for r,v in sorted(s['M'].items()) if v]},
            'planning_waits':waits,'final_hash_chain':tail}
