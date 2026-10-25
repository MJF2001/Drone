"""Primary rational predicates, adapted from saved grid-crossing method."""
from fractions import Fraction as Q

def inside(F, p, counts):
    counts['primary_domain_points'] += 1
    options = []
    for v in p:
        z = v + Q(1, 2)
        k = z.numerator // z.denominator
        options.append((k-1, k) if z.denominator == 1 else (k,))
    return all((x, y) in F for x in options[0] for y in options[1])

def legal(F, a, b, counts, phase):
    counts[phase+'_geometry'] += 1
    ts = {Q(0), Q(1)}
    for k in (0, 1):
        d = b[k]-a[k]
        if d:
            lo, hi = sorted((a[k], b[k]))
            for m in range(lo//1-2, hi//1+3):
                t = (Q(2*m+1, 2)-a[k])/d
                if 0 < t < 1:
                    ts.add(t)
    ts = sorted(ts)
    tests = ts + [(x+y)/2 for x, y in zip(ts, ts[1:])]
    return all(inside(F, tuple(a[k]+t*(b[k]-a[k]) for k in (0, 1)), counts) for t in tests)

def hit(a, b, p, counts, phase):
    counts[phase+'_service_intersections'] += 1
    dx, dy = b[0]-a[0], b[1]-a[1]
    x, y = p[0]-a[0], p[1]-a[1]
    if dx == dy == 0:
        return Q(0) if p == a else None
    if dx*y != dy*x:
        return None
    dot, sq = x*dx+y*dy, dx*dx+dy*dy
    return dot/sq if 0 <= dot <= sq else None
