"""Two complete engineering prototypes, NOT reproductions of the papers."""
from dataclasses import dataclass
import time
from model import Geometry, NoPath, DeadlineExceeded


@dataclass
class Result:
    algorithm: str
    status: str
    route: tuple
    seconds: float
    searches: int
    reason: str = ''


def candidates(g, demand, orientation):
    """Regular footprint-spaced samples, then explicit greedy coverage repair.

    This is a discrete camera-position generator, not OARP's rank optimization.
    """
    left = set(demand)
    if not left:
        return []
    x0 = min(x for x, y in left)
    y0 = min(y for x, y in left)
    x1 = max(x for x, y in left)
    y1 = max(y for x, y in left)
    step, r = 2*g.s.radius+1, g.s.radius
    points = []
    # Last footprint may extend beyond the target, but its centre must be legal.
    for y in range(y0+r, y1+r+1, step):
        for x in range(x0+r, x1+r+1, step):
            if (x, y) in g.views:
                points.append((x, y))
    if orientation == 'H':
        points.sort(key=lambda p: (p[1], p[0] if ((p[1]-y0-r)//step)%2 == 0 else -p[0]))
    else:
        points.sort(key=lambda p: (p[0], p[1] if ((p[0]-x0-r)//step)%2 == 0 else -p[1]))
    selected = []
    for p in points:
        g.check_time()
        if g.views[p] & left:
            selected.append(p)
            left.difference_update(g.views[p])
    while left:
        g.check_time()
        anchor = selected[-1] if selected else g.s.current
        best, key = None, None
        for p, view in g.views.items():
            g.check_time()
            gain = len(view & left)
            if not gain:
                continue
            rank = (-gain, abs(p[0]-anchor[0])+abs(p[1]-anchor[1]), p)
            if key is None or rank < key:
                best, key = p, rank
        if best is None:
            raise NoPath('uncovered_target_has_no_candidate')
        selected.append(best)
        left.difference_update(g.views[best])
    return selected


def insert_cheapest(g, existing, additions):
    visits = list(existing)
    for new in additions:
        best, best_key = None, None
        for i in range(len(visits)+1):
            a = g.s.current if i == 0 else visits[i-1]
            b = g.s.base if i == len(visits) else visits[i]
            increase = g.distance(a, new)+g.distance(new, b)-g.distance(a, b)
            key = increase, i
            if best_key is None or key < best_key:
                best, best_key = i, key
        visits.insert(best, new)
    return visits


def sequence_cost(g, visits):
    points = [g.s.current] + list(visits) + [g.s.base]
    return sum(g.distance(a, b) for a, b in zip(points, points[1:]))


def nearest(g, points):
    left, visits, current = set(points), [], g.s.current
    while left:
        p = min(left, key=lambda q: (g.distance(current, q), q))
        visits.append(p)
        left.remove(p)
        current = p
    return visits


def two_opt(g, visits, max_passes=8):
    """Fixed start/base, symmetric current-map distances, bounded passes."""
    visits = list(visits)
    for _ in range(max_passes):
        best_delta, best_pair = 0, None
        for i in range(len(visits)-1):
            a = g.s.current if i == 0 else visits[i-1]
            b = visits[i]
            for j in range(i+1, len(visits)):
                c = visits[j]
                d = g.s.base if j+1 == len(visits) else visits[j+1]
                delta = g.distance(a, c)+g.distance(b, d)-g.distance(a, b)-g.distance(c, d)
                if delta < best_delta:
                    best_delta, best_pair = delta, (i, j)
        if best_pair is None:
            break
        i, j = best_pair
        visits[i:j+1] = reversed(visits[i:j+1])
    return visits


def repair(g, offer):
    left = set(g.s.targets - g.s.covered - g.views[g.s.current])
    kept = []
    for p in g.s.old_route:
        g.check_time()
        if p in g.views and g.views[p] & left:
            kept.append(p)
            left.difference_update(g.views[p])
    for direction in ('H', 'V'):
        extra = candidates(g, left, direction)
        offer(g.expand(insert_cheapest(g, kept, extra)))


def rebuild(g, offer):
    demand = g.s.targets - g.s.covered - g.views[g.s.current]
    for direction in ('H', 'V'):
        points = candidates(g, demand, direction)
        # Preserve each feasible incumbent before the more expensive search.
        offer(g.expand(points))
        nn = nearest(g, points)
        offer(g.expand(nn))
        for seed in (points, nn):
            offer(g.expand(two_opt(g, seed)))


def solve(snapshot, algorithm, time_limit=5.0):
    begin = time.perf_counter()
    g, best = None, None
    def offer(route):
        nonlocal best
        if not route or route[0] != snapshot.current or route[-1] != snapshot.base:
            return
        if len(route)-1 > snapshot.distance_budget:
            return
        covered = set(snapshot.covered)
        previous = None
        for p in route:
            g.check_time()
            if p not in g.views:
                return
            if previous is not None and abs(previous[0]-p[0])+abs(previous[1]-p[1]) != 1:
                return
            covered.update(g.views[p])
            previous = p
        if not snapshot.targets <= covered:
            return
        if best is None or len(route) < len(best):
            best = route
    try:
        g = Geometry(snapshot, begin+time_limit)
        reason = g.precheck()
        if reason:
            return Result(algorithm, 'environment_infeasible', (), time.perf_counter()-begin,
                          g.searches, reason)
        # Both methods can keep the actual old suffix if it still completes the
        # entire updated task. This avoids an artificial no-change regression.
        offer(snapshot.old_route)
        {'P1': repair, 'P2': rebuild}[algorithm](g, offer)
        status, reason = ('planned', '') if best is not None else ('planning_failure', 'no_budget_feasible_incumbent')
    except DeadlineExceeded:
        status, reason = ('planned_at_timeout', 'deadline') if best is not None else ('timeout', 'no_incumbent')
    except NoPath as exc:
        status, reason = 'planning_failure', str(exc)
    return Result(algorithm, status, best or (), time.perf_counter()-begin,
                  g.searches if g else 0, reason)
