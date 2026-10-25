"""Warm single/interface and strict four-candidate entry; all work timed."""
from common_orient import *
from transform import transform,inverse_raw
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'基线复现准备_20261019'))
old=load('rotation_old_native',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')
new=load('rotation_new_native',H/'interface/ppcpp.py')
validate=load('rotation_validation',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py').validate
from model import Snapshot,DeadlineExceeded
def snapshot(c):return Snapshot(c['name'],frozenset(pts(c['free'])),frozenset(pts(c['targets'])),frozenset(pts(c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
def run(payload,mode,budget=20,seed=20261020,degree=0,*,clock=time.perf_counter,hook=None,solver=None,mutation=None):
 begin=clock();deadline=begin+budget;records=[];core_calls=0;raw=None;status='not_started';error=None;selected=None;phases={}
 def tick(stage):
  if hook:hook(stage)
  if clock()>=deadline:raise DeadlineExceeded()
 try:
  c=json.loads(payload)
  if mutation:c['predator']=[float(mutation),0]
  validate(c);tick('decoded');angles=(0,1,2,3) if mode=='COMBO' else (degree//90,)
  for k in angles:
   tick(f'candidate_{k}_before');a=clock();tick('transform_before');tc,meta=transform(c,k);tick('transform_after');s=snapshot(tc);tick(f'candidate_{k}_core_before');core_calls+=1
   fn=solver or (old.solve if mode=='OLD' else new.solve)
   r=fn(s,pts(tc['initial_targets']),deadline-clock(),seed,tuple(tc['predator']),tuple(tc['previous']) if tc['previous'] is not None else None,_clock=clock)
   tick(f'candidate_{k}_core_after')
   if r['status']!='core_complete':records.append(dict(degree=k*90,raw=r,transformed_input=tc,meta=meta));status='candidate_failed';break
   tick('inverse_before');back=inverse_raw(r,meta);tick('inverse_after');tick('check_before');checked=new.single_cell_audit(snapshot(c),tuple(map(tuple,back['route'])));tick('check_after')
   if not checked['valid']:raise ValueError(('inverse_invalid',checked))
   records.append(dict(degree=k*90,raw=r,inverse=back,transformed_input=tc,meta=meta,seconds=clock()-a))
   tick(f'candidate_{k}_after')
  else:
   chosen=min(range(len(records)),key=lambda i:(len(records[i]['inverse']['route']),i));selected=records[chosen]['degree'];raw=dict(version='PPCPP_ORIENT4_v0.1' if mode=='COMBO' else records[0]['raw']['version'],status='core_complete',route=records[chosen]['inverse']['route'],trace=records[chosen]['inverse']['trace'],selected_degree=selected,candidates=records);status='core_complete'
  if raw is None:raw=dict(status=status,route=[],candidates=records,selected_degree=None)
  tick('encode_before');a=clock();wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':'));phases['encoding']=clock()-a;tick('encode_after')
 except DeadlineExceeded:status='deadline';raw=dict(status=status,route=[],candidates=records,selected_degree=None)
 except Exception as exc:status='exception';error=dict(type=type(exc).__name__,message=str(exc));raw=dict(status=status,route=[],candidates=records,selected_degree=None)
 elapsed=clock()-begin
 if elapsed>=budget:status='deadline';raw=dict(status=status,route=[],candidates=records,selected_degree=None)
 return dict(raw=raw,status=status,exception=error,entry_seconds=elapsed,budget=budget,seed=seed,mode=mode,core_calls=core_calls,eligible=status=='core_complete' and elapsed<budget,phase_seconds=phases)
