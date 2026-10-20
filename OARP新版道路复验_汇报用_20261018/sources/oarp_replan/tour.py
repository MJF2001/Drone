"""Path sets, directed start/end GTSP, author-maintained GLNS C++ port.

Costs here are unit movement lengths: explicit UAV scene adaptation, not the
paper's acceleration/angular-velocity transition time model.
"""
from dataclasses import dataclass
import functools
import itertools
import math
import time
import glns


@dataclass(frozen=True)
class OldService:
    rank: object
    start_index: int
    end_index: int


def old_services(route, pending):
    """Recover disjoint straight service runs from actual first-visit history.

    Adapter for P2, which stores no native rank IDs. Not paper initialization.
    """
    from .ranks import Rank
    pending = set(pending)
    records, run, indices, step = [], [], [], None
    def flush():
        nonlocal run, indices, step
        if run:
            axis = 'V' if step and step[1] else 'H'
            canonical = tuple(sorted(run, key=lambda p:p[0] if axis == 'H' else p[1]))
            records.append(OldService(Rank(axis,canonical),indices[0],indices[-1]))
        run, indices, step = [], [], None
    for i,p in enumerate(route):
        if p not in pending:
            flush()
            continue
        if run:
            delta = p[0]-run[-1][0], p[1]-run[-1][1]
            if abs(delta[0])+abs(delta[1]) != 1 or (step is not None and delta != step):
                flush()
            else:
                step = delta
        run.append(p)
        indices.append(i)
        pending.remove(p)
    flush()
    if pending:
        raise ValueError('old route omitted original pending targets')
    return tuple(records)


def path_sets(ranks, services, old_route, free):
    """Retain consecutive unchanged ranks AND their exact legal old connectors."""
    remaining = {r.key:r for r in ranks}
    unchanged = set(remaining) & {s.rank.key for s in services}
    blocks, group = [], []
    def flush():
        nonlocal group
        if group:
            path = tuple(old_route[group[0].start_index:group[-1].end_index+1])
            if not set(path) <= free:
                raise ValueError('retained path packet crosses blocked pose')
            blocks.append({'kind':'path','rank_keys':[s.rank.key for s in group],'path':path})
        group = []
    for service in services:
        if service.rank.key not in unchanged:
            flush()
            continue
        if group:
            connector = old_route[group[-1].end_index:service.start_index+1]
            if not set(connector) <= free:
                flush()
        group.append(service)
        remaining.pop(service.rank.key)
    flush()
    for r in sorted(remaining.values(), key=lambda r:r.key):
        blocks.append({'kind':'rank','rank_keys':[r.key],'path':r.cells})
    used = [key for b in blocks for key in b['rank_keys']]
    if len(used) != len(ranks) or set(used) != {r.key for r in ranks}:
        raise RuntimeError('rank set partition failed')
    return blocks


def gtsp_instance(g, blocks):
    states, sets = [], []
    for block in blocks:
        path = tuple(block['path'])
        states.extend((path,tuple(reversed(path))))
        sets.append([len(states)-2,len(states)-1])
    start, end = len(states), len(states)+1
    states.extend(((g.s.current,),(g.s.base,)))
    sets.extend(([start],[end]))
    n = len(states)
    edges = {}
    for i in range(start+1):
        for j in range(end+1):
            g.check_time()
            if i == j or j == start or (i == start and j == start):
                continue
            # Departing service cost counts every internal edge once per block.
            edges[i,j] = len(states[i])-1+g.distance(states[i][-1],states[j][0])
    penalty = (n+1)*(max(edges.values(),default=0)+1)
    if penalty > 2147483647:
        raise ValueError('GTSP penalty exceeds solver integer range')
    matrix = [[penalty]*n for _ in range(n)]
    for (i,j), value in edges.items():
        matrix[i][j] = value
    matrix[end][start] = 0
    return states, sets, matrix, start, end, penalty


def exact_gtsp(matrix, sets, start, end):
    """Held-Karp with group and orientation states; <=12 service groups."""
    groups = [s for s in sets if s != [start] and s != [end]]
    if len(groups) > 12:
        raise ValueError('exact GTSP limit exceeded')
    @functools.lru_cache(None)
    def visit(mask, last):
        if mask == (1<<len(groups))-1:
            return matrix[last][end], (end,)
        options = []
        for k, group in enumerate(groups):
            if not mask>>k & 1:
                for node in group:
                    cost, tail = visit(mask|1<<k,node)
                    options.append((matrix[last][node]+cost,(node,)+tail))
        return min(options)
    cost, tail = visit(0,start)
    return cost, (start,)+tail


def decode_tour(g, states, sets, matrix, start, end, tour, penalty):
    tour = list(tour)
    if len(tour) != len(sets) or any(sum(v in group for v in tour) != 1 for group in sets):
        raise ValueError('GTSP did not select exactly one state per set')
    index = tour.index(start)
    tour = tour[index:]+tour[:index]
    if tour[-1] != end:
        raise ValueError('GTSP violated directed terminal constraint')
    cost = sum(matrix[a][b] for a,b in zip(tour,tour[1:]+tour[:1]))
    if any(matrix[a][b] >= penalty for a,b in zip(tour,tour[1:]+tour[:1])):
        raise ValueError('GTSP used forbidden edge')
    path = [g.s.current]
    for node in tour[1:]:
        block = states[node]
        path.extend(g.path(path[-1],block[0])[1:])
        path.extend(block[1:])
    if len(path)-1 != cost:
        raise RuntimeError('GTSP cost differs from expanded route')
    return tuple(path), cost, tuple(tour)


def tour_replan(g, blocks, seconds=1, seed=0, exact=False):
    begin = time.perf_counter()
    states,sets,matrix,start,end,penalty = gtsp_instance(g,blocks)
    if exact:
        value,tour = exact_gtsp(matrix,sets,start,end)
        solver_meta = {'backend':'exact-verification','optimal':True}
    else:
        remaining = min(seconds,g.deadline-time.perf_counter())
        if remaining <= 0:
            raise TimeoutError('GTSP preparation exhausted budget')
        solution = glns.solve(matrix,sets,mode='default',seed=seed,max_time=remaining,verbose=0)
        tour, value = solution.tour, solution.cost
        solver_meta = {'backend':'author-glns-cpp-0.1.0','optimal':False,
            'mode':'default','trials':5,'restarts':3,
            'timeout':solution.timeout,'iterations':solution.total_iterations}
    route, decoded, order = decode_tour(g,states,sets,matrix,start,end,tour,penalty)
    if value != decoded:
        raise RuntimeError('solver cost certificate mismatch')
    return {'route':route,'length':decoded,'order':order,'sets':sets,'states':states,
        'matrix':matrix,'solver':solver_meta,'seconds':time.perf_counter()-begin,
        'block_count':len(blocks),'path_set_count':sum(b['kind']=='path' for b in blocks),
        'rank_set_count':sum(b['kind']=='rank' for b in blocks)}
