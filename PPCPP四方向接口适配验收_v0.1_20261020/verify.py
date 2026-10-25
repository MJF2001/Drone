"""Read-only verification; no solve or clock-stub invocation."""
import csv
from common_orient import *
from environment import verify as environment_verify
from transform import transform,inverse_input,inverse_raw
from analyze import compute
def main():
 manifest=read(H/'manifest.json')
 for p,h in manifest.items():assert sha(H/p)==h,p
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts};assert actual==set(manifest)
 n=environment_verify();p=read(H/'protocol.json');old=Path(p['old_native']);a=old.read_bytes();b=(H/'interface/ppcpp.py').read_bytes()
 assert sha(old)==p['old_native_sha256'] and sha(H/'interface/ppcpp.py')==p['new_native_sha256']
 b=b.replace(b"VERSION='PPCPP_CORE4_ROTATION_INTERFACE_v0.1'",b"VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'").replace(b' or predator[1]<min(y for x,y in s.free) or predator[1]>max(y for x,y in s.free)',b'').replace(b'predator strictly outside flight-domain bounding rectangle required',b'predator outside fixed flight-domain x bounds required');assert a==b
 for item in p['inputs']:
  assert sha(item['input'])==sha(item['source'])==item['sha256'];c=read(item['input'])
  for k in range(4):tc,m=transform(c,k);assert inverse_input(tc,m)==c
 order=read(H/'order.json');actual_order=[json.loads(s) for s in (H/'actual_order.jsonl').read_text(encoding='utf-8').splitlines()];assert len(order)==len(actual_order)==285
 for x,y in zip(order,actual_order):assert all(x[k]==y[k] for k in x)
 for folder in ('execution','jobs'):assert len(list((H/folder).glob('*.json')))==285
 assert len(list((H/'execution').glob('*.log')))==285
 pure=read(H/'pure_tests.json');assert pure['passed'] and pure['transform_checks']==224 and len(pure['deadline_stubs'])==25 and len(pure['native_body_fake_geometry_stubs'])==2 and pure['real_solver_calls']==0
 assert not (H/'STOPPED.json').exists();d=compute();assert d==read(H/'analysis.json')
 byid={i['id']:i for i in p['inputs']};fixture={i['id']:i for i in p['fixtures']};expected_errors=0
 for info in read(H/'completion.json')['records']:
  x=read(H/info['output']);j=x['job'];c=read(j['input'])
  for rec in x['raw']['candidates']:
   tc,meta=transform(c,rec['degree']//90);assert tc==rec['transformed_input'] and meta==rec['meta']
   assert inverse_input(tc,meta)==c and inverse_raw(rec['raw'],meta)==rec['inverse']
  if j['expected']=='exception':expected_errors+=1;assert x['exception']['type']=='ValueError' and not x['eligible'] and not x['raw']['route']
 assert expected_errors==5
 with (H/'54四方向完整指标.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==216
 for row in rows:
  state=next(s for s in d['states'] if s['id']==row['id']);direction=next(q for q in state['directions'] if q['degree']==int(row['degree']))
  for k,v in direction['metrics'].items():assert row[k]==('' if v is None else str(v))
  assert int(row['selected_degree'])==state['selected_degree']
 ledger=read(H/'call_ledger.json');assert ledger['real_entries']==285 and ledger['real_core_calls']==d['core_calls']==293 and ledger['formal_comparison_entries']==ledger['P2_calls']==ledger['exact_calls']==0
 report=(H/'四方向接口适配验收结果.md').read_text(encoding='utf-8');assert f'{d["totals"]["baseline"]["length"]}→{d["totals"]["selected"]["length"]}' in report
 print(json.dumps(dict(verified=True,new_solver_calls=0,environment_files=n,entries=285,actual_real_core_calls=293,zero_degree_pairs=54,golden_pairs=54,new_directions=216,combo_entries=3,combo_candidate_pairs=12,expected_ValueError_rejections=5,formal_comparison_entries=0,short=d['short'],equal=d['equal'],totals=d['totals'],status='已封存，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
