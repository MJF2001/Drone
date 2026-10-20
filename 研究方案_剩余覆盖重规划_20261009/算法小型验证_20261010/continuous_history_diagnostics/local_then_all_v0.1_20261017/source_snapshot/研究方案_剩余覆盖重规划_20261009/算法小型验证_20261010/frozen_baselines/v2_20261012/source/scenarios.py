"""Declared exploratory snapshots. No future events are exposed to planners."""
from dataclasses import replace
from model import Snapshot, Geometry, footprint, capture_route
from planners import candidates, solve


def rectangle(x0, y0, width, height):
    return {(x, y) for x in range(x0, x0+width) for y in range(y0, y0+height)}


def flight_domain(targets, margin=2):
    return {(x+dx, y+dy) for x, y in targets
            for dx in range(-margin, margin+1) for dy in range(-margin, margin+1)}


def initial_checkpoint(length, width, fraction, initial_policy='snake'):
    targets = rectangle(3, 3, length, width)
    domain, base = flight_domain(targets), (1, 3)
    initial = Snapshot('initial', frozenset(domain), frozenset(targets), frozenset(),
                       base, base, (), distance_budget=4*len(domain))
    g = Geometry(initial)
    if initial_policy == 'snake':
        route = g.expand(candidates(g, targets-g.views[base], 'H'))
    elif initial_policy == 'optimized':
        result = solve(initial, 'P2', time_limit=5.0)
        if result.status != 'planned':
            raise RuntimeError('initial route optimization failed')
        route = result.route
    else:
        raise ValueError(initial_policy)
    coverage, index = set(), 0
    for index, p in enumerate(route):
        coverage.update(footprint(p, targets))
        if len(coverage)/len(targets) >= fraction:
            break
    snapshot = replace(initial, covered=frozenset(coverage), current=route[index],
                       old_route=route[index:])
    return snapshot, route[:index+1], targets, domain


def build_case(length, width, progress, family, initial_policy='snake'):
    old, prefix, old_targets, domain = initial_checkpoint(length, width, progress, initial_policy)
    xmax, ymax = length+2, width+2
    targets, obstacles = set(old_targets), set()
    if family == 'straight':
        targets.update(rectangle(xmax+1, 3, 9, width))
        domain = flight_domain(targets)
    elif family == 'corner':
        targets.update(rectangle(xmax+1, 3, width, width))
        targets.update(rectangle(xmax+1, ymax+1, width, 9))
        domain = flight_domain(targets)
    elif family == 'local_obstacle':
        # Two-cell thickness: every target within the footprint of a reachable
        # neighbour can still be observed in the declared no-occlusion model.
        patch = (xmax-4, 3+width//2-1)
        obstacles = rectangle(*patch, 2, 2)
        if old.current in obstacles:
            obstacles = rectangle(xmax-7, 3+width//2-1, 2, 2)
    elif family in ('channel_obstacle', 'closed_channel'):
        wall_x = xmax-4
        if wall_x == old.current[0]:
            wall_x -= 2
        ys = [y for x, y in domain if x == wall_x]
        top = max(ys)
        obstacles = {(wall_x, y) for y in ys
                     if family == 'closed_channel' or y != top}
    elif family == 'unobservable_target':
        # A 3x3 no-fly patch leaves its central unfinished target unobservable.
        candidates_left = sorted(old.targets-old.covered,
                                 key=lambda p: (-p[0], -p[1]))
        for p in candidates_left:
            patch = rectangle(p[0]-1, p[1]-1, 3, 3)
            if old.current not in patch and old.base not in patch:
                obstacles = patch
                break
    elif family != 'no_change':
        raise ValueError(family)
    assert old.current not in obstacles
    name = f'{family}_L{length}_W{width}_p{int(progress*100)}'
    snapshot = replace(old, name=name, free=frozenset(domain-obstacles),
                       targets=frozenset(targets), distance_budget=4*len(domain))
    meta = {'family': family, 'length': length, 'width': width, 'initial_policy': initial_policy,
            'requested_progress': progress, 'actual_progress': len(old.covered)/len(old_targets),
            'initial_targets': sorted(old_targets), 'domain': sorted(domain),
            'obstacles': sorted(obstacles), 'prefix': list(prefix)}
    return snapshot, meta


def all_cases(config):
    for length, width in config['road_sizes']:
        for progress in config['progress_fractions']:
            for family in config['families']:
                yield build_case(length, width, progress, family, config.get('initial_route_policy', 'snake'))
    for family in ('closed_channel', 'unobservable_target'):
        yield build_case(18, 6, 0.2, family, config.get('initial_route_policy', 'snake'))


def serialize(snapshot, meta):
    return {'name': snapshot.name, 'free': sorted(snapshot.free),
            'targets': sorted(snapshot.targets), 'covered': sorted(snapshot.covered),
            'current': snapshot.current, 'base': snapshot.base,
            'old_route': snapshot.old_route, 'radius': snapshot.radius,
            'distance_budget': snapshot.distance_budget, 'metadata': meta}


def deserialize(data):
    return Snapshot(data['name'], frozenset(map(tuple, data['free'])),
                    frozenset(map(tuple, data['targets'])),
                    frozenset(map(tuple, data['covered'])), tuple(data['current']),
                    tuple(data['base']), tuple(map(tuple, data['old_route'])),
                    data['radius'], data['distance_budget'])
