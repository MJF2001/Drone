from common import *
from verify import verify
from collections import Counter
def summarize(rows):
 paired=[r for r in rows if 'G' in r];positive=[r for r in paired if r['G']>0]
 before=[r for r in paired if r['checkpoints'][0].get('D') is not None]
 after=[r for r in before if r['checkpoints'][1].get('D') is not None]
 return dict(slots=len(rows),paired=len(paired),positive=len(positive),zero=sum(r['G']==0 for r in paired),Lp=sum(r['Lp'] for r in paired),Lstar=sum(r['Lstar'] for r in paired),G=sum(r['G'] for r in paired),mean_relative_gap=sum(r['relative_gap'] for r in paired if r['relative_gap'] is not None)/len([r for r in paired if r['relative_gap'] is not None]) if paired else None,first_recovery_exists=len(before),positive_before=sum(r['checkpoints'][0]['D']>0 for r in before),sum_before_D=sum(r['checkpoints'][0]['D'] for r in before),sum_before_R=sum(r['checkpoints'][0]['R'] for r in before),positive_recovery_increment=sum(r['checkpoints'][1]['D']>r['checkpoints'][0]['D'] for r in after),sum_recovery_increment=sum(r['checkpoints'][1]['D']-r['checkpoints'][0]['D'] for r in after),ending_cost=sum(r.get('ending_cost',0) for r in paired),positive_ending_cost=sum(r.get('ending_cost',0)>0 for r in paired),same_ending_saving=sum(r.get('same_ending_saving',0) for r in paired))
def main():
 x=verify();rows=x['states'];summary=summarize(rows);strata={}
 for key in ('event','shape','scale','progress'):
  strata[key]={str(v):summarize([r for r in rows if r[key]==v]) for v in sorted(set(r[key] for r in rows))}
 positive=sorted([r for r in rows if r.get('G',0)>0],key=lambda r:(-r['G'],r['id']));zero=sorted([r for r in rows if r.get('G')==0],key=lambda r:r['id']);prefix=sorted([r for r in rows if r['checkpoints'] and r['checkpoints'][0].get('D',0)>0],key=lambda r:r['id'])
 selected={k:v[0]['id'] if v else None for k,v in [('max_gap',positive),('zero_first',zero),('positive_prefix_first',prefix)]}
 queries=[read(p) for p in (H/'exact').rglob('*.json') if p.name not in ('mapping.json',) and not p.name.endswith('.request.json')]
 totals={}
 for name in ('ppcpp_metrics','optimal_metrics','fixed_last_metrics'):
  ms=[r[name] for r in rows if name in r];totals[name]={k:sum(m[k] for m in ms) for k in ms[0] if type(ms[0][k]) in (int,float) and k not in ('overlap_ratio','remaining_completion_fraction','active_coverage','published_coverage')}
  totals[name]['weighted_active_coverage']=totals[name]['active_covered']/totals[name]['active_targets'];totals[name]['weighted_published_coverage']=totals[name]['published_covered']/totals[name]['published_targets'];totals[name]['weighted_overlap']=totals[name]['duplicate_target_arrivals']/totals[name]['target_arrivals']
 save(H/'analysis.json',dict(states=rows,summary=summary,strata=strata,selected=selected,metric_totals=totals,query_count=len(queries),query_statuses=dict(Counter(q['status'] for q in queries)),query_max_seconds=max(q['seconds'] for q in queries),query_max_discovered=max(q['discovered'] for q in queries),exact_test_calls=271,ppcpp_calls=dict(preparation=4,formal=24,successful_wrapper_gates=2,aborted_v01_gate=1),note='待研究负责人审核；仅有限开发诊断'))
 old=R/'PPCPP小图最优差距诊断_v0.1_20261020';reuse={}
 for root in ('prep','inputs','witnesses','tests'):
  for p in (H/root).rglob('*'):
   if p.is_file():
    src=old/p.relative_to(H);assert sha(p)==sha(src);reuse[str(p.relative_to(H))]=dict(source=str(src.relative_to(R)),sha256=sha(p))
 save(H/'reuse.json',reuse)
 print(json.dumps(dict(summary=summary,strata=strata,selected=selected,queries=len(queries),max_states=max(q['discovered'] for q in queries)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
