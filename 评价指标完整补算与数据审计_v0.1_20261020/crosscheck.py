"""Separate implementation: arrival histograms/first indices and direction labels.
Does not import metrics.py, original metric code, or any planner.
"""
from collections import Counter
def calculate(c,route):
    r=list(map(tuple,route));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']));p=set(map(tuple,c['published_targets']));f=set(map(tuple,c['free']))
    visits=Counter(r[1:]);initial=int(r[0] in t-h)
    fresh=sum(q in visits and q!=r[0] for q in t-h)
    hist=sum(visits[q] for q in t&h)
    repeat=sum(visits[q]-(0 if q==r[0] else 1) for q in t-h if q in visits)
    non=sum(n for q,n in visits.items() if q not in t)
    directions={(-1,0):0,(0,1):1,(1,0):2,(0,-1):3}
    ds=[directions[b[0]-a[0],b[1]-a[1]] for a,b in zip(r,r[1:])]
    changes=[(y-x)%4 for x,y in zip(ds,ds[1:])]
    n90=sum(d in (1,3) for d in changes);n180=changes.count(2)
    first={}
    for i,q in enumerate(r):first.setdefault(q,i)
    remaining=t-h;missing=remaining-set(r);completion=None if missing else max((first[q] for q in remaining),default=0)
    arrivals=sum(visits[q] for q in t);duplicates=hist+repeat;credited=h|(set(r)&t)
    return dict(fresh_target_steps=fresh,historical_target_steps=hist,repeated_new_target_steps=repeat,non_target_steps=non,
        length=len(r)-1,target_arrivals=arrivals,duplicate_target_arrivals=duplicates,overlap_ratio=duplicates/arrivals if arrivals else None,
        turns90=n90,turns180=n180,direction_changes=n90+n180,initial_credit=initial,completion_step=completion,
        return_tail_steps=len(r)-1-completion if completion is not None else None,active_targets=len(t),remaining_before=len(remaining),
        newly_completed=len(remaining&set(r)),remaining_completion_fraction=len(remaining&set(r))/len(remaining) if remaining else 1.,
        active_covered=len(t&credited),active_coverage=len(t&credited)/len(t) if t else 1.,missing_active=len(t-credited),
        published_targets=len(p),published_covered=len(p&credited),published_coverage=len(p&credited)/len(p) if p else 1.,
        deferred=len(p-f-h),uncompleted_published=len(p-credited),returned=r[-1]==tuple(c['base']),complete_legal=not missing and r[-1]==tuple(c['base']))
