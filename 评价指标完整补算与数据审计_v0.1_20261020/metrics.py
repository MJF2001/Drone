"""Canonical single-cell four-neighbour postprocessing; no solver imports."""
def points(x):return set(map(tuple,x))
def percentile(xs,p):
    if not xs:return None
    a=sorted(xs);v=(len(a)-1)*p;i=int(v)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(v-i)
def metrics(c,path):
    path=list(map(tuple,path));assert path
    f=points(c['free']);t=points(c['targets']);h=points(c['covered']);pub=points(c['published_targets'])
    assert path[0]==tuple(c['current']) and set(path)<=f and t==pub&f and h<=pub
    assert points(c['deferred_targets'])==pub-f-h
    initial={path[0]}&t-h;seen=h|initial;pending=t-seen
    completion=0 if not pending else None
    counts=dict(fresh_target_steps=0,historical_target_steps=0,repeated_new_target_steps=0,non_target_steps=0)
    for i,p in enumerate(path[1:],1):
        if p not in t:counts['non_target_steps']+=1
        elif p in h:counts['historical_target_steps']+=1
        elif p in seen:counts['repeated_new_target_steps']+=1
        else:counts['fresh_target_steps']+=1
        seen.add(p);pending.discard(p)
        if completion is None and not pending:completion=i
    vec=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:])]
    assert all(abs(x)+abs(y)==1 for x,y in vec)
    n=len(path)-1;arrivals=n-counts['non_target_steps'];dup=counts['historical_target_steps']+counts['repeated_new_target_steps']
    assert sum(counts.values())==n<=c['distance_budget']
    credited=h|(set(path)&t);missing=t-credited;deferred=pub-f-h
    a=sum(u[0]*v[0]+u[1]*v[1]==0 for u,v in zip(vec,vec[1:]));b=sum(u[0]*v[0]+u[1]*v[1]==-1 for u,v in zip(vec,vec[1:]))
    return dict(**counts,length=n,target_arrivals=arrivals,duplicate_target_arrivals=dup,overlap_ratio=dup/arrivals if arrivals else None,
        turns90=a,turns180=b,direction_changes=a+b,initial_credit=len(initial),completion_step=completion,
        return_tail_steps=n-completion if completion is not None else None,active_targets=len(t),remaining_before=len(t-h),
        newly_completed=len((t-h)&set(path)),remaining_completion_fraction=len((t-h)&set(path))/len(t-h) if t-h else 1.,
        active_covered=len(t&credited),active_coverage=len(t&credited)/len(t) if t else 1.,missing_active=len(missing),
        published_targets=len(pub),published_covered=len(pub&credited),published_coverage=len(pub&credited)/len(pub) if pub else 1.,
        deferred=len(deferred),uncompleted_published=len(pub-credited),returned=path[-1]==tuple(c['base']),
        complete_legal=not missing and path[-1]==tuple(c['base']))
