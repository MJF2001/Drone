"""Controlled ordering/packet diagnostics. Not a proposed paper algorithm."""
import time
from model import Geometry, DeadlineExceeded, NoPath
from planners import candidates, components, old_packets, Result
from audit import audit


def admissible(order, labels, mode):
    if mode == 'free':
        return True
    seen, last, offsets = set(), None, []
    for index in order:
        group, offset = labels[index]
        if group != last:
            if group in seen:
                return False
            if mode == 'packet' and offsets not in (sorted(offsets), sorted(offsets, reverse=True)):
                return False
            seen.add(group)
            last, offsets = group, []
        offsets.append(offset)
    return mode != 'packet' or offsets in (sorted(offsets), sorted(offsets, reverse=True))


def strict_expand(g, visits):
    route = [g.s.current]
    for p in visits:
        route.extend(g.path(route[-1], p)[1:])
    route.extend(g.path(route[-1], g.s.base)[1:])
    return tuple(route)


def pool(g, kind):
    demand = g.s.targets-g.s.covered-g.views[g.s.current]
    if kind == 'G':
        blocks = [candidates(g, group, 'H') for group in components(demand)]
    else:
        blocks, left = old_packets(g)
        blocks = list(blocks)+[(p,) for p in candidates(g, left, 'H')]
    points, labels = [], []
    for i, block in enumerate(blocks):
        for offset, p in enumerate(block):
            points.append(p)
            labels.append((i, offset))
    return points, labels


def run_diagnostic(s, kind, locked, time_limit=5.0):
    begin = time.perf_counter()
    g, best, order, points, labels = None, None, None, [], []
    mode = ('group' if kind == 'G' else 'packet') if locked else 'free'
    reason, status, passes = '', 'planned', 0
    def cost(seq):
        poses = [s.current]+[points[i] for i in seq]+[s.base]
        return sum(g.distance(a, b) for a, b in zip(poses, poses[1:]))
    try:
        g = Geometry(s, begin+time_limit)
        reason = g.precheck()
        if reason:
            return {'status': 'environment_infeasible', 'reason': reason, 'route': (),
                    'seconds': time.perf_counter()-begin, 'point_count': 0, 'audit': None}
        points, labels = pool(g, kind)
        order = list(range(len(points)))
        # Fixed common initial order; no extra seed afforded to either variant.
        best = strict_expand(g, points)
        if not audit(s, best)['valid']:
            raise NoPath('invalid_common_seed')
        for _ in range(8):
            g.check_time()
            current_cost, improvement, pair = cost(order), 0, None
            for i in range(len(order)-1):
                for j in range(i+1, len(order)):
                    g.check_time()
                    trial = order[:i]+list(reversed(order[i:j+1]))+order[j+1:]
                    if not admissible(trial, labels, mode):
                        continue
                    a = s.current if i == 0 else points[order[i-1]]
                    b, c = points[order[i]], points[order[j]]
                    d = s.base if j+1 == len(order) else points[order[j+1]]
                    delta = g.distance(a, c)+g.distance(b, d)-g.distance(a, b)-g.distance(c, d)
                    if delta < improvement:
                        improvement, pair = delta, (i, j)
            if pair is None:
                break
            i, j = pair
            trial = order[:i]+list(reversed(order[i:j+1]))+order[j+1:]
            route = strict_expand(g, [points[k] for k in trial])
            # Commit order only after its complete path exists.
            order, best = trial, route
            passes += 1
    except DeadlineExceeded:
        status, reason = ('planned_at_timeout' if best else 'timeout'), 'deadline'
    except NoPath as exc:
        status, reason = 'planning_failure', str(exc)
    elapsed = time.perf_counter()-begin
    check = audit(s, best or ())
    # Optional post-processing is OUTSIDE the search time and its 5s budget.
    # Report separately, never use it to claim a budget-feasible search result.
    skipped, skip_check, proxy = (), None, None
    if best and order is not None:
        post = Geometry(s)
        visits = [points[i] for i in order]
        skipped = post.expand(visits)
        skip_check = audit(s, skipped)
        proxy = len(strict_expand(post, visits))-1
    return {'status': status, 'reason': reason, 'route': best or (), 'audit': check,
            'seconds': elapsed, 'point_count': len(points), 'labels': labels,
            'points': points, 'order': order, 'passes': passes,
            'ordering_constraint_valid': order is not None and admissible(order, labels, mode),
            'distance_proxy': proxy, 'skipped_route': skipped, 'skipped_audit': skip_check,
            'postprocess_outside_search_budget': True}
