from region_common import *
import traceback
from region_audit import audit
def worker(job):
 dest=H/'outputs'/(job['id']+'.json');token=H/'outputs'/(job['id']+'.claim')
 with token.open('x',encoding='utf-8') as f:f.write('exclusive registered job\n')
 wall=time.perf_counter();out=dict(job=job,passed=False,eligible=False,status='starting',counts={'native_detail_profile':None},started_utc=time.time());stage='guard'
 try:
  guard();b=bindings();sources=loaded_sources();runtime=read(H/'runtime_guards.json');active=read(H/'active_freeze.json')
  for p,v in sources.items():
   pp=Path(p)
   # The Python bundled standard library is environment, explicitly recorded here.
   if pp.is_relative_to(ROOT/'运行环境'):continue
   assert (p in runtime and runtime[p]==v) or (pp.is_relative_to(H) and active.get(str(pp.relative_to(H)))==v),('unbound source',p)
  out['loaded_sources']=sources;out['identity']=b['B'].identity();c=read(H/job['input']);before=norm(c);out['input']=c;out['input_sha256']=sha(H/job['input']);stage='input_contract'
  begin=time.perf_counter();phase_validate(c,b['validate']);assert len(c['free'])<=10000 and len(c['published_targets'])<=1500;s=snapshot(c,b['Snapshot']);deadline=begin+20
  stage='core';entry(job,'core')
  if job['arm']=='ORIGINAL':raw=b['reference'].solve(s,ps(c['initial_targets']),deadline-time.perf_counter(),20261023,tuple(c['predator']),tuple(c['previous']) if c['previous'] is not None else None)
  else:raw=b['native'].solve(s,ps(c['initial_targets']),deadline-time.perf_counter(),20261023,tuple(c['predator']),tuple(c['previous']) if c['previous'] is not None else None,labels=c['labels'],enabled=job['arm']=='ON')
  returned(job,'core');out['native']={'raw':norm(raw)}
  if raw['status']!='core_complete':out['status']=raw['status'];out['semantic_error']=raw['status']=='core_invalid';return
  if len(raw['route'])-1>4096:out['status']='route_size_cap';return
  json.dumps(out,ensure_ascii=False,allow_nan=False);native_end=time.perf_counter();out['native_entry_seconds']=native_end-begin
  if native_end>=deadline:out['status']='native_wrapper_deadline';return
  stage='raw_execution';out['views']={'A':b['metrics'].evaluate(c,raw['route'],grid=True)};rawend=time.perf_counter()
  wire=json.dumps({'id':job['id'],'input':c,'raw':norm(raw)},ensure_ascii=False,separators=(',',':')).encode();out['post_request_utf8']=wire.decode();stage='post';entry(job,'post');postwire,envelope=b['engine'].process(wire,limit=4096,soft=18,total=20);returned(job,'post')
  out.update(post_response_utf8=postwire,post_envelope=envelope,post=json.loads(postwire));stage='post_execution';out['views']['B']=b['metrics'].evaluate(c,out['post']['vertices']);json.dumps(out,ensure_ascii=False,allow_nan=False);mainend=time.perf_counter()
  out['timing']=dict(native_entry_seconds=native_end-begin,raw_common_end_to_end=rawend-begin,post_increment=mainend-rawend,combined_end_to_end=mainend-begin,post_engine_seconds=envelope['entry_seconds'],native_late=native_end-begin>=20,raw_stage_late=rawend-begin>20,post_late=mainend-rawend>20 or envelope['late'],combined_late=mainend-begin>40,scope='main includes validation/core/rule/full raw metrics/post/center credits/encoding and actual entry/returned ledger fsync; cold imports/hash/full-file output and independent audits outside; parent wall also recorded')
  out.update(passed=True,status='complete',eligible=not any(out['timing'][k] for k in ('native_late','raw_stage_late','post_late','combined_late')))
  dump(dest,out);stage='independent_review';astart=time.perf_counter();out['independent']=b['B'].audit_result(out);out['decision_audit']=audit(c,raw,job['arm']=='ON');out['independent_seconds']=time.perf_counter()-astart
  if job['arm']=='OFF':
   ref=read(H/'outputs'/(job['reference_id']+'.json'));out['off_equivalence']={'raw_semantic':canonical(raw)==canonical(ref['native']['raw']),'post_vertices':out['post']['vertices']==ref['post']['vertices'],'post_credits':out['post']['credit_witnesses']==ref['post']['credit_witnesses'],'raw_execution':out['views']['A']['events']==ref['views']['A']['events'],'post_execution':out['views']['B']['events']==ref['views']['B']['events'],'raw_metrics':out['views']['A']['metrics']==ref['views']['A']['metrics'],'post_metrics':out['views']['B']['metrics']==ref['views']['B']['metrics']};assert all(out['off_equivalence'].values()),'OFF equivalence failed'
  assert c==before;guard()
 except BaseException as e:out.update(passed=False,eligible=False,status='implementation_or_contract_error',semantic_error=True,failure=repr(e),traceback=traceback.format_exc())
 finally:
  out['last_stage']=stage;out['worker_wall_seconds']=time.perf_counter()-wall;dump(dest,out);print(json.dumps(dict(id=job['id'],status=out['status'],eligible=out['eligible'],semantic_error=out.get('semantic_error',False),failure=out.get('failure')),ensure_ascii=False),flush=True)
if __name__=='__main__':worker(read(sys.argv[1]))
