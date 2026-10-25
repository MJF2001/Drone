"""Whole-polyline virtual execution; independent region algorithm on audit path."""
from collections import Counter
from fractions import Fraction as Q
from math import atan2,hypot
from . import service as C
from .audit import region as Z
from .exact import Expr,distance,certificate
from .post import geometry as G

def scale(x,t):return Expr({r:v*t for r,v in x.terms.items()})
def display(x):
    a,b=x.interval();return float((a+b)/2)
def center_hit(a,b,p):
    dx,dy=b[0]-a[0],b[1]-a[1];x,y=p[0]-a[0],p[1]-a[1]
    return dx*y==dy*x and 0<=x*dx+y*dy<=dx*dx+dy*dy
def candidate(a,b,p):
    return all(5*max(a[j],b[j])>5*p[j]-1 and 5*min(a[j],b[j])<5*p[j]+1 for j in (0,1))

def evaluate(c,path,independent=False,grid=False):
    path=[tuple(p) for p in path];f=set(map(tuple,c['free']));P=set(map(tuple,c['published_targets']));h=set(map(tuple,c['covered']));initial=set(h)
    assert path and path[0]==tuple(c['current']) and path[-1]==tuple(c['base'])
    assert h<=P and set(map(tuple,c['deferred_targets']))==P-f-h
    active=P&f;pending=active-h;counts=Counter();events=[];sources=[];total=Expr();first=None;last=None;no_new=Expr();off=[];touches=duplicates=0
    for p in sorted(active):
        inside=Z.internal(path[0],p,counts) if independent else C.inside(path[0],p,counts,'execute')
        if inside:
            new=p not in h;h.add(p);touches+=1;duplicates+=not new
            events.append({'kind':'collect_here','cell':list(p),'new':new,'witness':{'t':{'n':0,'d':1},'point':C.pt(path[0])}})
            if new:first=first or Expr();last=Expr()
    dirs=[]
    for edge,(a,b) in enumerate(zip(path,path[1:])):
        assert a!=b
        if grid:
            assert a in f and b in f and abs(a[0]-b[0])+abs(a[1]-b[1])==1
            counts['unit_edge_membership_proofs']+=1
        elif not independent:
            counts['main_geometry']+=1;assert G.legal(f,a,b)
        length,square=distance(a,b,counts,'metric');sources.append(square)
        hits=[]
        for p in sorted(active):
            counts['target_box_tests']+=1
            if not candidate(a,b,p):continue
            evidence=Z.intersection(a,b,p,counts) if independent else C.intersection(a,b,p,counts,'execute')
            if evidence:
                t=evidence['witness']['t'];hits.append((Q(t['n'],t['d']),p,evidence))
        hits.sort(key=lambda x:(x[0],x[1]));new_count=0
        for t,p,evidence in hits:
            new=p not in h;h.add(p);touches+=1;duplicates+=not new
            events.append({'kind':'region_traverse','edge':edge,'cell':list(p),'new':new,'evidence':evidence})
            if new:
                position=total+scale(length,t);first=position if first is None else first;last=position;new_count+=1
                counts['new_credit_center_checks']+=1
                if b[0]!=a[0] and b[1]!=a[1] and not center_hit(a,b,p):off.append({'edge':edge,'cell':list(p),'evidence':evidence})
        if not new_count:no_new=no_new+length
        total=total+length;dirs.append((b[0]-a[0],b[1]-a[1]))
    assert not(active-h) and (Expr.number(c['distance_budget'])-total).sign()>=0
    turns=Counter();angle=0.
    for u,v in zip(dirs,dirs[1:]):
        cross=u[0]*v[1]-u[1]*v[0];dot=u[0]*v[0]+u[1]*v[1]
        if cross or dot<0:
            turns['total']+=1;angle+=atan2(abs(cross),dot)
            turns['90' if dot==0 else '180' if cross==0 and dot<0 else 'other']+=1
    never=[];vertices=set(path)
    for event in off:
        p=tuple(event['cell'])
        if p in vertices:continue
        counts['whole_history_center_tests']+=len(path)-1
        if not any(center_hit(a,b,p) for a,b in zip(path,path[1:])):never.append(list(p))
    stages=None if first is None else {'to_first_witness':certificate(first),'between_first_last_witness':certificate(last-first),
                                      'after_last_witness_return':certificate(total-last),'convention':'midpoint of first intersecting executed segment interval; not unique physical first service time'}
    metrics={'published':len(P),'initial_H':len(initial),'active':len(active),'remaining_before':len(pending),'deferred':len(P-f-h),
        'new_credit':len(h-initial),'missing':len(active-h),'active_coverage':len(h&active)/len(active) if active else 1,
        'published_coverage':len(h&P)/len(P) if P else 1,'covered_final':len(h),'return_success':path[-1]==tuple(c['base']),
        'length':display(total),'length_certificate':certificate(total),'stages':stages,'no_new_credit_route':first is None,
        'turns':dict(turns),'total_turn_radians':angle,'center_region_touch_events':touches,'repeated_touch_events':duplicates,
        'touch_definition':'one event per intersecting segment/task plus explicit initial collect; depends on segmentation, not extra distance',
        'segments_without_new_credit':sum(1 for k in range(len(path)-1) if not any(e.get('edge')==k and e['new'] for e in events)),
        'whole_segments_without_new_credit_length':display(no_new),'noncollecting_definition':'whole-segment no-new-credit label, not pointwise noncollection distance',
        'diagonal_offcenter_first_credit_tasks':len({tuple(v['cell']) for v in off}),'never_center_in_whole_actual_history_tasks':len({tuple(p) for p in never}),
        'diagonal_offcenter_witnesses':off,'final_H':[list(p) for p in sorted(h)],'final_position':list(path[-1])}
    return {'metrics':metrics,'events':events,'path':[list(p) for p in path],'counts':dict(counts),'squared_sources':sources,
        'scope':'full virtual execution from common externally given H; no event replay, future knowledge or state mutation'}
