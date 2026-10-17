"""OARP-Replan equations (7)-(36), SCIP LP, explicit integer fallback.

Neighbour differences implement the paper's directed-incidence inequalities.
H/V singleton matching arcs are distinct, removing notation ambiguity.
"""
from dataclasses import dataclass, asdict
import itertools
import math
import time
from pyscipopt import Model, quicksum


@dataclass(frozen=True)
class Rank:
    axis: str
    cells: tuple

    @property
    def key(self):
        return self.axis, self.cells[0], self.cells[-1]


def partition(cells, directions):
    cells = set(cells)
    if set(directions) != cells or any(v not in ('H', 'V') for v in directions.values()):
        raise ValueError('orientation must assign every target exactly once')
    out = []
    for p in sorted(cells):
        axis = directions[p]
        dx, dy = (1, 0) if axis == 'H' else (0, 1)
        previous = p[0]-dx, p[1]-dy
        if directions.get(previous) == axis:
            continue
        q, run = p, []
        while directions.get(q) == axis:
            run.append(q)
            q = q[0]+dx, q[1]+dy
        out.append(Rank(axis, tuple(run)))
    return tuple(out)


def endpoint_set(ranks):
    return {(r.axis, side, p) for r in ranks for side,p in
        (('L', r.cells[0]), ('R', r.cells[-1]))}


def metrics(ranks, old, directions):
    old_keys = {r.key for r in old}
    now, previous = endpoint_set(ranks), endpoint_set(old)
    # Removed/blocked old endpoints are outside the new model and not counted.
    previous = {e for e in previous if e[2] in directions}
    alpha = len(now-previous)
    beta = sum(directions[p] == axis for axis, side, p in previous-now)
    return {'rank_count': len(ranks), 'new_rank_count': sum(r.key not in old_keys for r in ranks),
        'added_endpoints': alpha, 'extended_endpoints': beta,
        'endpoint_bound': alpha+beta/2}


def enumerate_oracle(cells, old=(), cap=None, variant=1):
    """Independent orientation enumeration; tiny-instance verifier, NOT solver."""
    points = sorted(cells)
    if len(points) > 16:
        raise ValueError('oracle only supports <=16 cells')
    cap = len(points) if cap is None else cap
    best = None
    for bits in itertools.product(('H','V'), repeat=len(points)):
        dirs = dict(zip(points, bits))
        ranks = partition(points, dirs)
        m = metrics(ranks, old, dirs)
        counted = m['new_rank_count'] if variant == 1 else m['endpoint_bound']
        if counted <= cap:
            value = m['rank_count']+counted/(cap+1)
            if best is None or value < best['objective']-1e-9:
                best = {'objective': value, 'metrics': m, 'ranks': ranks}
    return best


