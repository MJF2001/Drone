"""Explicit current-position, unit-step UAV adaptation of the two-stage core.

Not a reproduction of the paper's concurrent robot dynamics/encounter framework.
"""
import time
from model import Geometry, DeadlineExceeded, NoPath
from .ranks import rank_replan
from .tour import old_services, path_sets, tour_replan
from .budget import cap_for_time


def solve_core(snapshot, initial_targets, variant=1, seconds=5, profile=None,
               cap_override=None, seed=0):
    if snapshot.radius != 0:
        raise ValueError('adapter requires single-cell coverage')
    begin, best, best_source = time.perf_counter(), None, None
    deadline = begin+seconds
    detail = {'variant':variant,'cost_model':'unit-step','original_encounter_framework':False}
    g = None
    def offer(route, source):
        nonlocal best,best_source
        if not route or route[0] != snapshot.current or route[-1] != snapshot.base:
            return
        if not set(route) <= snapshot.free or len(route)-1 > snapshot.distance_budget:
            return
        if not snapshot.targets <= snapshot.covered | set(route):
            return
        if any(abs(a[0]-b[0])+abs(a[1]-b[1]) != 1 for a,b in zip(route,route[1:])):
            return
        if time.perf_counter() > deadline:
            return
        if best is None or len(route) < len(best):
            best,best_source = route,source
    try:
        g = Geometry(snapshot,deadline)
        reason = g.precheck()
        if reason:
            return {'status':'environment_infeasible','reason':reason,'route':(),
                'seconds':time.perf_counter()-begin,'detail':detail}
        offer(snapshot.old_route,'unchanged_old_suffix')
        pending = snapshot.targets-snapshot.covered
        # Greedy detour fallback: old service order, then new targets in H snake.
        # It is an explicit adapter fallback, not an author-provided GD implementation.
        visits = []
        left = set(pending)
        for p in snapshot.old_route:
            if p in left and p in snapshot.free:
                visits.append(p)
                left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2 == 0 else -p[0])))
        offer(g.expand(visits),'GD_adapter_fallback')
        detail['fallback_seconds'] = time.perf_counter()-begin
        service = old_services(snapshot.old_route,set(initial_targets)-set(snapshot.covered))
        old = tuple(s.rank for s in service)
        if cap_override is not None:
            cap = cap_override
        elif profile is not None:
            cap = cap_for_time(profile,max(0,deadline-time.perf_counter()))
        else:
            cap = 2*len(pending)
        detail.update({'old_rank_count':len(old),'rank_cap':cap,
                       'cap_source':'override' if cap_override is not None else 'empirical' if profile else 'unbounded'})
        if cap is None:
            raise TimeoutError('insufficient predicted TOUR budget')
        ranked = rank_replan(pending,old,cap,variant,deadline)
        detail['rank'] = {k:v for k,v in ranked.items() if k != 'ranks'}
        if ranked['ranks'] is not None:
            blocks = path_sets(ranked['ranks'],service,snapshot.old_route,snapshot.free)
            planned = tour_replan(g,blocks,seconds=max(.001,deadline-time.perf_counter()),seed=seed)
            offer(planned['route'],'RANK_and_TOUR')
            detail['tour'] = {k:v for k,v in planned.items() if k not in ('route','matrix','states')}
            detail['ranks'] = [{'axis':r.axis,'cells':r.cells} for r in ranked['ranks']]
            detail['blocks'] = blocks
        else:
            detail['core_no_solution'] = ranked['status']
    except (DeadlineExceeded,TimeoutError) as exc:
        detail['interruption'] = str(exc) or 'deadline'
    except NoPath as exc:
        detail['interruption'] = str(exc)
    elapsed = time.perf_counter()-begin
    return {'status':'planned' if best is not None else 'planning_failure','route':best or (),
        'seconds':elapsed,'reason':'' if best is not None else 'no_budget_feasible_incumbent',
        'source':best_source,'overrun_seconds':max(0,elapsed-seconds),
        'deadline_overrun':elapsed > seconds+.01,'detail':detail,
        'searches':g.searches if g else 0}
