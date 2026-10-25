"""Saved-data schema normalization only; no planner, geometry or BFS import."""
from common import *
from copy import deepcopy
import datetime,hashlib
def main():
 assert not (H/'usable_snapshots_v02.json').exists()
 rows=[]
 for selected in read(H/'scan_results.json')['selected']:
  n=read(H/selected['N']);old_e=read(H/selected['E']);r=read(H/'records'/(selected['id']+'.json'));P=ps(n['published_targets']);Hh=ps(n['covered']);U=ps(n['targets'])-Hh
  e=deepcopy(old_e);f=ps(e['free']);blocked=ps(n['free'])-f
  assert blocked and blocked<=Hh and not blocked&U
  assert all(old_e[k]==n[k] for k in n if k!='free')
  e['targets']=[list(p) for p in sorted(P&f)]
  e['deferred_targets']=[list(p) for p in sorted(P-f-Hh)]
  assert P==ps(e['published_targets']) and Hh==ps(e['covered']) and U==ps(e['targets'])-Hh and not e['deferred_targets']
  assert all(n[k]==e[k] for k in n if k not in ('free','targets','deferred_targets'))
  assert ps(n['targets'])==P&ps(n['free']) and ps(e['targets'])==P&ps(e['free'])
  dest=(H/selected['E']).parent;ep=dest/'E_contract_v02.json';dump(ep,e)
  prefixproof=[{'cell':list(p),'first_original_prefix_index':next(i for i,q in enumerate(r['prefix']) if tuple(q)==p),'point':list(p),'published_before_cut':p in P,'within_initial_free':p in ps(n['free'])} for p in sorted(blocked)]
  cert={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':selected['id'],'N':selected['N'],'E_initial_unormalized_preserved_not_for_algorithm':selected['E'],'E_contract_v02':str(ep.relative_to(H)),'N_sha256':sha(H/selected['N']),'original_E_sha256':sha(H/selected['E']),'E_v02_sha256':sha(ep),'published_target_set_P_unchanged':True,'H_unchanged':True,'pending_U_unchanged':True,'U':[list(p) for p in sorted(U)],'blocked_initial_H_evidence':prefixproof,'active_targets_removed_completed_only':[list(p) for p in sorted(ps(n['targets'])-ps(e['targets']))],'active_T_definition':'T=P intersect current public F; E removes only completed target(s) from active T, never a pending task','D_definition':'D=P minus F minus H; empty in both N/E','other_input_fields_unchanged':True,'geometric_domain_unchanged_from_original_selected_E':old_e['free']==e['free'],'existing_map_certificate':selected['certificate'],'existing_map_certificate_sha256':sha(H/selected['certificate']),'new_geometric_BFS_R_post_core_calls':0}
  cp=dest/'contract_certificate_v02.json';dump(cp,cert)
  fpath=dest/'contract_freeze_v02.json';dump(fpath,{'utc':cert['utc'],'files':{str(p.relative_to(H)):sha(p) for p in (ep,cp,H/selected['N'],H/selected['E'],H/selected['certificate'])}})
  rows.append(dict(selected,E=str(ep.relative_to(H)),initial_E_not_for_algorithm=selected['E'],contract_certificate=str(cp.relative_to(H)),contract_freeze=str(fpath.relative_to(H))))
 dump(H/'usable_snapshots_v02.json',{'selected':rows,'count':len(rows),'purpose':'valid current input schema for owner review only, not an algorithm run','initial_draft_issue':'The initial emitter changed only F. For a blocked completed target, keeping all old active targets violates T=P intersect F. Initial E files and first selection freezes are preserved, and are not algorithm-ready inputs.','resolution':'derived active target set normalized in separately named v02 E, P/H/U unchanged; D remains empty; same registered blockers and same tested free domain; no new candidate or geometry checks','scope':'does not relax occlusion of uncompleted tasks; no performance or intervention authorization','new_core_R_post_geometry_BFS':0})
 print({'usable_snapshots':len(rows),'new_core_R_post_geometry_BFS':0,'initial_E_retained':True})
if __name__=='__main__':main()
