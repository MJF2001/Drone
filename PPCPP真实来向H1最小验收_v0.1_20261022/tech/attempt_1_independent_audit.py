"""Independent saved-output audit. No production/heading implementation imports."""
import math
from fractions import Fraction as F

def direction(raw):
    if raw is None:return None
    a,b=(F(x) for x in raw)
    den=math.lcm(a.denominator,b.denominator);a,b=int(a*den),int(b*den)
    divisor=math.gcd(abs(a),abs(b));assert divisor
    return (a//divisor,b//divisor)

def scalar_interval(cert, bits):
    A=F(cert['A']);B=F(cert['B']);N=cert['N'];root=math.isqrt(N)
    if root*root==N:
        z=A+B/root;return z,z
    den=1<<bits;k=math.isqrt(N*den*den);lo,hi=F(k,den),F(k+1,den)
    values=(A+B/lo,A+B/hi)
    return min(values),max(values)

def certified_winner(rows):
    """Independent interval enclosure, no primary exact-sign comparator."""
    for bits in (32,64,128,256):
        bounds={tuple(r['cell']):scalar_interval(r['h1_certificate'],bits) for r in rows}
        candidates=[]
        for r in rows:
            ok=True
            for q in rows:
                if r is q:continue
                x,y=r['h1_certificate'],q['h1_certificate'];assert x['N']==y['N']
                bx,by=bounds[tuple(r['cell'])],bounds[tuple(q['cell'])]
                same=(F(x['A'])==F(y['A']) and x['B']==y['B']) or (bx[0]==bx[1]==by[0]==by[1])
                if same:
                    if tuple(r['cell'])>tuple(q['cell']):ok=False;break
                elif not bx[0]>by[1]:ok=False;break
            if ok:candidates.append(tuple(r['cell']))
        if len(candidates)==1:return candidates[0],bits
    raise AssertionError('independent_direction_comparison_uncertain')

def expected_options(cur, h, pending, free, predator):
    x,y=cur;cells=sorted(z for z in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)) if z in pending and z in free)
    if not cells:return []
    ds={z:math.hypot(z[0]-predator[0],z[1]-predator[1]) for z in cells};low,high=min(ds.values()),max(ds.values())
    rows=[]
    for z in cells:
        rd=(ds[z]-low)/(high-low) if high>low else 0.0
        px,py=z;n=sum(t in pending and t in free for t in ((px+1,py),(px,py+1),(px-1,py),(px,py-1)));rb=(4-n)/4
        d=(z[0]-x,z[1]-y)
        row=dict(cell=z,distance_reward=rd,boundary_reward=rb)
        if h is None:rs=0.0
        elif 0 in h:rs=(h[0]*d[0]+h[1]*d[1]+1)/2
        else:
            row['h1_certificate']=dict(A=str(F(rd)+1+F(.5*rb)),B=h[0]*d[0]+h[1]*d[1],N=h[0]*h[0]+h[1]*h[1]);rs=None
        if rs is not None:row.update(straight_reward=rs,score=rd+2.*rs+.5*rb)
        rows.append(row)
    return rows

def audit_output(c, heading, raw, newer):
    assert raw['status']=='core_complete',raw['status']
    route=[tuple(p) for p in raw['route']];free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));history=set(map(tuple,c['covered']))
    assert route and route[0]==tuple(c['current']) and route[-1]==tuple(c['base'])
    assert all(p in free and all(type(v) is int for v in p) for p in route)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
    assert len(route)-1<=c['distance_budget']
    U=targets-history;seen=set();credits=[]
    for i,p in enumerate(route):
        if p in U and p not in seen:credits.append(dict(point=list(p),index=i));seen.add(p)
    assert seen==U
    events=raw['trace'];assert events and events[-1]['kind']=='return'
    bits_used=[];decisions=[];updates=[]
    for k,event in enumerate(events):
        i=event['index'];cur=route[i];assert tuple(event['current'])==cur
        pend=U-set(route[:i+1])
        h=direction(heading['vector']) if i==0 and heading['status']=='KNOWN' else None if i==0 else (cur[0]-route[i-1][0],cur[1]-route[i-1][1])
        if newer:
            state=event['incoming_heading'];assert tuple(state['primitive'])==h if h is not None else state['primitive'] is None
            if i==0:assert state['source']==heading['source']
            else:assert state['source']==dict(kind='predicted_route_edge',start=list(route[i-1]),end=list(cur),end_index=i)
            updates.append(dict(index=i,heading=list(h) if h else None,source=state['source']))
        else:
            prev=c['previous'] if i==0 else list(route[i-1]);assert event.get('previous',prev)==prev
        expect=expected_options(cur,h,pend,free,c['predator'])
        if event['kind']=='local':
            actual=event['options'];assert [tuple(z['cell']) for z in actual]==[z['cell'] for z in expect]
            for a,b in zip(actual,expect):
                for field in ('distance_reward','boundary_reward'):assert a[field]==b[field]
                if 'h1_certificate' in b:
                    assert a['h1_certificate']==b['h1_certificate']
                    cert=b['h1_certificate'];rounded=None
                    for precision in (32,64,128,256):
                        lower,upper=scalar_interval(dict(A='1/2',B=str(F(cert['B'],2)),N=cert['N']),precision)
                        if float(lower)==float(upper):rounded=float(lower);break
                    assert rounded is not None and a['straight_reward']==rounded
                    assert a['score']==a['distance_reward']+2.*rounded+.5*a['boundary_reward']
                else:
                    assert a['straight_reward']==b['straight_reward'] and a['score']==b['score']
            if expect and 'h1_certificate' in expect[0]:chosen,bits=certified_winner(expect);bits_used.append(bits)
            else:chosen=min(expect,key=lambda z:(-z['score'],z['cell']))['cell']
            assert tuple(event['goal'])==chosen and route[i+1]==chosen
        elif event['kind']=='recovery':
            assert not expect and tuple(event['goal']) in pend
        elif event['kind']=='return':
            assert not pend and tuple(event['goal'])==tuple(c['base'])
        else:raise AssertionError('unknown decision')
        end=events[k+1]['index'] if k+1<len(events) else len(route)-1
        assert end>=i and route[end]==tuple(event['goal'])
        decisions.append(dict(kind=event['kind'],index=i,current=list(cur),goal=event['goal'],pending_count=len(pend)))
    return dict(valid=True,steps=len(route)-1,credits=credits,decisions=decisions,heading_updates=updates,
                interval_bits_used=bits_used,route_edge_checks=len(route)-1,trace_events=len(events),graph_searches=0,LOS_queries=0)

def equivalence(original, newer):
    fields=('route','status','reason','seed','weights','predator')
    assert all(original.get(f)==newer.get(f) for f in fields)
    assert len(original['trace'])==len(newer['trace'])
    for a,b in zip(original['trace'],newer['trace']):
        for field in ('kind','index','current','pending_count','goal','options'):
            assert a.get(field)==b.get(field),field
    return True
