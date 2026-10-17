"""Development-only geometry generator for design 45 (stdlib; never calls solve).

Holdout generation intentionally has no CLI option. Geometric witnesses are
input preparation artifacts, not algorithms being benchmarked or free candidates.
"""
from collections import Counter, deque
from pathlib import Path
import argparse
import hashlib
import heapq
import json
import time
import traceback
from prepare_scale_design_20261014 import MASTER, tables


def rect(x, y, length, width):
    return {(x+i, y+j) for i in range(length) for j in range(width)}


def adjacent(p):
    x, y = p
    return ((x+1, y), (x, y+1), (x-1, y), (x, y-1))


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode('utf-8')).hexdigest()


def reflect(p, params):
    return (p[0], params['width']-1-p[1]) if params['reflect_y'] else p


def initial_targets(params):
    L, W, A = (params[k] for k in ('length', 'width', 'arm'))
    targets = rect(0, 0, L, W)
    if A:
        targets |= rect(L-W, W, W, A)
    d = params['extra_width']
    if d:
        a, b = params['widen_start'], params['widen_stop']
        targets |= rect(a, -d, b-a, W+2*d)
    return frozenset(reflect(p, params) for p in targets)


def extension(params, percent, kind, turn=None):
    W, L, A = (params[k] for k in ('width', 'length', 'arm'))
    old = initial_targets(params)
    cross_sections = (percent*len(old)+100*W-1)//(100*W)
    length = max(1, cross_sections-(W if kind == 'corner' else 0))
    if A:
        origin, tangent, normal = (L-1, W+A), (0, 1), (-1, 0)
    else:
        origin, tangent, normal = (L, 0), (1, 0), (0, 1)
    def cell(i, j):
        return reflect((origin[0]+i*tangent[0]+j*normal[0],
                        origin[1]+i*tangent[1]+j*normal[1]), params)
    if kind == 'straight':
        cells = {cell(i,j) for i in range(length) for j in range(W)}
    elif kind == 'corner':
        if turn not in ('left', 'right'):
            raise ValueError('corner turn required')
        cells = {cell(i,j) for i in range(W) for j in range(W)}
        js = range(W, W+length) if turn == 'left' else range(-length, 0)
        cells |= {cell(i,j) for i in range(W) for j in js}
    else:
        raise ValueError(kind)
    return frozenset(cells-old), dict(length=length,
        requested_fraction=percent/100, actual_fraction=len(cells-old)/len(old),
        minimum_corner_size_clipped=kind == 'corner' and cross_sections-W < 1)


def layout(params):
    targets = initial_targets(params)
    envelope = set(targets)
    envelope.update(extension(params, 40, 'straight')[0])
    for turn in ('left', 'right'):
        envelope.update(extension(params, 40, 'corner', turn)[0])
    L = params['length']
    bx, tx = (-2, 0) if params['base_side'] == 'west' else (L+1, L-1)
    base = reflect((bx, 0), params)
    access = {reflect((x, 0), params) for x in range(min(bx,tx), max(bx,tx)+1)}
    if params['domain_kind'] == 'open':
        x0, x1 = min(x for x,y in envelope)-2, max(x for x,y in envelope)+2
        y0, y1 = min(y for x,y in envelope)-2, max(y for x,y in envelope)+2
        domain = rect(x0, y0, x1-x0+1, y1-y0+1)
    elif params['domain_kind'] == 'corridor':
        domain = envelope | {q for p in envelope for q in adjacent(p)}
    else:
        raise ValueError(params['domain_kind'])
    domain |= access
    return frozenset(domain), targets, base


def distances(free, start):
    if start not in free:
        return {}
    result = {start: 0}; queue = deque([start])
    while queue:
        p = queue.popleft()
        for q in adjacent(p):
            if q in free and q not in result:
                result[q] = result[p]+1; queue.append(q)
    return result


def path(free, a, b):
    """Canonical endpoint A*, matching frozen tie conventions; no shared cache."""
    if a not in free or b not in free:
        raise ValueError('endpoint_not_free')
    lo, hi = sorted((a,b))
    h = lambda p: abs(p[0]-hi[0])+abs(p[1]-hi[1])
    queue = [(h(lo), 0, lo)]; costs = {lo: 0}; parent = {}
    while queue:
        _, cost, p = heapq.heappop(queue)
        if cost != costs[p]:
            continue
        if p == hi:
            result = [hi]
            while result[-1] != lo:
                result.append(parent[result[-1]])
            result.reverse()
            return tuple(result if a == lo else reversed(result))
        for q in adjacent(p):
            if q in free and cost+1 < costs.get(q, float('inf')):
                costs[q] = cost+1; parent[q] = p
                heapq.heappush(queue, (cost+1+h(q), cost+1, q))
    raise ValueError('no_path')


def expand(free, targets, covered, current, base, visits):
    route = [current]; seen = set(covered) | ({current} & targets)
    for p in visits:
        if p in seen:
            continue
        segment = path(free, route[-1], p)
        route.extend(segment[1:]); seen.update(set(segment) & targets)
    route.extend(path(free, route[-1], base)[1:])
    return tuple(route)


