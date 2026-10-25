"""Read-only delivery verification: no planner calls, no output mutation."""
import csv,sys
from collections import defaultdict
from common import *
from semantics import norm,compare,p0_semantic,last_capture
from analyze import compute
def main():
 manifest=read(H/'manifest.json')
 for name,h in manifest.items():assert sha(H/name)==h,name
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts}
 assert actual==set(manifest),('unexpected/missing files',actual-set(manifest),set(manifest)-actual)
 protect();protocol=read(H/'protocol.json');seal=read(H/'source_seal.json')
 for name,h in read(H/'input_seal.json').items():assert sha(H/name)==h
 for name in ('runtime.py','common.py','audit.py','audit_adapter.py'):assert sha(H/name)==sha(R/'PPCPP_LAST新开发地图验证_v0.1_20261020'/name)
 assert sha(H/'candidate_v1.py')==sha(R/'PPCPP_LAST新开发地图验证_v0.1_20261020/candidate.py')
 a=(H/'candidate_v1.py').read_bytes();b=(H/'candidate_v2.py').read_bytes()
 assert b.replace(b"VERSION='PPCPP_LAST_RESERVE_v0.2'",b"VERSION='PPCPP_LAST_RESERVE_v0.1'").replace(b'full.distance(s.base,q)',b'full.distance(q,s.base)')==a
 gi=read(H/'gate_index.json');adapter=load('speed_verify_adapter',H/'audit_adapter.py');groups=defaultdict(dict);auditors={};expected_stages=[];gate_count=0
 for info in gi['index']:
  rec=read(H/info['path']);c=rec['input'];x=rec['result'];key=json.dumps(c,sort_keys=True)
  if key not in auditors:auditors[key]=adapter.Audit(c)
  assert norm(auditors[key].check(x))==rec['audit']
  assert rec['production_sources']==seal['actual_sources'][info['method']]
  assert x['raw']['version']==('PPCPP_LAST_RESERVE_v0.2' if info['method']=='LAST_V2' else 'PPCPP_LAST_RESERVE_v0.1')
  if info['kind'] in ('regression','fixture'):groups[info['kind'],info['name']][info['method']]=x
  if info['kind']=='deadline_injection':
   expected_stages.append(info['name']);assert not x['eligible'] and x['raw']['status']=='deadline' and x['raw']['selected'] is None and not x['raw']['route']
   assert x['raw']['branches']['P0']['status']=='core_complete' and x['raw']['branches']['P0']['accepted_seconds']<20
   assert any(e['stage']==info['name'] and e['seconds']>=30 for e in x['injection_events'])
  if x['eligible']:assert norm(last_capture(c,x['raw']['route']))==rec['last_capture']
  gate_count+=1
 assert gate_count==259 and expected_stages==protocol['deadline_stages'] and len(groups)==124
 for pair in groups.values():assert compare(pair['LAST_V1'],pair['LAST_V2'])=='equal_complete'
 for item in protocol['inputs']:
  c=read(H/item['input']);golden=read(R/item['golden']);gp=read(R/item['golden_p0'])['raw']['branches']['P0']
  for method in ('LAST_V1','LAST_V2'):
   x=groups['regression',item['id']][method];compare(x,golden);assert p0_semantic(x['raw']['branches']['P0'])==p0_semantic(gp)
 for item in protocol['fixtures']:
  if item['golden']:
   for method in ('LAST_V1','LAST_V2'):compare(groups['fixture',item['id']][method],read(R/item['golden'])['result'])
 dg=read(H/'bfs_internal_deadline.json');assert dg['passed'] and dg['checks']==[0,0,2] and dg['stored_rows']==0
 pg=read(H/'path_direction_gate.json');assert pg['raw_forward']!=pg['raw_reverse_back'] and len(pg['raw_forward'])==len(pg['raw_reverse_back'])==6 and pg['first_v1']!=pg['first_v2']
 cg=read(H/'cache_gate.json');assert len(cg['spies'])==2 and all(x['distinct'] and x['cache_objects']==3 for x in cg['spies']) and cg['offline_audit_gate']['queries']==60
 # Independent base BFS recomputes every saved diagnostic distance/e.
 diagnostics=read(H/'distance_diagnostics.json');assert len(diagnostics)==54
 for item,rec in zip(protocol['inputs'][:54],diagnostics):
  c=read(H/item['input']);u=points(c['targets'])-points(c['covered'])-{tuple(c['current'])};dist=adapter.uncached(points(c['free']),tuple(c['base']))
  assert rec['id']==item['id'] and rec['pending']==len(u)
  assert rec['distances']==[dict(q=list(q),distance=dist[q]) for q in sorted(u)] and rec['e']==list(min(u,key=lambda q:(dist[q],q)))
  # These particular 54 have no zero endpoint, so the observed row counts equal |U|/1.
  assert not rec['zero_distances'] and not rec['base_in_pending'] and rec['v1_rows']==len(u) and rec['v2_rows']==1
 complete=read(H/'completion.json');actual_order=[json.loads(line) for line in (H/'actual_order.jsonl').read_text(encoding='utf-8').splitlines()];planned=read(H/'formal_order.json')
 assert actual_order==complete['actual_order'] and len(actual_order)==810
 for a,b in zip(planned,actual_order):assert all(a[k]==b[k] for k in a)
 assert len(list((H/'execution').glob('*.json')))==len(list((H/'execution').glob('*.log')))==len(list((H/'jobs').glob('*.json')))==810
 for p in (H/'execution').glob('*.json'):
  x=read(p);m=x['job']['method'];assert x['raw']['version']==('PPCPP_LAST_RESERVE_v0.2' if m=='LAST_V2' else 'PPCPP_LAST_RESERVE_v0.1')
  wrong='candidate_v1.py' if m=='LAST_V2' else 'candidate_v2.py'
  assert not any(Path(f).resolve()==H/wrong for f in x['imported_modules'])
 print('HASH/INPUT/MINIMAL-DIFF/259-GATES/54-DISTANCE/810-ORDER verified',flush=True)
 d=compute();saved=read(H/'analysis.json');assert d==saved,'complete recomputation differs'
 byid={c['id']:c for c in d['calls']};bycase={r['id']:r for r in d['states']}
 with (H/'810调用时间与分段.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==810
 for r in rows:
  c=byid[r['id']];assert int(r['sequence'])==c['sequence'] and float(r['entry_ms'])==c['entry_seconds']*1000
  for k in ('p0','candidate','p1','final_audit','encoding'):assert float(r[k+'_ms'])==c['phases'].get(k,0)*1000
 with (H/'54状态配对.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==54
 for r in rows:
  c=bycase[r['id']];assert int(r['saved'])==c['saved'] and json.loads(r['e'])==c['e']
  for m in ('PPCPP','LAST_V1','LAST_V2'):assert float(r[m+'_mean_ms'])==c['methods'][m]['mean']*1000 and json.loads(r[m+'_r0_r4_ms'])==[v*1000 for v in c['methods'][m]['times']]
 with (H/'完整路线指标.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==216
 for r in rows:
  for k,v in bycase[r['id']]['metrics'][r['method']].items():assert r[k]==('' if v is None else str(v))
 with (H/'分层时间配对.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==11
 strata={(s['factor'],str(s['value'])):s for s in d['strata']}
 for r in rows:
  st=strata[r['factor'],r['value']]
  for m in ('PPCPP','LAST_V1','LAST_V2'):assert float(r[m+'_mean_ms'])==st['timing'][m]['mean']*1000
 report=(H/'LAST距离查询等价提速结果.md').read_text(encoding='utf-8')
 for m in ('PPCPP','LAST_V1','LAST_V2'):
  for k in ('mean','median','p95','max'):assert f'{d["timing"][m][k]*1000:.6f}' in report
 assert '270' in report and '540' in report and '162' in report and '5530→5476' in report and '752→796' in report and '90个文件' in report
 fail=read(H/'failures.json');assert fail['formal_calls']==810 and fail['formal_technical_failures']==fail['formal_deadlines']==fail['formal_non_time_discrepancies']==0
 assert 'FileNotFoundError' in (H/'analysis.log').read_text(encoding='utf-8')
 assert len(read(H/'imported_dependency_inventory.json')['optional_package_files_without_individual_preseal'])==90
 print(json.dumps(dict(verified=True,planner_calls=0,manifest_files=len(manifest),gate_calls=259,regression_pairs=114,fixture_pairs=10,formal_calls=810,V1_V2_pairs=270,P0_pairs=540,stable_groups=162,timing=d['timing'],time_pairs=d['time_pairs'],provenance_limitation='90 optional package imported files individually inventoried post-run; not a pre-run seal',status='执行完成，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
