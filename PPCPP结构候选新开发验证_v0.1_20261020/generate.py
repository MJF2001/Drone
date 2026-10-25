"""Fixed geometry and real execution prefixes. No outcome-dependent sampling."""
from collections import deque
from spec import plans
from common import H,R,read,save,sha,protect,call,signature
def rect(x,y,w,h):return {(a,b) for a in range(x,x+w) for b in range(y,y+h)}
def before(p):
    L,w=p['length'],p['width'];f=rect(0,0,2*L+2*w+12,L+2*w+12);t=rect(4,4,L,w)
    if p['layout']=='B':t|=rect(4+L-w,4+w,w,L//2)
    return f,t
def snapshot(name,f,t,h,current,initial,previous,old):
    return dict(name=name,free=sorted(f),targets=sorted(t&f),covered=sorted(h),published_targets=sorted(t),deferred_targets=sorted(t-f-h),current=current,base=(1,1),distance_budget=1000000,initial_targets=sorted(initial),predator=(-1,0),previous=previous,old_route=old)
def path(f,a,b):
    if a==b:return [a]
    if abs(a[0]-b[0])+abs(a[1]-b[1])==1 and b in f:return [a,b]
    parent={a:None};q=deque([a])
    while q and b not in parent:
        x,y=q.popleft()
        for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if z in f and z not in parent:parent[z]=(x,y);q.append(z)
    assert b in parent,'witness unreachable';result=[];cur=b
    while cur is not None:result.append(cur);cur=parent[cur]
    return result[::-1]
def completion_witness(f,t,h,current):
    route=[current];pending=t-h-{current}
    for goal in sorted(pending,key=lambda q:(q[1],q[0])):
        if goal not in pending:continue
        segment=path(f,route[-1],goal);route+=segment[1:];pending-=set(segment)
    route+=path(f,route[-1],(1,1))[1:];assert not pending;return route
def main():
    p=protect();assert not (H/'prep').exists() and not (H/'inputs').exists();prepared={}
    for plan in plans():
        f,t=before(plan);c=snapshot(plan['plan_id']+'_initial',f,t,set(),(1,1),t,None,[(1,1)])
        inp=H/'prep/inputs'/(plan['plan_id']+'.json');save(inp,c)
        j=dict(run_id=plan['plan_id']+'_prepare',batch='preparation',case_id=plan['plan_id'],input=str(inp),seed=20261021,method='PPCPP',budget=20)
        result=call(j,H/'prep/results'/(plan['plan_id']+'.json'));assert result['eligible'],j
        prepared[plan['plan_id']]=(f,t,list(map(tuple,result['raw']['route'])),str(inp),str(H/'prep/results'/(plan['plan_id']+'.json')))
        print('prepared',plan['plan_id'],len(t),flush=True)
    for case in p['cases']:
        f0,t0,route,initial_input,initial_result=prepared[case['plan_id']];L,w=case['length'],case['width'];goal=(len(t0)*case['progress']+99)//100;h=set();cut=None
        for i,q in enumerate(route):
            if q in t0:h.add(q)
            if len(h)>=goal:cut=i;break
        assert cut is not None and cut>0 and len(h)==goal
        prefix=route[:cut+1];cur=prefix[-1];f=set(f0);t=set(t0);blocked=set();switched=False
        if case['event']=='straight':
            t|=rect(4+L,4,L//2,w) if case['layout']=='A' else rect(4+L-w,4+w+L//2,w,L//2)
        elif case['event']=='corner':
            t|=rect(4+L-w,4+w,w,L//2) if case['layout']=='A' else rect(4+L-w-L//2,4+L//2,L//2,w)
        else:
            blocked=rect(4+2*L//3,4,max(2,L//10),w//2)
            if cur in blocked:blocked=rect(4+2*L//3,4+w-w//2,max(2,L//10),w//2);switched=True
            assert cur not in blocked and (1,1) not in blocked;f-=blocked
        assert t<=f0 and h<=t0 and cur in f
        c=snapshot(case['case_id'],f,t,h,cur,t0,prefix[-2],route[cut:]);save(__import__('pathlib').Path(case['input']),c)
        witness=completion_witness(f,t&f,h,cur)
        save(H/'witnesses'/(case['case_id']+'.json'),dict(case=case,initial_input=initial_input,initial_result=initial_result,cut_index=cut,history=prefix,goal_covered=goal,blocked=sorted(blocked),switched=switched,feasible_route=witness))
        print('generated',case['case_id'],len(h),len(t&f),len(t-f-h),flush=True)
    protect();print('generated 36 fixed snapshots; not yet input-sealed')
if __name__=='__main__':main()
