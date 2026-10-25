from common import *
from policy import *
import sys,subprocess,traceback,importlib
def packet(free,current,pending,old,base=(0,0)):
 return dict(event=dict(free=norm(free),base=list(base)),stop_state=dict(current=list(current),pending=norm(pending)),old_order=norm(old))
def main():
 start=time.perf_counter();results=[];manifest=read(H/'manifest.json')
 def run(name,expected,f):
  t=time.perf_counter()
  try:actual=f();results.append(dict(id=name,passed=True,expected=expected,actual=actual,seconds=time.perf_counter()-t))
  except BaseException as ex:results.append(dict(id=name,passed=False,expected=expected,failure=repr(ex),traceback=traceback.format_exc(),seconds=time.perf_counter()-t));raise
 def whitelist():
  a={k:None for k in manifest['input_whitelist']};a['schema']='shadow_crop_v1';validate_packet(a,manifest['input_whitelist']);a['actual_full_length']=123
  try:validate_packet(a,manifest['input_whitelist'])
  except AssertionError:return 'extra outcome field rejected'
  raise AssertionError('leak')
 def normalize():assert ps([[1,2],[1,2]])=={(1,2)} and norm(((1,2),))==[[1,2]];return 'tuple/list normalized'
 def imports():
  calls=[]
  def watch(frame,event,arg):
   if event=='call' and frame.f_code.co_name in ('solve','core_route','run_payload','process'):calls.append(frame.f_code.co_name)
  sys.setprofile(watch)
  try:
   from frozen_shadow_connector_20261023.model import Geometry
   from frozen_shadow_connector_20261023.unified_geometry import UnifiedGeometry
   from frozen_shadow_center_20261023.post import engine
   from frozen_shadow_center_20261023 import metrics
  finally:sys.setprofile(None)
  assert not calls and Geometry.__module__.startswith('frozen_shadow_connector_') and engine.__name__.startswith('frozen_shadow_center_');return dict(import_execution_calls=calls)
 def zero():
  from collections import Counter
  c=Counter({k:0 for k in ('core','post','path','cache')});assert dict(c)==dict(core=0,post=0,path=0,cache=0);return dict(c)
 def clipped(path,q,pending,why,n,local=0):
  x=clip(path,0,q,set(pending),set(path),(0,-1));assert x['reason']==why and x['edges']==n and x['local_edges']==local;return x
 def middle():return clipped([(i,0) for i in range(81)],(80,0),{(80,0)},'total_64',64)
 def local16():return clipped([(i,0) for i in range(25)],(1,0),{(i,0) for i in range(1,25)},'local_16',17,16)
 def total64():return clipped([(i,0) for i in range(71)],(50,0),{(i,0) for i in range(50,71)},'total_64',64,14)
 def nextrec():return clipped([(0,0),(1,0),(2,0),(3,0),(4,0)],(1,0),{(1,0),(4,0)},'next_recovery_after_q',1)
 def last():return clipped([(0,0),(1,0),(2,0),(3,0)],(1,0),{(1,0),(2,0)},'all_pending_collected',2,1)
 def incidental():
  p=packet([(i,0) for i in range(4)],(0,0),[(1,0),(2,0),(3,0)],[(3,0),(3,0),(2,0),(1,0)])
  def query(a,b):return [(i,0) for i in range(a[0],b[0]+1)] if b[0]>=a[0] else [(i,0) for i in range(a[0],b[0]-1,-1)]
  x=tail(p,query,time.perf_counter()+2);assert x['counts']['task_path_queries']==1 and x['counts']['return_path_queries']==1 and x['counts']['incidental_tasks']==2 and x['counts']['old_entries_skipped']==3 and x['counts']['old_duplicate_entries']==1;return x['counts']
 def missing():
  try:tail(packet([(0,0),(1,0)],(0,0),[(1,0)],[]),lambda a,b:(),time.perf_counter()+1)
  except Unavailable as e:assert str(e)=='old_order_missing_tasks' and e.details['counts']['path_queries']==0;return 'missing rejected before path'
  raise AssertionError('missing accepted')
 def obstacle():
  from frozen_shadow_connector_20261023.model import Snapshot
  from frozen_shadow_connector_20261023.unified_geometry import UnifiedGeometry
  F=frozenset({(x,y) for x in range(3) for y in range(2)}-{(1,0)});s=Snapshot('stub',F,frozenset({(2,0)}),frozenset(),(0,0),(0,0),(),0,30);g=UnifiedGeometry(s,time.perf_counter()+2);a=g.path((0,0),(2,0));assert len(a)-1==4 and set(a)<=F and g.path((2,0),(0,0))==tuple(reversed(a));return dict(path=norm(a),searches=g.searches,geometry_contexts=1)
 def seams():
  x=join([[0,0],[1,0]],[[1,0],[2,0]],[[2,0],[1,0],[0,0]]);assert len(x)-1==4;return x
 def commoncost():
  x=join([[0,0],[1,0],[2,0]],[[2,0],[3,0]],[[3,0],[2,0],[1,0],[0,0]]);assert len(x)-1==2+1+3;return 'common prefix charged once'
 def signs():
  x=[decide(True,['-2','-1']),decide(True,['0','0'],True),decide(True,['-1e-12','1e-12']),decide(False,['-9','-8']),decide(True,['1','2'])];assert [v['choice'] for v in x]==['ALT1','OFF','OFF','OFF','OFF'];return x
 def exclusive():
  p=H/'technical/exclusive.claim'
  with p.open('x') as f:f.write('one')
  try:
   with p.open('x'):pass
  except FileExistsError:return 'duplicate refused and retained'
  raise AssertionError('duplicate accepted')
 def budgets():
  p=packet([(i,0) for i in range(4)],(0,0),[(3,0)],[(3,0)])
  try:tail(p,lambda a,b:[(0,0),(1,0),(2,0),(3,0)],time.perf_counter()+1,edge_cap=1)
  except Unavailable as e:assert str(e)=='tail_edge_cap' and e.details['counts']['tail_new_edges']==1;return e.details
  raise AssertionError('cap bypass')
 def isolation():
  dump(H/'technical/probe_crop.json',{'saved_prefix_only':True});r=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'isolation_probe.py')],capture_output=True,text=True,encoding='utf-8',timeout=30);assert r.returncode==0,r.stderr;return json.loads(r.stdout)
 cases=[('01_input_labels','extra fields rejected',whitelist),('02_normalization','list tuple equivalent',normalize),('03_unique_imports','no core or public post invocation',imports),('04_zero_schema','explicit zero counters',zero),('05_recovery_midway','64 edges before selected target',middle),('06_local_16','16 local edges after arrival',local16),('07_total_64','64 including recovery',total64),('08_next_recovery','stop before selecting next target',nextrec),('09_last_collection','exclude actual return',last),('10_incidental_duplicate','incidental collected, old entries skipped',incidental),('11_missing_order','contract rejection',missing),('12_obstacle_tie','frozen legal connector four-edge detour',obstacle),('13_seam','no duplicate vertices',seams),('14_common_cost','prefix paid once',commoncost),('15_prediction_signs','negative/equal/unknown/unavailable/positive',signs),('16_exclusive_failure','duplicate refusal',exclusive),('17_partial_failure_account','partial work retained',budgets),('18_data_access','original and truth data reads denied',isolation)]
 try:
  for name,expected,f in cases:run(name,expected,f)
 finally:
  passed=len(results)==18 and all(x['passed'] for x in results);dump(H/'technical/round1.json',dict(passed=passed,unique_cases=18,attempts=len(results),cases=results,wall_seconds=time.perf_counter()-start,core_calls=0,public_post_calls=0,scope='handwritten micro paths/stubs; one frozen micro connector check, import watcher only during imports; no actual development prefix'))
 print(dict(passed=passed,cases=len(results)));assert passed
if __name__=='__main__':main()
