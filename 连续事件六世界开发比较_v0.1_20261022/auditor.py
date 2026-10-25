"""Independent saved-log reconstruction. Does not import executor/contracts.
Own event-prefix sets, credit ledger, compass turns, response checks and BFS.
"""
import json,math,hashlib
def ps(xs):return {tuple(p) for p in xs}
def pack(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def public_at(w,t):
    P=ps(w['published']);F=ps(w['free']);origin={p:'initial' for p in P};group=[]
    for e in sorted(w['events'],key=lambda e:(e['tick'],e['id'])):
        if e['tick']>t:continue
        for cell in e['add_targets']:p=tuple(cell);P.add(p);origin.setdefault(p,e['id'])
        F-=ps(e['block'])
        if e['tick']==t:group.append(e['id'])
    prior=ps(w['published'])|{tuple(p) for e in w['events'] if e['tick']<t for p in e['add_targets']}
    epochs=[e for e in w['events'] if e['tick']<=t];latest=max((e['tick'] for e in epochs),default=0)
    epoch='initial' if not epochs else '|'.join(sorted(e['id'] for e in epochs if e['tick']==latest))
    return P,F,origin,group,prior,epoch
def walk_component(f,start,counter):
    counter['BFS']+=1;found={start};layer=[start]
    while layer:
        nxt=[]
        for p in layer:
            for axis,delta in ((0,-1),(0,1),(1,-1),(1,1)):
                q=list(p);q[axis]+=delta;q=tuple(q)
                if q in f and q not in found:found.add(q);nxt.append(q)
        layer=nxt
    return found
def manual_subset(actual,expected,location=''):
    if isinstance(expected,dict):
        assert isinstance(actual,dict),location
        for k,v in expected.items():assert k in actual,(location,k);manual_subset(actual[k],v,location+'/'+k)
    else:assert actual==expected,(location,actual,expected)
def serialized_stub(x):
    if isinstance(x,dict):return {k:({'nonfinite_float':'nan'} if k=='entry_seconds' and v=='NaN_STUB_FIELD' else serialized_stub(v)) for k,v in x.items()}
    if isinstance(x,list):return [serialized_stub(v) for v in x]
    return x
def response_rule(c,r):
    if r is None:return 'solver_no_solution','missing_response'
    if not isinstance(r,dict):return 'technical_error','response_not_object'
    sec=r.get('entry_seconds')
    if type(sec) not in (int,float) or not math.isfinite(sec) or sec<0:return 'technical_error','invalid_time_field'
    if sec>=20:return 'deadline','entry_not_strictly_less_than_20'
    route=r.get('route')
    if not route:return ('deadline','native_deadline_without_route') if r.get('native_status')=='deadline' else ('solver_no_solution','no_route')
    if not isinstance(route,list) or any(not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(v) is not int for v in p) for p in route):return 'invalid_route','route_points'
    if route[0]!=c['current'] or route[-1]!=c['base'] or not ps(route)<=ps(c['free']):return 'invalid_route','endpoint_or_collision'
    dirs={(1,0),(-1,0),(0,1),(0,-1)}
    if any((q[0]-p[0],q[1]-p[1]) not in dirs for p,q in zip(route,route[1:])):return 'invalid_route','non_four_neighbor_move'
    if (ps(c['targets'])-ps(c['covered']))-ps(route):return 'invalid_route','coverage_omission'
    if len(route)>c['distance_budget']+1:return 'resource_infeasible','full_route_exceeds_remaining_resource'
    return 'accepted',None
