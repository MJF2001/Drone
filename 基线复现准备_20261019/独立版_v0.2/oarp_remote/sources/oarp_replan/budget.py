"""Empirical cubic TOUR runtime estimate; explicitly NOT a real-time guarantee."""
import math
import time
import numpy as np
from model import Snapshot, Geometry
from .tour import tour_replan


def calibrate():
    records = []
    # Benchmark 2m+1 groups to account conservatively for new-rank + old-packet sets.
    for m in (0,1,2,4,8,16,32,64):
        for repeat in range(3):
            rng = np.random.default_rng(701+repeat+10*m)
            points = [tuple(map(int,p)) for p in rng.integers(1,40,size=(2*m+1,2))]
            free = frozenset((x,y) for x in range(41) for y in range(41))
            s = Snapshot('runtime-calibration',free,frozenset(points),frozenset(),
                         (0,0),(0,0),(),radius=0)
            g = Geometry(s)
            blocks = [{'kind':'rank','path':(p,),'rank_keys':[]} for p in points]
            begin = time.perf_counter()
            r = tour_replan(g,blocks,seconds=15,seed=repeat)
            elapsed = time.perf_counter()-begin
            records.append({'new_rank_budget':m,'groups':len(blocks),'seconds':elapsed,
                'censored':r['solver'].get('timeout',False)})
    uncensored = [r for r in records if not r['censored']]
    if len(uncensored) < 4:
        raise RuntimeError('insufficient uncensored runtime calibration')
    x = np.array([[1,r['new_rank_budget'],r['new_rank_budget']**2,r['new_rank_budget']**3]
                  for r in uncensored],dtype=float)
    coefficients = np.linalg.lstsq(x,np.array([r['seconds'] for r in uncensored]),rcond=None)[0]
    max_m = max(r['new_rank_budget'] for r in uncensored)
    envelope, previous = [], .001
    for m in range(max_m+1):
        fitted = sum(float(c)*m**k for k,c in enumerate(coefficients))
        observed = max((r['seconds'] for r in records if r['new_rank_budget'] <= m),default=0)
        previous = max(previous,fitted,observed)
        envelope.append(1.5*previous+.001)
    return {'records':records,'coefficients_ascending':coefficients.tolist(),
        'monotone_seconds':envelope,'maximum_calibrated_cap':max_m,
        'mapping':'2m+1 service sets; 1.5x monotone upper envelope plus 1ms',
        'caveat':'Synthetic grid calibration, not paper constants or worst-case bound; Geometry preprocessing excluded.'}


def cap_for_time(profile, seconds):
    feasible = [i for i,t in enumerate(profile['monotone_seconds']) if t <= seconds]
    return max(feasible) if feasible else None
