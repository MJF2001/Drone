"""Single-cell downward capture; blocked targets retained in a deferred ledger."""
from dataclasses import replace
from model import Snapshot
from planners import solve, components
from audit import audit, environment_check
from scenarios_v2 import layout, checkpoint, obstacle, FAMILIES


def initial(length, width, kind):
    old, straight, corner, domain = layout(length, width, kind)
    seed = Snapshot('initial_v3', frozenset(domain), frozenset(old), frozenset(),
                    (1, 3), (1, 3), (), radius=0, distance_budget=4*len(domain))
    result = solve(seed, 'P2', 5)
    if result.status not in ('planned', 'planned_at_timeout') or not audit(seed, result.route)['valid']:
        raise RuntimeError(('initial_generation_failed', length, width, kind, result.status))
    return seed, result.route, straight, corner


def case_from_checkpoint(old, prefix, straight, corner, length, width, kind, progress, family):
    published = set(old.targets)
    if family in ('straight', 'straight_channel'):
        published.update(straight)
    if family in ('corner', 'corner_channel'):
        published.update(corner)
    blocked, placement = obstacle(old, family, length)
    deferred = (published-set(old.covered)) & blocked
    # Retain covered history in planner targets; defer only unfinished blocked cells.
    active_ledger = published-deferred
    s = replace(old, name=f'v3_{kind}_{family}_L{length}_W{width}_p{int(progress*100)}',
                targets=frozenset(active_ledger), free=old.free-blocked)
    meta = {'domain_kind': kind, 'family': family, 'length': length, 'width': width,
        'requested_progress': progress, 'actual_progress': len(old.covered)/len(old.targets),
        'initial_targets': sorted(old.targets), 'published_targets': sorted(published),
        'deferred_targets': sorted(deferred), 'deferred_count': len(deferred),
        'active_pending_count': len(s.targets-s.covered),
        'domain': sorted(old.free), 'prefix': list(prefix), 'obstacles': sorted(blocked),
        'placement': placement, 'new_target_count': len(published-set(old.targets)),
        'old_route_collision': bool(set(s.old_route)-s.free),
        'remaining_target_components': len(components(s.targets-s.covered)),
        'environment_reason': environment_check(s), 'flight_domain_fixed': True,
        'initial_policy': 'P2_before_event_radius0', 'capture_radius': 0}
    return s, meta


def all_cases_v3():
    for length, width in ((18, 6), (24, 9)):
        for kind in ('open', 'corridor'):
            seed, route, straight, corner = initial(length, width, kind)
            for progress in (.25, .75):
                old, prefix = checkpoint(seed, route, progress)
                for family in FAMILIES:
                    yield case_from_checkpoint(old, prefix, straight, corner, length, width,
                                               kind, progress, family)
