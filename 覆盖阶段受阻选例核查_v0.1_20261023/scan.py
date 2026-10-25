"""Bounded existing-suffix selection only. No algorithm, repair, shortcut or route generation."""
from common import *
from collections import Counter,deque
from copy import deepcopy
from itertools import combinations
from fractions import Fraction as Q
import shutil,datetime
HIST=ROOT/'PPCPP_LAST新开发地图验证_v0.1_20261020'
OFF=ROOT/'中心区OFF全量质量时间开发比较_v0.1_20261022'
OLD=ROOT/'旧计划真实受阻PPCPP成对诊断_v0.1_20261023'
NEIGHBORS=((1,0),(0,1),(-1,0),(0,-1))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def interior(a,b,p,counts):
 counts['strict_open_box_tests']+=1;lo=Q(0);hi=Q(1)
 for k in (0,1):
  d=b[k]-a[k];left=Q(p[k])-Q(1,2);right=Q(p[k])+Q(1,2)
  if not d:
   if not left<a[k]<right:return None
  else:
   t1=(left-a[k])/d;t2=(right-a[k])/d;lo=max(lo,min(t1,t2));hi=min(hi,max(t1,t2))
   if lo>=hi:return None
 if lo>=hi:return None
 t=(lo+hi)/2
 return {'open_t_interval':[str(lo),str(hi)],'interior_witness_t':str(t),'point':[str(Q(a[k])+t*(b[k]-a[k])) for k in (0,1)]}
def reachable(f,s,counts):
 counts['connectivity_BFS_started']+=1;seen={s};queue=deque([s])
 while queue:
  p=queue.popleft();counts['connectivity_BFS_popped']+=1
  for dx,dy in NEIGHBORS:
   counts['connectivity_neighbor_tests']+=1;q=p[0]+dx,p[1]+dy
   if q in f and q not in seen:seen.add(q);queue.append(q)
 counts['connectivity_BFS_returned']+=1
 return seen
