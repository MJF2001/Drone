"""Independent predicate: intersect closed forbidden cell boxes using slabs.
No import of primary geometry. Bounding-box exterior is also forbidden.
"""
from fractions import Fraction
from math import ceil,floor

def rectangle_intersects(a,b,x0,x1,y0,y1):
    low,high=Fraction(0),Fraction(1)
    for v,w,left,right in ((a[0],b[0],x0,x1),(a[1],b[1],y0,y1)):
        d=w-v
        if not d:
            if v<left or v>right:return False
        else:
            u,vv=(left-v)/d,(right-v)/d
            low=max(low,min(u,vv));high=min(high,max(u,vv))
            if low>high:return False
    return True

def legal(F,a,b):
    a=tuple(map(Fraction,a));b=tuple(map(Fraction,b));xs=[x for x,y in F];ys=[y for x,y in F]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);half=Fraction(1,2)
    if any(not (xmin-half<p[0]<xmax+half and ymin-half<p[1]<ymax+half) for p in (a,b)):return False
    for x in range(max(xmin,ceil(min(a[0],b[0])-half)),min(xmax,floor(max(a[0],b[0])+half))+1):
        for y in range(max(ymin,ceil(min(a[1],b[1])-half)),min(ymax,floor(max(a[1],b[1])+half))+1):
            if (x,y) not in F and rectangle_intersects(a,b,x-half,x+half,y-half,y+half):return False
    return True

def hit(a,b,p):
    ts=[]
    for k in (0,1):
        if a[k]==b[k]:
            if p[k]!=a[k]:return None
        else:ts.append(Fraction(p[k]-a[k],b[k]-a[k]))
    if not ts:return Fraction(0)
    return ts[0] if all(t==ts[0] for t in ts) and 0<=ts[0]<=1 else None