def _build(cells, old, cap, variant, integer, deadline):
    model = Model('OARP-RANK-'+str(variant))
    model.hideOutput()
    model.setIntParam('parallel/maxnthreads', 1)
    kind = 'B' if integer else 'C'
    points = sorted(cells)
    orientation, endpoint = {}, {}
    for p in points:
        for axis in ('H','V'):
            orientation[axis,p] = model.addVar(vtype=kind, lb=0, ub=1)
            for side in ('L','R'):
                endpoint[axis,side,p] = model.addVar(vtype=kind, lb=0, ub=1)
        model.addCons(orientation['H',p]+orientation['V',p] == 1)
    for p in points:
        for axis, step in (('H',(1,0)),('V',(0,1))):
            for side, sign in (('L',-1),('R',1)):
                neighbour = p[0]+sign*step[0], p[1]+sign*step[1]
                source = orientation.get((axis,neighbour), 0)
                model.addCons(endpoint[axis,side,p] >= orientation[axis,p]-source)
    previous = endpoint_set(old)
    if variant in (0,1):
        if variant == 0:
            changed = 0
        else:
            old_keys, matches = {r.key for r in old}, {}
            incoming, outgoing = {}, {}
            for axis, step in (('H',(1,0)),('V',(0,1))):
                for p in points:
                    if time.perf_counter() > deadline:
                        raise TimeoutError('rank model construction')
                    q = p
                    while q in cells:
                        z = model.addVar(vtype=kind, lb=0, ub=1)
                        matches[axis,p,q] = z
                        outgoing.setdefault((axis,p),[]).append(z)
                        incoming.setdefault((axis,q),[]).append(z)
                        q = q[0]+step[0], q[1]+step[1]
            for axis in ('H','V'):
                for p in points:
                    model.addCons(quicksum(outgoing[axis,p]) == endpoint[axis,'L',p])
                    model.addCons(quicksum(incoming[axis,p]) == endpoint[axis,'R',p])
            changed = quicksum(z for key,z in matches.items() if key not in old_keys)
    elif variant == 2:
        added = quicksum(v for key,v in endpoint.items() if key not in previous)
        extensions = []
        for key, y in endpoint.items():
            axis, side, p = key
            beta = model.addVar(vtype=kind, lb=0, ub=1)
            model.addCons(beta >= (1-y if key in previous else 0)+orientation[axis,p]-1)
            extensions.append(beta)
        changed = added+quicksum(extensions)/2
    else:
        raise ValueError('variant must be 0,1,2')
    count = quicksum(endpoint.values())/2
    if variant:
        model.addCons(changed <= cap)
    model.setObjective(count+changed/(cap+1), 'minimize')
    return model, orientation, endpoint


def rank_replan(cells, old=(), cap=None, variant=1, deadline=math.inf, integer_fallback=True):
    begin = time.perf_counter()
    cells = frozenset(cells)
    cap = len(cells) if cap is None else int(cap)
    if cap < 0:
        raise ValueError('negative rank budget')
    if not cells:
        return {'status':'optimal', 'ranks':(), 'objective':0, 'fractional_lp':False,
            'used_integer_fallback':False, 'metrics':metrics((),old,{}), 'seconds':0}
    fractional = False
    attempts = []
    for integer in (False, True) if integer_fallback else (False,):
        if time.perf_counter() >= deadline:
            return {'status':'timeout','ranks':None,'attempts':attempts}
        model, orient, endpoints = _build(cells, old, cap, variant, integer, deadline)
        model.setRealParam('limits/time', min(1e6, max(.001,deadline-time.perf_counter())))
        model.optimize()
        status = str(model.getStatus())
        attempts.append({'mode':'MIP' if integer else 'LP','status':status,
            'variables':model.getNVars(),'constraints':model.getNConss()})
        if model.getNSols() == 0:
            return {'status':status,'ranks':None,'attempts':attempts}
        sol = model.getBestSol()
        values = [model.getSolVal(sol,v) for v in model.getVars()]
        integral = all(abs(v-round(v)) <= 1e-6 for v in values)
        if not integral:
            fractional = True
            if integer:
                raise RuntimeError('MIP solution not integral')
            continue
        dirs = {p:'H' if model.getSolVal(sol,orient['H',p]) > .5 else 'V' for p in cells}
        ranks = partition(cells,dirs)
        m = metrics(ranks,old,dirs)
        counted = m['new_rank_count'] if variant == 1 else m['endpoint_bound'] if variant == 2 else 0
        expected = m['rank_count']+counted/(cap+1)
        value = model.getSolObjVal(sol)
        if (variant and counted > cap+1e-6) or abs(expected-value) > 1e-5:
            raise RuntimeError(('decoded partition differs from model',variant,expected,value,m))
        if variant == 2 and m['new_rank_count'] > m['endpoint_bound']+1e-6:
            raise RuntimeError('new-rank bound violated')
        return {'status':status,'ranks':ranks,'objective':value,'metrics':m,
            'fractional_lp':fractional,'used_integer_fallback':integer,'attempts':attempts,
            'seconds':time.perf_counter()-begin}
    return {'status':'fractional_lp','ranks':None,'fractional_lp':True,'attempts':attempts}
