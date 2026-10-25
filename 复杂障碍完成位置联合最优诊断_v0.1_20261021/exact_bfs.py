"""Unit-edge BFS: acquired mask, integer packed states; full proof records."""
import time,gzip,json
from collections import deque,Counter
def solve(q,certificate):
    begin=time.perf_counter();f=set(map(tuple,q['free']));cells=sorted(f);idx={p:i for i,p in enumerate(cells)};n=len(cells);tasks=sorted(map(tuple,q['tasks']));bits={p:1<<i for i,p in enumerate(tasks)};allbits=(1<<len(tasks))-1
    s=tuple(q['start']);b=tuple(q['base']);e=tuple(q['last']) if q['last'] is not None else None;limit=q['resource'];assert s in f and b in f and (e is None or e in tasks)
    adjacency=[]
    for x,y in cells:adjacency.append([idx[v] for v in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)) if v in f])
    initial=bits.get(s,0);lastbit=bits.get(e,0);invalid=e==s and initial!=allbits
    records=[[initial*n+idx[s],-1,0]];known={records[0][0]:0};todo=deque([] if invalid else [0]);popped=[];goal=None;status='infeasible';reason='last_at_start' if invalid else 'exhausted';peak=len(todo)
    while todo:
        if time.perf_counter()-begin>=q['seconds']:status='unresolved';reason='time_limit';break
        k=todo.popleft();packed,parent,d=records[k];mask,pos=divmod(packed,n)
        if mask==allbits and cells[pos]==b:goal=k;status='optimal';reason='first_goal_dequeued';break
        popped.append(k)
        if d>=limit:continue
        for dest in adjacency[pos]:
            bit=bits.get(cells[dest],0)
            if bit==lastbit and lastbit and not(mask&lastbit) and (mask|lastbit)!=allbits:continue
            new=(mask|bit)*n+dest
            if new in known:continue
            if len(records)>=q['max_states']:status='unresolved';reason='state_limit';break
            known[new]=len(records);records.append([new,k,d+1]);todo.append(len(records)-1)
        peak=max(peak,len(todo))
        if reason=='state_limit':break
    route=[]
    if goal is not None:
        k=goal
        while k!=-1:route.append(cells[records[k][0]%n]);k=records[k][1]
        route.reverse()
    seconds=time.perf_counter()-begin
    with gzip.open(certificate,'xt',encoding='utf8') as out:json.dump(dict(engine='BFS',cells=cells,tasks=tasks,records=records,popped=popped,goal=goal,invalid_start=invalid,frontier=list(todo)),out,separators=(',',':'))
    return dict(engine='BFS',status=status,reason=reason,length=len(route)-1 if route else None,route=route,search_seconds=seconds,discovered=len(records),expanded=len(popped),queue_peak=peak,level_discovered=dict(Counter(r[2] for r in records)),limits={k:q[k] for k in ('seconds','max_states','resource')})
