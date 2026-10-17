"""Grid-phase position candidates with unchanged P2 ordering rules."""
import time
from model import Geometry, DeadlineExceeded, NoPath
from planners import candidates, nearest, two_opt

PHASES = ((0,0), (-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,-1), (-1,1), (1,1))


def shifted_candidates(g, demand, orientation, phase):
    if phase == (0,0):
        return candidates(g, demand, orientation)
    left = set(demand)
    if not left:
        return []
    if g.s.radius != 1:
        raise ValueError('phase experiment declared only for radius one')
    x0, x1 = min(x for x,y in left), max(x for x,y in left)
    y0, y1 = min(y for x,y in left), max(y for x,y in left)
    dx, dy = phase
    sx, sy, step = x0+1+dx, y0+1+dy, 3
    points = [(x,y) for y in range(sy, y1+2, step) for x in range(sx, x1+2, step)
              if (x,y) in g.views]
    if orientation == 'H':
        points.sort(key=lambda p: (p[1], p[0] if ((p[1]-sy)//step)%2 == 0 else -p[0]))
    else:
        points.sort(key=lambda p: (p[0], p[1] if ((p[0]-sx)//step)%2 == 0 else -p[1]))
    selected = []
    for p in points:
        g.check_time()
        if g.views[p] & left:
            selected.append(p)
            left.difference_update(g.views[p])
    while left:
        g.check_time()
        anchor = selected[-1] if selected else g.s.current
        best, best_key = None, None
        for p, view in g.views.items():
            g.check_time()
            gain = len(view & left)
            if not gain:
                continue
            key = (-gain, abs(p[0]-anchor[0])+abs(p[1]-anchor[1]), p)
            if best_key is None or key < best_key:
                best, best_key = p, key
        if best is None:
            raise NoPath('uncovered_target_has_no_candidate')
        selected.append(best)
        left.difference_update(g.views[best])
    return selected


def solve_phases(s, mode='SHIFT', time_limit=5.0):
    if mode not in ('SHIFT', 'REPEAT', 'ZERO'):
        raise ValueError(mode)
    begin = time.perf_counter()
    best, source, baseline_length, g = None, None, None, None
    logs = []
    def offer(route, origin):
        nonlocal best, source
        if not route or route[0] != s.current or route[-1] != s.base or len(route)-1 > s.distance_budget:
            return False
        covered, previous = set(s.covered), None
        for p in route:
            g.check_time()
            if p not in g.views:
                return False
            if previous is not None and abs(previous[0]-p[0])+abs(previous[1]-p[1]) != 1:
                return False
            covered.update(g.views[p])
            previous = p
        if not s.targets <= covered:
            return False
        if best is None or len(route) < len(best):
            best, source = route, origin
        return True
    try:
        g = Geometry(s, begin+time_limit)
        reason = g.precheck()
        if reason:
            return {'algorithm': mode, 'status': 'environment_infeasible', 'reason': reason,
                    'route': (), 'seconds': time.perf_counter()-begin, 'logs': [],
                    'baseline_stage_length': None, 'source': None}
        offer(s.old_route, {'kind': 'old_suffix'})
        demand = s.targets-s.covered-g.views[s.current]
        phases = PHASES if mode == 'SHIFT' else ((0,0),)*(1 if mode == 'ZERO' else 9)
        for index, phase in enumerate(phases):
            for direction in ('H', 'V'):
                log = {'phase_index': index, 'phase': phase, 'direction': direction,
                       'points': [], 'candidates': [], 'completed': False}
                logs.append(log)
                points = shifted_candidates(g, demand, direction, phase)
                log['points'] = points
                def attempt(label, visits):
                    route = g.expand(visits)
                    origin = {'phase_index': index, 'phase': phase, 'direction': direction, 'label': label}
                    valid = offer(route, origin)
                    log['candidates'].append({'label': label, 'length': len(route)-1,
                                              'valid': valid, 'visits': list(visits)})
                attempt('snake', points)
                nn = nearest(g, points)
                attempt('nearest', nn)
                attempt('snake_2opt', two_opt(g, points))
                attempt('nearest_2opt', two_opt(g, nn))
                log['completed'] = True
            if index == 0:
                baseline_length = len(best)-1 if best else None
        status, reason = ('planned', '') if best else ('planning_failure', 'no_budget_feasible_incumbent')
    except DeadlineExceeded:
        status, reason = ('planned_at_timeout' if best else 'timeout'), 'deadline'
    except NoPath as exc:
        status, reason = 'planning_failure', str(exc)
    return {'algorithm': mode, 'status': status, 'reason': reason, 'route': best or (),
            'seconds': time.perf_counter()-begin, 'source': source, 'logs': logs,
            'baseline_stage_length': baseline_length, 'searches': g.searches if g else 0}
