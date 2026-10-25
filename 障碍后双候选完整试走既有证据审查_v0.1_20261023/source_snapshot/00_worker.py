from common import *
import traceback
from expand_hook import Diagnostic,scan_ref
from decision_audit import audit
def worker(job):
 dest=H/'outputs'/(job['id']+'.json');token=H/'outputs'/(job['id']+'.claim')
 with token.open('x',encoding='utf-8') as f:f.write('exclusive job slot\n')
 wall=time.perf_counter();out=dict(job=job,passed=False,eligible=False,status='starting',counts={'native_detail_profile':None},started_utc=time.time());stage='guard'
 try:
  guard();b=bindings();sources=loaded_sources()
  for p,v in sources.items():assert (p in read(H/'runtime_guards.json') and read(H/'runtime_guards.json')[p]==v) or (Path(p).is_relative_to(H) and sha(p)==read(H/'active_freeze.json')[str(Path(p).relative_to(H))]),('unbound source',p)
  out['loaded_sources']=sources;out['identity']=b['B'].identity()
  c=read(H/job['input']);before=norm(c);out['input']=c;old=job.get('old_order',[]);out['input_sha256']=sha(H/job['input']);stage='input_contract'
  begin=time.perf_counter();phase_validate(c,b['validate']);s=snapshot(c,b['Snapshot']);deadline=begin+20
  out['initial_collect_here']={'new_H':[],'reason':'non-target base: no credit' if c['phase']=='history_prepare' else 'actual prefix collected S; idempotent'}
  diag=Diagnostic(old,job['arm']=='ALT1') if job['arm'] in ('OFF','ALT1') else None
  stage='core';entry(job,'core');raw=(b['native'] if diag is not None else b['reference']).solve(s,ps(c['initial_targets']),deadline-time.perf_counter(),20261020,tuple(c['predator']),tuple(c['previous']) if c['previous'] is not None else None,**({'_diag':diag} if diag is not None else {}));returned(job,'core')
  out['native']={'raw':norm(raw)};out['diagnostic']=diag.export() if diag else None
  if raw['status']!='core_complete':
   out['status']=raw['status'];out['semantic_error']=raw['status']=='core_invalid';return
  if len(raw['route'])-1>4096:out['status']='route_size_cap';return
  if job['arm']=='REF':
   stage='selector';out['scanner']=scan_ref(iter(raw['trace']),iter(enumerate(raw['route'])),ps(c['targets'])-ps(c['covered']),old,deadline)
  json.dumps(out,ensure_ascii=False,allow_nan=False);native_end=time.perf_counter();out['native_entry_seconds']=native_end-begin
  if native_end>=deadline:out['status']='native_or_selector_deadline';return
  stage='raw_execution';out['views']={'A':b['metrics'].evaluate(c,raw['route'],grid=True)};rawend=time.perf_counter()
  request={'id':job['id'],'input':c,'raw':norm(raw)};wire=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()
  out['post_request_utf8']=wire.decode();stage='post';entry(job,'post');poststart=time.perf_counter();postwire,envelope=b['engine'].process(wire,limit=4096,soft=18,total=20);returned(job,'post')
  out.update(post_response_utf8=postwire,post_envelope=envelope,post=json.loads(postwire));stage='post_execution';out['views']['B']=b['metrics'].evaluate(c,out['post']['vertices']);json.dumps(out,ensure_ascii=False,allow_nan=False);mainend=time.perf_counter()
  out['timing']=dict(native_entry_seconds=native_end-begin,raw_common_end_to_end=rawend-begin,post_increment=mainend-rawend,combined_end_to_end=mainend-begin,post_engine_seconds=envelope['entry_seconds'],native_late=native_end-begin>=20,raw_stage_late=rawend-begin>20,post_late=mainend-rawend>20 or envelope['late'],combined_late=mainend-begin>40,scope='input/selection/core/encoding and actual raw/post execution inside; disk/cold/source guards and independent audits outside, worker wall includes them')
  out['passed']=True;out['status']='complete';out['eligible']=not any(out['timing'][k] for k in ('native_late','raw_stage_late','post_late','combined_late'))
  dump(dest,out);stage='independent_review';astart=time.perf_counter();out['independent']=b['B'].audit_result(out);out['decision_audit']=audit(c,raw,old,job['arm'],out['diagnostic'],out.get('scanner'));out['independent_seconds']=time.perf_counter()-astart
  if out['independent_seconds']>150:out['eligible']=False;out['status']='independent_deadline'
  if job['arm']=='OFF':
   ref=read(H/'outputs'/(job['reference_id']+'.json'))
   out['off_equivalence']=dict(raw_semantic=canonical(raw)==canonical(ref['native']['raw']),post_vertices=out['post']['vertices']==ref['post']['vertices'],post_anchors=out['post']['locked_nominal_anchors']==ref['post']['locked_nominal_anchors'],post_credits=out['post']['credit_witnesses']==ref['post']['credit_witnesses'],raw_credits=out['views']['A']['events']==ref['views']['A']['events'],actual_post_credits=out['views']['B']['events']==ref['views']['B']['events'])
   assert all(out['off_equivalence'].values()),'OFF equivalence failure'
  assert c==before;guard()
 except AssertionError as ex:
  if str(ex) in ('selector_deadline','independent_deadline'):
   out.update(eligible=False,status=str(ex),passed=False,semantic_error=False)
  else:out.update(passed=False,eligible=False,status='semantic_or_contract_error',semantic_error=True,failure=repr(ex),traceback=traceback.format_exc())
 except BaseException as ex:out.update(passed=False,eligible=False,status='implementation_error',semantic_error=True,failure=repr(ex),traceback=traceback.format_exc())
 finally:
  out['last_stage']=stage;out['worker_wall_seconds']=time.perf_counter()-wall;out['diagnostic_total_seconds']=out['worker_wall_seconds'];dump(dest,out)
  print(json.dumps({'id':job['id'],'status':out['status'],'eligible':out['eligible'],'semantic_error':out.get('semantic_error',False),'seconds':out['worker_wall_seconds']},ensure_ascii=False),flush=True)
if __name__=='__main__':worker(read(sys.argv[1]))
