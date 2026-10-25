"""Independent common task/route audit. No algorithm imports."""
def points(xs):return set(map(tuple,xs))
def audit(c,result):
    route=list(map(tuple,result['route']));f=points(c['free']);t=points(c['targets']);h=points(c['covered']);p=points(c['published_targets'])
    assert t==p&f and h<=p and points(c['deferred_targets'])==p-f-h
    if not route:return dict(valid=False,steps=None,reason='no_complete_route')
    errors=[]
    if route[0]!=tuple(c['current']):errors.append('start')
    if route[-1]!=tuple(c['base']):errors.append('return')
    if not set(route)<=f:errors.append('blocked')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(route,route[1:])):errors.append('nonunit')
    if not t<=h|set(route):errors.append('coverage')
    if len(route)-1>c['distance_budget']:errors.append('resource')
    return dict(valid=not errors,steps=len(route)-1 if not errors else None,reason=errors,route_steps=len(route)-1)