def audit(result,spec,counter=None):
    if counter is None:counter={'BFS':0}
    bfs_before=counter['BFS'];w=spec['world'];assert result['world']==w and result['world_hash']==hashlib.sha256(pack(w).encode()).hexdigest()
    assert set(result['sessions'])==set(spec['methods']);last=max([e['tick'] for e in w['events']],default=0);expected_pubs=[]
    for t in sorted({0}|{e['tick'] for e in w['events']}):
        P,F,origin,group,prior,epoch=public_at(w,t);expected_pubs.append(dict(tick=t,ids=group,P_before=sorted(map(list,prior)),P=sorted(map(list,P)),F=sorted(map(list,F)),epoch=epoch))
    assert result['publications']==expected_pubs
    expected_bfs=[];proofs={};fatal=None
    for name,s in result['sessions'].items():
        cur=tuple(w['start']);prev=None;H=set();moves=waits=0;plan=None;cursor=0;credits=[];first={};classes=dict(fresh_target=0,initial_historical=0,session_repeat=0,non_target=0);n90=n180=0;walk=[list(cur)];requests=s['requests'];actions=s['actions'];ri=ai=0;terminal=None
        def state(P,F):return dict(current=list(cur),previous=list(prev) if prev is not None else None,H=sorted(map(list,H)),M=moves,E=w['E0']-moves,waits=waits,plan=plan,cursor=cursor,U=sorted(map(list,(P&F)-H)),D=sorted(map(list,P-F-H)))
        def credit(p,t,source,P,origin,epoch):
            if p in P and p not in H:
                ev=dict(point=list(p),tick=t,source=source,event_id=epoch,target_first_published=origin[p]);credits.append(ev);first[p]=ev;H.add(p)
        assert s['frames'] and [f['tick'] for f in s['frames']]==list(range(s['terminal']['tick']+1))
        for frame in s['frames']:
            t=frame['tick'];P,F,origin,group,prior,epoch=public_at(w,t);assert frame['before']==state(P,F),(spec['id'],name,t,'before')
            status=reason=None
            if cur not in F or tuple(w['base']) not in F:status='environment_termination';reason='current_blocked' if cur not in F else 'base_blocked'
            else:
                credit(cur,t,'publication',P,origin,epoch);reached=walk_component(F,cur,counter);expected_bfs.append(dict(method=name,tick=t,kind='environment_reachability_BFS'))
                if tuple(w['base']) not in reached or not ((P&F)-H)<=reached:status='environment_termination';reason='base_unreachable' if tuple(w['base']) not in reached else 'target_unreachable'
                elif t>=last and not ((P&F)-H) and cur==tuple(w['base']):status='success'
                elif t==w['T_max']:status='tick_limit';reason='maximum_tick_reached'
            if status is None and (t==0 or group):
                req=requests[ri];assert req['sequence']==ri and req['tick']==t
                snap=dict(name='stub_snapshot',free=sorted(map(list,F)),targets=sorted(map(list,P&F)),covered=sorted(map(list,H)),published_targets=sorted(map(list,P)),deferred_targets=sorted(map(list,P-F-H)),initial_targets=sorted(map(list,prior|H)),current=list(cur),previous=list(prev) if prev is not None else None,base=w['base'],predator=[-1,0],old_route=plan[cursor:] if plan is not None else [list(cur)],distance_budget=w['E0']-moves,radius=0)
                assert req['input']==snap and req['payload_utf8']==pack(snap) and req['payload_sha256']==hashlib.sha256(pack(snap).encode()).hexdigest()
                assert req['plan_before']==plan and req['cursor_before']==cursor and req['actual_prefix']==walk
                assert isinstance(req['response'],dict);admission,why=response_rule(snap,req['response']);assert (req['admission'],req['reason'])==(admission,why);ri+=1
                if admission!='accepted':status,reason=admission,why
                else:plan=req['response']['route'];cursor=0;assert req['plan_adopted']==plan
            if status is None:
                action=actions[ai];assert action['tick']==t;ai+=1
                if plan is not None and cursor<len(plan)-1:
                    q=tuple(plan[cursor+1]);assert q in F and w['E0']-moves>0
                    cls='non_target' if q not in P else 'session_repeat' if q in H else 'fresh_target';degree=None
                    if prev is not None:
                        compass={(1,0):0,(0,1):1,(-1,0):2,(0,-1):3};oldv=(cur[0]-prev[0],cur[1]-prev[1]);newv=(q[0]-cur[0],q[1]-cur[1]);change=(compass[newv]-compass[oldv])%4;degree=90 if change in (1,3) else 180 if change==2 else 0;n90+=degree==90;n180+=degree==180
                    old_credit=first.get(q);expected=dict(kind='move',tick=t,arrival_tick=t+1,start=list(cur),end=list(q),classification=cls,turn_degrees=degree,first_credit_event=old_credit['event_id'] if old_credit else None,repeat_across_event=bool(old_credit and old_credit['event_id']!=epoch));assert action==expected
                    prev=cur;cur=q;moves+=1;cursor+=1;walk.append(list(cur));classes[cls]+=1;credit(q,t+1,'arrival',P,origin,epoch)
                else:
                    assert cur==tuple(w['base']) and not ((P&F)-H)
                    assert action==dict(kind='wait',tick=t,end_tick=t+1,current=list(cur),previous=list(prev) if prev is not None else None);waits+=1
            if status is not None:
                terminal=dict(status=status,reason=reason,tick=t,state=state(P,F));assert frame==s['frames'][-1]
                if status=='technical_error':fatal=reason
            assert frame['after']==state(P,F),(spec['id'],name,t,'after')
        assert terminal==s['terminal'] and ai==len(actions) and ri==len(requests) and ri<=3 and credits==s['credits']
        P,F,*_=public_at(w,max([e['tick'] for e in w['events']],default=0));summary=dict(status=terminal['status'],reason=terminal['reason'],finish_tick=terminal['tick'],M=moves,E=w['E0']-moves,waits=waits,current=list(cur),previous=list(prev) if prev is not None else None,H=sorted(map(list,H)),P=sorted(map(list,P)),F=sorted(map(list,F)),U=sorted(map(list,(P&F)-H)),D=sorted(map(list,P-F-H)),historical_now_blocked=sorted(map(list,H-F)),returned=cur==tuple(w['base']),response_calls=ri,move_classes=classes,turns90=n90,turns180=n180,first_credit=credits,zero_move_credits=sum(e['source']=='publication' for e in credits),benchmark_eligible=False)
        assert s['summary']==summary and sum(classes.values())==moves;assert_real_source = True
        if name in spec.get('wait_ticks',{}):assert [a['tick'] for a in actions if a['kind']=='wait']==spec['wait_ticks'][name]
        proofs[name]=dict(passed=True,frames=len(s['frames']),actual_moves=moves,waits=waits,requests=ri,hand_expectations_passed=False,real_saved_response_audit=True,source_prefix_and_all_snapshots_passed=True)
    for e in spec.get('input_expectations',[]):
        req=result['sessions'][e['method']]['requests'][e['sequence']];assert req['tick']==e['tick'];manual_subset(req['input'],e['fields'],spec['id']+'/manual_input')
    assert sorted(result['environment_BFS'],key=lambda x:(x['tick'],x['method']))==sorted(expected_bfs,key=lambda x:(x['tick'],x['method']))
    assert result['fatal_technical_error']==fatal
    return dict(passed=True,category=spec['category'],subcase=spec['id'],methods=proofs,independent_audit_BFS=counter['BFS']-bfs_before,main_environment_BFS=len(expected_bfs),manual_expectations_original=False,real_response_mode=True)
