"""Explicit one-region target-state contract, NOT a replacement CAP solver.

No missing-target heuristic, no autonomous region order/entry/next-target
policy. Those missing restart decisions are intentionally not invented here.
"""
import time,math
from primitives import Metric,tour,components,Deadline,Unreachable

class TargetContractError(ValueError):pass
class ResourceLimit(Exception):pass

class Session:
    def __init__(self,c,budget=5,*,clock=time.perf_counter,hook=None):
        if not math.isfinite(budget) or budget<=0:raise ValueError('budget')
        self.clock=clock;self.deadline=clock()+budget;self.hook=hook
        self.free=set(map(tuple,c['free']));self.targets=set(map(tuple,c['targets']));self.covered=set(map(tuple,c['covered']))
        self.current=tuple(c['current']);self.base=tuple(c['base']);self.published=set(map(tuple,c.get('published_targets',list(self.targets|self.covered))))
        self.distance_budget=c.get('distance_budget',float('inf'))
        if self.current not in self.free or self.base not in self.free or not self.targets<=self.free or not (self.covered|self.targets)<=self.published or math.isnan(self.distance_budget) or self.distance_budget<0:raise ValueError('snapshot')
        self.covered|={self.current}&self.targets;self.pending=self.targets-self.covered
        self.path=[self.current];self.events=[];self.state=None;self.generation=0;self.metric=None
    def check(self,stage):
        if self.hook:self.hook(stage)
        if self.clock()>=self.deadline:raise Deadline(stage)
    def bind_target(self,point,*,source,reference):
        self.check('bind_target');point=tuple(point)
        if self.state is not None and self.state['phase']=='bound':raise TargetContractError('active target cannot silently be overwritten')
        if self.state is not None and source!='explicit_next_transition':raise TargetContractError('next target requires an explicit transition source')
        if point not in self.free:raise TargetContractError('target is not currently free; explicit invalidation/decision required')
        if source not in ('provided_resume_state','declared_restart','explicit_next_transition') or not isinstance(reference,str) or not reference:raise TargetContractError('target provenance required')
        self.generation+=1;self.state=dict(point=point,source=source,reference=reference,generation=self.generation,phase='bound')
        self.events.append(dict(type='bind',state=dict(self.state)))
    def snapshot(self,status,**extra):
        return dict(status=status,current=self.current,path=list(self.path),covered=sorted(self.covered),pending=sorted(self.pending),deferred=sorted(self.published-self.free-self.covered),
            target_state=dict(self.state) if self.state else None,events=list(self.events),global_complete=False,benchmark_eligible=False,
            scope='Explicit caller target/entry, ONE known region only; no automatic restart or next-region policy',**extra)
    def _execute(self,waypoints,mode):
        if self.metric is None:self.metric=Metric(self.free,self.check)
        for goal in waypoints:
            for p in self.metric.path(self.current,tuple(goal))[1:]:
                self.check('move_before')
                if len(self.path)>self.distance_budget:raise ResourceLimit()
                old=self.current;self.current=p;self.path.append(p)
                credit=[p] if p in self.pending else []
                self.pending.discard(p)
                if credit:self.covered.add(p)
                self.events.append(dict(type='move',mode=mode,start=old,end=p,credited=credit,target_generation=self.state['generation']))
                self.check('move_after')
    def enter_region(self,explicit_path):
        if self.state is None:return self.snapshot('missing_resume_target')
        if self.state['phase']!='bound':return self.snapshot('next_target_transition_required')
        path=list(map(tuple,explicit_path))
        if not path or path[0]!=self.current or not set(path)<=self.free or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(path,path[1:])):raise TargetContractError('entry must be an explicit legal four-neighbour path')
        token=dict(self.state)
        # Execute EXACT caller-supplied path, not shortest-path substitution.
        try:
            for p in path[1:]:self._execute([p],'entry')
        except Deadline:return self.snapshot('deadline')
        except ResourceLimit:return self.snapshot('resource_exceeded')
        assert self.state==token
        return self.snapshot('entry_completed')
    def cover_region(self,selected_area):
        if self.state is None:return self.snapshot('missing_resume_target')
        if self.state['phase']!='bound':return self.snapshot('next_target_transition_required')
        area=set(map(tuple,selected_area))
        if not area<=self.targets:raise TargetContractError('region must be a declared acquisition area')
        if self.current not in area:return self.snapshot('entry_contract_required')
        try:
            self.check('region_contract');required=area&self.pending
            if not required:return self.snapshot('region_already_covered')
            pieces=components(required,self.check)
            if len(pieces)>1:return self.snapshot('partition_update_required',parts=[sorted(p) for p in pieces])
            if self.metric is None:self.metric=Metric(self.free,self.check)
            endpoint=self.state['point'];token=dict(self.state)
            order,info=tour(sorted(required),self.current,lambda p:p,self.metric,endpoint)
            self.events.append(dict(type='local_plan',required=sorted(required),start=self.current,end=endpoint,order=order,tsp=info,target_state=dict(token),path_index=len(self.path)-1))
            self._execute(order[1:],'local')
            assert not (required&self.pending) and self.current==endpoint and self.state==token
            self.check('region_complete');self.state['phase']='reached'
            self.events.append(dict(type='target_reached',generation=self.generation,point=endpoint,path_index=len(self.path)-1))
            return self.snapshot('region_complete_transition_required',region_complete=True)
        except Deadline:return self.snapshot('deadline',region_complete=False)
        except ResourceLimit:return self.snapshot('resource_exceeded',region_complete=False)
        except Unreachable:return self.snapshot('unreachable_interface',region_complete=False)
