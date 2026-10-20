"""Equal-soft-budget engineering candidates. TREE is NOT TRACE or STC."""
from collections import deque
import time
import oarp_replan
from oarp_replan.ranks import partition
from oarp_replan.tour import tour_replan
from model import Geometry, DeadlineExceeded, NoPath, adjacent
from planners import rebuild, two_opt
from unified_geometry import UnifiedGeometry, single_cell_audit as audit


def metric_tree(g):
    """Prim MST of pending-cell terminals, edge weights free-map BFS distance."""
    vertices = set(g.s.targets-g.s.covered)|{g.s.current}
    remaining = vertices-{g.s.current}
    best = {p:(float('inf'),None) for p in remaining}
    children = {p:[] for p in vertices}
    current = g.s.current
    edges = []
    while remaining:
        g.check_time()
        for p in sorted(remaining):
            candidate = g.distance(current,p),current
            if candidate < best[p]:
                best[p]=candidate
        current = min(remaining,key=lambda p:(best[p],p))
        cost,parent = best[current]
        children[parent].append((cost,current))
        edges.append((parent,current,cost))
        remaining.remove(current)
    return children,edges


def preorder(children,root,reverse=False):
    visits=[]
    stack=[root]
    while stack:
        p=stack.pop()
        visits.append(p)
        ordered=sorted(children[p],reverse=reverse)
        stack.extend(q for _,q in reversed(ordered))
    return visits


def solve_candidate(s,algorithm,seconds=5,seed=0,geometry_class=UnifiedGeometry,final_audit=True):
    begin=time.perf_counter()
    deadline=begin+seconds
    best=None
    source=None
    detail={}
    g=None
    def offer(route,label):
        nonlocal best,source
        g.check_time()
        valid=route and audit(s,route)['valid']
        g.check_time()
        if valid and (best is None or len(route)<len(best)):
            best,source=tuple(route),label
            detail.setdefault('improvements',[]).append({'elapsed':time.perf_counter()-begin,
                'steps':len(route)-1,'source':label})
    try:
        if s.radius!=0:
            raise ValueError('single-cell model required')
        g=geometry_class(s,deadline)
        reason=g.precheck()
        if reason:
            return {'algorithm':algorithm,'status':'environment_infeasible','reason':reason,'route':(),
                'seconds':time.perf_counter()-begin,'source':None,'detail':detail,'audit':None}
        offer(s.old_route,'common_old_suffix')
        left=set(s.targets-s.covered)
        visits=[]
        for p in s.old_route:
            if p in left and p in s.free:
                visits.append(p)
                left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        offer(g.expand(visits),'common_GD_adapter')
        detail['common_length']=len(best)-1 if best else None
        if algorithm=='P2_SHARED':
            rebuild(g,lambda route:offer(route,'P2_search'))
        elif algorithm=='STRIP_HV':
            for index,axis in enumerate(('H','V')):
                ranks=partition(s.targets-s.covered,{p:axis for p in s.targets-s.covered})
                blocks=[{'kind':'rank','path':r.cells} for r in ranks]
                # All preparation and postprocessing share one total deadline.
                remain=deadline-time.perf_counter()
                allowance=max(.001,(remain-.05)/(2-index))
                result=tour_replan(g,blocks,seconds=allowance,seed=seed)
                offer(result['route'],axis+'_full')
                points=[p for node in result['order'][1:-1] for p in result['states'][node]]
                offer(g.expand(points),axis+'_skip')
                detail[axis]={'ranks':len(ranks),'full_length':result['length'],'solver':result['solver']}
        elif algorithm=='TREE_MST':
            children,edges=metric_tree(g)
            detail['tree_edges']=edges
            orders=[]
            for reverse in (False,True):
                order=preorder(children,s.current,reverse)
                orders.append(order)
                offer(g.expand(order),'MST_preorder_'+str(reverse))
            # Explicit local search, not part of TRACE or a novel tree method.
            for order in orders:
                offer(g.expand(two_opt(g,order)),'MST_preorder_2opt')
        else:
            raise ValueError(algorithm)
        status='planned' if best else 'planning_failure'
    except (DeadlineExceeded,TimeoutError):
        status='planned_at_timeout' if best else 'timeout'
    except NoPath as exc:
        status='planning_failure'
        detail['error']=str(exc)
    elapsed=time.perf_counter()-begin
    return {'algorithm':algorithm,'status':status,'route':best or (),
        'seconds':elapsed,'overrun_gt_10ms':elapsed>seconds+.01,'source':source,
        'detail':detail,'audit':audit(s,best) if best and final_audit else None}
