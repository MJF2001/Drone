from region_common import *
from collections import Counter
from copy import deepcopy
import ast,traceback
import region_audit as A
from fixtures import active,unchecked,memory_variant
AUDIT_COUNTS=Counter()
def observe(frame,event,arg):
 if frame.f_code.co_filename==A.__file__ and frame.f_code.co_name=='distances':
  if event=='call':AUDIT_COUNTS['BFS_calls']+=1
  elif event=='return' and isinstance(arg,dict):AUDIT_COUNTS['BFS_nodes_returned']+=len(arg)
def checked(c,r):
 sys.setprofile(observe)
 try:return A.audit(c,r,True)
 finally:sys.setprofile(None)
def refuses(c,r):
 try:checked(c,r)
 except (AssertionError,KeyError,TypeError,ValueError):return
 raise AssertionError('tampered evidence accepted')
def main():
 assert not (H/'entry_log.jsonl').exists();guard();spec=read(H/'regression_cases.json');assert len(spec)==16;results=[]
 saved=read(OLD/'outputs/formal__G1-A__ON.json');basec=saved['input'];baser=saved['native']['raw'];start=time.perf_counter()
 for item in spec:
  t=time.perf_counter();row=dict(item,passed=False);before=dict(AUDIT_COUNTS)
  try:
   n=item['id']
   if n==1:
    calls=[]
    def profile(f,e,a):
     if e=='call' and f.f_code.co_name in ('solve','core_route','process'):calls.append(f.f_code.co_filename)
    sys.setprofile(profile)
    try:b=bindings()
    finally:sys.setprofile(None)
    assert not calls and b['B'].identity()['primary']['file']!=b['B'].identity()['independent']['file']
    assert Path(b['native'].__file__).parent==H and Path(A.__file__).parent==H
    for x in read(H/'immutable_bindings.json'):assert sha(H/x['copy'])==sha(OLD/x['old'])==x['sha256']
    for f in ('setup.py','regression.py','review_old.py','run.py','worker.py'):assert "__name__=='__main__'" in (H/f).read_text(encoding='utf-8')
    runtime=read(H/'runtime_guards.json');freeze=read(H/'active_freeze.json')
    for p,v in loaded_sources().items():
     pp=Path(p)
     if pp.is_relative_to(ROOT/'运行环境'):continue
     assert runtime.get(p)==v or (pp.is_relative_to(H) and freeze.get(str(pp.relative_to(H)))==v),('unbound',p)
   elif n==2:row['audit']=checked(deepcopy(basec),deepcopy(baser))
   elif n==3:
    c=memory_variant(basec);r=memory_variant(baser);assert type(r['rule']['check']['q0']) is tuple;row['audit']=checked(c,r)
   elif n==4:
    c=deepcopy(basec);r=memory_variant(baser);r['rule']['check']['Q']=tuple(r['rule']['check']['Q']);r['route']=baser['route'];r['rule']['check']['representatives']=deepcopy(baser['rule']['check']['representatives']);row['audit']=checked(c,r)
   elif n==5:
    c,r=unchecked();row['audit']=checked(c,r)
   elif n==6:
    records=[]
    for mode in ('memory','list','mixed'):
     c,r=active()
     if mode=='list':c=norm(c);r=norm(r)
     if mode=='mixed':r['rule']['transitions']=tuple(r['rule']['transitions']);r['rule']['release_pending']=[(2,0)];r['rule']['check']['Q']=norm(r['rule']['check']['Q'])
     records.append(checked(c,r))
    assert len({json.dumps(A.coordinate_form(r['transitions']),sort_keys=True) for r in records})==1;row['audits']=records
   elif n==7:
    c,r=active();r['rule'].update(phase='CANCELLED',release_pending=None,transitions=[dict(index=0,phase='OTHER',Q_S=1,Q_other=2),dict(index=1,phase='CANCELLED',Q_S=0,Q_other=2)])
    A.validate_schema(c,r,True);assert A.coordinate_form(r['rule'])==A.coordinate_form(norm(r['rule']))
    row['scope']='schema/representation only, not executable planner cancellation evidence'
   elif n==8:
    c,r=active();r['rule']['check']['q0']=(6,0);refuses(c,r)
    c,r=active();r['rule']['check']['representatives']['R']=(7,0);refuses(c,r)
   elif n==9:
    c,r=active();r['trace'][0]['Q']=[(2,0),(6,0)];refuses(c,r)
    c,r=active();r['trace'][0]['allowed'].append((2,0));refuses(c,r)
   elif n==10:
    c,r=active();r['trace'][0]['phase']='TAIL';refuses(c,r)
    c,r=active();r['rule']['transitions'][1]['index']=2;refuses(c,r)
    c,r=active();r['rule']['transitions'].reverse();refuses(c,r)
   elif n==11:
    c,r=active();r['trace'][1]['original_options'][0]['score']+=1;refuses(c,r)
    c,r=active();r['trace'][1]['options'][0]['boundary_reward']=0.;refuses(c,r)
    # options aliases in handmade evidence mean the independent original row is
    # checked too; append a bogus option tests complete option cardinality.
    c,r=active();r['trace'][1]['options'].append(dict(r['trace'][1]['options'][0],cell=(8,0)));refuses(c,r)
   elif n==12:
    c,r=active();del r['rule']['check']['reason'];refuses(c,r)
    c,r=active();del r['trace'][0]['goal'];refuses(c,r)
   elif n==13:
    c,r=active();r['rule']['check']['q0']=(2,0,0);refuses(c,r)
    c,r=active();r['route'][0]=(True,0);refuses(c,r)
    c,r=active();r['rule']['transitions'][0]['Q_S']=True;refuses(c,r)
   elif n==14:
    c,r=active();r['rule']['checked']=1;refuses(c,r)
    c,r=active();r['rule']['check']=None;refuses(c,r)
    c,r=unchecked();r['rule']['check']={};refuses(c,r)
    assert A.coordinate_form(True)!=A.coordinate_form(1) and A.coordinate_form(None)!=A.coordinate_form(0)
   elif n==15:
    c,r=active();r['rule']['check']['extra']='discard me';refuses(c,r)
    c,r=active();r['rule']['check']['Q'].reverse();refuses(c,r)
    c,r=active();r['route'].reverse();refuses(c,r)
    assert A.coordinate_form([(1,0),(2,0)])!=A.coordinate_form([(2,0),(1,0)])
   elif n==16:
    for d in ('regression/worker','regression/parent'):
     (H/d).mkdir(exist_ok=True);dump(H/d/'same_basename.json',{'scope':d})
    assert read(H/'regression/worker/same_basename.json')!=read(H/'regression/parent/same_basename.json')
    try:dump(H/'regression/worker/same_basename.json',{})
    except FileExistsError:pass
    else:raise AssertionError('exclusive create failed')
    zeros={'real_core':0,'real_post':0,'unobserved_queries':None};assert zeros['real_core']==zeros['real_post']==0 and zeros['unobserved_queries'] is None
   row['passed']=True
  except BaseException as e:row.update(failure=repr(e),traceback=traceback.format_exc())
  row['seconds']=time.perf_counter()-t;row['observed_main_external_BFS_calls']=AUDIT_COUNTS['BFS_calls']-before.get('BFS_calls',0);results.append(row);dump(H/'regression'/(str(n).zfill(2)+'.json'),row);print('TYPE',n,row['passed'],row.get('failure',''),flush=True)
  if not row['passed']:break
 result=dict(passed=len(results)==16 and all(r['passed'] for r in results),fixed_cases=len(spec),executed_cases=len(results),real_core=0,real_post=0,audit_profile_outside_main=True,main_external_synthetic_BFS=dict(AUDIT_COUNTS),route_generation=0,representation_variants_not_lost_memory_restoration=True,seconds=time.perf_counter()-start)
 dump(H/'regression_receipt.json',result);return result['passed']
if __name__=='__main__':raise SystemExit(0 if main() else 1)
