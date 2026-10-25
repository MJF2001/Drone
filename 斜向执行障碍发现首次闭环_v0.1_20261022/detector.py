"""Primary: exact rational slab entry into closed boxes. No route-wide reveal."""
from fractions import Fraction as Q

PAD=Q(1,8)

def box(cell,pad=Q(0)):
    return (Q(cell[0])-Q(1,2)-pad,Q(cell[0])+Q(1,2)+pad,
            Q(cell[1])-Q(1,2)-pad,Q(cell[1])+Q(1,2)+pad)

def entry(a,b,bounds,c,kind):
    c[kind+'_box_queries']+=1
    lo,hi=Q(0),Q(1)
    for axis,left,right in ((0,bounds[0],bounds[1]),(1,bounds[2],bounds[3])):
        d=b[axis]-a[axis]
        if d==0:
            if not left<=a[axis]<=right:
                return None
        else:
            t,u=(left-a[axis])/d,(right-a[axis])/d
            lo,hi=max(lo,min(t,u)),min(hi,max(t,u))
            if lo>hi:
                return None
    return lo

def probe(a,b,truth,known,c):
    c['detector_probes']+=1
    collisions=[]
    detections=[]
    for cell in sorted(truth):
        t=entry(a,b,box(cell),c,'safety')
        if t is not None:
            collisions.append((t,cell))
        if cell not in known:
            t=entry(a,b,box(cell,PAD),c,'detector')
            if t is not None:
                detections.append((t,cell))
        else:
            c['known_obstacles_not_republished']+=1
    collision=min(collisions) if collisions else None
    if collision and collision[0]==0:
        return {'kind':'unsafe','t':Q(0),'cell':collision[1]}
    detection=min(detections) if detections else None
    if collision and (detection is None or collision[0]<=detection[0]):
        return {'kind':'unsafe_proposed_segment','t':collision[0],'cell':collision[1]}
    if detection:
        return {'kind':'detected','t':detection[0],'cell':detection[1]}
    return {'kind':'clear','t':Q(1),'cell':None}
