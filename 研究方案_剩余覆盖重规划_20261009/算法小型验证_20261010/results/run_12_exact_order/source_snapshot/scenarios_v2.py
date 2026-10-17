"""Explicit fixed flight domains; published inspection targets may expand."""
from dataclasses import replace
from model import Snapshot, capture_route
from planners import solve, components
from audit import audit, environment_check
from scenarios import rectangle, flight_domain, serialize

FAMILIES = ('no_change', 'straight', 'corner', 'near_obstacle', 'far_obstacle',
            'channel_obstacle', 'straight_channel', 'corner_channel')


def layout(length, width, domain_kind):
    old = rectangle(3, 3, length, width)
    straight = rectangle(length+3, 3, 9, width)
    corner = rectangle(length+3, 3, width, width) | rectangle(length+3, width+3, width, 9)
    # Flight permission is explicitly known before targets are published.
    envelope = old | straight | corner
    if domain_kind == 'open':
        domain = rectangle(0, 0, max(x for x, y in envelope)+4,
                           max(y for x, y in envelope)+4)
    elif domain_kind == 'corridor':
        domain = flight_domain(envelope, 1) | {(1, 3), (2, 3)}
    else:
        raise ValueError(domain_kind)
    return old, straight, corner, domain


def initial(length, width, domain_kind):
    old, straight, corner, domain = layout(length, width, domain_kind)
    snapshot = Snapshot('initial_v2', frozenset(domain), frozenset(old), frozenset(),
                        (1, 3), (1, 3), (), radius=1, distance_budget=4*len(domain))
    result = solve(snapshot, 'P2', 5)
    if result.status != 'planned' or not audit(snapshot, result.route)['valid']:
        raise RuntimeError(('initial_generation_failed', length, width, domain_kind, result.status))
    return snapshot, result.route, straight, corner


def checkpoint(snapshot, route, progress):
    seen = set()
    for i, p in enumerate(route):
        seen.update(capture_route((p,), snapshot.targets, snapshot.radius))
        if len(seen)/len(snapshot.targets) >= progress:
            return replace(snapshot, current=p, covered=frozenset(seen), old_route=route[i:]), route[:i+1]
    raise RuntimeError('progress_not_reached')


def obstacle(old, family, length):
    if family in ('near_obstacle', 'far_obstacle'):
        fraction = .15 if family == 'near_obstacle' else .70
        start = min(len(old.old_route)-1, int(fraction*(len(old.old_route)-1)))
        indices = list(range(start, len(old.old_route)))+list(range(start))
        for i in indices:
            x, y = old.old_route[i]
            patch = rectangle(x, y, 2, 2) & old.free
            if patch and old.current not in patch and old.base not in patch:
                return patch, {'old_route_anchor_index': i, 'requested_route_fraction': fraction}
        raise RuntimeError('no_safe_local_obstacle_position')
    if family in ('channel_obstacle', 'straight_channel', 'corner_channel'):
        desired_x = 3+(2*length)//3
        choices = [desired_x]+[desired_x+delta for delta in (1, -1, 2, -2)]
        for x in choices:
            column = sorted((p for p in old.free if p[0] == x), key=lambda p: p[1])
            if len(column) < 2:
                continue
            gap = column[0]
            blocked = set(column[1:])
            if old.current not in blocked and old.base not in blocked:
                return blocked, {'wall_x': x, 'gap': gap}
        raise RuntimeError('no_safe_channel_obstacle_position')
    return set(), {}


def case_from_checkpoint(old, prefix, straight, corner, length, width, kind, progress, family):
    targets = set(old.targets)
    if family in ('straight', 'straight_channel'):
        targets.update(straight)
    if family in ('corner', 'corner_channel'):
        targets.update(corner)
    blocked, placement = obstacle(old, family, length)
    name = f'v2_{kind}_{family}_L{length}_W{width}_p{int(progress*100)}'
    s = replace(old, name=name, targets=frozenset(targets), free=old.free-blocked)
    assert s.targets <= old.free
    assert s.current in s.free and s.base in s.free
    assert s.covered == capture_route(prefix, old.targets, old.radius)
    meta = {'domain_kind': kind, 'family': family, 'length': length, 'width': width,
            'requested_progress': progress, 'actual_progress': len(old.covered)/len(old.targets),
            'initial_targets': sorted(old.targets), 'domain': sorted(old.free),
            'prefix': list(prefix), 'obstacles': sorted(blocked), 'placement': placement,
            'new_target_count': len(s.targets-old.targets),
            'old_route_collision': bool(set(s.old_route)-s.free),
            'remaining_target_components': len(components(s.targets-s.covered)),
            'environment_reason': environment_check(s), 'flight_domain_fixed': True,
            'initial_policy': 'P2_before_event'}
    return s, meta


def all_cases_v2():
    for length, width in ((18, 6), (24, 9)):
        for kind in ('open', 'corridor'):
            seed, route, straight, corner = initial(length, width, kind)
            for progress in (.25, .75):
                old, prefix = checkpoint(seed, route, progress)
                for family in FAMILIES:
                    yield case_from_checkpoint(old, prefix, straight, corner, length, width,
                                               kind, progress, family)
