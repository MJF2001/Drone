"""Same frozen request validation for BOTH methods, no solver imports."""
import math
def validate(c):
    if not isinstance(c,dict):raise ValueError('object required')
    def point(p):
        if not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(x) is not int for x in p):raise ValueError('integer grid point required')
    for field in ('free','targets','covered'):
        if not isinstance(c[field],list):raise ValueError(field)
        for p in c[field]:point(p)
    for field in ('published_targets','deferred_targets'):
        if field in c:
            if not isinstance(c[field],list):raise ValueError(field)
            for p in c[field]:point(p)
    point(c['current']);point(c['base'])
    if 'distance_budget' in c:
        v=c['distance_budget']
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('finite nonnegative distance budget')
    if 'cap_resume_target' in c and c['cap_resume_target'] is not None:
        r=c['cap_resume_target']
        if not isinstance(r,dict):raise ValueError('resume object')
        point(r['point'])
        if not isinstance(r['reference'],str) or not r['reference']:raise ValueError('resume reference')
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']))
    published=set(map(tuple,c.get('published_targets',list(t|h))))
    if tuple(c['current']) not in f or tuple(c['base']) not in f or not t<=f or not (t|h)<=published or (published&f)-h-t:raise ValueError('snapshot ledger')
    if 'deferred_targets' in c and set(map(tuple,c['deferred_targets']))!=published-f-h:raise ValueError('deferred ledger')
    if c.get('cap_resume_target') is not None and tuple(c['cap_resume_target']['point']) not in f:raise ValueError('resume not free')
