"""Four engineering prototypes, NOT reproductions of the papers."""
from dataclasses import dataclass
import time
from model import Geometry, NoPath, DeadlineExceeded, adjacent


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


def components(demand):
    """Target adjacency, not flight connectivity or a historical TRACE tree."""
    left, groups = set(demand), []
    while left:
        seed = min(left)
        left.remove(seed)
        group, queue = {seed}, [seed]
        while queue:
            for q in adjacent(queue.pop()):
                if q in left:
                    left.remove(q)
                    group.add(q)
                    queue.append(q)
        groups.append(group)
    return groups


def block_cost(g, blocks):
    current, total = g.s.current, 0
    for block in blocks:
        total += g.distance(current, block[0])
        total += sum(g.distance(a, b) for a, b in zip(block, block[1:]))
        current = block[-1]
    return total + g.distance(current, g.s.base)


def orient_blocks(g, blocks):
    """Optimal binary orientations for a fixed block order (two-state DP)."""
    if not blocks:
        return []
    states = [(0, g.s.current, [])]
    for block in blocks:
        g.check_time()
        next_states = []
        for candidate in (tuple(block), tuple(reversed(block))):
            inside = sum(g.distance(a, b) for a, b in zip(candidate, candidate[1:]))
            choices = [(cost+g.distance(end, candidate[0])+inside, route+[candidate])
                       for cost, end, route in states]
            cost, route = min(choices, key=lambda item: item[0])
            next_states.append((cost, candidate[-1], route))
        states = next_states
    return min(states, key=lambda item: item[0]+g.distance(item[1], g.s.base))[2]


def expand_blocks(g, blocks, rigid=False):
    if not rigid:
        return g.expand([p for block in blocks for p in block])
    # Old packets retain their actual internal movement, even if transit has
    # incidentally covered their targets. Thus packet reuse is measurable.
    route = [g.s.current]
    for block in blocks:
        g.check_time()
        route.extend(g.path(route[-1], block[0])[1:])
        for p in block[1:]:
            route.extend(g.path(route[-1], p)[1:])
    route.extend(g.path(route[-1], g.s.base)[1:])
    return tuple(route)


def optimize_blocks(g, blocks, offer, rigid=False):
    """Shared fixed-start/end block reversal search, at most eight passes."""
    blocks = orient_blocks(g, blocks)
    offer(expand_blocks(g, blocks, rigid))
    for _ in range(8):
        best, best_cost = blocks, block_cost(g, blocks)
        for i in range(len(blocks)):
            for j in range(i+1, len(blocks)):
                trial = orient_blocks(g, blocks[:i]+list(reversed(blocks[i:j+1]))+blocks[j+1:])
                cost = block_cost(g, trial)
                if cost < best_cost:
                    best, best_cost = trial, cost
        if best == blocks:
            break
        blocks = best
        offer(expand_blocks(g, blocks, rigid))


def grouped(g, offer):
    demand = g.s.targets-g.s.covered-g.views[g.s.current]
    groups = components(demand)
    def first_touch(group):
        for i, p in enumerate(g.s.old_route):
            g.check_time()
            if p in g.views and g.views[p] & group:
                return i
        return len(g.s.old_route)
    groups.sort(key=lambda group: (first_touch(group), min(group)))
    for direction in ('H', 'V'):
        blocks = [tuple(candidates(g, group, direction)) for group in groups]
        # Preserve old-touched group order; new groups get cheapest insertion.
        touched, added = [], []
        for group, block in zip(groups, blocks):
            (touched if first_touch(group) < len(g.s.old_route) else added).append(block)
        for block in added:
            choices = [orient_blocks(g, touched[:i]+[block]+touched[i:])
                       for i in range(len(touched)+1)]
            touched = min(choices, key=lambda b: block_cost(g, b))
        offer(expand_blocks(g, orient_blocks(g, touched)))


def old_packets(g):
    """Legal straight movement runs, split at turns, gaps and blocked poses."""
    runs, run, direction = [], [], None
    for p in g.s.old_route:
        g.check_time()
        if p not in g.views:
            if run:
                runs.append(tuple(run))
            run, direction = [], None
            continue
        if not run:
            run = [p]
            continue
        step = (p[0]-run[-1][0], p[1]-run[-1][1])
        if abs(step[0])+abs(step[1]) != 1:
            runs.append(tuple(run))
            run, direction = [p], None
        elif direction is not None and direction != step:
            runs.append(tuple(run))
            run, direction = [run[-1], p], step
        else:
            run.append(p)
            direction = step
    if run:
        runs.append(tuple(run))
    left, kept = set(g.s.targets-g.s.covered-g.views[g.s.current]), []
    for run in runs:
        view = set().union(*(g.views[p] for p in run))
        if view & left:
            kept.append(run)
            left.difference_update(view)
    return kept, left


def reuse_segments(g, offer):
    kept, left = old_packets(g)
    for direction in ('H', 'V'):
        extra = [(p,) for p in candidates(g, left, direction)]
        blocks = kept+extra
        # Both the original order and an endpoint-distance nearest seed.
        optimize_blocks(g, blocks, offer, rigid=True)
        remaining, seed, current = list(blocks), [], g.s.current
        while remaining:
            options = [(g.distance(current, b[0]), i, False) for i, b in enumerate(remaining)]
            options += [(g.distance(current, b[-1]), i, True) for i, b in enumerate(remaining)]
            _, i, reverse = min(options)
            block = remaining.pop(i)
            block = tuple(reversed(block)) if reverse else block
            seed.append(block)
            current = block[-1]
        optimize_blocks(g, seed, offer, rigid=True)


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
        {'P1': repair, 'P2': rebuild, 'P3': grouped, 'P4': reuse_segments}[algorithm](g, offer)
        status, reason = ('planned', '') if best is not None else ('planning_failure', 'no_budget_feasible_incumbent')
    except DeadlineExceeded:
        status, reason = ('planned_at_timeout', 'deadline') if best is not None else ('timeout', 'no_incumbent')
    except NoPath as exc:
        status, reason = 'planning_failure', str(exc)
    return Result(algorithm, status, best or (), time.perf_counter()-begin,
                  g.searches if g else 0, reason)
