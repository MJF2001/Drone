"""Read-only saved certificates and arithmetic. No graph searches/imports."""
from pathlib import Path
import json,hashlib,time
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(sealed=True):
 t=time.perf_counter();guards=read(H/'source_hashes.json')
 for p,v in guards.items():assert sha(p)==v,p
 plan=read(H/'plan.json')
 for p,v in plan['code_hashes'].items():assert sha(H/p)==v,p
 rows=read(H/'results.json');assert len(rows)==18 and len({r['id'] for r in rows})==18;assert read(H/'pure_receipt.json')['passed'] and len(read(H/'pure_receipt.json')['cases'])==6
 total=0
 for r in rows:
  assert r['audit']['passed'];assert read(H/'states'/(r['id']+'.json'))==r
  ds=read(H/'distance_rows'/(r['id']+'.json'));assert ds['primary']==ds['independent'] and len(ds['primary'])<=3 and not ds['contains_parents'] and not ds['contains_paths'];total+=len(ds['primary'])
  e=r['extraction'];d=r['decision']
  if not e['has_recovery']:assert d['reason']=='no_recovery' and r['Q_components'] is None
  else:
   Q={tuple(p) for p in e['Q']};lookup={tuple(z['source']):{tuple(a['cell']):a['distance'] for a in z['distances']} for z in ds['primary']};dx=lookup[tuple(e['X'])];assert tuple(e['q0'])==min(Q,key=lambda p:(dx[p],p));assert sum(map(len,r['Q_components']))==len(Q)
   if d['conditions'] is not None:
    assert d['trigger']==all(z['on_return'] and z['detour_strict'] for z in d['conditions'])
    for z in d['conditions']:assert z['on_return']==(z['d_R_B']==z['d_R_S']+z['d_S_B']) and z['detour_strict']==(z['d_X_R']<z['d_X_S']+z['d_R_S'])
  assert r['blockage']['old_actual_post_blocked'] is None
 w=read(H/'workload.json');assert w['primary']['component_calls']==w['independent']['component_calls']==27
 assert total==w['primary']['distance_rows']==w['independent']['distance_rows']==11 and total<=54
 assert all(w[k]==0 for k in ('actual_core','actual_post','new_history','candidate_routes','coverage_searches','visibility_queries','geometry_post_queries'))
 assert (R/'当前进度与下一步.md').read_bytes()==(H/'root_after.md').read_bytes() and (H/'root_after.md').read_bytes().endswith((H/'root_before.md').read_bytes())
 old=R/'连续道路与剩余任务地图语义盘点_v0.1_20261023';assert (H/'root_before.md').read_bytes()==(old/'root_after.md').read_bytes()
 count=0
 if sealed:
  f=read(H/'final_receipt.json');assert f['root_sha256']==sha(R/'当前进度与下一步.md')
  for p,v in f['files'].items():assert sha(H/p)==v,p;count+=1
 return dict(passed=True,scope='source/code/seal/root chain and saved primary/independent distance equality, q0 and condition arithmetic, counts ONLY; no new component/distance/geometry queries; independent semantic computations saved in states/workload',states=18,source_hashes=len(guards),sealed_files=count,trigger_opportunities=sum(r['decision']['trigger'] for r in rows),primary_distance_rows=total,independent_distance_rows=total,core=0,post=0,seconds=time.perf_counter()-t)
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
