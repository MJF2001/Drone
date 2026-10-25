"""Bounded old-record geometry/connectivity selection. No planner or repair imports."""
from common import *
from collections import Counter,deque
from itertools import combinations
from copy import deepcopy
from fractions import Fraction as Q
import sys,time,shutil
HIST=ROOT/'PPCPP_LAST新开发地图验证_v0.1_20261020'
OFF=ROOT/'中心区OFF全量质量时间开发比较_v0.1_20261022'
NEIGHBORS=((1,0),(0,1),(-1,0),(0,-1))
def connected(f,s,counts):
 counts['connectivity_BFS_started']+=1;q=deque([s]);seen={s}
 while q:
  x,y=q.popleft();counts['connectivity_BFS_popped']+=1
  for dx,dy in NEIGHBORS:
   counts['connectivity_neighbor_tests']+=1;p=x+dx,y+dy
   if p in f and p not in seen:seen.add(p);q.append(p)
 counts['connectivity_BFS_returned']+=1;return seen
def interior(a,b,p,counts):
 counts['open_box_intersection_tests']+=1;lo=Q(0);hi=Q(1)
 for k in (0,1):
  d=b[k]-a[k];left=Q(p[k])-Q(1,2);right=Q(p[k])+Q(1,2)
  if not d:
   if not left<a[k]<right:return None
  else:
   t1=(left-a[k])/d;t2=(right-a[k])/d;lo=max(lo,min(t1,t2));hi=min(hi,max(t1,t2))
   if lo>=hi:return None
 if lo>=hi:return None
 mid=(lo+hi)/2
 return {'open_t_interval':[str(lo),str(hi)],'interior_witness_t':str(mid),'point':[str(Q(a[k])+mid*(b[k]-a[k])) for k in (0,1)]}
