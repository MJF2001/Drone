"""Task/lap obligation adaptation of C*: history enters planning, not occupancy."""
import time,math
from history_core.planner import CStar,WallClockCap
from history_core.rcg import RCG
from history_core.public_map import PublicMap,lap_points
from common_geometry import GridMetric,NoPath
from equivalent_tsp import equivalent_cover_holes
from diagonal_geometry import DiagonalMetric,length,legal_step
class TaskPublicMap(PublicMap):
    """F remains physical flight geometry; S is the frozen initial task residual.

    Service boundaries are NOT obstacles. F-boundary samples remain a closed
    transit skeleton. No outside occupancy or future event is fabricated.
    """
    knowledge_scope='closed_current_task_domain'
    def __init__(self,service):
        super().__init__();self.service=frozenset(service)
    def frontier(self,p):
        service_boundary=p in self.service and any((p[0]+dx,p[1]+dy) not in self.service for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
        return super().frontier(p) or service_boundary
    def unknown_adjacent(self,p):
        # All CURRENT task/flight cells are public. Domain exterior is not an
        # unknown coverage obligation and is not inserted as physical blocking.
        return False
class TaskGraph(RCG):
    def __init__(self,known):super().__init__(known);self.task_protected=set()
    def prune(self,current):
        if hasattr(self,'before_prune'):self.before_prune()
        owner=getattr(self,'audit_owner',None)
        record=dict(current=current,pending=sorted(owner.pending),protected=sorted(self.task_protected),before=self.snapshot(),status='interrupted') if owner else None
        if owner:owner.prune_audits.append(record)
        try:
            result=super().prune(current)
            if record is not None:record['status']='completed'
            return result
        finally:
            if record is not None:record['after']=self.snapshot()
class HistoryCStar(CStar):
    def __init__(self,start,known,targets,covered,**kw):
        self.targets=set(targets);self.covered=set(covered);self.pending=self.targets-self.covered-{tuple(start)}
        self.service=frozenset(self.pending)
        self.task_events=[];self.task_filters=[];self.prune_audits=[]
        self._protection_cache=None
        self.protection_cache_stats=dict(requests=0,hits=0,rebuilds=0,search_attempts=0)
        super().__init__(start,known,graph_factory=TaskGraph,**kw)
        self.graph.before_prune=self.sync_task_protection
        self.graph.audit_owner=self
        self.sync_task_protection()
    def metric(self):
        if self._metric is None or self._metric_version!=self.map.version:
            self._metric=DiagonalMetric(self.map.free,checkpoint=self._check_deadline);self._metric_version=self.map.version
        return self._metric
    def needed(self,p):
        if p in self.pending:return True
        if p not in self.service:return False
        # Another endpoint's pending status alone does not give a transit-only
        # endpoint an acquisition obligation. Interior lap tasks still count.
        return any(q[0]==p[0] and (set(lap_points(p,q))-{q})&self.pending for q in self.graph.edges[p])
    def close_transit_states(self):
        for p,n in self.graph.nodes.items():
            self._check_deadline('service_state')
            if p not in self.service or not self.needed(p):n.state='Cl'
    def sync_task_protection(self):
        # Acquisition anchors and transit anchors are different obligations.
        # Protect existing RCG paths only; never create occupancy-grid shortcuts.
        self.protection_cache_stats['requests']+=1
        self._check_deadline('task_protection')
        self.close_transit_states()
        # Exact structural identity, not a lossy hash or assumed revision counter.
        # States/kinds/reasons do not affect needed(), components(), or RCG.path.
        # Include dictionary order and edge weights conservatively. Update node
        # display metadata even on hits, since node objects may be replaced.
        key=(self.current,self.map.version,tuple(self.map.cells.items()),frozenset(self.pending),frozenset(self.covered),
             tuple((p,tuple(self.graph.edges[p].items())) for p in self.graph.nodes))
        self._check_deadline('task_protection')
        if self._protection_cache is not None and self._protection_cache[0]==key:
            acquisition,transit,protected=self._protection_cache[1]
            self.acquisition_anchors=set(acquisition);self.transit_anchors=set(transit)
            self.graph.task_protected=set(protected)
            for p,n in self.graph.nodes.items():n.tasked=p in self.covered
            self.protection_cache_stats['hits']+=1
            return
        self.protection_cache_stats['rebuilds']+=1
        acquisition={p for p in self.graph.nodes if self.needed(p)}
        transit=set()
        component=set(next((s for s in self.graph.components() if self.current in s),[]))
        for p in sorted(acquisition&component):
            self._check_deadline('task_protection')
            self.protection_cache_stats['search_attempts']+=1
            route,_=self.graph.path(self.current,p);transit.update(route)
        self.acquisition_anchors=acquisition;self.transit_anchors=transit-acquisition
        self.graph.task_protected=acquisition|transit
        for p,n in self.graph.nodes.items():n.tasked=p in self.covered
        self._protection_cache=(key,(frozenset(self.acquisition_anchors),frozenset(self.transit_anchors),frozenset(self.graph.task_protected)))
    def refresh_retreat(self,a=None,b=None):
        super().refresh_retreat(a,b);self.retreat={p for p in self.retreat if self.needed(p)}
    def navigate(self,route,mode):
        before=len(self.path);pending_before=set(self.pending);completed=False
        try:
            n=super().navigate(route,mode);completed=True
        finally:
            # Even an interrupted diagnostic prefix must have an honest ledger.
            traversed=self.path[before:];self.covered.update(set(traversed)&self.targets);self.pending-=set(traversed)
            self.task_events.append(dict(mode=mode,start_index=before-1,end_index=len(self.path)-1,credited=sorted(pending_before-self.pending),pending_after=sorted(self.pending),rcg_route=[list(p) for p in route],interrupted=not completed))
        if getattr(self,"_fixed_tour",False):self.close_transit_states()
        else:self.sync_task_protection()
        self.refresh_retreat();return n
    def select_goal(self):
        self.sync_task_protection();p=self.current
        original=sorted(q for q in self.graph.edges[p] if self.graph.is_open(q))
        opened=[q for q in original if self.needed(q)]
        self.task_filters.append(dict(current=p,original=original,eligible=opened,pending=sorted(self.pending)))
        if not self.pending:return None,None,False,dict(group='task_complete',options=[],chosen=None)
        groups=[('left',[q for q in opened if q[0]<p[0]]),('up',[q for q in opened if q[0]==p[0] and q[1]>p[1]]),('down',[q for q in opened if q[0]==p[0] and q[1]<p[1]]),('right',[q for q in opened if q[0]>p[0]])]
        for name,qs in groups:
            if qs:
                goal=self.rng.choice(qs);return goal,[p,goal],False,dict(group=name,options=qs,chosen=goal)
        self.refresh_retreat();candidates=sorted(self.retreat-{p})
        if candidates:
            paths=[self.graph.path(p,q) for q in candidates];path,cost=min(paths,key=lambda v:(v[1],v[0][-1]))
            return path[-1],path,True,dict(group='retreat',options=candidates,chosen=path[-1],rcg_path_cost=cost)
        # Existing direct acquisition and C* retreat retain priority. If neither
        # applies, traverse ONE existing RCG edge toward an explicit service
        # action. Closed/covered nodes remain traversable. This is a disclosed
        # task-transit adaptation, not a global target-completion pass.
        actions=[]
        component=set(next((s for s in self.graph.components() if p in s),[]))
        for a in sorted(self.acquisition_anchors&component):
            self._check_deadline()
            approach,cost=self.graph.path(p,a)
            if a in self.pending and len(approach)>1:
                actions.append((cost,tuple(approach),'node',a,a))
            for b in sorted(self.graph.edges[a]):
                if a[0]==b[0] and set(lap_points(a,b))&self.pending:
                    actions.append((cost+abs(a[1]-b[1]),tuple(approach+[b]),'lap',a,b))
        if actions:
            cost,full,kind,a,b=min(actions)
            goal=full[1]
            return goal,[p,goal],True,dict(group='task_transit',options=[goal],chosen=goal,
                rcg_service_route=full,service_kind=kind,service_edge=[a,b],rcg_service_cost=cost)
        return None,None,False,dict(group='no_task_representative',options=[],chosen=None,pending=sorted(self.pending))
    def detect_holes(self,goal):
        # Preserve the original open-component connectivity test. Only components
        # carrying real pending work can demand an Algorithm-3 service tour.
        self.close_transit_states()
        holes=super().detect_holes(goal)
        if holes and not any(self.needed(p) for p in holes):return set()
        return holes
    def densify(self,holes,goal):
        # Native Algorithm-3 densification, restricted to outstanding service
        # cells. Non-target flight cells remain usable graph transit, not TSP
        # visit requirements. Current and goal retain their interface roles.
        points=set(holes)|{self.current,goal};additions=set()
        for p in sorted(points):
            self._check_deadline('densify')
            for q in self.graph.edges[p]:
                if p[0]==q[0] and q in points:additions.update(set(lap_points(p,q))&self.pending)
        new=additions-set(self.graph.nodes)
        for p in sorted(new):self.graph.insert(p,'tsp')
        self.graph.expand(new)
        return points|additions
    cover_holes=equivalent_cover_holes
    def run(self,max_iterations=400):
        super().run(max_iterations)
        if self.status=='graph_exhausted':self.status='task_complete' if not self.pending else 'task_incomplete'
        return self
def solve(c,budget=2,seed=0,*,clock=time.perf_counter,max_iterations=400,checkpoint_hook=None):
    begin=clock();deadline=begin+budget
    free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']));start=tuple(c['current']);base=tuple(c['base'])
    if not targets<=free or start not in free or base not in free:raise ValueError('invalid active map')
    if not math.isfinite(budget) or budget<=0:raise ValueError('budget')
    published=set(map(tuple,c.get('published_targets',list(targets|covered))))
    if not covered<=published:raise ValueError('history outside published ledger')
    if not targets<=published:raise ValueError('active target outside published ledger')
    if set(map(tuple,c.get('known_blocked',[])))&free:raise ValueError('conflicting occupancy')
    known=TaskPublicMap(targets-covered-{start});known.update({p:True for p in free})
    known.update({p:False for p in published-free})
    # No made-up sensing history or outside obstacle ring. Explicit known blocked
    # cells, when supplied, belong to the current public input for every method.
    known.update({tuple(p):False for p in c.get('known_blocked',[])})
    planner=HistoryCStar.__new__(HistoryCStar)
    try:
        planner.__init__(start,known,targets,covered,seed=seed,deadline=deadline,wall_clock=clock,checkpoint_hook=checkpoint_hook)
        planner.run(max_iterations)
    except WallClockCap as exc:
        planner.status='wall_clock_cap';planner.error=str(exc)
    diagnostic=list(planner.path);route=[];status=planner.status
    if status=='task_complete':
        if clock()>=deadline:status='deadline'
        else:
            try:
                planner._check_deadline('return_before')
                diagnostic.extend(DiagonalMetric(free,checkpoint=planner._check_deadline).path(diagnostic[-1],base)[1:])
                planner._check_deadline('final_audit')
                if clock()>=deadline:status='deadline'
                elif length(diagnostic)>c['distance_budget']+1e-9:status='resource_exceeded'
                elif not targets<=covered|set(diagnostic):status='coverage_incomplete'
                elif any(not legal_step(a,b,free) for a,b in zip(diagnostic,diagnostic[1:])):status='illegal_route'
                elif clock()>=deadline:status='deadline'
                else:route=diagnostic
            except (ValueError,NoPath):status='return_unreachable'
            except WallClockCap as exc:status='deadline';planner.error=str(exc)
    result=dict(route=route,diagnostic_route=diagnostic,status=status,pending=sorted(planner.pending),
        task_events=planner.task_events,task_filters=planner.task_filters,iterations=planner.iterations_trace,
        rcg_nodes=sorted(planner.graph.nodes),rcg_edges=planner.graph.snapshot()['edges'],
        events=planner.events,graph_status=planner.status,graph_error=planner.error,
        graph_counts=dict(added=planner.graph.total_added,pruned=planner.graph.total_pruned,links=planner.graph.link_count,tsp=planner.graph.tsp_count),
        historical_nodes=[p for p in planner.graph.nodes if p in covered],completion_tsp=False,
        open_graph_nodes=sum(planner.graph.is_open(p) for p in planner.graph.nodes),
        termination_trigger=planner.iterations_trace[-1]['why']['group'] if planner.iterations_trace else None,
        prune_audits=planner.prune_audits,
        adaptation='DIAGNOSTIC motion change only from v0.7: native diagonal RCG execution and 8-neighbour return; weighted distance, no extra coverage at corner-touch cells; not common-budget algorithm ranking.',
        efficiency_stats=getattr(planner,'efficiency_stats',[]),
        version='CSTAR_DIAGONAL_SENSITIVITY_v0.1',motion_model='8-neighbour no-corner-cut, cardinal1 diagonal_sqrt2; landed cells only',route_distance=length(route) if route else None,diagnostic_distance=length(diagnostic),knowledge_scope=known.knowledge_scope,initial_service=sorted(known.service),
        protection_cache=planner.protection_cache_stats)
    try:planner._check_deadline('result_ready')
    except WallClockCap as exc:
        if result['status'] not in ('wall_clock_cap','deadline'):result.update(route=[],route_distance=None,status='deadline',graph_error=str(exc))
    end=clock();result['seconds']=end-begin
    if end>=deadline:result['route']=[];result['route_distance']=None;result['status']='wall_clock_cap' if result['status']=='wall_clock_cap' else 'deadline'
    return result
