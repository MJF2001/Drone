"""Square occupancy cells, continuous segments, and a circular coverage device.

Coordinates are in units of lap spacing w. Cells have integer centers and unit
side. Geometry is restricted to unions of these squares, not arbitrary polygons.
"""
from __future__ import annotations
import math
from functools import lru_cache

CARDINAL = ((-1,0),(0,1),(0,-1),(1,0))
AROUND = tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if x or y)

def add(a,b):
    return a[0]+b[0],a[1]+b[1]

def dist(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])

def point_segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0.
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def box_hit(a,b,cell,pad=0.):
    """Liang-Barsky interval: segment intersects the closed square."""
    lo,hi=0.,1.
    for axis in (0,1):
        d=b[axis]-a[axis]
        low,high=cell[axis]-.5-pad,cell[axis]+.5+pad
        if abs(d)<1e-12:
            if not low<=a[axis]<=high:
                return None
        else:
            u,v=(low-a[axis])/d,(high-a[axis])/d
            if u>v:
                u,v=v,u
            lo,hi=max(lo,u),min(hi,v)
            if lo>hi+1e-12:
                return None
    return lo,hi

@lru_cache(maxsize=100000)
def supercover(a,b):
    """All closed cells touched by segment, ordered by first intersection.

    Includes both side cells at an exact diagonal corner: no corner cutting.
    """
    cells=[]
    for x in range(math.floor(min(a[0],b[0])-.5),math.ceil(max(a[0],b[0])+.5)+1):
        for y in range(math.floor(min(a[1],b[1])-.5),math.ceil(max(a[1],b[1])+.5)+1):
            interval=box_hit(a,b,(x,y))
            if interval is not None:
                cells.append((interval[0],(x,y)))
    return tuple(p for _,p in sorted(cells))

def segment_free(a,b,free):
    return all(p in free for p in supercover(tuple(a),tuple(b)))

def lap_points(a,b):
    assert a[0]==b[0]
    return [(a[0],y) for y in range(min(a[1],b[1]),max(a[1],b[1])+1)]

def connected(free,start):
    seen,todo={start},[start]
    while todo:
        p=todo.pop()
        for d in CARDINAL:
            q=add(p,d)
            if q in free and q not in seen:
                seen.add(q)
                todo.append(q)
    return seen

class KnownMap:
    """Planner-side occupancy only. No reference to the simulator/world."""
    def __init__(self):
        self.cells={}
        self.free=set()
        self.new_free=set()

    def update(self,observation):
        if any(p in self.cells and self.cells[p] != v for p,v in observation.items()):
            raise ValueError('Static-world observation changed occupancy')
        fresh={p:v for p,v in observation.items() if p not in self.cells}
        self.cells.update(observation)
        f={p for p,v in fresh.items() if v}
        self.new_free.update(f)
        self.free.update(f)
        return fresh

    def frontier(self,p):
        # B(p,w) intersects any of eight neighboring closed squares.
        return any(add(p,d) not in self.free for d in AROUND)

    def unknown_adjacent(self,p):
        return any(add(p,d) not in self.cells for d in AROUND)

    def endpoint(self,p):
        return any(add(p,d) not in self.free for d in ((0,1),(0,-1)))

    def feasible(self,a,b):
        return segment_free(a,b,self.free)

    def clearance_score(self,a,b):
        """Def. III.8/9 proximity tie-break, k=5 points, nearest blocked square.

        Unknown counts as blocked. Scores are mean sample clearances, followed
        by edge length and coordinates for deterministic ties.
        """
        samples=[(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])) for t in (0,.25,.5,.75,1)]
        values=[]
        for x,y in samples:
            best=math.inf
            for xx in range(math.floor(x)-2,math.floor(x)+3):
                for yy in range(math.floor(y)-2,math.floor(y)+3):
                    if (xx,yy) not in self.free:
                        dd=math.hypot(max(abs(x-xx)-.5,0),max(abs(y-yy)-.5,0))
                        best=min(best,dd)
            values.append(best)
        return (sum(values)/len(values),dist(a,b),b)

class World:
    """Ground truth exposed only through observe(), and evaluator-side methods."""
    def __init__(self,free,radius=5):
        self.free=frozenset(free)
        self.radius=radius
        self.offsets=tuple((x,y) for x in range(-math.ceil(radius),math.ceil(radius)+1)
                           for y in range(-math.ceil(radius),math.ceil(radius)+1)
                           if x*x+y*y<=radius*radius)

    def observe(self,pose):
        # Ideal grid ray sensor. Same-radius center tests, opaque square obstacles.
        origin=(int(round(pose[0])),int(round(pose[1])))
        observed={}
        for dx,dy in self.offsets:
            q=(origin[0]+dx,origin[1]+dy)
            if dist(pose,q)>self.radius:
                continue
            # At a corner several closed cells have the same entry distance.
            # Test the entire group before exposing free cells: coordinate-order
            # tie breaking used to leak a free cell behind an opaque corner.
            ray=supercover(tuple(pose),q)
            index=0
            while index<len(ray):
                entry=box_hit(pose,q,ray[index])[0]
                group=[]
                while index<len(ray) and abs(box_hit(pose,q,ray[index])[0]-entry)<1e-10:
                    group.append(ray[index]); index+=1
                blocked=[p for p in group if p not in self.free]
                if blocked:
                    observed.update({p:False for p in blocked})
                    break
                observed.update({p:True for p in group})
        return observed

def coverage_audit(free,path,rc=.75,subdivisions=4):
    """Independent area quadrature + conservative whole-cell coverage bound.

    Distance to swept disks is exact for each quadrature point. Whole-cell
    certificate: midpoint distance + subcell half diagonal <= rc. A failure
    of this sufficient bound is 'uncertified', not necessarily uncovered.
    """
    import numpy as np
    points=np.asarray([(x-.5+(i+.5)/subdivisions,y-.5+(j+.5)/subdivisions)
                       for x,y in sorted(free) for i in range(subdivisions)
                       for j in range(subdivisions)],dtype=float)
    minimum=np.full(len(points),np.inf)
    segments=list(zip(path,path[1:])) or [(path[0],path[0])]
    for a,b in segments:
        a=np.asarray(a); v=np.asarray(b)-a
        denom=float(v@v)
        t=np.clip((points-a)@v/denom,0,1) if denom else np.zeros(len(points))
        minimum=np.minimum(minimum,np.linalg.norm(points-a-t[:,None]*v,axis=1))
    covered=minimum<=rc+1e-10
    # Evaluate the paper's boundary-resolution qualification separately.
    clearance=np.full(len(points),np.inf)
    boundary={add(p,d) for p in free for d in AROUND if add(p,d) not in free}
    for p in boundary:
        delta=np.maximum(np.abs(points-np.asarray(p))-.5,0.)
        clearance=np.minimum(clearance,np.linalg.norm(delta,axis=1))
    interior=clearance>1+1e-10
    margin=math.sqrt(2)/(2*subdivisions)
    certified=minimum+margin<=rc+1e-10
    return dict(area_samples=len(points),area_sample_coverage=float(covered.mean()),
                certified_area_lower_bound=float(certified.mean()),
                interior_sample_coverage=float(covered[interior].mean()) if interior.any() else None,
                uncovered_interior_samples=int((~covered & interior).sum()),
                uncovered_boundary_samples=int((~covered & ~interior).sum()),
                max_sample_distance=float(minimum.max()),
                missing_sample_points=points[~covered].tolist(),
                collisions=sum(not segment_free(tuple(a),tuple(b),free) for a,b in segments))
