"""Minimal synchronous world/session executor; callbacks receive bytes only."""
from collections import deque
import json,hashlib,copy
from contracts import points,wire,safe,admit,validate_world,SNAPSHOT_KEYS,TechnicalError
def world_hash(w):return hashlib.sha256(wire(w).encode('utf8')).hexdigest()
def reach(f,start,accounts,method,tick):
    accounts.append(dict(method=method,tick=tick,kind='environment_reachability_BFS'))
    seen={start};queue=deque([start])
    while queue:
        x,y=queue.popleft()
        for p in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
            if p in f and p not in seen:seen.add(p);queue.append(p)
    return seen
class Session:
    def __init__(self,start,E0):
        self.current=tuple(start);self.previous=None;self.H=set();self.M=0;self.E=E0;self.waits=0;self.plan=None;self.cursor=0
        self.terminal=None;self.credits=[];self.requests=[];self.actions=[];self.frames=[]
        self.move_classes=dict(fresh_target=0,initial_historical=0,session_repeat=0,non_target=0);self.turns90=0;self.turns180=0;self.first_credit={}
    def suffix(self):return self.plan[self.cursor:] if self.plan is not None else [list(self.current)]
    def record(self,P,F):
        return dict(current=self.current,previous=self.previous,H=sorted(self.H),M=self.M,E=self.E,waits=self.waits,plan=self.plan,cursor=self.cursor,U=sorted((P&F)-self.H),D=sorted(P-F-self.H))
    def credit(self,p,tick,source,P,origin,epoch):
        if p in P and p not in self.H:
            self.H.add(p);ev=dict(point=p,tick=tick,source=source,event_id=epoch,target_first_published=origin[p]);self.credits.append(ev);self.first_credit[p]=ev;return True
        return False
    def end(self,status,reason,tick,P,F):self.terminal=dict(status=status,reason=reason,tick=tick,state=safe(self.record(P,F)))
    def snapshot(self,P,F,P_before,base):
        x=dict(name='stub_snapshot',free=sorted(F),targets=sorted(P&F),covered=sorted(self.H),published_targets=sorted(P),deferred_targets=sorted(P-F-self.H),initial_targets=sorted(P_before|self.H),current=self.current,previous=self.previous,base=base,predator=[-1,0],old_route=self.suffix(),distance_budget=self.E,radius=0)
        x=json.loads(wire(x));assert set(x)==SNAPSHOT_KEYS and points(x['covered'])<=points(x['initial_targets']);return x
