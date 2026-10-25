"""Independent exact boundary partition, no production credit implementation."""
from fractions import Fraction as R

def rat(v):
    return {'n':v.numerator,'d':v.denominator}
def pt(p):
    return [rat(R(v)) for v in p]
def internal(v,p,c):
    c['independent_region_point_tests']+=1
    return all(R(5)*abs(v[j]-p[j])<1 for j in (0,1))

def intersection(a,b,p,c,end_open=False):
    c['independent_service_intersections']+=1
    if a==b:
        return None
    cuts={R(0),R(1)}
    for j in (0,1):
        if a[j]!=b[j]:
            for boundary in (R(p[j])-R(1,5),R(p[j])+R(1,5)):
                c['independent_region_boundary_parameters']+=1
                t=(boundary-a[j])/(b[j]-a[j])
                if 0<t<1:
                    cuts.add(t)
    knots=sorted(cuts)
    def at(t):
        return tuple(a[j]+t*(b[j]-a[j]) for j in (0,1))
    components=[]
    for left,right in zip(knots,knots[1:]):
        if internal(at((left+right)/2),p,c):
            components.append((left,right))
    if not components:
        return None
    left,right=components[0][0],components[-1][1]
    assert all(x[1]==y[0] for x,y in zip(components,components[1:]))
    lower_closed=internal(at(left),p,c)
    upper_closed=internal(at(right),p,c) and not(end_open and right==1)
    witness=(left+right)/2
    assert internal(at(witness),p,c)
    return {'interval':{'lower':rat(left),'upper':rat(right),'lower_closed':lower_closed,'upper_closed':upper_closed},
            'witness':{'t':rat(witness),'point':pt(at(witness))},'parameterization':'committed_or_predicted_prefix',
            'meaning':'interior_existence_witness_not_first_internal_time'}

def collect(s,c):
    c['independent_collect_here_checks']+=1
    out=[]
    for p in sorted(s['P']):
        yes=internal(s['S'],p,c)
        if yes and p in s['F'] and p not in s['H']:
            out.append({'kind':'collect_here','cell':list(map(int,p)),
                        'witness':{'t':rat(R(0)),'point':pt(s['S'])}})
            s['H'].add(p)
    s['D']=s['P']-s['F']-s['H']
    return out

def service(s,a,b,c,end_open=False):
    found=[]
    for p in sorted(s['P']):
        evidence=intersection(a,b,p,c,end_open)
        if evidence is not None and p in s['F'] and p not in s['H']:
            found.append({'kind':'region_traverse','cell':list(map(int,p)),'evidence':evidence})
    def key(e):
        v=e['evidence']['witness']['t']
        return R(v['n'],v['d']),e['cell']
    found.sort(key=key)
    for event in found:
        s['H'].add(tuple(event['cell']))
    s['D']=s['P']-s['F']-s['H']
    return found
