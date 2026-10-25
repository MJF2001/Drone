"""One arm, no true outcomes or original source-directory access."""
from pathlib import Path
import sys,json,time,traceback
from collections import Counter
from common import H,read,dump,sha,ps,norm
from isolation import install
from policy import tail,join,Unavailable,validate_packet
def run(cropfile):
 wall=time.perf_counter();cropfile=Path(cropfile).resolve();dest=H/'outputs'/cropfile.name
 with (H/'outputs'/(cropfile.stem+'.claim')).open('x',encoding='utf-8') as f:f.write('one attempt only\n')
 access,reads=install(H,cropfile);stage='input';out=dict(id=cropfile.stem,status='starting',passed=False,eligible=False,timing={},counts={'detail_profile':None,'astar_expanded':None,'geometry_context_BFS_popped':None,'geometry_context_BFS_neighbors':None,'distance_queries':0},started_utc=time.time(),crop_sha256=sha(cropfile));frozen=read(H/'freeze.json')
 try:
  for p,v in frozen.items():assert sha(H/p)==v,('source_changed',p)
  t=time.perf_counter();p=read(cropfile);manifest=read(H/'manifest.json');validate_packet(p,manifest['input_whitelist']);assert p['id']==cropfile.stem;out['timing']['crop_read_seconds']=time.perf_counter()-t
  import_start=time.perf_counter()
  from frozen_shadow_connector_20261023.model import Snapshot,NoPath,DeadlineExceeded
  from frozen_shadow_connector_20261023.unified_geometry import UnifiedGeometry,single_cell_audit
  from frozen_shadow_center_20261023 import metrics
  from frozen_shadow_center_20261023.post import engine
  out['timing']['frozen_import_seconds']=time.perf_counter()-import_start
  c=p['event'];stop=p['stop_state'];out['prefix_summary']=dict(common_edges=len(p['common_prefix'])-1,finite_edges=stop['edges'],local_edges=stop['local_edges'],new_tasks=len(stop['new_tasks']),tail_start_pending=len(stop['pending']),stop_current=stop['current'],stop_previous=stop['previous'],q_arrived=stop['q_arrived'],stop_reason=stop['reason'])
  stage='tail';t=time.perf_counter();deadline=t+20
  s=Snapshot(c['name'],frozenset(ps(c['free'])),frozenset(ps(c['targets'])),frozenset(ps(c['covered'])|ps(p['common_prefix'])&ps(c['targets'])|ps(p['finite_prefix'])&ps(c['targets'])),tuple(stop['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
  g=UnifiedGeometry(s,deadline);out['counts']['geometry_contexts']=1;out['counts']['geometry_context_reachable']=len(g.reachable);assert g.precheck() is None
  query_counts=Counter(path_cache_hits=0,path_cache_misses=0)
  def connect(a,b):
   query_counts['path_cache_hits' if (a,b) in g.cache else 'path_cache_misses']+=1
   return g.path(a,b)
  result=tail(p,connect,deadline);out['tail']=result;out['counts'].update(result['counts']);out['counts'].update(query_counts);out['counts']['astar_searches']=g.searches;out['counts']['distance_BFS_rows']=g.bfs_rows_built;out['timing']['tail_construct_seconds']=time.perf_counter()-t
  if out['timing']['tail_construct_seconds']>=20:raise Unavailable('tail_soft_deadline')
  stage='join_and_native_contract';t=time.perf_counter();route=join(p['common_prefix'],p['finite_prefix'],result['route']);fulls=Snapshot(c['name'],frozenset(ps(c['free'])),frozenset(ps(c['targets'])),frozenset(ps(c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget']);check=single_cell_audit(fulls,tuple(map(tuple,route)));assert check['valid'],check;out['native_contract']=check;out['timing']['join_native_contract_seconds']=time.perf_counter()-t
  out['raw']={'route':route,'trace':[],'kind':'shadow_substitute_not_actual_PPCPP_future'}
  request={'id':p['id'],'input':c,'raw':out['raw']};wire=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode();out['post_request_utf8']=wire.decode();stage='post'
  with (H/'logs'/(p['id']+'.post_started')).open('x',encoding='utf-8') as f:f.write(str(time.time()))
  t=time.perf_counter();postwire,envelope=engine.process(wire,limit=4096,soft=18,total=20);out['timing']['post_call_seconds']=time.perf_counter()-t;out['post_response_utf8']=postwire;out['post']=json.loads(postwire);out['post_envelope']=envelope
  stage='necessary_full_credit_metrics';t=time.perf_counter();out['views']={'A':metrics.evaluate(c,route,grid=True),'B':metrics.evaluate(c,out['post']['vertices'])};out['timing']['full_credit_metrics_seconds']=time.perf_counter()-t
  out['Jhat_raw']=len(route)-1;out['Jhat_post']=out['views']['B']['metrics']['length'];out['Jhat_certificate']=out['views']['B']['metrics']['length_certificate'];out['counts']['post']=out['post']['counts'];out['counts']['native_metric']=out['views']['A']['counts'];out['counts']['post_metric']=out['views']['B']['counts'];out['passed']=True;out['eligible']=not envelope['late'] and envelope['fallback'] is None and out['timing']['post_call_seconds']+out['timing']['full_credit_metrics_seconds']<=20;out['status']='complete' if out['eligible'] else 'post_budget_unavailable'
 except Unavailable as ex:out.update(status=str(ex),passed=True,eligible=False,model_unavailable=True,partial_tail=ex.details)
 except BaseException as ex:
  expected=type(ex).__name__ in ('NoPath','DeadlineExceeded')
  out.update(status='unreachable_or_tail_budget' if expected else 'implementation_or_contract_error',passed=expected,eligible=False,model_unavailable=expected,failure=repr(ex),traceback=traceback.format_exc())
 finally:
  if 'g' in locals():out['counts'].update(astar_searches=g.searches,distance_BFS_rows=g.bfs_rows_built)
  if 'query_counts' in locals():out['counts'].update(query_counts)
  out['last_stage']=stage;out['wall_seconds']=time.perf_counter()-wall;out['read_guard']=dict(counts=access,read_paths=sorted(reads),scope='only one crop, local frozen code/config and Python runtime; originals and other outputs denied');out['new_core_calls']=0;out['post_calls']=int((H/'logs'/(cropfile.stem+'.post_started')).exists());dump(dest,out);print(json.dumps(dict(id=out['id'],status=out['status'],eligible=out['eligible'],post=out['post_calls'],wall=out['wall_seconds']),ensure_ascii=False),flush=True)
if __name__=='__main__':run(sys.argv[1])
