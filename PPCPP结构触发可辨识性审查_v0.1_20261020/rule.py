"""Structural feature only; no route generation and no outcome-dependent trigger."""
from collections import deque

def components(cells):
    cells=set(cells);label={};sizes=[];anchors=[]
    for root in sorted(cells):
        if root in label:continue
        k=len(sizes);anchors.append(root);q=deque([root]);label[root]=k;n=0
        while q:
            x,y=q.popleft();n+=1
            for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if z in cells and z not in label:label[z]=k;q.append(z)
        sizes.append(n)
    return label,sizes,anchors

def distances(free,start):
    d={start:0};q=deque([start])
    while q:
        x,y=q.popleft()
        for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if z in free and z not in d:d[z]=d[x,y]+1;q.append(z)
    return d

def measure(c,raw,k):
    state=raw['branch_state']
    if state is None:return dict(triggered=False,eligible=False,recovery_index=k)
    pending=set(map(tuple,state['pending']));path=list(map(tuple,state['path']));free=set(map(tuple,c['free']))
    assert pending==set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(path)
    d=distances(free,path[-1]);db=distances(free,tuple(c['base']))
    nearest=min(pending,key=lambda q:(d[q],q));near=min(pending,key=lambda q:(db[q],q));far=min(pending,key=lambda q:(-db[q],q))
    goals=[]
    for q in (nearest,near,far):
        if q not in goals:goals.append(q)
    assert goals==[tuple(b['forced_goal']) for b in raw['branches']]
    ev=[e for e in raw['branches'][0]['trace'] if e['kind']=='recovery'][k-1];assert ev['index']==len(path)-1
    label,sizes,anchors=components(pending);ids=[label[q] for q in goals]
    return dict(triggered=True,eligible=len(set(ids))>=2,recovery_index=k,pending_count=len(pending),prefix_steps=len(path)-1,component_count=len(sizes),component_sizes=sizes,component_anchors=anchors,candidate_goals=goals,candidate_component_ids=ids,candidate_component_count=len(set(ids)))

def select(policy,first,second):
    if first['eligible']:return 'FIRST'
    if policy=='TWO_WINDOW_REPLAY' and second['eligible']:return 'SECOND'
    if policy not in ('FIRST_FILTER','TWO_WINDOW_REPLAY'):raise ValueError(policy)
    return 'PPCPP'
