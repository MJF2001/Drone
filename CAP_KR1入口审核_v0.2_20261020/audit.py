"""Independent ledger, decision and partition auditor; no planner imports."""
from collections import deque
from partition_audit import audit as partition_audit
def pts(x):return set(map(tuple,x))
def distances(f,start):
    d={start:0};q=deque([start])
    while q:
        x,y=q.popleft()
        for p in ((x-1,y),(x,y+1),(x,y-1),(x+1,y)):
            if p in f and p not in d:d[p]=d[(x,y)]+1;q.append(p)
    return d
def audit(c,r):
    f=pts(c['free']);t=pts(c['targets']);h=pts(c['covered']);path=list(map(tuple,r['diagnostic_route']))
    assert path and path[0]==tuple(c['current']) and set(path)<=f
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
    assert r['distance']==len(path)-1<=c.get('distance_budget',float('inf'))
    assert pts(r['pending'])==t-h-set(path)
    assert pts(r['deferred'])==pts(c.get('published_targets',list(t|h)))-f-h
    assert not r['benchmark_eligible'] and not r['global_completion_fallback']
    pending=t-h-{path[0]};cursor=0;state=None;generation=0;reached={}
    for e in r['events']:
        if e['type']=='bind':
            assert state is None or state['phase']=='reached'
            generation+=1;state=dict(e['state']);assert state['generation']==generation and state['phase']=='bound'
            assert pts(e['pending'])==pending and tuple(e['current'])==path[cursor]
            point=tuple(state['point']);assert point in f
            if generation==1 and c.get('cap_resume_target') is not None:
                assert state['source']=='provided_resume' and point==tuple(c['cap_resume_target']['point'])
                assert state['reference']==c['cap_resume_target']['reference']
            else:
                x,y=path[cursor];v=next((p for p in ((x-1,y),(x,y+1),(x,y-1),(x+1,y)) if p in pending),None)
                if v is not None:assert point==v and state['source']=='KR1_global_direction'
                else:
                    d=distances(f,path[cursor]);assert point==min(pending,key=lambda p:(d[p],p)) and state['source']=='KR1_global_nearest'
                assert state['reference']==('KR1_restart' if generation==1 else 'KR1_explicit_next_region')
        elif e['type']=='move':
            assert tuple(e['start'])==path[cursor] and tuple(e['end'])==path[cursor+1]
            v=path[cursor+1];assert pts(e['credited'])==({v} if v in pending else set());pending.discard(v);cursor+=1
            if e['mode']=='region':assert state and state['phase']=='bound' and e['generation']==state['generation']
            else:assert e['mode']=='return' and not pending
        elif e['type']=='target_reached':
            assert state and state['phase']=='bound' and e['generation']==generation
            assert tuple(e['point'])==tuple(state['point'])==path[cursor] and e['path_index']==cursor
            state['phase']='reached';reached[generation]=cursor
        else:raise AssertionError(e['type'])
    assert cursor==len(path)-1 and pending==pts(r['pending']) and state==r['target_state']
    for plan in r['plans']:
        before=plan['structure_before'];i=plan['region_id'];assert before['order'][0]==i
        node=next(n for n in before['nodes'] if n['id']==i)
        required=pts(plan['required']);assert required==pts(node['R'])
        start=plan['path_start'];assert required<=t-h-set(path[:start+1])
        order=list(map(tuple,plan['order']));assert order[0]==path[start]==tuple(plan['start'])
        assert order[-1]==tuple(plan['end'])==tuple(plan['target_state']['point']) and required<=set(order)
        if plan['completed']:
            end=plan['path_end'];assert required<=set(path[start:end+1])
            assert end-start==plan['tsp']['final_cost'] and path[end]==tuple(plan['end'])
            assert reached[plan['target_state']['generation']]==end
            if 'structure_after' in plan:
                partition_audit(before,plan['structure_after'],t-h-set(path[:end+1]))
    if r['status']=='complete':
        assert list(map(tuple,r['route']))==path and not pending and path[-1]==tuple(c['base'])
        assert all(p['completed'] and 'structure_after' in p for p in r['plans'])
    else:assert r['route']==[]
    return dict(legal=True,status=r['status'],moves=len(path)-1,decisions=generation)
