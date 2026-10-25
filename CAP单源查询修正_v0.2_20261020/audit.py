"""Read-only independent ledger/route/structure auditor. No planner imports."""
import json
from collections import deque
def cells(xs):return set(map(tuple,xs))
def distance(f,a,b):
    q=deque([(a,0)]);seen={a}
    while q:
        p,d=q.popleft()
        if p==b:return d
        x,y=p
        for v in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if v in f and v not in seen:seen.add(v);q.append((v,d+1))
    return None
def structure(s,pending,method):
    nodes={n['id']:n for n in s['nodes']};order=s['order'];assert len(order)==len(set(order))
    active=[n for n in nodes.values() if not n.get('children') and n['state']!='C']
    assert set(order)=={n['id'] for n in active}
    union=set()
    for n in active:
        r=cells(n['R']);assert r and r<=cells(n['A']);assert not union&r;union|=r
    assert union==pending,('region ledger',len(union),len(pending))
    if method=='TRACE':
        index={tuple(p):i for p,i in s['index']};assert len(index)==len(s['index'])
        for n in active:
            for p in cells(n['R']):assert index[p]==n['id']
        for n in nodes.values():
            if n['children']:
                parts=[cells(nodes[i]['A']) for i in n['children']]
                assert set().union(*parts)==cells(n['R'])
                assert sum(map(len,parts))==len(set().union(*parts))
                assert all(nodes[i]['parent']==n['id'] for i in n['children'])
def audit(c,r):
    f=cells(c['free']);t=cells(c['targets']);h=cells(c['covered']);p=cells(c.get('published_targets',list(t|h)))
    path=list(map(tuple,r['diagnostic_route']));assert path and path[0]==tuple(c['current'])
    assert set(path)<=f
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
    assert cells(r['deferred'])==p-f-h
    assert cells(r['pending'])==t-h-set(path)
    cursor=0
    for move in r['moves']:
        a,b=move['start_index'],move['end_index'];assert a==cursor and a<=b<len(path);cursor=b
        before=t-h-set(path[:a+1]);after=t-h-set(path[:b+1])
        assert cells(move['credited'])==before-after
        assert cells(move['pending_after'])==after
        if not move['interrupted']:
            dest=tuple(move['destination']);assert path[b]==dest
            assert b-a==distance(f,path[a],dest),'nonshortest connector'
    assert cursor==len(path)-1
    previous_A={}
    for plan in r['plans']:
        a=plan['path_start'];before=t-h-set(path[:a+1]);structure(plan['structure_before'],before,r['method'])
        order=list(map(tuple,plan['order']));executed=list(map(tuple,plan['executed_order']));required=cells(plan['required'])
        assert order[0]==path[a]==tuple(plan['start']);assert required<=set(order)
        if plan['end'] is not None:assert order[-1]==tuple(plan['end'])
        assert executed==(order[:-1] if r['method']=='TRACE' and plan['end'] is not None else order)
        assert plan['tsp']['final_cost']<=plan['tsp']['initial_cost']
        for n in plan['structure_before']['nodes']:
            area=cells(n['A'])
            if n['id'] in previous_A:assert previous_A[n['id']]==area
            previous_A[n['id']]=area
        if plan['completed']:
            b=plan['path_end'];assert required<=set(path[a:b+1]);assert path[b]==executed[-1]
            structure(plan['structure_after'],t-h-set(path[:b+1]),r['method'])
    for event in r['structure_events']:
        if event['type']=='update':
            old=event['old_order'];new=event['new_order'];survivors=set(old)&set(new)
            assert [i for i in old if i in survivors]==[i for i in new if i in survivors]
    if r['status']=='complete':
        assert list(map(tuple,r['route']))==path;assert path[-1]==tuple(c['base'])
        assert not cells(r['pending']);assert len(path)-1<=c['distance_budget']
        assert r['seconds']>=0
    else:assert not r['route']
    assert r['global_completion'] is False
    return dict(audit='PASS',status=r['status'],steps=len(path)-1,plans=len(r['plans']),seconds=r['seconds'])
