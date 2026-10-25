"""Independent analytic detector: enumerate rectangle-face intersections, not slabs."""
from fractions import Fraction as R

def entry(a,b,cell,padded,c,kind):
    c['independent_'+kind+'_box_queries']+=1
    half=R(5,8) if padded else R(1,2)
    lo=(R(cell[0])-half,R(cell[1])-half)
    hi=(R(cell[0])+half,R(cell[1])+half)
    if all(lo[k]<=a[k]<=hi[k] for k in (0,1)):
        return R(0)
    candidates=[]
    for axis in (0,1):
        d=b[axis]-a[axis]
        if d==0:
            continue
        other=1-axis
        for face in (lo[axis],hi[axis]):
            t=(face-a[axis])/d
            if 0<=t<=1:
                cross=a[other]+t*(b[other]-a[other])
                if lo[other]<=cross<=hi[other]:
                    candidates.append(t)
    return min(candidates) if candidates else None

def probe(a,b,truth,known,c):
    collisions=[]
    detections=[]
    for cell in sorted(truth):
        t=entry(a,b,cell,False,c,'safety')
        if t is not None:
            collisions.append((t,cell))
        if cell not in known:
            t=entry(a,b,cell,True,c,'detector')
            if t is not None:
                detections.append((t,cell))
    collision=min(collisions) if collisions else None
    detection=min(detections) if detections else None
    if collision and collision[0]==0:
        return 'unsafe',R(0),collision[1]
    if collision and (detection is None or collision[0]<=detection[0]):
        return 'unsafe_proposed_segment',collision[0],collision[1]
    if detection:
        return 'detected',detection[0],detection[1]
    return 'clear',R(1),None
