"""PPCPP_CORE4 v0.1: explicit four-neighbor adaptation, NOT full PPCPP.

Own source; frozen v2 geometry/contract/auditor are imported without modifying
them. No future map, online weight optimization, diagonal motion or dynamics.
"""
import math
import time
from pathlib import Path
import portable_frozen
from baseline_suite import check_contract
from model import DeadlineExceeded, NoPath, adjacent
from unified_geometry import UnifiedGeometry, single_cell_audit
from audit import audit

assert Path(portable_frozen.solve.__code__.co_filename).resolve().is_relative_to(portable_frozen.FROZEN/'source')
VERSION='PPCPP_CORE4_v0.1_20261014'


def predator_for(targets, base):
    if not targets:return None
    lo=min(p[0] for p in targets);hi=max(p[0] for p in targets)
    return (lo-1 if 2*base[0]<=lo+hi else hi+1,base[1])


def reward_options(current,previous,pending,free,predator,weights):
    """Pure scoring helper; neighbors are actual uncovered cardinal cells."""
    options=sorted(q for q in adjacent(current) if q in pending and q in free)
    if not options:return []
    ds={q:math.hypot(q[0]-predator[0],q[1]-predator[1]) for q in options}
    lo=min(ds.values());hi=max(ds.values());out=[]
    for q in options:
        rd=(ds[q]-lo)/(hi-lo) if hi>lo else 0.0
        if previous is None:rs=0.0
        else:
            old=(current[0]-previous[0],current[1]-previous[1])
            new=(q[0]-current[0],q[1]-current[1])
            rs=(old[0]*new[0]+old[1]*new[1]+1)/2
        n=sum(z in pending and z in free for z in adjacent(q))
        rb=(4-n)/4
        out.append(dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,
                        score=rd+weights[0]*rs+weights[1]*rb))
    return out


def choose_neighbor(options):
    return min(options,key=lambda row:(-row['score'],row['cell']))['cell']


class Incumbent:
    def __init__(self,snapshot,geometry,begin):
        self.s=snapshot;self.g=geometry;self.begin=begin
        self.route=();self.source=None;self.attempts=[];self.improvements=[]

    def offer(self,route,label):
        self.g.check_time()
        checked=single_cell_audit(self.s,route) if route else dict(valid=False,errors=['empty_route'])
        self.g.check_time()
        elapsed=time.perf_counter()-self.begin
        self.attempts.append(dict(source=label,seconds=elapsed,valid=checked['valid'],
                                  errors=checked['errors'],steps=len(route)-1 if route else None))
        if checked['valid'] and (not self.route or len(route)<len(self.route)):
            self.route=tuple(route);self.source=label
            self.improvements.append(dict(source=label,seconds=elapsed,steps=len(route)-1))
        return checked['valid']


def common_fallback(g,incumbent):
    s=g.s
    incumbent.offer(s.old_route,'old_suffix')
    left=set(s.targets-s.covered);visits=[]
    for p in s.old_route:
        g.check_time()
        if p in left and p in s.free:visits.append(p);left.remove(p)
    visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
    incumbent.offer(g.expand(visits),'common_fallback')


def credit_segment(g,route,pending,segment):
    """Simulate actual traversed cells, not only the requested service endpoint."""
    if not segment or segment[0]!=route[-1]:raise ValueError('segment_start_mismatch')
    fresh=0
    for p in segment[1:]:
        g.check_time()
        route.append(p)
        if p in pending:pending.remove(p);fresh+=1
    return fresh


def core_route(g,weights,detail):
    s=g.s;pending=set(s.targets-s.covered-g.views[s.current]);route=[s.current]
    predator=predator_for(s.targets,s.base)
    detail.update(predator=predator,initial_pending=len(pending),remaining_pending=len(pending),
        local_moves=0,recovery_moves=0,recovery_count=0,recoveries=[],return_moves=0)
    while pending:
        g.check_time();before=len(pending);current=route[-1]
        options=reward_options(current,route[-2] if len(route)>1 else None,pending,s.free,predator,weights)
        if options:
            goal=choose_neighbor(options)
            credit_segment(g,route,pending,(current,goal));detail['local_moves']+=1
        else:
            # The common geometry performs exact BFS distance queries, with
            # its own deadline checks; no input-generator cache is available.
            goal=min(pending,key=lambda p:(g.distance(current,p),p))
            segment=g.path(current,goal)
            fresh=credit_segment(g,route,pending,segment)
            detail['recovery_count']+=1;detail['recovery_moves']+=len(segment)-1
            detail['recoveries'].append(dict(start=current,goal=goal,
                steps=len(segment)-1,fresh=fresh,route_end_index=len(route)-1))
        if len(pending)>=before:raise AssertionError('no_core_progress')
        detail['remaining_pending']=len(pending)
    segment=g.path(route[-1],s.base)
    credit_segment(g,route,pending,segment)
    detail['return_moves']=len(segment)-1
    g.check_time()
    return tuple(route)


def solve(s,initial_targets,budget,seed=0,weights=(1.,1.)):
    begin=time.perf_counter();deadline=begin+budget
    check_contract(s,initial_targets,budget)
    if not math.isfinite(budget):raise ValueError('finite budget required')
    if len(weights)!=2 or any(not math.isfinite(w) or w<0 for w in weights):
        raise ValueError('two finite nonnegative reward weights required')
    detail=dict(version=VERSION,weights=list(weights),seed_used_for_decisions=False,
        core_valid_before_deadline=False,core_route=(),core_status='not_started')
    incumbent=None;status='finished';reason=None
    try:
        g=UnifiedGeometry(s,deadline)
        reason=g.precheck()
        if reason:status='environment_infeasible'
        else:
            incumbent=Incumbent(s,g,begin)
            common_fallback(g,incumbent)
            detail['core_status']='building'
            route=core_route(g,weights,detail)
            # Keep the full core output, even when it does not beat the fallback.
            detail['core_route']=route;detail['core_status']='full_route_constructed'
            valid=incumbent.offer(route,'PPCPP_core4')
            detail['core_valid_before_deadline']=valid
            detail['core_status']='valid_before_deadline' if valid else 'invalid_before_deadline'
            detail['core_steps']=len(route)-1
            if not incumbent.route:status='no_legal_candidate'
    except DeadlineExceeded:
        status='deadline';detail['interruption']='soft_deadline'
        if not detail['core_valid_before_deadline']:detail['core_status']='not_validated_before_deadline'
    except NoPath as exc:
        status='planning_failure';reason=str(exc)
    route=incumbent.route if incumbent else ()
    if incumbent:
        detail.update(candidate_attempts=incumbent.attempts,improvements=incumbent.improvements)
    result=dict(method='PPCPP_CORE4',version=VERSION,seed=seed,budget=budget,status=status,
        reason=reason,route=route,source=incumbent.source if incumbent else None,detail=detail,
        seconds=time.perf_counter()-begin)
    result['fallback_selected']=result['source'] in ('old_suffix','common_fallback')
    result['overrun_gt_10ms']=result['seconds']>budget+.01
    # These audits deliberately occur outside the reported solve time.
    result['independent_audit']=audit(s,route) if route else None
    result['core_independent_audit']=audit(s,detail['core_route']) if detail['core_route'] else None
    if route and not result['independent_audit']['valid']:raise AssertionError('invalid incumbent')
    if detail['core_valid_before_deadline'] and not result['core_independent_audit']['valid']:
        raise AssertionError('invalid core certificate')
    return result
