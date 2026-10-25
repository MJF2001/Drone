"""Independent shortest-path ledgers for the already fixed illustrations."""
import json
from bridge_graph import bfs
from bridge_analysis import H,read,save
def account(c,route):
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));seen=set(map(tuple,c['covered']));path=list(map(tuple,route));anchors=[0]
    seen.add(path[0])
    for i,p in enumerate(path[1:],1):
        if p in t-seen:anchors.append(i)
        seen.add(p)
    if anchors[-1]!=len(path)-1:anchors.append(len(path)-1)
    legs=[];cache={}
    for a,b in zip(anchors,anchors[1:]):
        start,goal=path[a],path[b]
        if start not in cache:cache[start]=bfs(f,start)
        distances,parents=cache[start];short=[goal]
        while short[-1]!=start:short.append(parents[short[-1]])
        short.reverse();assert len(short)-1==distances[goal]<=b-a
        legs.append(dict(from_step=a,to_step=b,start=start,goal=goal,actual_steps=b-a,shortest_distance=distances[goal],shortest_path=short))
    return dict(anchors=anchors,legs=legs,total_actual=sum(x['actual_steps'] for x in legs),sum_endpoint_distances=sum(x['shortest_distance'] for x in legs),interpretation='Endpoints are fixed by this actual route. This is a distance ledger, not an independently executable competing coverage algorithm or an optimality proof.')
def compute():
    cases=sorted({c for ex in read(H/'example_index.json') for c in ex.get('cases',[])})
    out={}
    for case in cases:
        c=read(H/'inputs'/f'{case}.json')
        for method in ('PPCPP','P2_MULTI'):
            jid=f'{case}__r0__{method}';r=read(H/'outputs'/f'{jid}.json')['result']['raw']['route'];out[jid]=account(c,r)
    return out
if __name__=='__main__':
    save(H/'example_shortest_path_ledger.json',compute());print('Saved independent BFS path ledgers for fixed rep0 illustrations; no planner/exact calls.')
