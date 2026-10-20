import json
import statistics
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
NEW=HERE.parent/'DeepSeek_底层算法开发比较_20261018'
rows=[json.loads(p.read_text(encoding='utf-8')) for p in (NEW/'runs').glob('*/results/*.json')]
dev=[r for r in rows if r.get('kind')=='development']
assert len(dev)==300
groups=defaultdict(dict)
for r in dev: groups[(r['batch'],r['case_id'],r['seed'])][r['method_id']]=r
pairs=Counter(); allpairs=Counter()
for g in groups.values():
 p=g['P2_MULTI']
 for m,r in g.items():
  if m=='P2_MULTI':continue
  if p.get('audit',{}).get('valid') and r.get('audit',{}).get('valid'):
   k='p2_short' if p['route_steps']<r['route_steps'] else 'tie' if p['route_steps']==r['route_steps'] else 'p2_long'
   allpairs[k]+=1
   if p.get('within_budget') and r.get('within_budget'):pairs[k]+=1
examples=[]
for r in dev:
 if r['method_id']=='P2_MULTI' and r['case_id']=='large_g1_development' and r['seed']==20261018:
  examples.append({k:r.get(k) for k in ('batch','route_steps','call_total_seconds','within_budget','final_source','termination')}
                  | {'improvements':r['meta'].get('improvements'),'active_stage':r['meta'].get('active_stage')})
caps=[]
for r in dev:
 if r['method_id']=='OARP_CORE2' and r['seed']==20261018:
  caps.append({'batch':r['batch'],'case':r['case_id'],'steps':r.get('route_steps'),
               'rank_cap':r['meta'].get('rank_cap'),'rank_status':r['meta'].get('rank_status'),
               'solver':r['meta'].get('solver'),'core_status':r['meta'].get('core_status'),
               'natural':r['termination'].get('natural')})
longp2=[r for r in dev if r['method_id']=='P2_MULTI' and r['batch']=='LONG120']
stages=defaultdict(float)
for r in longp2:
 for name,value in r.get('stage_seconds',{}).items():
  if name.startswith('engine:') and isinstance(value,(int,float)):
   stages[name]+=value
result={'dev_rows':len(dev),'paired_inbudget':dict(pairs),'paired_all_valid_diagnostic':dict(allpairs),
        'p2_large_g1':examples,'oarp_caps':caps,
        'p2_long_total_seconds':sum(r['call_total_seconds'] for r in longp2),
        'p2_long_stage_totals':dict(sorted(stages.items(),key=lambda item:-item[1]))}
matched=[]
for method in ('TREE_MST','OARP_CORE2','PPCPP_CORE4','EPSILON_STAR'):
 pairs_long=[]
 for (batch,case,seed),group in groups.items():
  if batch!='LONG120':continue
  p=group['P2_MULTI'];r=group[method]
  if p.get('within_budget') and r.get('within_budget') and p['audit']['valid'] and r['audit']['valid']:
   pairs_long.append((p,r))
 matched.append({'method':method,'n':len(pairs_long),
  'p2_median_seconds':statistics.median(p['call_total_seconds'] for p,r in pairs_long),
  'other_median_seconds':statistics.median(r['call_total_seconds'] for p,r in pairs_long),
  'median_paired_time_ratio_p2_over_other':statistics.median(p['call_total_seconds']/r['call_total_seconds'] for p,r in pairs_long)})
result['matched_long_timing']=matched
(HERE/'review_dev_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
