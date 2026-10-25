"""Read-only receipt/source/schema verification. No algorithm or geometry imports."""
from common import *
from collections import Counter
import sys,datetime
def main():
 checks=[]
 for fn in ('pre_scan_freeze.json','selection_freeze.json'):
  f=read(H/fn)
  for p,d in f['files'].items():assert sha(H/p)==d,(fn,p)
  checks.append(fn+' intact: '+str(len(f['files'])))
 guards=read(H/'sources_guard.json')
 for p,d in guards.items():assert sha(p)==d,p
 checks.append(str(len(guards))+' original source files unchanged')
 plan=read(H/'plan.json');scan=read(H/'scan_results.json');rows=scan['rows'];bounds=plan['bounds'];summ=read(H/'summary.json');l=read(H/'ledger.json')
 assert [r['id'] for r in rows]==[r['id'] for r in plan['source_slots']] and len(rows)==54
 assert Counter(r['status'] for r in rows)=={'no_allowed_coverage_cell':42,'selected_coverage_blockage':2,'skip_already_selected_base':10}
 assert scan['gap_count']==0 and all(len(r['candidate_checks'])<=20 for r in rows)
 detailed=[r for r in rows if 'physical_cut_sha256' in r];assert len(detailed)==44 and len({r['physical_cut_sha256'] for r in detailed})==16
 for r in detailed:
  v=read(H/'records'/(r['id']+'.json'));n=v['N_source_reconstruction'];suffix=v['suffix'];first=v['first_services'];U=ps(n['targets'])-ps(n['covered'])
  assert set(tuple(e['cell']) for e in first)==U and n['old_route']==suffix
  assert all(suffix[e['vertex_index']]==e['cell'] for e in first)
  assert v['last_first_service_vertex_index']==max(e['vertex_index'] for e in first)
  assert len(v['edges'])==len(suffix)-1==r['suffix_edges']
  for e in v['edges']:
   assert suffix[e['edge']]==e['a'] and suffix[e['edge']+1]==e['b']
   assert e['pending_at_start']==sum(x['vertex_index']>e['edge'] for x in first)
   if e['phase']=='coverage_at_least_2_pending':assert e['edge']<v['last_first_service_vertex_index'] and e['pending_at_start']>=2
  if r['status']=='no_allowed_coverage_cell':
   assert r['eligible_single_cells']==r['eligible_adjacent_pairs']==r['candidate_checks_count']==0
   assert all(z['initial_identity'] in ('initial_pending_target_forbidden','S_or_base_forbidden') for e in v['edges'] if e['phase']=='coverage_at_least_2_pending' for z in e['endpoint_identities'])
  for x in v['source_files'].values():assert sha(x['path'])==x['sha256']
 agg=Counter()
 for r in detailed:agg.update(r['counts'])
 for k,v in agg.items():assert scan['counts'][k]==v,(k,scan['counts'][k],v)
 assert scan['counts']['independent_legality_calls']==sum(r['suffix_edges'] for r in detailed)+6==2163
 assert scan['counts']['candidate_sets_checked']==sum(len(r['candidate_checks']) for r in rows)==2
 assert scan['counts']['closed_forbidden_rectangle_tests']==2 and scan['counts']['strict_open_box_tests']==4
 assert scan['counts']['connectivity_BFS_started']==scan['counts']['connectivity_BFS_returned']==2
 assert scan['counts']['connectivity_BFS_popped']==4006 and scan['counts']['connectivity_neighbor_tests']==16024
 assert scan['counts']['independent_legality_calls']<=bounds['max_N_and_candidate_closed_legality_calls'] and scan['counts']['connectivity_BFS_popped']<=bounds['max_BFS_popped']
 checks.append('54 labels / 44 detailed suffixes / 10 duplicate-base skips / 16 physical cuts; phase indices and saved counts bound, no geometry replay')
 usable=read(H/'usable_snapshots_v02.json');assert usable['count']==len(usable['selected'])==2
 assert {s['base_id'] for s in usable['selected']}=={'large_Z','medium_Z'}
 for s in usable['selected']:
  n,e=read(H/s['N']),read(H/s['E']);initial=read(H/s['initial_E_not_for_algorithm']);P=ps(n['published_targets']);F=ps(e['free']);hh=ps(n['covered']);U=ps(n['targets'])-hh;removed=ps(n['free'])-F
  assert len(removed)==1 and removed<=hh and not removed&U
  assert P==ps(e['published_targets']) and hh==ps(e['covered']) and U==ps(e['targets'])-hh
  assert ps(e['targets'])==P&F and ps(e['deferred_targets'])==P-F-hh==set()
  assert initial['free']==e['free'] and ps(initial['targets'])!=P&F
  assert all(n[k]==e[k] for k in n if k not in ('free','targets','deferred_targets'))
  for fn in (s['contract_freeze'],str((H/s['certificate']).parent.relative_to(H))+'/freeze.json'):
   for p,d in read(H/fn)['files'].items():assert sha(H/p)==d
  cert=read(H/s['certificate']);ct=read(H/s['contract_certificate']);r=read(H/'records'/(s['id']+'.json'))
  assert sha(H/s['N'])==ct['N_sha256'] and sha(H/s['E'])==ct['E_v02_sha256'] and sha(H/s['initial_E_not_for_algorithm'])==ct['original_E_sha256']
  for q in ct['blocked_initial_H_evidence']:assert r['prefix'][q['first_original_prefix_index']]==q['cell'] and tuple(q['cell']) in hh
  assert cert['N_legal'] and cert['remaining_all_reachable']
  for b in cert['strict_coverage_blockages']:
   assert b['pending_at_start']>=2 and b['edge']<b['last_first_service_index']
   er=r['edges'][b['edge']];assert er['a']==b['a'] and er['b']==b['b'] and er['pending_at_start']==b['pending_at_start']
   assert list(removed)[0]==tuple(b['obstacle'])
 checks.append('2 first-qualified Z snapshots and prior H witnesses intact; v02 active T valid, P/H/U unchanged, initial E draft retained')
 hypo=read(H/'hypothetical_occlusion_annotations.json');assert hypo['count']==6 and hypo['geometric_tests_on_these_positions']==hypo['E_maps_constructed_for_them']==0
 assert all(l[k]==0 for k in ('algorithm_or_core','R_repair','candidate_coverage_routes','shortcut','performance_batches','new_closed_loops'))
 assert len(list((H/'figures').glob('*.png')))==2 and read(H/'figure_qa.json')['new_geometry_BFS_core_R_post']==0
 assert (ROOT/'当前进度与下一步.md').read_bytes().endswith((H/'root_before.md').read_bytes())
 final=H/'final_receipt.json'
 if final.exists():
  f=read(final)
  for p,d in f['files'].items():assert sha(H/p)==d,p
  actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert actual==set(f['files'])
  assert sha(ROOT/'当前进度与下一步.md')==f['root_sha256'];checks.append('final seal '+str(len(actual))+' files and root progress intact')
 else:assert '--preseal' in sys.argv
 print(json.dumps({'passed':True,'mode':'sealed' if final.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'selected_distinct_bases':2,'new_algorithm_core_R_post_performance_calls':0,'new_geometry_calls':0,'new_BFS_calls':0,'writes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
