"""Independent audit: does not call planner coverage/path routines."""


def audit(snapshot, route):
    errors = []
    if not route:
        return {'valid': False, 'errors': ['empty_route'], 'length': None,
                'uncovered': len(snapshot.targets-snapshot.covered)}
    if route[0] != snapshot.current:
        errors.append('wrong_start')
    if route[-1] != snapshot.base:
        errors.append('missing_return')
    if any(p not in snapshot.free for p in route):
        errors.append('collision_or_out_of_bounds')
    for a, b in zip(route, route[1:]):
        if abs(a[0]-b[0])+abs(a[1]-b[1]) != 1:
            errors.append('illegal_step')
            break
    seen = set(snapshot.covered)
    for target in snapshot.targets - seen:
        if any(p in snapshot.free and
               abs(p[0]-target[0]) <= snapshot.radius and
               abs(p[1]-target[1]) <= snapshot.radius for p in route):
            seen.add(target)
    missing = snapshot.targets-seen
    if missing:
        errors.append('coverage_omission')
    length = len(route)-1
    if length > snapshot.distance_budget:
        errors.append('distance_budget_exceeded')
    vectors = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(route, route[1:])]
    return {'valid': not errors, 'errors': errors, 'length': length,
            'uncovered': len(missing), 'coverage_fraction': len(seen & snapshot.targets)/len(snapshot.targets),
            'revisited_positions': len(route)-len(set(route)),
            'direction_changes': sum(a != b for a, b in zip(vectors, vectors[1:]))}


def environment_check(snapshot):
    """Independent reachability/visibility check, not a resource infeasibility oracle."""
    if snapshot.current not in snapshot.free:
        return 'current_not_free'
    reached, pending = {snapshot.current}, [snapshot.current]
    while pending:
        x, y = pending.pop()
        for q in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if q in snapshot.free and q not in reached:
                reached.add(q)
                pending.append(q)
    if snapshot.base not in reached:
        return 'base_unreachable'
    for a, b in snapshot.targets-snapshot.covered:
        if not any(abs(x-a) <= snapshot.radius and abs(y-b) <= snapshot.radius for x,y in reached):
            return 'target_unobservable'
    return None
