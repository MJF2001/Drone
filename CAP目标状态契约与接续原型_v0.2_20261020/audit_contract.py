"""Independent explicit-target state/physical ledger checker; no runtime."""
def pts(xs):return set(map(tuple,xs))
def audit(c,r):
    f=pts(c['free']);t=pts(c['targets']);h=pts(c['covered']);p=pts(c.get('published_targets',list(t|h)))
    path=list(map(tuple,r['path']));assert path and path[0]==tuple(c['current']) and set(path)<=f
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
    assert pts(r['covered'])==h|(set(path)&t) and pts(r['pending'])==t-h-set(path)
    assert pts(r['deferred'])==p-f-h
    assert not r['global_complete'] and not r['benchmark_eligible'] and 'route' not in r
    assert len(path)-1<=c.get('distance_budget',float('inf'))
    cursor=0;pending=t-h-{tuple(c['current'])};active=None;lastgen=0;plans={}
    for e in r['events']:
        if e['type']=='bind':
            assert active is None or active['phase']=='reached'
            active=dict(e['state']);assert active['generation']==lastgen+1;lastgen+=1
            assert tuple(active['point']) in f and active['reference'] and active['phase']=='bound'
        elif e['type']=='move':
            assert active and active['phase']=='bound' and e['target_generation']==active['generation']
            assert tuple(e['start'])==path[cursor] and tuple(e['end'])==path[cursor+1]
            v=path[cursor+1];credit={v} if v in pending else set();assert credit==pts(e['credited']);pending-=credit;cursor+=1
        elif e['type']=='local_plan':
            assert e['target_state']==active and tuple(e['end'])==tuple(active['point'])
            order=list(map(tuple,e['order']));assert order[0]==path[e['path_index']] and order[-1]==tuple(active['point'])
            assert pts(e['required'])<=set(order) and e['tsp']['final_cost']<=e['tsp']['initial_cost']
            plans[active['generation']]=e
        elif e['type']=='target_reached':
            assert active and e['generation']==active['generation'] and tuple(e['point'])==tuple(active['point'])==path[e['path_index']]
            plan=plans[active['generation']];assert pts(plan['required'])<=set(path[plan['path_index']:e['path_index']+1])
            assert e['path_index']-plan['path_index']==plan['tsp']['final_cost'];active['phase']='reached'
        else:raise AssertionError(e['type'])
    assert cursor==len(path)-1 and pending==pts(r['pending']) and active==r['target_state']
    if r['status']=='region_complete_transition_required':assert active and active['phase']=='reached' and r['region_complete']
    return dict(checked=True,moves=len(path)-1,status=r['status'])
