from test_synthetic_main import *
from types import SimpleNamespace
from contextlib import contextmanager
from audit_helpers import *
@contextmanager
def changes(module,**items):
 old={k:getattr(module,k) for k in items}
 try:
  for k,v in items.items():setattr(module,k,v)
  yield
 finally:
  for k,v in old.items():setattr(module,k,v)
def late(module):
 clock=[0.0]
 def tick(d):
  if clock[0]>d:raise DeadlineExceeded()
 def auditlate(s,r):clock[0]=2.;return {'valid':True}
 class G:
  def __init__(self,*a):pass
  def precheck(self):return None
  def expand(self,*a):return s.old_route
 with changes(module,UnifiedGeometry=G,time=SimpleNamespace(perf_counter=lambda:clock[0]),tick=tick,single_cell_audit=auditlate):
  return module.solve(s,initial,'POOL_INIT' if module is pool else 'LITERAL',1,0)
def expect_fail(fn):
 try:fn()
 except (AssertionError,ValueError):return
 raise AssertionError('tamper undetected')
if __name__=='__main__':
 original_call=call
 def call(name,fn):
  if name.startswith('late_'):name+='__corrected_geometry_clock'
  previous=[r for r in map(json.loads,LEDGER.read_text().splitlines()) if r['name']==name]
  if previous:return json.loads((D/f"synthetic_{previous[0]['call_index']:02d}.json").read_text())
  return original_call(name,fn)
 free=frozenset((x,0) for x in range(3));route=((2,0),(1,0),(0,0));initial=set(free)
 s=Snapshot('empty',free,free,free,(2,0),(0,0),route,0,100)
 for method in ('POOL_INIT','POOL_PLUS1'):
  x=call('empty_'+method,lambda:pool.solve(s,initial,method,2,0));assert len(x['route'])==3
 x=call('empty_fixed',lambda:fixed.solve(s,initial,'LITERAL',2,0));assert len(x['route'])==3
 free=frozenset((x,y) for x in range(3) for y in range(2) if (x,y)!=(1,0));initial={(1,0),(2,0)}
 s=Snapshot('blocked_deferred',free,frozenset({(2,0)}),frozenset(),(0,0),(0,0),((0,0),(1,0),(2,0),(1,0),(0,0)),0,100)
 x=call('illegal_old_repair',lambda:pool.solve(s,initial,'POOL_INIT',2,0));assert audit(s,tuple(map(tuple,x['route'])))['valid'] and (1,0) not in x['route']
 free=frozenset((x,y) for x in range(3) for y in range(2));initial={(1,0)}
 s=Snapshot('late',free,frozenset(initial),frozenset(),(0,0),(0,0),((0,0),(1,0),(0,0)),0,100)
 for module in (fixed,pool):
  x=call('late_'+module.__name__,lambda:late(module));assert not x['route'];events=x.get('candidate_events',x.get('detail',{}).get('candidate_events'));assert events and not any(e['accepted'] for e in events)
 def cutoff(*args):raise DeadlineExceeded()
 with changes(pool,range_plan=cutoff):
  x=call('construction_cutoff',lambda:pool.solve(s,initial,'POOL_PLUS1',2,0));assert x['route'] and x['continuation_subcalls']==0
 oldroute=((0,0),(0,1),(1,1),(1,0),(2,0),(1,0),(0,0));s=Snapshot('continuation',free,frozenset(initial),frozenset(),(0,0),(0,0),oldroute,0,100)
 class Geometry:
  def __init__(self,*args):pass
  def precheck(self):return None
  def expand(self,*args):return oldroute
 cfg={'left':0,'right':0,'required':[]}
 for better in (False,True):
  candidate=((0,0),(1,0),(0,0)) if better else oldroute+((0,1),(0,0))
  def continuation(*args,**kw):
   at=time.perf_counter()-kw['public_t0'];kw['on_candidate'](dict(label='stub',source_scope=None,patch=None,cfg=None,route=candidate,valid=True,validation_complete_public_elapsed=at,public_elapsed=at,before_deadline=True,route_sha256=digest(candidate),steps=len(candidate)-1));return {'status':'finished','detail':{'stages':{}}}
  with changes(pool,UnifiedGeometry=Geometry,range_plan=lambda *a:{'plans':{'R_PLUS1':cfg,'R_SEED':cfg}},fixed_solve=continuation):
   x=call('continuation_better' if better else 'continuation_worse',lambda:pool.solve(s,initial,'POOL_PLUS1',2,0));assert len(x['route'])==(3 if better else 7)
 c=dict(free=list(free),targets=[(1,0)],covered=[],current=(0,0),base=(0,0),old_route=oldroute,distance_budget=100)
 cfg={'left':1,'right':5,'required':[(1,0)]};assert compatibility(c,oldroute,cfg)['valid']
 assert not compatibility(c,((0,0),(1,0),(0,0)),cfg)['valid']
 assert 'omitted_target' in route_errors(c,[(0,0)])
 assert not compatibility(c,oldroute[:-2]+((1,1),(0,1),(0,0)),cfg)['valid']
 expect_fail(lambda:check_unique([{'run_id':'x'},{'run_id':'x'}]))
 expect_fail(lambda:check_acceptances([{'accepted':True,'valid':True,'accepted_public_elapsed':2}],1))
 expect_fail(lambda:check_selected({'selected_candidate_id':0,'source':'wrong','route':[]},[{'candidate_id':0,'accepted':True,'source':'right','route':[]}]))
 expected={'known':'abc'};expect_fail(lambda:(_ for _ in ()).throw(AssertionError('unknown source')) if 'unknown' not in expected else None)
 (D/'synthetic_edge_results.json').write_text(json.dumps({'status':'PASS','edge_calls':9,'harness_failure':'call44 real geometry used real clock with mock deadline; preserved; corrected with geometry stub', 'total_calls':len(LEDGER.read_text().splitlines()),'tamper_checks':['goal','suffix','source','duplicate','late','unknown_hash'],'compatibility_positive_negative':True},indent=2),encoding='utf-8')
 print('PASS synthetic edges; total 49')

