"""Independent heap Dijkstra: remaining mask, coordinate keys, own transitions."""
import heapq,time,gzip,json
def solve(request,certificate):
    started=time.perf_counter();area={tuple(p) for p in request['free']};points=list(reversed(sorted({tuple(t) for t in request['tasks']})));weights={p:2**i for i,p in enumerate(points)}
    origin=tuple(request['start']);home=tuple(request['base']);last=tuple(request['last']) if request['last'] is not None else None
    remaining=sum(weights.values());remaining&=~weights.get(origin,0);initial=(origin,remaining);invalid=last==origin and remaining!=0
    entries=[[origin[0],origin[1],remaining,-1,0]];index={initial:0};best={initial:0};heap=[] if invalid else [(0,origin,remaining)];settled=[];closed=set();answer=None;status='infeasible';reason='last_at_start' if invalid else 'exhausted';peak=len(heap)
    while heap:
        if time.perf_counter()-started>=request['seconds']:status='unresolved';reason='time_limit';break
        cost,where,rest=heapq.heappop(heap);state=(where,rest)
        if state in closed or best[state]!=cost:continue
        closed.add(state);number=index[state]
        if where==home and rest==0:answer=number;status='optimal';reason='minimum_goal_settled';break
        settled.append(number)
        if cost==request['resource']:continue
        # Deliberately no BFS adjacency/mask/filter function reused.
        for axis,increment in ((1,1),(0,-1),(1,-1),(0,1)):
            other=list(where);other[axis]+=increment;other=tuple(other)
            if other not in area:continue
            targetbit=weights.get(other,0)
            if other==last and rest&targetbit and rest!=targetbit:continue
            newrest=rest&~targetbit;nextstate=(other,newrest);newcost=cost+1
            if newcost>=best.get(nextstate,float('inf')):continue
            if nextstate not in index:
                if len(entries)==request['max_states']:status='unresolved';reason='state_limit';break
                index[nextstate]=len(entries);entries.append([other[0],other[1],newrest,number,newcost])
            else:entries[index[nextstate]]=[other[0],other[1],newrest,number,newcost]
            best[nextstate]=newcost;heapq.heappush(heap,(newcost,other,newrest))
        peak=max(peak,len(heap))
        if reason=='state_limit':break
    path=[]
    if answer is not None:
        i=answer
        while i!=-1:row=entries[i];path.append((row[0],row[1]));i=row[3]
        path.reverse()
    elapsed=time.perf_counter()-started
    with gzip.open(certificate,'xt',encoding='utf8') as f:json.dump(dict(engine='DIJKSTRA',tasks=points,records=entries,popped=settled,goal=answer,invalid_start=invalid,frontier=[[d,p,m] for d,p,m in heap]),f,separators=(',',':'))
    return dict(engine='DIJKSTRA',status=status,reason=reason,length=len(path)-1 if path else None,route=path,search_seconds=elapsed,discovered=len(entries),expanded=len(settled),queue_peak=peak,limits={k:request[k] for k in ('seconds','max_states','resource')})