def main():
 assert not (H/'scan_results.json').exists() and not (H/'pre_scan_freeze.json').exists()
 for d in ('records','selected','figures','sources'):(H/d).mkdir(exist_ok=True)
 (H/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
 draft=ROOT/'覆盖阶段真实受阻选例核查执行稿_给sol_20261023.md'
 (H/'sources/执行稿.md').write_bytes(draft.read_bytes())
 geom=ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/audit/_post_geometry.py'
 shutil.copyfile(geom,H/'independent_geometry.py')
 slots=sorted(read(HIST/'protocol.json')['slots'],key=lambda s:s['id']);assert len(slots)==54
 bases=sorted({s['base_id'] for s in slots});guards={}
 for p in (draft,geom,HIST/'protocol.json',OLD/'final_receipt.json',OLD/'selection.json',OLD/'00_通俗成对诊断报告.md',ROOT/'研究双方向与接续思路_新增任务与新障碍_20261023.md',ROOT/'旧计划真实受阻_PPCPP直达主线成对诊断执行稿_v2_给sol_20261023.md'):
  guards[str(p)]=sha(p)
 for c in read(OLD/'selection.json')['selected']:
  p=OLD/c['history'];guards[str(p)]=sha(p)
 bound_rows=[]
 for base in bases:
  p=HIST/'prep/results'/(base+'.json');q=HIST/'prep/inputs'/(base+'.json');guards[str(p)]=sha(p);guards[str(q)]=sha(q)
  bound_rows.append({'base_id':base,'full_route_edges':len(read(p)['raw']['route'])-1,'free_cells':len(read(q)['free'])})
 nmax=max(r['full_route_edges'] for r in bound_rows);fmax=max(r['free_cells'] for r in bound_rows)
 # Each unit edge can enter only its two endpoint cell interiors. One candidate
 # costs at most 3 closed-domain calls and 2*nmax strict interior calls.
 bounds={'source_states':54,'candidates_per_state':20,'selected_distinct_bases':6,'max_existing_suffix_edges':nmax,'max_free_cells':fmax,'max_N_and_candidate_closed_legality_calls':54*nmax+54*20*3,'max_strict_open_box_calls':54*20*2*nmax,'max_connectivity_BFS':54*20,'max_BFS_popped':54*20*fmax,'max_BFS_neighbor_tests':54*20*fmax*4}
 dump(H/'plan.json',{'utc':now(),'source_slots':slots,'bounds':bounds,'base_bounds':bound_rows,'order':'lex source ID; prefer unused base; coverage qualifying edge index first then cell coordinates; all singles before adjacent pairs; first qualifying then freeze; stop on 6 distinct bases','coverage_edge':'i < last first-service vertex index AND remaining tasks with first-service index > i >= 2','barrier':'initial pending target cells forbidden even if an old hypothetical future path would service them earlier; current/base forbidden; only initial H or non-target transit allowed','N':'actual pre-event prep map/targets plus evidenced cut prefix, not old event-after expansion/obstacle state','no_method_results_used':'No prior B/R/C relative gaps or new algorithm results read for selection','diagram_rule':'selected examples if any; if none, first lex state per (shape,progress), up to six, marked excluded representative','hypothetical_occlusion_only':'up to six distinct-base text annotations from pending cells; no E construction/geometry/BFS for them','neighbors':NEIGHBORS,'algorithm_core_R_post_candidate_route_calls':0})
 dump(H/'pre_scan_sources.json',guards)
 dump(H/'pre_scan_freeze.json',{'utc':now(),'files':{str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file()}})
 import independent_geometry as G
 total=Counter({k:0 for k in ('source_states_processed','candidate_sets_checked','independent_legality_calls','closed_forbidden_rectangle_tests','strict_open_box_tests','connectivity_BFS_started','connectivity_BFS_returned','connectivity_BFS_popped','connectivity_neighbor_tests','suffix_service_vertex_scans','edge_phase_classifications','endpoint_identity_classifications')})
 original=G.rectangle_intersects;current=None
 def box(*a):
  total['closed_forbidden_rectangle_tests']+=1
  if current is not None:current['closed_forbidden_rectangle_tests']+=1
  return original(*a)
 G.rectangle_intersects=box
 def legal(f,a,b,counts):counts['independent_legality_calls']+=1;return G.legal(f,a,b)
 selected=[];rows=[];used=set();hypothetical=[];hypobases=set()
 for slot in slots:
  if len(selected)>=6:break
  ident=slot['id'];total['source_states_processed']+=1
  row={'id':ident,'base_id':slot['base_id'],'shape':slot['family'],'size':slot['size'],'progress':slot['progress'],'candidate_checks':[]}
  if slot['base_id'] in used:
   row['status']='skip_already_selected_base';rows.append(row);continue
  counts=Counter({k:0 for k in total if k!='source_states_processed'});current=counts
  try:
   paths={'prep_input':HIST/'prep/inputs'/(slot['base_id']+'.json'),'prep_result':HIST/'prep/results'/(slot['base_id']+'.json'),'cut_witness':HIST/'witnesses'/(ident+'.json'),'old_after_reference_only':OFF/'inputs'/(ident+'.json')}
   sources={k:{'path':str(p),'sha256':sha(p)} for k,p in paths.items()};guards.update({v['path']:v['sha256'] for v in sources.values()})
   before=read(paths['prep_input']);prep=read(paths['prep_result']);w=read(paths['cut_witness']);after=read(paths['old_after_reference_only']);cut=w['cut'];full=prep['raw']['route'];prefix=full[:cut+1];suffix=full[cut:]
   assert prep['eligible'] and prefix==w['history'] and suffix==after['old_route']
   assert Path(prep['job']['input']).resolve()==paths['prep_input'].resolve() and prep['runtime_reads'] and all(Path(p).resolve()==paths['prep_input'].resolve() for p in prep['runtime_reads'])
   F=ps(before['free']);T=ps(before['published_targets']);hh=ps(prefix)&T;U=T-hh;s=tuple(prefix[-1]);base=tuple(before['base'])
   assert ps(before['targets'])==T and T<=F and hh==ps(after['covered']) and s in hh
   assert prefix[-1]==after['current'] and prefix[-2]==after['previous'] and before['distance_budget']==after['distance_budget']
   assert set(map(tuple,prefix))<=F and all(sum(abs(a[k]-b[k]) for k in (0,1))==1 for a,b in zip(prefix,prefix[1:]))
   assert suffix[0]==prefix[-1] and suffix[-1]==before['base'] and len(suffix)-1<=nmax and len(F)<=fmax
   for a,b in zip(suffix,suffix[1:]):assert sum(abs(a[k]-b[k]) for k in (0,1))==1 and legal(F,a,b,counts)
   n=deepcopy(before);n.update(name=ident+'__pre_event_cut',covered=[list(p) for p in sorted(hh)],current=list(s),previous=prefix[-2],old_route=suffix,deferred_targets=[])
   first={}
   for i,p in enumerate(suffix):
    counts['suffix_service_vertex_scans']+=1;p=tuple(p)
    if p in U and p not in first:first[p]=i
   assert set(first)==U
   last=max(first.values()) if first else 0
   def identity(p):
    if p in {s,base}:return 'S_or_base_forbidden'
    if p in U:return 'initial_pending_target_forbidden'
    if p in hh:return 'initial_H_allowed'
    return 'non_target_transit_allowed'
   phases=Counter(coverage_at_least_2_pending=0,before_last_but_only_1_pending=0,return_after_last_service=0);occ=Counter();cells={};edge_rows=[];earliest={};shadows=[]
   for i,(a,b) in enumerate(zip(suffix,suffix[1:])):
    counts['edge_phase_classifications']+=1;pending=sum(v>i for v in first.values())
    phase='return_after_last_service' if i>=last else 'coverage_at_least_2_pending' if pending>=2 else 'before_last_but_only_1_pending'
    phases[phase]+=1;ends=[]
    for p in (tuple(a),tuple(b)):
     counts['endpoint_identity_classifications']+=1;cl=identity(p);ends.append({'cell':list(p),'initial_identity':cl})
     cells.setdefault(p,{'identity':cl,'phases':set(),'first_any_edge':i})['phases'].add(phase)
     if phase=='coverage_at_least_2_pending':
      occ[cl]+=1
      if cl.endswith('_allowed'):earliest.setdefault(p,i)
      elif cl=='initial_pending_target_forbidden':shadows.append({'cell':list(p),'eligible_coverage_edge':i,'pending_at_edge_start':pending,'first_service_vertex_index':first[p],'initial_identity':cl})
    edge_rows.append({'edge':i,'a':a,'b':b,'phase':phase,'pending_at_start':pending,'first_services_completed_at_start':len(U)-pending,'endpoint_identities':ends})
   singles=sorted(earliest,key=lambda p:(earliest[p],p));allowed_any=sorted(p for p,c in cells.items() if c['identity'].endswith('_allowed'))
   pairs=sorted((p for p in combinations(allowed_any,2) if any(q in earliest for q in p) and sum(abs(p[0][k]-p[1][k]) for k in (0,1))==1),key=lambda p:(min(earliest.get(q,nmax+1) for q in p),p))
   pool=[(p,) for p in singles]+pairs;found=None
   for obstacles in pool[:20]:
    counts['candidate_sets_checked']+=1;f1=F-set(obstacles);test={'number':len(row['candidate_checks'])+1,'obstacles':[list(p) for p in obstacles],'kind':'single' if len(obstacles)==1 else 'adjacent_pair'};certs=[]
    for edge in edge_rows:
     if edge['phase']!='coverage_at_least_2_pending':continue
     a,b=edge['a'],edge['b']
     for p in obstacles:
      if p not in (tuple(a),tuple(b)):continue
      hit=interior(a,b,p,counts)
      if hit:certs.append({'edge':edge['edge'],'a':a,'b':b,'obstacle':list(p),'pending_at_start':edge['pending_at_start'],'last_first_service_index':last,**hit})
    test['coverage_interior_certificates']=certs
    if not certs:test['status']='reject_no_qualifying_strict_interior'
    elif set(obstacles)&U:test['status']='reject_pending_occlusion'
    elif s not in f1 or base not in f1:test['status']='reject_S_or_base'
    else:
     assert legal(f1,s,s,counts) and legal(f1,base,base,counts)
     assert not legal(f1,certs[0]['a'],certs[0]['b'],counts)
     reached=reachable(f1,s,counts);missing=sorted((U|{base})-reached);test['unreachable_required']=[list(p) for p in missing];test['reachable_count']=len(reached)
     if missing:test['status']='reject_free_but_unreachable'
     else:test['status']='first_qualified_frozen';found=(obstacles,f1,certs)
    row['candidate_checks'].append(test)
    if found:break
   unique_cov=Counter(cells[p]['identity'] for p in cells if 'coverage_at_least_2_pending' in cells[p]['phases'])
   allowed_return_only=[list(p) for p in allowed_any if cells[p]['phases']=={'return_after_last_service'}]
   row.update(remaining_tasks=len(U),suffix_edges=len(suffix)-1,last_first_service_vertex=last,phase_edges=dict(phases),coverage_endpoint_occurrences=dict(occ),coverage_endpoint_unique_cells=dict(unique_cov),eligible_single_cells=len(singles),eligible_adjacent_pairs=len(pairs),allowed_any_suffix_cells=len(allowed_any),allowed_return_only_cells=len(allowed_return_only),candidate_checks_count=len(row['candidate_checks']))
   if found:
    obstacles,f1,certs=found;e=deepcopy(n);e['free']=[list(p) for p in sorted(f1)];dest=H/'selected'/ident;dest.mkdir()
    dump(dest/'N.json',n);dump(dest/'E.json',e);dump(dest/'certificate.json',{'source_state':ident,'obstacles':list(map(list,obstacles)),'strict_coverage_blockages':certs,'N_legal':True,'remaining_all_reachable':True,'first_qualified_candidate':len(row['candidate_checks'])})
    dump(dest/'freeze.json',{'utc':now(),'files':{str(p.relative_to(H)):sha(p) for p in dest.glob('*.json')}})
    row['status']='selected_coverage_blockage';selected.append({'id':ident,'base_id':slot['base_id'],'shape':slot['family'],'N':str((dest/'N.json').relative_to(H)),'E':str((dest/'E.json').relative_to(H)),'certificate':str((dest/'certificate.json').relative_to(H))});used.add(slot['base_id'])
   elif not singles:
    row['status']='no_allowed_coverage_cell'
   elif len(pool)>20 and len(row['candidate_checks'])==20:row['status']='no_qualified_within_20_unchecked_pool_retained'
   else:row['status']='all_allowed_candidates_rejected'
   # Text-only annotations of currently forbidden target cells. No altered map,
   # candidate geometry or BFS is run on these hypothetical occlusion examples.
   if slot['base_id'] not in hypobases and len(hypothetical)<6 and shadows:
    shadow=sorted(shadows,key=lambda x:(x['eligible_coverage_edge'],x['cell']))[0]
    hypothetical.append({'source_state':ident,'base_id':slot['base_id'],**shadow,'note':'would occlude an initial pending task; forbidden this round; text identity only, no E construction/geometry/BFS/algorithm tested'});hypobases.add(slot['base_id'])
   normalized={k:v for k,v in n.items() if k!='name'};physical=__import__('hashlib').sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest();row['physical_cut_sha256']=physical
   record={'summary':row,'N_source_reconstruction':n,'source_files':sources,'actual_prep_job':prep['job'],'actual_runtime_reads':prep['runtime_reads'],'cut':cut,'prefix':prefix,'suffix':suffix,'first_services':[{'cell':list(p),'vertex_index':i,'source_full_route_index':cut+i} for p,i in sorted(first.items(),key=lambda z:(z[1],z[0]))],'last_first_service_vertex_index':last,'edges':edge_rows,'allowed_cells_anywhere':[{'cell':list(p),'identity':cells[p]['identity'],'first_edge':cells[p]['first_any_edge'],'phases':sorted(cells[p]['phases'])} for p in allowed_any],'allowed_return_only_cells':allowed_return_only,'eligible_ordered_single_candidates':[{'cell':list(p),'first_qualifying_edge':earliest[p]} for p in singles],'eligible_ordered_pair_candidates':[list(map(list,z)) for z in pairs],'counts':dict(counts),'model':'old grid-center first service for phase classification, not new-region replay; externally given H unchanged; no algorithm or repair imported'}
   dump(H/'records'/(ident+'.json'),record)
  except Exception as exc:
   import traceback
   row.update(status='source_or_execution_gap',reason=repr(exc),traceback=traceback.format_exc())
   dump(H/'records'/(ident+'.json'),{'summary':row,'counts':dict(counts)})
  finally:
   current=None
   for k,v in counts.items():
    if k!='closed_forbidden_rectangle_tests':total[k]+=v
   row['counts']=dict(counts);rows.append(row);dump(H/'scan_progress.json',{'rows':rows,'selected':selected,'counts':dict(total)})
 assert len(rows)<=54 and len(selected)<=6 and all(len(r['candidate_checks'])<=20 for r in rows)
 assert total['independent_legality_calls']<=bounds['max_N_and_candidate_closed_legality_calls'] and total['strict_open_box_tests']<=bounds['max_strict_open_box_calls'] and total['connectivity_BFS_started']<=bounds['max_connectivity_BFS']
 assert total['connectivity_BFS_popped']<=bounds['max_BFS_popped'] and total['connectivity_neighbor_tests']<=bounds['max_BFS_neighbor_tests']
 dump(H/'sources_guard.json',guards)
 dump(H/'hypothetical_occlusion_annotations.json',{'examples':hypothetical,'count':len(hypothetical),'permitted_for_current_selection':False,'geometric_tests_on_these_positions':0,'E_maps_constructed_for_them':0,'core_R_post_calls':0})
 result={'utc':now(),'rows':rows,'selected':selected,'counts':dict(total),'status_counts':dict(Counter(r['status'] for r in rows)),'distinct_physical_cuts':len({r['physical_cut_sha256'] for r in rows if 'physical_cut_sha256' in r}),'distinct_base_ids_scanned':len({r['base_id'] for r in rows}),'completed_scan_or_six_base_stop':len(rows)==54 or len(selected)==6,'gap_count':sum(r['status']=='source_or_execution_gap' for r in rows),'new_algorithm_core_R_candidate_route_post_performance_calls':0,'conclusion_boundary':'existence/absence only within saved old suffixes, grid-center cuts, unchanged pending responsibility and registered cap; no algorithm quality or universal obstacle-direction claim'}
 dump(H/'scan_results.json',result)
 dump(H/'selection_freeze.json',{'utc':now(),'files':{str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name!='selection_freeze.json'}})
 print(json.dumps({k:result[k] for k in ('status_counts','selected','counts','distinct_physical_cuts','distinct_base_ids_scanned','gap_count')},ensure_ascii=False))
if __name__=='__main__':main()
