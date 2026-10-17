"""Three scene-adapted baselines. No historical implementation is modified."""
import time
import oarp_replan
from model import DeadlineExceeded,NoPath
from unified_geometry import UnifiedGeometry,single_cell_audit
from p2_search_audit import solve as p2_solve
from unified_candidates import solve_candidate
from oarp_replan.ranks import rank_replan
from oarp_replan.tour import old_services,path_sets,tour_replan
from oarp_replan.budget import cap_for_time
from audit import audit

METHODS=('P2_MULTI','OARP_CORE2','TREE_MST')

def check_contract(s,initial_targets,budget):
    if s.radius!=0:raise ValueError('one-cell downward footprint required')
    if budget<=0:raise ValueError('positive soft budget required')
    if not s.targets<=s.free:raise ValueError('blocked targets must be deferred before planning')
    if not s.current in s.free or not s.base in s.free:raise ValueError('start/base outside free map')
    if not s.covered<=set(initial_targets):raise ValueError('covered history must belong to initial published targets')

def oarp_solve(s,initial_targets,seconds,profile,seed):
    begin=time.perf_counter();deadline=begin+seconds;best=None;source=None;detail={};g=None
    def offer(route,label):
        nonlocal best,source
        g.check_time();valid=route and single_cell_audit(s,route)['valid'];g.check_time()
        if valid and (best is None or len(route)<len(best)):
            best=tuple(route);source=label
            detail.setdefault('improvements',[]).append(dict(seconds=time.perf_counter()-begin,steps=len(route)-1,source=label))
    try:
        g=UnifiedGeometry(s,deadline)
        reason=g.precheck()
        if reason:return dict(route=(),source=None,status='environment_infeasible',reason=reason,seconds=time.perf_counter()-begin,detail=detail)
        offer(s.old_route,'old_suffix')
        left=set(s.targets-s.covered);visits=[]
        for p in s.old_route:
            if p in left and p in s.free:visits.append(p);left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        offer(g.expand(visits),'common_fallback')
        pending=s.targets-s.covered-g.views[s.current]
        if not pending:return dict(route=best or (),source=source,status='finished',seconds=time.perf_counter()-begin,detail=detail)
        # Old route describes pre-event targets, including cells newly blocked by the event.
        # Keep these old ranks as change references; only current pending cells are serviced.
        service=old_services(s.old_route,set(initial_targets)-set(s.covered)-g.views[s.current])
        old=tuple(z.rank for z in service)
        cap=cap_for_time(profile,max(0,deadline-time.perf_counter()-.01))
        detail.update(old_rank_count=len(old),rank_cap=cap,cap_source='frozen_empirical_common_geometry',variant=2)
        if cap is None:raise TimeoutError('insufficient calibrated TOUR budget')
        ranked=rank_replan(pending,old,cap,2,deadline)
        detail['rank']={k:v for k,v in ranked.items() if k!='ranks'}
        if ranked['ranks'] is not None:
            blocks=path_sets(ranked['ranks'],service,s.old_route,s.free)
            g.check_time()
            result=tour_replan(g,blocks,seconds=max(.001,deadline-time.perf_counter()-.01),seed=seed)
            offer(result['route'],'RANK_and_TOUR')
            detail['tour']={k:v for k,v in result.items() if k not in ('route','matrix','states')}
            detail['ranks']=[dict(axis=r.axis,cells=r.cells) for r in ranked['ranks']]
            detail['blocks']=blocks
        else:detail['core_no_solution']=ranked['status']
        status='finished'
    except (DeadlineExceeded,TimeoutError) as exc:
        status='deadline';detail['interruption']=str(exc)
    except NoPath as exc:
        status='planning_failure';detail['interruption']=str(exc)
    return dict(route=best or (),source=source,status=status,seconds=time.perf_counter()-begin,detail=detail)

def solve(s,initial_targets,method,budget,seed,profile):
    begin=time.perf_counter()
    check_contract(s,initial_targets,budget)
    if method not in METHODS:raise ValueError(method)
    remaining=budget-(time.perf_counter()-begin)
    if remaining<=0:r=dict(route=(),source=None,status='deadline',seconds=time.perf_counter()-begin)
    elif method=='P2_MULTI':
        try:r=p2_solve(s,remaining,'multi',seed)
        except ValueError as exc:
            if str(exc)!='infeasible input':raise
            r=dict(route=(),source=None,status='environment_infeasible',reason=str(exc),seconds=None)
    elif method=='TREE_MST':r=solve_candidate(s,'TREE_MST',remaining,seed)
    else:r=oarp_solve(s,initial_targets,remaining,profile,seed)
    r['seconds']=time.perf_counter()-begin
    r['method']=method;r['budget']=budget;r['seed']=seed
    r['independent_audit']=audit(s,tuple(map(tuple,r['route']))) if r['route'] else None
    if r['route'] and not r['independent_audit']['valid']:raise AssertionError((method,r['independent_audit']))
    r['fallback_selected']=r.get('source') in ('old_suffix','common_fallback','common_old_suffix','common_GD_adapter')
    r['overrun_gt_10ms']=r.get('seconds') is not None and r['seconds']>budget+.01
    # External audit is excluded from reported solver seconds for all methods.
    return r