def main():
 assert not (H/'selection.json').exists()
 for d in ('inputs','history','outputs','logs','source_snapshot','figures'):(H/d).mkdir(exist_ok=True)
 (H/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
 draft=ROOT/'旧计划真实受阻_PPCPP直达主线成对诊断执行稿_v2_给sol_20261023.md'
 (H/'source_snapshot/执行稿_v2.md').write_bytes(draft.read_bytes())
 gsource=ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/audit/_post_geometry.py'
 shutil.copyfile(gsource,H/'selection_geometry.py')
 import selection_geometry as G
 counts=Counter({k:0 for k in ('source_states_scanned','candidate_sets_checked','independent_legality_calls','closed_rectangle_tests','open_box_intersection_tests','connectivity_BFS_started','connectivity_BFS_returned','connectivity_BFS_popped','connectivity_neighbor_tests')})
 original=G.rectangle_intersects
 def box(*a):counts['closed_rectangle_tests']+=1;return original(*a)
 G.rectangle_intersects=box
 def legal(f,a,b):counts['independent_legality_calls']+=1;return G.legal(f,a,b)
 slots=sorted(read(HIST/'protocol.json')['slots'],key=lambda x:x['id']);assert len(slots)==54
 guards={str(draft):sha(draft),str(gsource):sha(gsource),str(HIST/'protocol.json'):sha(HIST/'protocol.json')};selected=[];scanned=[];used=set()
 for slot in slots:
  if len(selected)==6:break
  counts['source_states_scanned']+=1;ident=slot['id'];rec={'id':ident,'base_id':slot['base_id'],'candidate_checks':[]}
  if slot['base_id'] in used:rec['status']='skip_already_selected_base';scanned.append(rec);continue
  try:
   files={'before':HIST/'prep/inputs'/(slot['base_id']+'.json'),'prep':HIST/'prep/results'/(slot['base_id']+'.json'),'witness':HIST/'witnesses'/(ident+'.json'),'old_after':OFF/'inputs'/(ident+'.json')}
   for p in files.values():guards[str(p)]=sha(p)
   before=read(files['before']);prep=read(files['prep']);w=read(files['witness']);oldafter=read(files['old_after'])
   route=prep['raw']['route'];cut=w['cut'];prefix=route[:cut+1];suffix=route[cut:]
   assert prep['eligible'] and prefix==w['history'] and suffix==oldafter['old_route']
   assert Path(prep['job']['input']).resolve()==files['before'].resolve() and prep['runtime_reads'] and all(Path(p).resolve()==files['before'].resolve() for p in prep['runtime_reads'])
   F=ps(before['free']);T=ps(before['published_targets']);hh=ps(prefix)&T;s=tuple(prefix[-1]);base=tuple(before['base']);remain=T-hh
   assert ps(before['targets'])==T and T<=F and s in hh and prefix[-2]==oldafter['previous'] and list(s)==oldafter['current']
   assert hh==ps(oldafter['covered']) and before['distance_budget']==oldafter['distance_budget']
   assert all(tuple(p) in F for p in prefix) and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(prefix,prefix[1:]))
   assert suffix[-1]==before['base'] and all(legal(F,a,b) for a,b in zip(suffix,suffix[1:]))
   n=deepcopy(before);n.update(name=ident+'__pre_event_cut_snapshot',covered=[list(p) for p in sorted(hh)],current=list(s),previous=prefix[-2],old_route=suffix,deferred_targets=[])
   cells=sorted(ps(suffix)-remain-{s,base});candidate_list=[(p,) for p in cells]
   candidate_list += [z for z in combinations(cells,2) if sum(abs(z[0][k]-z[1][k]) for k in (0,1))==1]
   found=None
   for obs in candidate_list[:20]:
    counts['candidate_sets_checked']+=1;f1=F-set(obs);r={'obstacles':[list(p) for p in obs],'candidate_number':len(rec['candidate_checks'])+1}
    certs=[]
    for i,(a,b) in enumerate(zip(suffix,suffix[1:])):
     for p in obs:
      cert=interior(a,b,p,counts)
      if cert:certs.append(dict(edge=i,a=a,b=b,obstacle=list(p),**cert))
    r['interior_invalid_edges']=certs
    if not certs:r['status']='reject_no_strict_interior_block'
    elif remain-set(f1):r['status']='reject_pending_blocked'
    elif s not in f1 or base not in f1:r['status']='reject_S_or_base_blocked'
    else:
     reachable=connected(f1,s,counts);missing=sorted((remain|{base})-reachable)
     r['reachable_count']=len(reachable);r['unreachable_required']=[list(p) for p in missing]
     if missing:r['status']='reject_free_but_unreachable'
     else:
      assert any(not legal(f1,v['a'],v['b']) for v in certs)
      r['status']='selected_first_qualified';found=(obs,f1,certs)
    rec['candidate_checks'].append(r)
    if found:break
   if not found:rec['status']='no_qualified_within_20';scanned.append(rec);continue
   obs,f1,certs=found;e=deepcopy(n);e['free']=[list(p) for p in sorted(f1)]
   assert all(n[k]==e[k] for k in n if k!='free') and not remain&set(obs)
   for env,inp in [('N',n),('E',e)]:dump(H/'inputs'/(ident+'__'+env+'.json'),inp)
   history={'source_state':ident,'base_id':slot['base_id'],'slot':slot,'cut':cut,'prefix':prefix,'suffix':suffix,'H':[list(p) for p in sorted(hh)],'source_files':{k:{'path':str(p),'sha256':sha(p)} for k,p in files.items()},'actual_prep_job':prep['job'],'runtime_reads':prep['runtime_reads'],'semantics':'pre-event cut reconstructed from original prepared native plan, externally supplied center-witness H; no later expansion/obstacle state spliced in; no new-rule replay','event':'new obstacle revealed/introduced at fixed snapshot; no sensing or in-segment stopping simulated','blocked':list(map(list,obs)),'old_suffix_N_legal':True,'old_suffix_E_invalid_interiors':certs,'remaining_required':[list(p) for p in sorted(remain)]}
   dump(H/'history'/(ident+'.json'),history)
   selected.append({'id':ident,'base_id':slot['base_id'],'shape':slot['family'],'size':slot['size'],'progress':slot['progress'],'source_label_not_reused_event':slot['event'],'obstacles':list(map(list,obs)),'candidate_number':len(rec['candidate_checks']),'history':'history/'+ident+'.json','N':'inputs/'+ident+'__N.json','E':'inputs/'+ident+'__E.json'})
   used.add(slot['base_id']);rec['status']='selected';scanned.append(rec)
  except Exception as exc:rec['status']='source_gap';rec['reason']=repr(exc);scanned.append(rec)
 assert counts['source_states_scanned']<=54 and all(len(s['candidate_checks'])<=20 for s in scanned)
 dump(H/'source_guards_selection.json',guards)
 dump(H/'selection.json',{'selected':selected,'scanned':scanned,'counts':dict(counts),'cap':{'states':54,'candidate_sets_per_state':20,'selected':6},'selection':'lexical source-state order, first qualified per unused base, prefer six distinct bases; sorted suffix eligible single cells then adjacent pairs; no core/repair/outcome selection','neighbors':NEIGHBORS,'core_calls':0,'repair_routes_constructed':0,'post_calls':0,'sensing_closed_loop':False})
 dump(H/'input_freeze.json',{'utc':time.time(),'files':{str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.is_relative_to(H/'inputs') or p.is_relative_to(H/'history') or p.name in ('select_inputs.py','common.py','selection_geometry.py','selection.json','source_guards_selection.json','root_before.md','执行稿_v2.md'))}})
 print(json.dumps({'selected':selected,'counts':dict(counts),'core_calls':0,'repair_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