def route_audit(free, targets, covered, current, base, route, budget=None):
    """Independent linear route check; no path construction is called."""
    errors = []
    if not route:
        return dict(valid=False, errors=['empty_route'])
    if route[0] != current: errors.append('wrong_start')
    if route[-1] != base: errors.append('missing_return')
    if any(p not in free for p in route): errors.append('collision')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1]) != 1 for a,b in zip(route,route[1:])):
        errors.append('illegal_step')
    missing = targets-set(covered)-set(route)
    if missing: errors.append('missing_targets')
    if budget is not None and len(route)-1 > budget: errors.append('resource_limit')
    return dict(valid=not errors, errors=errors, missing=len(missing), steps=len(route)-1)


def scan_route(free, targets, base, axis):
    xmin = min(x for x,y in targets); ymin = min(y for x,y in targets)
    if axis == 'H':
        key = lambda p: (p[1], p[0] if (p[1]-ymin)%2 == 0 else -p[0])
    elif axis == 'V':
        key = lambda p: (p[0], p[1] if (p[0]-xmin)%2 == 0 else -p[1])
    else: raise ValueError(axis)
    route = expand(free, targets, set(), base, base, sorted(targets, key=key))
    assert route_audit(free, targets, set(), base, base, route)['valid']
    return route


def checkpoint(targets, route, percent):
    seen = set()
    for i,p in enumerate(route):
        if p in targets: seen.add(p)
        if 100*len(seen) >= percent*len(targets):
            return dict(current=p, covered=frozenset(seen), prefix=route[:i+1],
                        old_route=route[i:], index=i, actual_progress=len(seen)/len(targets))
    raise ValueError('progress_not_reached')