def run_world(world,callbacks):
    validate_world(world);original=wire(world);P=points(world['published']);F=points(world['free']);base=tuple(world['base']);origin={p:'initial' for p in P};epoch='initial'
    states={name:Session(world['start'],world['E0']) for name in callbacks};publog=[];bfs=[];result=dict(world=copy.deepcopy(world),world_hash=world_hash(world),publications=publog,sessions={},environment_BFS=bfs)
    final_tick=max([e['tick'] for e in world['events']],default=0);fatal=None
    for tick in range(world['T_max']+1):
        before=set(P);events=sorted([e for e in world['events'] if e['tick']==tick],key=lambda e:e['id'])
        if tick==0 or events:
            for e in events:
                for p in map(tuple,e['add_targets']):origin.setdefault(p,e['id']);P.add(p)
                F.difference_update(map(tuple,e['block']))
            epoch='initial' if tick==0 else '|'.join(e['id'] for e in events)
            publog.append(dict(tick=tick,ids=[e['id'] for e in events],P_before=sorted(before),P=sorted(P),F=sorted(F),epoch=epoch))
        for name,s in states.items():
            if s.terminal:continue
            frame=dict(tick=tick,before=safe(s.record(P,F)));s.frames.append(frame)
            if s.current not in F or base not in F:
                s.end('environment_termination','current_blocked' if s.current not in F else 'base_blocked',tick,P,F);frame['after']=safe(s.record(P,F));continue
            s.credit(s.current,tick,'publication',P,origin,epoch)
            reached=reach(F,s.current,bfs,name,tick);U=(P&F)-s.H
            if base not in reached or not U<=reached:
                s.end('environment_termination','base_unreachable' if base not in reached else 'target_unreachable',tick,P,F);frame['after']=safe(s.record(P,F));continue
            if tick>=final_tick and not U and s.current==base:
                s.end('success',None,tick,P,F);frame['after']=safe(s.record(P,F));continue
            if tick==world['T_max']:
                s.end('tick_limit','maximum_tick_reached',tick,P,F);frame['after']=safe(s.record(P,F));continue
            if tick==0 or events:
                snap=s.snapshot(P,F,before,world['base']);payload=wire(snap).encode('utf8');req=dict(sequence=len(s.requests),tick=tick,input=snap,payload_utf8=payload.decode('utf8'),payload_sha256=hashlib.sha256(payload).hexdigest(),plan_before=copy.deepcopy(s.plan),cursor_before=s.cursor,actual_prefix=[[*world['start']]]+[a['end'] for a in s.actions if a['kind']=='move'])
                s.requests.append(req)
                try:response=callbacks[name](payload)
                except BaseException as ex:
                    req.update(response=None,admission='technical_error',reason='callback_exception',exception=repr(ex));s.end('technical_error','callback_exception',tick,P,F);fatal='callback_exception';frame['after']=safe(s.record(P,F));break
                admission,reason=admit(snap,response);req.update(response=safe(response),admission=admission,reason=reason)
                if admission!='accepted':
                    s.end(admission,reason,tick,P,F);frame['after']=safe(s.record(P,F))
                    if admission=='technical_error':fatal=reason;break
                    continue
                s.plan=copy.deepcopy(response['route']);s.cursor=0;req['plan_adopted']=copy.deepcopy(s.plan)
            if s.plan is not None and s.cursor+1<len(s.plan):
                nxt=tuple(s.plan[s.cursor+1])
                if nxt not in F or abs(nxt[0]-s.current[0])+abs(nxt[1]-s.current[1])!=1:
                    s.end('technical_error','next_move_invalid',tick,P,F);fatal='next_move_invalid';frame['after']=safe(s.record(P,F));break
                if s.E<=0:s.end('resource_infeasible','no_resource_for_next_move',tick,P,F);frame['after']=safe(s.record(P,F));continue
                old=s.current;kind='non_target' if nxt not in P else 'session_repeat' if nxt in s.H else 'fresh_target'
                angle=None
                if s.previous is not None:
                    dot=(old[0]-s.previous[0])*(nxt[0]-old[0])+(old[1]-s.previous[1])*(nxt[1]-old[1]);angle=90 if dot==0 else 180 if dot==-1 else 0
                    s.turns90+=angle==90;s.turns180+=angle==180
                prior=s.first_credit.get(nxt);s.actions.append(dict(kind='move',tick=tick,arrival_tick=tick+1,start=list(old),end=list(nxt),classification=kind,turn_degrees=angle,first_credit_event=prior['event_id'] if prior else None,repeat_across_event=bool(prior and prior['event_id']!=epoch)))
                s.current=nxt;s.previous=old;s.M+=1;s.E-=1;s.cursor+=1;s.move_classes[kind]+=1;s.credit(nxt,tick+1,'arrival',P,origin,epoch)
            elif s.current==base and not ((P&F)-s.H):
                s.actions.append(dict(kind='wait',tick=tick,end_tick=tick+1,current=list(s.current),previous=list(s.previous) if s.previous is not None else None));s.waits+=1
            else:
                s.end('technical_error','plan_exhausted_without_completion',tick,P,F);fatal='plan_exhausted_without_completion';frame['after']=safe(s.record(P,F));break
            frame['after']=safe(s.record(P,F))
        if fatal:break
        if all(s.terminal for s in states.values()) and tick>=final_tick:break
    for name,s in states.items():
        result['sessions'][name]=dict(terminal=s.terminal,actions=s.actions,requests=s.requests,credits=s.credits,frames=s.frames,summary=safe(dict(status=s.terminal['status'],reason=s.terminal['reason'],finish_tick=s.terminal['tick'],M=s.M,E=s.E,waits=s.waits,current=s.current,previous=s.previous,H=sorted(s.H),P=sorted(P),F=sorted(F),U=sorted((P&F)-s.H),D=sorted(P-F-s.H),historical_now_blocked=sorted(s.H-F),returned=s.current==base,response_calls=len(s.requests),move_classes=s.move_classes,turns90=s.turns90,turns180=s.turns180,first_credit=s.credits,zero_move_credits=sum(e['source']=='publication' for e in s.credits),benchmark_eligible=False)))
    assert original==wire(world),'world mutated by executor';result['fatal_technical_error']=fatal
    if fatal:raise TechnicalError(fatal,safe(result))
    return safe(result)
