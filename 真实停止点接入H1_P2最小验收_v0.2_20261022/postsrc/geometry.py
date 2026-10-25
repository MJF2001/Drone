"""Primary predicate: exact rational grid crossing events, no sampled LOS."""
from fractions import Fraction as Q
from math import isqrt
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING

def inside(F,p):
    options=[]
    for x in p:
        z=x+Q(1,2); k=z.numerator//z.denominator
        options.append((k-1,k) if z.denominator==1 else (k,))
    return all((x,y) in F for x in options[0] for y in options[1])

def legal(F,a,b):
    a=tuple(map(Q,a));b=tuple(map(Q,b));ts={Q(0),Q(1)}
    for k in (0,1):
        d=b[k]-a[k]
        if d:
            lo,hi=sorted((a[k],b[k]))
            for m in range(int(lo)-2,int(hi)+3):
                t=(Q(2*m+1,2)-a[k])/d
                if 0<t<1:ts.add(t)
    ts=sorted(ts);tests=ts+[(x+y)/2 for x,y in zip(ts,ts[1:])]
    return all(inside(F,tuple(a[k]+t*(b[k]-a[k]) for k in (0,1))) for t in tests)

def hit(a,b,p):
    dx,dy=b[0]-a[0],b[1]-a[1];x,y=p[0]-a[0],p[1]-a[1]
    if dx==dy==0:return Q(0) if p==a else None
    if dx*y!=dy*x:return None
    dot=x*dx+y*dy;sq=dx*dx+dy*dy
    return Q(dot,sq) if 0<=dot<=sq else None

def interval(points):
    with localcontext() as c:
        c.prec=50;lo=hi=Decimal(0)
        for a,b in zip(points,points[1:]):
            n=sum((x-y)**2 for x,y in zip(a,b));r=isqrt(n)
            if r*r==n:l=u=Decimal(r)
            else:
                z=Decimal(n).sqrt();l=z.next_minus();u=z.next_plus()
            c.rounding=ROUND_FLOOR;lo=lo+l
            c.rounding=ROUND_CEILING;hi=hi+u
        return str(lo),str(hi)
