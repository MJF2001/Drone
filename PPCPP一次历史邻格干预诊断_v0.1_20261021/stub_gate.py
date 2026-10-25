"""Exactly eight fixed stub checks; no real planner or geometry call."""
import sys,types
from probe_common import *
from probe_hook import force_history_step
def run():
    rows=[];action=dict(current=[5,2],previous=[4,2],next=[5,1]);helpercalls=0
    class Deadline(Exception):pass
    for case in range(1,8):
        s=types.SimpleNamespace(current=(5,2),free={(5,2),(5,1),(5,3)},covered={(5,1)},distance_budget=20);pending={(5,3)};route=[s.current];trace=[];record=dict(enabled=True,trigger_count=0);a=dict(action);clock=[0];regular_started=False
        if case==2:a['next']=[5,0]
        if case==3:s.free.remove((5,1))
        if case==4:a['next']=[5,3]
        if case==5:pending={(8,8)};s.free.add((8,8))
        def tick():
            if clock[0]>=20:raise Deadline()
        def hook(stage):
            if case==6 and stage=='force_before':clock[0]=20
            if case==7 and stage=='force_after':clock[0]=20
        exc=None
        try:
            helpercalls+=1;force_history_step(s,(4,2),pending,route,trace,a,tick,20,record,hook);regular_started=True
        except (ValueError,Deadline) as e:exc=type(e).__name__+':'+str(e)
        if case==1:
            assert exc is None and route==[(5,2),(5,1)] and pending=={(5,3)} and record['after']['previous']==(5,2) and record['trigger_count']==1 and record['added_new_capture_credit']==0 and record['added_steps']==1 and len(trace)==1
        elif case in (2,3,4,5):assert exc is not None and exc.startswith('ValueError:') and len(route)==1 and record['trigger_count']==0
        elif case==6:assert exc.startswith('Deadline:') and len(route)==1 and not regular_started
        elif case==7:assert exc.startswith('Deadline:') and len(route)==2 and record['trigger_count']==1 and not regular_started and record['deadline']==20
        rows.append(norm(dict(case=case,passed=True,exception=exc,route=route,pending=sorted(pending),intervention=record,regular_started=regular_started)))
    # Execute actual entry timing/encoding wrapper, replacing solve with a non-planning stub.
    sys.path.insert(0,str(H));import runtime,candidate
    previous=candidate.solve;clock=[0];calls=[]
    def stub(*args,**kwargs):calls.append('stub_only');return dict(status='core_complete',route=[(5,2),(5,1)],branches={},trace=[],selected='stub')
    candidate.solve=stub
    def stage(name):
        if name=='encode_after':clock[0]=20
    try:x=runtime.run_payload((H/'inputs'/f'{CASES[0]}.json').read_bytes(),'PPCPP',20,SEEDS[0],hook=stage,clock=lambda:clock[0])
    finally:candidate.solve=previous
    assert calls==['stub_only'] and not x['eligible'] and x['entry_seconds']==20 and x['raw']['status']=='deadline' and not x['raw']['route']
    rows.append(dict(case=8,passed=True,actual_wrapper_stub_solve_calls=1,result=x))
    return dict(tests=rows,passed=len(rows)==8,force_helper_stub_invocations=helpercalls,entry_wrapper_stub_invocations=1,real_core_calls=0,real_planner_entries=0)
if __name__=='__main__':save(H/'stub_results.json',run());print('PASS 8 fixed stub checks; helper calls=7, wrapper stub=1, real planner/core=0')
