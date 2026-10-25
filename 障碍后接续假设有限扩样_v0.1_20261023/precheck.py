from common import *
import ast,traceback,inspect,difflib
from types import SimpleNamespace
from collections import Counter
from expand_hook import Diagnostic,select
from analysis_metrics import shared_C,witness,independent_sign
def precheck():
 assert not (H/'entry_log.jsonl').exists(),'no technical tests after real start'
 rounds=sorted(H.glob('prechecks_round*.json'));assert len(rounds)<3;roundno=len(rounds)+1;records=[];calls=[]
 def watch(frame,event,arg):
  if event=='call' and frame.f_code.co_name in ('solve','core_route','process','legal','bfs','reachable','core_path'):calls.append(dict(name=frame.f_code.co_name,file=frame.f_code.co_filename))
 sys.setprofile(watch)
 try:
  b=bindings()
  base=dict(name='pure',phase='history_prepare',free=[[0,0],[1,0],[2,0],[0,2]],targets=[[2,0],[0,2]],published_targets=[[2,0],[0,2]],initial_targets=[[2,0],[0,2]],covered=[],deferred_targets=[],current=[0,0],base=[0,0],previous=None,predator=[-2,0],old_route=[],distance_budget=10000)
  for name in ('P1','P2','P3','P4','P5','P6'):
   try:
    details={}
    if name=='P1':
     phase_validate(base,b['validate']);bad=norm(base);bad['covered']=[[0,0]]
     rejected=0
     for c in (bad,dict(base,phase='event_response'),dict(base,phase='unknown')):
      try:phase_validate(c,b['validate'])
      except (AssertionError,ValueError):rejected+=1
     good=dict(base,phase='event_response',current=[2,0],previous=[1,0],covered=[[2,0]])
     phase_validate(good,b['validate']);assert rejected==3
     details=dict(phase_accepts=2,phase_rejections=3,history_H_still_empty=not base['covered'])
    elif name=='P2':
     p={(2,0),(0,2)};a,t=select(p,(2,0),[[2,0],[0,2],[0,2]])
     assert a==(0,2) and t['q0_is_first_pending_in_old_order'] and t['q0_old_rank']==0 and t['q1_old_rank']==1
     assert select(p,(2,0),[[2,0]])[0] is None
     a,t=select(p,(2,0),[[0,2],[2,0]]);assert a==(0,2) and t['identity_class']=='alternative_precedes_default'
     a,t=select(p,(2,0),[[0,2]]);assert t['identity_class']=='default_not_in_old_order'
     assert select({(2,0)},(2,0),[[0,2]])[0] is None
     details=dict(order_fixture_checks=5,selector_parameters=list(inspect.signature(select).parameters))
    elif name=='P3':
     qs=Counter();p={(2,0),(0,2)}
     def distance(a,z):qs['stub_distance']+=1;return abs(a[0]-z[0])+abs(a[1]-z[1])
     g=SimpleNamespace(s=SimpleNamespace(free=p),reachable=p,distance=distance)
     for enabled in (False,True):
      d=Diagnostic([[2,0],[0,2]],enabled);assert d.choose([],[(0,0)],(0,0),None,p,(2,0),g)==((0,2) if enabled else (2,0))
      assert d.choose([{}],[(0,0)],(0,0),None,p,(2,0),g)==(2,0)
      assert d.counts['matched']==1 and d.counts['applied']==int(enabled)
     d=Diagnostic([[2,0]],True);assert d.choose([],[(0,0)],(0,0),None,p,(2,0),g)==(2,0)
     assert d.choose([{}],[(0,0)],(0,0),None,p,(0,2),g)==(0,2) and d.counts['applied']==0
     details=dict(stub_distance_queries=qs['stub_distance'],second_changes=0,no_candidate_moves_to_later_trigger=False)
    elif name=='P4':
     q=(1,0);path=[(0,0),(-1,0),(-1,1),(0,1),(1,1),(1,0)];w,edges=witness(path,0,q);assert w['segments'][0]['length']==4 and len(edges)==4
     assert len({0,1,2,3}|{2,3,4})==5
     path2=[(0,0),(1,0),(2,0),(1,0),(0,0)];C=shared_C(path2,0,{(1,0),(2,0)})
     assert C['C']==2 and C['identity_total']==4 and shared_C(path2,0,{(1,0),(2,0)})==C
     assert shared_C(path2,0,set()) is None
     E=b['exact'].Expr;z=E.sqrt(2)-E.number(2);sg,proof=independent_sign(z.save());assert sg==z.sign()==-1 and independent_sign(E().save())[0]==0
     details=dict(W=4,union_W=5,same_path_different_goal_labels_C_gain=0,C_identity=C,radical_sign_independent=sg)
    elif name=='P5':
     p=H/'logs'/('pure_owner_round'+str(roundno))
     with p.open('x',encoding='utf-8') as f:f.write('one')
     rejected=False
     try:
      with p.open('x'):pass
     except FileExistsError:rejected=True
     assert rejected and sha(H/'root_before.md')==sha(ROOT/'当前进度与下一步.md')
     assert read(H/'plan.json')['cap_core']==42 and read(H/'plan.json')['post_candidate_cap']==4096
     assert norm({'native_detail':None,'unknown':None})=={'native_detail':None,'unknown':None}
     text=(H/'worker.py').read_text(encoding='utf-8');assert text.index("entry(job,'core')")<text.index('.solve(') and text.index("entry(job,'post')")<text.index("b['engine'].process")
     details=dict(binary_copy=True,exclusive_rejection=True,null_preserved=True,entry_before_dispatch=True)
    else:
     for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
     assert sha(H/'expand_native.py')==sha(H/'source_snapshot/recovery_diag_native.py')
     assert 'goal=min(pending,key=lambda q:(g.distance(cur,q),q))' in (H/'expand_native.py').read_text(encoding='utf-8')
     from center_bench_v01_20261022.audit import _post_saved
     # Original functions support arbitrary legal starting H; only old workers
     # asserted S in H. This check is static, with no post or credit queries.
     for fn in (b['engine'].process,b['metrics'].evaluate,b['B'].audit_result,_post_saved.audit_one):
      src=inspect.getsource(fn);assert "assert tuple(c['current']) in" not in src
     details=dict(native_byte_identical_to_accepted_hooked_core=True,credit_identities=b['B'].identity(),post_and_audit_phase_check='static plus phase accept/reject fixtures, not a real post acceptance')
    records.append(dict(id=name,passed=True,details=details))
   except BaseException as ex:
    records.append(dict(id=name,passed=False,reason=repr(ex),traceback=traceback.format_exc()));break
 finally:sys.setprofile(None)
 result=dict(round=roundno,passed=len(records)==6 and all(z['passed'] for z in records) and not calls,cases=records,forbidden_real_call_observations=calls,real_core_calls=0,real_post_calls=0,real_geometry_queries=0,real_BFS=0,repairs_used=roundno-1)
 dump(H/('prechecks_round'+str(roundno)+'.json'),result)
 print(json.dumps({'passed':result['passed'],'identities':len(records),'round':roundno,'last':records[-1] if not result['passed'] else None},ensure_ascii=False),flush=True)
 if result['passed']:
  dump(H/'prechecks.json',result);guards=read(H/'source_guards.json');guards.update(loaded_sources());guards={p:v for p,v in guards.items() if not Path(p).is_relative_to(H)};dump(H/'runtime_guards.json',{p:v for p,v in loaded_sources().items() if not Path(p).is_relative_to(H)})
  dump(H/'source_guards.json',guards)
 return result['passed']
if __name__=='__main__':raise SystemExit(0 if precheck() else 1)
