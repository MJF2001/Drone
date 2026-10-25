from common import *
from collections import Counter
from types import SimpleNamespace
import ast,inspect,traceback
from expand_hook import select,Diagnostic
from variant_qualify import signature,rebuild_done,choose_cut,changed_fields
from analysis_metrics import shared_C,witness,independent_sign
def precheck():
 assert not (H/'entry_log.jsonl').exists();roundno=len(list(H.glob('prechecks_round*.json')))+1;assert roundno<=3
 start=time.perf_counter();records=[];calls=[]
 def watch(frame,event,arg):
  if event=='call' and frame.f_code.co_name in ('solve','core_route','process','legal','bfs','reachable','slab'):calls.append(dict(function=frame.f_code.co_name,file=frame.f_code.co_filename))
 sys.setprofile(watch)
 try:
  b=bindings();plan=read(H/'plan.json');sources=read(H/'source_bindings.json')
  for name in ('P1','P2','P3','P4','P5','P6'):
   details={}
   try:
    if name=='P1':
     for src in sources:
      hist=read(src['history_output']);k=src['fixed_global_edge'];e=hist['post']['edges'][k];assert [e['a'],e['b']]==src['edge_vertices'] and [e['left'],e['right']]==src['source_interval'];assert hist['independent']['passed'] and hist['decision_audit']['passed']
     for f in ('expand_native.py','expand_hook.py','decision_audit.py','analysis_metrics.py','worker.py'):assert sha(H/f)==sha(H/'source_snapshot'/('previous_'+f))
     details=dict(source_global_edge_bindings=3,byte_identical_implementations=5)
    elif name=='P2':
     src=sources[0];old=read(src['old_input']);hist=read(src['history_output']);FN=ps(hist['input']['free']);P=ps(old['published_targets']);HH=ps(old['covered']);b0=tuple(src['old_obstacle']);U=P-HH
     newb=next(p for p in sorted(FN-U-{tuple(old['current']),tuple(old['base']),tuple(old['previous']),b0}))
     new=dict(old,free=norm(sorted(FN-{newb})),targets=norm(sorted(P&(FN-{newb}))))
     assert ps(new['covered'])==HH and ps(new['targets'])-HH==U and set(changed_fields(old,new))<={'free','targets'} and b0 in ps(new['free'])
     phase_validate(new,b['validate']);details=dict(A_changes_only_obstacle_and_derived_targets=True,U_and_H_preserved=True)
    elif name=='P3':
     counts=Counter();n=0
     for src in sources:
      hist=read(src['history_output']);P=ps(hist['input']['published_targets']);done=rebuild_done(hist,counts)
      for spec in (s for s in plan['slots'] if s['origin']==src['id'] and s['kind']=='B'):
       t=(spec['progress_percent']*len(P)+99)//100;j=choose_cut(hist['post']['vertices'],done,P,t)
       if j is not None:
        assert len(done[j])>=t and tuple(hist['post']['vertices'][j]) in done[j]
        i=hist['post']['edges'][j-1]['right'];assert hist['native']['raw']['route'][i]==hist['post']['vertices'][j]
       n+=1
     details=dict(B_fixed_thresholds_checked=n,saved_credit_reconstruction=dict(counts),not_a_geometry_or_BFS_check=True)
    elif name=='P4':
     src=sources[0];c=read(src['old_input']);old=src['old_registry']['old_order'];assert signature(c,old)==signature(dict(c,name='different_label'),old)
     assert signature(c,old)!=signature(dict(c,distance_budget=9999),old) and signature(c,old)!=signature(c,list(reversed(old)))
     path=[(0,0),(1,0),(2,0),(1,0),(0,0)];cc=shared_C(path,0,{(1,0),(2,0)});assert cc['C']==2 and cc['identity_total']==4
     w,ee=witness([(0,0),(-1,0),(-1,1),(0,1),(1,1),(1,0)],0,(1,0));assert len(ee)==4
     E=b['exact'].Expr;z=E.sqrt(2)-E.number(2);assert independent_sign(z.save())[0]==z.sign()==-1
     details=dict(dedup_ignores_only_name=True,old_order_in_identity=True,same_path_label_only_C_gain=0,W_fixture=4)
    elif name=='P5':
     pending={(2,0),(0,2)};a,t=select(pending,(2,0),[[2,0],[0,2]]);assert a==(0,2) and t['q0_is_first_pending_in_old_order']
     qs=Counter()
     def distance(c,q):qs['stub_distance']+=1;return abs(c[0]-q[0])+abs(c[1]-q[1])
     g=SimpleNamespace(s=SimpleNamespace(free=pending),reachable=pending,distance=distance)
     for on in (False,True):
      d=Diagnostic([[2,0],[0,2]],on);assert d.choose([],[(0,0)],(0,0),None,pending,(2,0),g)==((0,2) if on else (2,0));assert d.choose([{}],[(0,0)],(0,0),None,pending,(2,0),g)==(2,0);assert d.counts['applied']==int(on)
     details=dict(selector_unchanged=True,one_exception_only=True,stub_distance_queries=qs['stub_distance'])
    else:
     for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
     assert plan['cap_core']==plan['cap_post']==36 and plan['qualification_BFS_cap']==66 and len(plan['slots'])==12 and plan['no_new_histories']
     assert 'len(starts)<36' in (H/'common.py').read_text(encoding='utf-8') and "cap=0 if phase=='history'" in (H/'common.py').read_text(encoding='utf-8')
     p=H/'logs'/('pure_exclusive_'+str(roundno));p.write_bytes(b'\x00\xffbinary');assert p.read_bytes()==b'\x00\xffbinary'
     rejected=False
     try:
      with p.open('x'):pass
     except FileExistsError:rejected=True
     assert rejected and norm({'detail':None})=={'detail':None}
     from center_bench_v01_20261022.audit import _post_saved
     details=dict(cap_core=36,history_cap=0,BFS_cap=66,null_not_zero=True,exclusive_refusal=True,credit_identity=b['B'].identity())
    records.append(dict(id=name,passed=True,details=details))
   except BaseException as ex:records.append(dict(id=name,passed=False,reason=repr(ex),traceback=traceback.format_exc()));break
 finally:sys.setprofile(None)
 result=dict(round=roundno,passed=len(records)==6 and all(x['passed'] for x in records) and not calls,cases=records,forbidden_real_calls=calls,repairs=roundno-1,wall_seconds=time.perf_counter()-start,real_core=0,real_post=0,real_geometry=0,real_BFS=0)
 dump(H/('prechecks_round'+str(roundno)+'.json'),result)
 if result['passed']:
  dump(H/'prechecks.json',result);actual={p:v for p,v in loaded_sources().items() if not Path(p).is_relative_to(H)};dump(H/'runtime_guards.json',actual);g=read(H/'source_guards.json');g.update(actual);dump(H/'source_guards.json',g)
 print(json.dumps(dict(passed=result['passed'],round=roundno,identities=len(records),failure=records[-1] if not result['passed'] else None),ensure_ascii=False));return result['passed']
if __name__=='__main__':raise SystemExit(0 if precheck() else 1)
