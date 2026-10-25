"""Task/lap obligation adaptation of C*: history enters planning, not occupancy."""
import time,math
from history_core.planner import CStar,WallClockCap
from history_core.rcg import RCG
from history_core.public_map import PublicMap,lap_points
from common_geometry import GridMetric,NoPath
class TaskGraph(RCG):
    def __init__(self,known):super().__init__(known);self.task_protected=set()
    def prune(self,current):
        if hasattr(self,'before_prune'):self.before_prune()
        return super().prune(current)
class HistoryCStar(CStar):
    def __init__(self,start,known,targets,covered,**kw):
        self.targets=set(targets);self.covered=set(covered);self.pending=self.targets-self.covered-{tuple(start)}
        self.task_events=[];self.task_filters=[]
        super().__init__(start,known,graph_factory=TaskGraph,**kw)
        self.graph.before_prune=self.sync_task_protection
        self.sync_task_protection()
    def needed(self,p):
        if p in self.pending:return True
        return any(q[0]==p[0] and set(lap_points(p,q))&self.pending for q in self.graph.edges[p])
    def sync_task_protection(self):
        # Acquisition anchors and transit anchors are different obligations.
        # Protect existing RCG paths only; never create occupancy-grid shortcuts.
        acquisition={p for p in self.graph.nodes if self.needed(p)}
        transit=set()
        component=set(next((s for s in self.graph.components() if self.current in s),[]))
        for p in sorted(acquisition&component):
            route,_=self.graph.path(self.current,p);transit.update(route)
        self.acquisition_anchors=acquisition;self.transit_anchors=transit-acquisition
        self.graph.task_protected=acquisition|transit
        for p,n in self.graph.nodes.items():n.tasked=p in self.covered
    def refresh_retreat(self,a=None,b=None):
        super().refresh_retreat(a,b);self.retreat={p for p in self.retreat if self.needed(p)}
    def navigate(self,route,mode):
        before=len(self.path);pending_before=set(self.pending);n=super().navigate(route,mode)
        traversed=self.path[before:];self.covered.update(set(traversed)&self.targets);self.pending-=set(traversed)
        self.task_events.append(dict(mode=mode,start_index=before-1,end_index=len(self.path)-1,credited=sorted(pending_before-self.pending),pending_after=sorted(self.pending)))
        self.task_events[-1]['rcg_route']=[list(p) for p in route]
        self.sync_task_protection();self.refresh_retreat();return n
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
        holes=super().detect_holes(goal)
        if holes and not any(self.needed(p) for p in holes):return set()
        return holes
    def run(self,max_iterations=400):
        super().run(max_iterations)
        if self.status=='graph_exhausted':self.status='task_complete' if not self.pending else 'task_incomplete'
        return self
def solve(c,budget=2,seed=0,*,clock=time.perf_counter,max_iterations=400):
    begin=clock();deadline=begin+budget
    free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']));start=tuple(c['current']);base=tuple(c['base'])
    if not targets<=free or start not in free or base not in free:raise ValueError('invalid active map')
    if not math.isfinite(budget) or budget<=0:raise ValueError('budget')
    published=set(map(tuple,c.get('published_targets',list(targets|covered))))
    if not covered<=published:raise ValueError('history outside published ledger')
    if not targets<=published:raise ValueError('active target outside published ledger')
    if set(map(tuple,c.get('known_blocked',[])))&free:raise ValueError('conflicting occupancy')
    known=PublicMap();known.update({p:True for p in free})
    known.update({p:False for p in published-free})
    # No made-up sensing history or outside obstacle ring. Explicit known blocked
    # cells, when supplied, belong to the current public input for every method.
    known.update({tuple(p):False for p in c.get('known_blocked',[])})
    planner=HistoryCStar(start,known,targets,covered,seed=seed,deadline=deadline,wall_clock=clock)
    planner.run(max_iterations);diagnostic=list(planner.path);route=[];status=planner.status
    if status=='task_complete':
        if clock()>=deadline:status='deadline'
        else:
            try:
                diagnostic.extend(GridMetric(free).path(diagnostic[-1],base)[1:])
                if clock()>=deadline:status='deadline'
                elif len(diagnostic)-1>c['distance_budget']:status='resource_exceeded'
                elif not targets<=covered|set(diagnostic):status='coverage_incomplete'
                elif any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(diagnostic,diagnostic[1:])):status='illegal_route'
                elif clock()>=deadline:status='deadline'
                else:route=diagnostic
            except (ValueError,NoPath):status='return_unreachable'
    return dict(route=route,diagnostic_route=diagnostic,status=status,seconds=clock()-begin,pending=sorted(planner.pending),
        task_events=planner.task_events,task_filters=planner.task_filters,iterations=planner.iterations_trace,
        rcg_nodes=sorted(planner.graph.nodes),rcg_edges=planner.graph.snapshot()['edges'],
        events=planner.events,graph_status=planner.status,graph_error=planner.error,
        graph_counts=dict(added=planner.graph.total_added,pruned=planner.graph.total_pruned,links=planner.graph.link_count,tsp=planner.graph.tsp_count),
        historical_nodes=[p for p in planner.graph.nodes if p in covered],completion_tsp=False,
        open_graph_nodes=sum(planner.graph.is_open(p) for p in planner.graph.nodes),
        termination_trigger=planner.iterations_trace[-1]['why']['group'] if planner.iterations_trace else None,
        adaptation='v0.2 acquisition plus existing-RCG transit obligations; not original C* completeness or global completion.')
