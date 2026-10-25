from common import *
from verify import verify
from analyze import summary,select
from spec import plans,definition,after,before
import csv
def main():
 v=verify();a=read(H/'analysis.json');rows=v['states'];assert a['summary']==summary(rows) and a['selected']==select(rows)
 old=R/'PPCPP小图最优差距诊断_v0.2_20261020'
 for name in ('exact.py','independent.py','common.py','tests.py'):assert sha(H/name)==sha(old/name)
 rc=read(H/'recheck_summary.json');assert rc['calls']==rc['completed']==v['exact_queries'];assert len(rc['rows'])==rc['calls']
 for x in rc['rows']:
  p=H/x['query'];req=p.with_suffix('.request.json');assert x['result_sha256']==sha(p) and x['request_sha256']==sha(req) and x['status']=='complete' and x['wall_seconds']<60
  assert read(p)['length']==x['length'];saved=read(H/'rechecks'/p.parent.name/p.name)
  assert saved=={k:val for k,val in x.items() if k!='query'}
 # Confirm all raw inputs, results and requests accounted without rerunning solvers.
 ledger=a['ledger'];assert ledger==read(H/'call_ledger.json')
 assert ledger['formal_ppcpp']==len(list((H/'execution').glob('*.json')))==36
 assert ledger['preparation_ppcpp']==len(list((H/'prep').glob('*.json')))==6
 assert len(list((H/'inputs').glob('*.json')))==len(list((H/'witnesses').glob('*.json')))==36
 assert ledger['formal_exact']==len(list((H/'exact').glob('*/*.request.json')))==93
 for k,groups in a['strata'].items():
  for label,s in groups.items():assert s==summary([r for r in rows if str(r[k])==label])
 for g,data in a['geometry_groups'].items():assert data['summary']==summary([r for r in rows if r['shape_group']==g])
 supports=[r for r in rows if r.get('E',0)>0 and not r['old_shape_d4'] and not r['old_state_d4']]
 supported={f:sorted({r['shape_group'] for r in supports if r['family']==f}) for f in ('I','L','Z')};assert supported==a['family_support_groups']
 criterion=any(x['family']!=y['family'] and x['shape_group']!=y['shape_group'] for x in supports for y in supports);assert criterion==a['cross_shape_criterion_met']
 assert all(r['d_emin']<r['d_e0'] for r in rows if r.get('near_minus_L0',0)>0)
 # Independently re-audit metrics aggregation and denominators.
 for field,total in a['metric_totals'].items():
  metrics=[r[field] for r in rows if field in r];assert total['N']==len(metrics)
  for k,n in total.items():
   if k not in ('N','weighted_active','weighted_published','weighted_overlap'):assert n==sum(m[k] for m in metrics)
 # Human table vs saved numbers: every cell of the 36-row CSV must match.
 with (H/'状态表.csv').open(encoding='utf-8-sig',newline='') as f:csvrows=list(csv.reader(f))
 assert len(csvrows)==37
 report=(H/'结束位置跨几何验证结果.md').read_text(encoding='utf-8')
 for row,r in zip(csvrows[1:],rows):
  assert row[:5]==list(map(str,[r['id'],r['shape_group'],r['Lp'],r['Lstar'],r['G']]))
  assert '|'+ '|'.join(row)+'|' in report
 assert '执行完成，待负责人审核' in report
 for name in set(v for v in a['selected'].values() if v):
  assert (H/'figures'/f'{name}.png').exists() and (H/'figures'/f'{name}.svg').exists()
 assert read(H/'tests/results.json')['count']==271 and read(H/'tests/new_gates.json')['count']==8
 addendum=read(H/'supplemental_geometry_audit.json');assert addendum['solver_calls']==0 and len(addendum['rows'])==6
 for p in plans():
  d=definition(p['scale'],p['family']);c1,c2=map(tuple,d['obstacle_candidates']);f,t=before(p['scale'],p['family']);assert c1!=c2 and {c1,c2}<=f&t and (0,0) not in (c1,c2)
  assert after(p['scale'],p['family'],'obstacle',c1)[2]=={c2}
 v.pop('states');v.update(input_slots=36,ppcpp_calls=44,independent_rechecks=rc['completed'],report_rows=36,cross_shape_criterion_met=criterion,review_status='执行完成，待负责人审核');print(json.dumps(v,ensure_ascii=False))
if __name__=='__main__':main()
