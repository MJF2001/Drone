"""Handwritten maps/routes/expectations, frozen BEFORE any executor run.
No route generator, solver, BFS, or executor imports. Helpers package literals.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
L2=[[0,0],[1,0]]
L3=[[0,0],[1,0],[2,0]]
L4=[[0,0],[1,0],[2,0],[3,0]]
S6=[[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]]
S4=[[0,0],[1,0],[0,1],[1,1]]
R2=[[0,0],[1,0],[0,0]]
R4=[[0,0],[1,0],[2,0],[1,0],[0,0]]
RB=[[0,0],[0,1],[1,1],[2,1],[2,0],[1,0],[0,0]]
def event(t,id,add=[],block=[]):return dict(tick=t,id=id,add_targets=add,block=block)
def world(f,p,E=10,T=10,events=[]):return dict(free=f,published=p,base=[0,0],start=[0,0],E0=E,T_max=T,events=events)
def response(route,seconds=.01,status='complete'):return dict(route=route,entry_seconds=seconds,native_status=status,source='HANDWRITTEN_STUB_NOT_PPCPP_OR_P2')
def expect(status,t,M,E,H,current=[0,0],previous=[1,0],waits=0,calls=1,reason=None,**kw):return dict(status=status,finish_tick=t,M=M,E=E,H=H,current=current,previous=previous,waits=waits,response_calls=calls,reason=reason,**kw)
def case(id,category,w,methods,expected,**kw):return dict(id=id,category=category,world=w,methods=methods,expected=expected,**kw)
def specs():
    a=[]
    a.append(case('01_two_event_chain',1,world(S6,[[1,0],[2,0]],20,10,[event(1,'e1',[[2,1]]),event(3,'e2',block=[[1,0]])]),
      {'A':[response(R4),response([[1,0],[2,0],[2,1],[1,1],[0,1],[0,0]]),response([[2,1],[1,1],[0,1],[0,0]])]},
      {'A':expect('success',6,6,14,[[1,0],[2,0],[2,1]],previous=[0,1],calls=3,turns90=3,turns180=0,historical_now_blocked=[[1,0]],move_classes=dict(fresh_target=3,initial_historical=0,session_repeat=0,non_target=3))},
      input_expectations=[dict(method='A',sequence=2,tick=3,fields=dict(current=[2,1],previous=[2,0],covered=[[1,0],[2,0],[2,1]],distance_budget=17,old_route=[[2,1],[1,1],[0,1],[0,0]],initial_targets=[[1,0],[2,0],[2,1]]))],hand_note='At t1 adopt response1; its moves arrive(2,0)@2,(2,1)@3; event2 input must use precisely these moves. Plan lengths4+5+3=12, actual M=6.'))
    a.append(case('02_independent_histories',2,world(S6,[[2,0]],20,10,[event(1,'e1',[[2,1]]),event(2,'e2',block=[[0,1]])]),
      {'A':[response(R4),response([[1,0],[2,0],[2,1],[1,1],[1,0],[0,0]]),response([[2,0],[2,1],[1,1],[1,0],[0,0]])],
       'B':[response(RB),response([[0,1],[1,1],[2,1],[2,0],[1,0],[0,0]]),response([[1,1],[2,1],[2,0],[1,0],[0,0]])]},
      {'A':expect('success',6,6,14,[[2,0],[2,1]],calls=3),'B':expect('success',6,6,14,[[2,0],[2,1]],calls=3)},
      input_expectations=[dict(method='A',sequence=2,tick=2,fields=dict(current=[2,0],previous=[1,0],covered=[[2,0]],distance_budget=18)),dict(method='B',sequence=2,tick=2,fields=dict(current=[1,1],previous=[0,1],covered=[],distance_budget=18))],hand_note='Same two publication records and world hash; different own currents/H at event2.'))
    a.append(case('03_early_finish_wait',3,world(L4,[[1,0]],20,18,[event(4,'e1',[[2,0]]),event(10,'e2',[[3,0]])]),
      {'A':[response(R2),response(R4),response([[0,0],[1,0],[2,0],[3,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('success',16,12,8,[[1,0],[2,0],[3,0]],waits=4,calls=3,turns90=0,turns180=5)},
      wait_ticks=dict(A=[2,3,8,9]),hand_note='Return@2, wait ticks2,3; return@8, wait8,9; final event still publishes@10.'))
    a.append(case('04_current_new_credit',4,world(L3,[],10,5,[event(1,'e1',[[1,0],[0,0]])]),
      {'A':[response(R2),response([[1,0],[0,0]])]},
      {'A':expect('success',2,2,8,[[0,0],[1,0]],calls=2,zero_move_credits=1)},
      input_expectations=[dict(method='A',sequence=1,tick=1,fields=dict(current=[1,0],previous=[0,0],covered=[[1,0]],initial_targets=[[1,0]],distance_budget=9,old_route=[[1,0],[0,0]]))],hand_note='t0 traversed unpublished1; initial0 also unpublished. At t1 current1 earns exactly one credit, past0 does not; 0 credited only on actual arrival@2.'))
    a.append(case('05_block_history_and_pending',5,world(S6,[[1,0],[2,0]],10,8,[event(2,'e1',block=[[1,0],[2,0]])]),
      {'A':[response([[0,0],[1,0],[1,1],[2,1],[2,0],[1,0],[0,0]]),response([[1,1],[0,1],[0,0]])]},
      {'A':expect('success',4,4,6,[[1,0]],previous=[0,1],calls=2,D=[[2,0]],historical_now_blocked=[[1,0]])},hand_note='1 was captured@1 then blocked; 2 never captured and becomes deferred.'))
    a.append(case('06_only_A_current_blocked',6,world(S6,[[2,0]],20,10,[event(1,'e1',block=[[1,0]])]),
      {'A':[response(R4)],'B':[response(RB),response([[0,1],[1,1],[2,1],[2,0],[2,1],[1,1],[0,1],[0,0]])]},
      {'A':expect('environment_termination',1,1,19,[],current=[1,0],previous=[0,0],reason='current_blocked'),
       'B':expect('success',8,8,12,[[2,0]],previous=[0,1],calls=2)},hand_note='No world repair. A frozen prefix1 is not a winning shorter route; B uses upper return.'))
    a.append(case('07a_base_blocked',7,world(L3,[[1,0]],10,4,[event(1,'e1',block=[[0,0]])]),{'A':[response(R2)]},
      {'A':expect('environment_termination',1,1,9,[[1,0]],current=[1,0],previous=[0,0],reason='base_blocked')}))
    a.append(case('07b_pending_disconnected',7,world([[0,0],[1,0],[2,0],[0,1]],[[2,0]],10,6,[event(1,'e1',block=[[1,0]])]),
      {'A':[response([[0,0],[0,1],[0,0],[1,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('environment_termination',1,1,9,[],current=[0,1],previous=[0,0],reason='target_unreachable',U=[[2,0]],D=[])}))
    a.append(case('07c_return_disconnected',7,world(L3,[[2,0]],10,5,[event(2,'e1',block=[[1,0]])]),{'A':[response(R4)]},
      {'A':expect('environment_termination',2,2,8,[[2,0]],current=[2,0],previous=[1,0],reason='base_unreachable')}))
    a.append(case('08a_time_19_999',8,world(L2,[[1,0]],2,3),{'A':[response(R2,19.999,'deadline')]},{'A':expect('success',2,2,0,[[1,0]])}))
    a.append(case('08b_time_20_000',8,world(L2,[[1,0]],2,3),{'A':[response(R2,20.000,'deadline')]},{'A':expect('deadline',0,0,2,[],previous=None,reason='entry_not_strictly_less_than_20')}))
    a.append(case('08c_time_20_001',8,world(L2,[[1,0]],2,3),{'A':[response(R2,20.001,'deadline')]},{'A':expect('deadline',0,0,2,[],previous=None,reason='entry_not_strictly_less_than_20')}))
    a.append(case('09a_invalid_no_old_fallback',9,world(S6,[[2,0]],10,5,[event(1,'e1',block=[[2,0]])]),
      {'A':[response(R4),response([[1,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('invalid_route',1,1,9,[],current=[1,0],previous=[0,0],calls=2,reason='endpoint_or_collision',D=[[2,0]])},
      input_expectations=[dict(method='A',sequence=1,tick=1,fields=dict(old_route=[[1,0],[2,0],[1,0],[0,0]]))]))
    a.append(case('09b_missing_no_old_fallback',9,world(S6,[[2,0]],10,5,[event(1,'e1',block=[[2,0]])]),{'A':[response(R4),None]},
      {'A':expect('solver_no_solution',1,1,9,[],current=[1,0],previous=[0,0],calls=2,reason='missing_response',D=[[2,0]])}))
    a.append(case('10a_exact_resource_success',10,world(L2,[[1,0]],2,3),{'A':[response(R2)]},{'A':expect('success',2,2,0,[[1,0]])}))
    a.append(case('10b_resource_event_reject',10,world(L3,[[1,0]],2,5,[event(1,'e1',[[2,0]])]),{'A':[response(R2),response([[1,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('resource_infeasible',1,1,1,[[1,0]],current=[1,0],previous=[0,0],calls=2,reason='full_route_exceeds_remaining_resource')},input_expectations=[dict(method='A',sequence=1,tick=1,fields=dict(distance_budget=1))]))
    a.append(case('10c_Tmax_arrival_success',10,world(L2,[[1,0]],10,2),{'A':[response(R2)]},{'A':expect('success',2,2,8,[[1,0]])}))
    a.append(case('10d_Tmax_cannot_move',10,world(L2,[[1,0]],10,1),{'A':[response(R2)]},
      {'A':expect('tick_limit',1,1,9,[[1,0]],current=[1,0],previous=[0,0],reason='maximum_tick_reached')}))
    a.append(case('11a_wait_keeps_turn_repeat',11,world(L3,[[1,0]],10,9,[event(3,'e1',[[2,0]])]),{'A':[response(R2),response(R4)]},
      {'A':expect('success',7,6,4,[[1,0],[2,0]],waits=1,calls=2,turns90=0,turns180=3,move_classes=dict(fresh_target=2,initial_historical=0,session_repeat=2,non_target=2))},
      wait_ticks=dict(A=[2]),input_expectations=[dict(method='A',sequence=1,tick=3,fields=dict(previous=[1,0],old_route=[[0,0]]))]))
    a.append(case('11b_cross_plan_right_angle',11,world(S4,[[1,0]],10,6,[event(1,'e1',[[1,1]])]),{'A':[response(R2),response([[1,0],[1,1],[0,1],[0,0]])]},
      {'A':expect('success',4,4,6,[[1,0],[1,1]],previous=[0,1],calls=2,turns90=3,turns180=0,move_classes=dict(fresh_target=2,initial_historical=0,session_repeat=0,non_target=2))}))
    a.append(case('12a_merged_future_A',12,world(L4,[[1,0]],10,8,[event(1,'b',block=[[3,0]]),event(1,'a',[[2,0]])]),{'A':[response(R2),response([[1,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('success',4,4,6,[[1,0],[2,0]],calls=2)},isolation_pair='12b_merged_future_B',hand_note='IDs sorted a,b; one request at tick1. Callback input at tick0 byte-identical to future_B.'))
    a.append(case('12b_merged_future_B',12,world(L4,[[1,0]],10,8,[event(1,'b'),event(1,'a',[[3,0]])]),{'A':[response(R2),response([[1,0],[2,0],[3,0],[2,0],[1,0],[0,0]])]},
      {'A':expect('success',6,6,4,[[1,0],[3,0]],calls=2)},isolation_pair='12a_merged_future_A'))
    # Intentionally expected fatal technical rejection comes LAST: no callback
    # or simulated session starts after this terminal technical case.
    a.append(case('08d_NaN_expected_technical_stop_LAST',8,world(L2,[[1,0]],2,3),{'A':[response(R2,'NaN_STUB_FIELD')]},
      {'A':expect('technical_error',0,0,2,[],previous=None,reason='invalid_time_field')},expected_technical_stop=True))
    return a
def main():
    cases=specs();assert len(cases)==23 and {c['category'] for c in cases}==set(range(1,13))
    count=sum(len(v) for c in cases for v in c['methods'].values());assert count==43
    obj=dict(scope='SYNTHETIC_HANDWRITTEN_NOT_RESEARCH_MAPS',categories=12,subcases=23,planned_sessions=25,planned_stub_responses=43,cumulative_stub_cap_all_rounds=48,technical_round_cap=3,routes='literal hand-written complete routes; never solved/optimized',expected_values='manual arithmetic before executor first run; not copied from outputs',ordered_cases=cases)
    with (H/'fixture_spec.json').open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
    print('Locked12 categories/23 subcases/25 sessions/43 planned handwritten stub responses; cap48 across all technical rounds')
if __name__=='__main__':main()
