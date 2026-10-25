"""Strict rational inequalities; witnesses prove service, never first entry time."""
from fractions import Fraction as Q
from .exact import rat,pt
DELTA=Q(1,5)

def inside(a,p,c,phase):
    c[phase+'_inside_tests']+=1
    return all(abs(a[k]-p[k])<DELTA for k in (0,1))

def intersection(a,b,p,c,phase,end_open=False):
    c[phase+'_service_intersections']+=1
    if a==b:
        return None
    lo,hi=Q(0),Q(1)
    lc,hc=True,not end_open
    for k in (0,1):
        d=b[k]-a[k]
        if not d:
            if not abs(a[k]-p[k])<DELTA:
                return None
            continue
        left,right=sorted(((p[k]-DELTA-a[k])/d,(p[k]+DELTA-a[k])/d))
        if left>=lo:
            lo,lc=left,False
        if right<=hi:
            hi,hc=right,False
        if lo>=hi:
            return None
    if lo>=hi:
        return None
    t=(lo+hi)/2
    w=tuple(a[k]+t*(b[k]-a[k]) for k in (0,1))
    assert 0<=lo<t<hi<=1 and all(abs(w[k]-p[k])<DELTA for k in (0,1))
    return {'interval':{'lower':rat(lo),'upper':rat(hi),'lower_closed':lc,'upper_closed':hc},
            'witness':{'t':rat(t),'point':pt(w)},'parameterization':'committed_or_predicted_prefix',
            'meaning':'interior_existence_witness_not_first_internal_time'}

def collect(s,c,phase):
    c[phase+'_collect_here']+=1
    events=[]
    for p in sorted(s['P']&s['F']-s['H']):
        if inside(s['S'],p,c,phase):
            s['H'].add(p)
            events.append({'kind':'collect_here','cell':list(map(int,p)),
                           'witness':{'t':rat(0),'point':pt(s['S'])}})
    s['D']=s['P']-s['F']-s['H']
    return events

def credit_move(s,a,b,c,phase,end_open=False):
    events=[]
    for p in sorted(s['P']&s['F']-s['H']):
        evidence=intersection(a,b,p,c,phase,end_open)
        if evidence is not None:
            events.append({'kind':'region_traverse','cell':list(map(int,p)),'evidence':evidence})
    events.sort(key=lambda e:(Q(e['evidence']['witness']['t']['n'],e['evidence']['witness']['t']['d']),e['cell']))
    for event in events:
        s['H'].add(tuple(event['cell']))
    s['D']=s['P']-s['F']-s['H']
    return events