def obstacle_patch(params, anchor, shape):
    # Inverse reflection equals forward reflection.
    x,y = reflect(anchor, params); W = params['width']
    if shape == 'block':
        s = max(1, W//3); cells = rect(x,y,s,s)
    elif shape == 'barrier':
        length = max(1,W-1); offset = (length-1)//2
        cells = (rect(x-offset,y,length,1) if params['arm'] and y >= W
                 else rect(x,y-offset,1,length))
    else: raise ValueError(shape)
    return frozenset(reflect(p,params) for p in cells)


def choose_obstacle(params, free, targets, base, state, schedule):
    current, covered = state['current'], state['covered']
    old_points = set(state['old_route']); ds = distances(free, current)
    candidates = []
    for anchor in sorted(targets-covered):
        if anchor in (base,current): continue
        blocked = obstacle_patch(params, anchor, schedule['obstacle_shape']) & free
        if not blocked or blocked & {base,current}: continue
        if not blocked & (targets-covered) or not blocked & old_points: continue
        candidates.append((ds[anchor],anchor,blocked))
    candidates.sort(key=lambda z:(z[0],z[1]))
    log = dict(candidate_count=len(candidates), shape=schedule['obstacle_shape'],
               distance_band=schedule['obstacle_distance'], attempts=[])
    if len(candidates) < 3:
        return None, dict(log, failure='insufficient_placement_pool')
    n = (len(candidates)+2)//3
    band = candidates[:n] if schedule['obstacle_distance'] == 'near' else candidates[-n:]
    def key(z):
        anchor = z[1]
        label = '|'.join(map(str, (MASTER, params['map_id'], schedule['history'],
            schedule['progress_percent'], anchor[0], anchor[1], schedule['obstacle_shape'])))
        return hashlib.sha256(label.encode('utf-8')).hexdigest()
    ordered = sorted(band,key=lambda z:(key(z),z[1]))
    ranks = {z[1]:i for i,z in enumerate(candidates)}
    for distance,anchor,blocked in ordered[:64]:
        reached = distances(free-blocked,current)
        reason = ('base_unreachable' if base not in reached else
                  'old_target_unreachable' if targets-covered-blocked-set(reached) else None)
        log['attempts'].append(dict(anchor=anchor,distance=distance,
            pool_rank=ranks[anchor], blocked=sorted(blocked), rejection=reason))
        if reason is None:
            return blocked, dict(log, selected_anchor=anchor,selected_distance=distance)
    return None, dict(log, failure='placement_attempts_exhausted')


def make_case(params, free0, old_targets, base, state, schedule, obstacle_result):
    event = schedule['event']; extra = frozenset(); ext_info = None
    if event in ('straight','straight_obstacle'):
        extra,ext_info = extension(params,schedule['extension_percent'],'straight')
    elif event in ('corner','corner_obstacle'):
        extra,ext_info = extension(params,schedule['extension_percent'],'corner',schedule['turn'])
    if not extra <= free0: raise AssertionError('expansion_outside_fixed_flight_domain')
    blocked, placement = obstacle_result if 'obstacle' in event else (frozenset(),None)
    if blocked is None:
        return dict(state_id=schedule['state_id'],status='generation_failure',
                    reason=placement['failure'], placement=placement), None
    covered = state['covered']; published = old_targets | extra
    deferred = (published-covered) & blocked
    targets = published-blocked; free = free0-blocked; current = state['current']
    reached = distances(free,current)
    if base not in reached or targets-covered-set(reached):
        return dict(state_id=schedule['state_id'],status='generation_failure',
            reason='combination_generation_failure',placement=placement), None
    witness = expand(free, targets, covered, current, base, sorted(targets-covered))
    limit = max(1,2*(len(witness)-1))
    check = route_audit(free,targets,covered,current,base,witness,limit)
    assert check['valid'], check
    assert covered == old_targets & set(state['prefix'])
    assert state['prefix'][-1] == current == state['old_route'][0]
    assert targets <= free and covered <= old_targets and not deferred & covered
    metadata = dict(schedule, initial_targets=sorted(old_targets),
        published_targets=sorted(published), deferred_targets=sorted(deferred),
        obstacles=sorted(blocked), prefix=state['prefix'],
        actual_progress=state['actual_progress'], extension=ext_info,
        placement=placement, witness_sha256=digest(witness), witness_steps=len(witness)-1,
        witness_audit=check, initial_policy='raw_'+schedule['history']+'_canonical',
        flight_domain_fixed=True, blocked_historical_count=len(covered & blocked),
        counts=dict(free=len(free),published=len(published),covered=len(covered),
                    pending=len(targets-covered),deferred=len(deferred),new_targets=len(extra)),
        all_published_work_completed=False if deferred else None)
    snapshot = dict(name=schedule['state_id'],free=sorted(free),targets=sorted(targets),
        covered=sorted(covered),current=current,base=base,old_route=state['old_route'],
        radius=0,distance_budget=limit,metadata=metadata)
    return dict(state_id=schedule['state_id'],status='generated',
                snapshot_sha256=digest(snapshot), witness_sha256=digest(witness)), (snapshot,witness)


def write_json(path_, obj):
    with path_.open('x',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,separators=(',', ':')); f.write('\n')


def generate(out, scale=None):
    maps, schedules = tables()
    maps = [m for m in maps if m['split'] == 'development' and (scale is None or m['scale']==scale)]
    schedules = [s for s in schedules if s['map_id'] in {m['map_id'] for m in maps}]
    # No accidental CLI switch can expose or generate the holdout geometry.
    assert all(m['split']=='development' for m in maps)
    out.mkdir(parents=True,exist_ok=False)
    begin = time.perf_counter(); ledger = []
    write_json(out/'protocol.json',dict(version='scale_geometry_v0.1_20261014',
        design_version='scale_design_v0.1_20261014',status='development_input_preparation',
        holdout_generated=False,solver_called=False,expected_states=len(schedules),
        scope='geometry and resource-witness validation only',scale_filter=scale))
    try:
        with (out/'snapshots.jsonl').open('x',encoding='utf-8') as sf, (out/'witnesses.jsonl').open('x',encoding='utf-8') as wf:
            for params in maps:
                free, old, base = layout(params)
                routes = {h:scan_route(free,old,base,h) for h in ('H','V')}
                write_json(out/(params['map_id']+'.json'),dict(parameters=params,
                    domain=sorted(free),initial_targets=sorted(old),base=base,routes=routes))
                for history in ('H','V'):
                    for progress in (25,50,75):
                        rows = [s for s in schedules if s['map_id']==params['map_id'] and
                                s['history']==history and s['progress_percent']==progress]
                        state = checkpoint(old,routes[history],progress)
                        obstacle_row = next(s for s in rows if s['event']=='obstacle')
                        obstacle = choose_obstacle(params,free,old,base,state,obstacle_row)
                        for row in rows:
                            entry, data = make_case(params,free,old,base,state,row,obstacle)
                            ledger.append(entry)
                            if data:
                                snapshot,witness = data
                                sf.write(json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))+'\n')
                                wf.write(json.dumps(dict(state_id=row['state_id'],route=witness),separators=(',',':'))+'\n')
                print(json.dumps(dict(map_id=params['map_id'],completed_rows=len(ledger)),ensure_ascii=False),flush=True)
        write_json(out/'generation_ledger.json',ledger)
        completion = dict(status='generation_finished_not_benchmark',base_maps=len(maps),
            states=len(ledger),counts=dict(Counter(r['status'] for r in ledger)),
            failure_reasons=dict(Counter(r.get('reason') for r in ledger if r['status']!='generated')),
            seconds=time.perf_counter()-begin,holdout_generated=False,solver_called=False)
        write_json(out/'completion.json',completion)
        sources = [Path(__file__),Path(__file__).with_name('prepare_scale_design_20261014.py')]
        hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
        write_json(out/'sha256.json',dict(artifacts=hashes,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))
        return completion
    except BaseException:
        write_json(out/'aborted.json',dict(status='aborted_input_generation',completed_rows=len(ledger),
            traceback=traceback.format_exc(),solver_called=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--scale',choices=('small','medium','large'))
    args = parser.parse_args()
    print(json.dumps(generate(args.out,args.scale),ensure_ascii=False))
