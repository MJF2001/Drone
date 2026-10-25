from common import *
from analyze import compute,summarize,metrics_totals,timing,selected_figures
from input_audit import audit_all
from novelty import compute as compute_novelty
import csv
def main():
 protect();p=read(H/'protocol.json');old=R/'PPCPP保留末采集格候选_v0.1_20261020'
 for name,item in p['reused'].items():assert sha(H/name)==sha(R/item['source'])==item['sha256']
 # Referenced old gates were sealed and reviewed; no rerun or exact calls here.
 oldseal=read(old/'source_seal.json');oldmanifest=read(old/'manifest.json')
 for f in ('candidate.py','runtime.py','worker.py','audit.py','common.py','gate_index.json','gate_exact_bounds.json'):
  assert sha(old/f)==oldseal['files'][f]==oldmanifest[f]
 assert read(old/'gate_index.json')['calls']==218 and len(read(old/'gate_exact_bounds.json'))==8
 assert read(H/'preflight.json')['passed'] and read(H/'preflight.json')['audit_cache_gate']['passed']
 assert audit_all()==read(H/'input_audit.json')
 nov=compute_novelty();assert nov==read(H/'novelty.json');assert nov['old_records']==143
 # Reproduce D4 shape grouping using a second coordinate implementation.
 def second(c):
  road=points(c['published_targets']);blocked=road-points(c['free']);options=[]
  for swap in (False,True):
   for sx in (-1,1):
    for sy in (-1,1):
     def tr(q):return (sx*q[1],sy*q[0]) if swap else (sx*q[0],sy*q[1])
     transformed=[tr(q) for q in road];dx=min(q[0] for q in transformed);dy=min(q[1] for q in transformed)
     options.append((tuple(sorted((x-dx,y-dy) for x,y in transformed)),tuple(sorted((tr(q)[0]-dx,tr(q)[1]-dy) for q in blocked))))
  return min(options)
 keys={s['id']:second(read(H/'inputs'/f"{s['id']}.json")) for s in p['slots']};groups={x['id']:x['shape_group'] for x in nov['new']}
 for x in keys:
  for y in keys:assert (keys[x]==keys[y])==(groups[x]==groups[y])
 for job in read(H/'gate_index.json')['jobs']:
  x=read(H/'gates'/f"{job['id']}.json");assert x['eligible'] and sha(job['input'])==job['input_sha256'];c=read(job['input']);pa.audit(c,x['raw']['branches']['P0']);assert metric(c,x['raw']['route'])==cross(c,x['raw']['route'])
 for s in p['slots']:
  g=H/'gates';a=read(g/f"{s['id']}__PPCPP.json");b=read(g/f"{s['id']}__ONE.json")
  for k in ('route','trace'):assert a['raw'][k]==b['raw'][k]
 rows,calls,pairs=compute();a=read(H/'analysis.json');assert a['states']==rows and a['calls']==calls and a['summary']==summarize(rows) and a['metric_totals']==metrics_totals(rows) and a['selected']==selected_figures(rows) and a['P0_pairs']==pairs
 for factor,levels in a['strata'].items():
  for value,summary in levels.items():assert summary==summarize([r for r in rows if str(r[factor])==value])
 assert a['copy_exclusions']['exclude_old_state_copies']==summarize([r for r in rows if not r['old_copy']])
 assert a['copy_exclusions']['exclude_old_state_and_shape_copies']==summarize([r for r in rows if not r['old_copy'] and not r['old_shape_copy']])
 support=[r for r in rows if r.get('saved',0)>0 and not r['old_copy'] and not r['old_shape_copy']];criterion=any(x['family']!=y['family'] and x['shape_group']!=y['shape_group'] for x in support for y in support);assert criterion==a['cross_shape_preservation']
 for method,t in a['timing'].items():assert t==timing([c['entry_seconds'] for c in calls if c['method']==method])
 assert pairs==270 and len(rows)==54 and len(calls)==540 and len(list((H/'execution').glob('*.json')))==540
 assert len(read(H/'gate_index.json')['jobs'])==108 and len(list((H/'prep/results').glob('*.json')))==9
 with (H/'54槽位完整状态表.csv').open(encoding='utf-8-sig',newline='') as f:tab=list(csv.reader(f))
 report=(H/'LAST新开发地图验证结果.md').read_text(encoding='utf-8');assert len(tab)==55
 for cells,r in zip(tab[1:],rows):
  expected=[r['id'],r['shape_group'],r['PPCPP_metrics']['length'],r['P1_metrics']['length'],r['LAST_metrics']['length'],r['saved'],f"{r['relative_saved']*100:.4f}",r['selected'],r['P1_status'],r['e']]
  assert '|'+ '|'.join(map(str,expected))+'|' in report and cells[:9]==[str(x) for x in expected[:9]]
 with (H/'540调用时间与分段.csv').open(encoding='utf-8-sig',newline='') as f:tt=list(csv.reader(f))
 assert len(tt)==541
 for cells,c in zip(tt[1:],calls):assert cells[0]==c['id'] and float(cells[6])==c['entry_seconds']
 for name in set(v for v in a['selected'].values() if v):assert (H/'figures'/f'{name}.png').exists() and (H/'figures'/f'{name}.svg').exists()
 if (H/'manifest.json').exists():
  for f,h in read(H/'manifest.json').items():assert sha(H/f)==h,f
 print(json.dumps(dict(verified=True,preparation_calls=9,new_input_gates=108,formal_calls=540,old_inputs_compared=143,source_bytes_unchanged=True,P0_pairs=270,stable_method_state_groups=108,report_rows=54,cross_shape_preservation=criterion,exact_calls=0,manifest_sealed=(H/'manifest.json').exists(),review_status='执行完成，待负责人审核'),ensure_ascii=False))
if __name__=='__main__':main()
