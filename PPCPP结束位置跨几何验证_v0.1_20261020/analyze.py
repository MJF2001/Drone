from common import *
from verify import verify
from collections import Counter
def summary(rows):
 pairs=[r for r in rows if 'G' in r];ends=[r for r in rows if 'E' in r];near=[r for r in rows if 'near_minus_L0' in r];groups={r['shape_group'] for r in rows};positive=[r for r in ends if r['E']>0]
 return dict(slots=len(rows),shape_groups=len(groups),paired=len(pairs),optimal=sum(r['G']==0 for r in pairs),gap_positive=sum(r['G']>0 for r in pairs),Lp=sum(r['Lp'] for r in pairs),Lstar=sum(r['Lstar'] for r in pairs),G=sum(r['G'] for r in pairs),mean_relative_gap=sum(r['relative_gap'] for r in pairs if r['relative_gap'] is not None)/len([r for r in pairs if r['relative_gap'] is not None]) if pairs else None,ending_pairs=len(ends),E_positive=len(positive),E_groups=len({r['shape_group'] for r in positive}),E=sum(r['E'] for r in ends),R=sum(r['R'] for r in ends),gap_without_E=sum(r['G']>0 and r['E']==0 for r in ends),E_positive_no_recovery=sum(not r['has_recovery'] for r in positive),near_finite=len(near),near_less_L0=sum(r['near_minus_L0']<0 for r in near),near_equal_L0=sum(r['near_minus_L0']==0 for r in near),near_greater_L0=sum(r['near_minus_L0']>0 for r in near),near_infeasible=sum(r.get('near_status')=='infeasible' for r in rows),near_less_Lp=sum(r['near_minus_Lp']<0 for r in near),near_equal_Lp=sum(r['near_minus_Lp']==0 for r in near),near_greater_Lp=sum(r['near_minus_Lp']>0 for r in near))
def select(rows):
 choices={'max_E':sorted([r for r in rows if r.get('E',0)>0],key=lambda r:(-r['E'],r['id'])),'zero_G':sorted([r for r in rows if r.get('G')==0],key=lambda r:r['id']),'gap_zero_E':sorted([r for r in rows if r.get('G',0)>0 and r.get('E')==0],key=lambda r:r['id']),'near_worse':sorted([r for r in rows if r.get('near_minus_L0',0)>0],key=lambda r:r['id']),'near_infeasible':sorted([r for r in rows if r.get('near_status')=='infeasible'],key=lambda r:r['id'])}
 return {k:v[0]['id'] if v else None for k,v in choices.items()}
def main():
 x=verify();rows=x['states'];strata={k:{str(v):summary([r for r in rows if r[k]==v]) for v in sorted(set(r[k] for r in rows))} for k in ('family','scale','event','progress')}
 groups={g:dict(summary=summary([r for r in rows if r['shape_group']==g]),states=[r['id'] for r in rows if r['shape_group']==g],families=sorted({r['family'] for r in rows if r['shape_group']==g})) for g in sorted({r['shape_group'] for r in rows})}
 # Conservative evidence: exclude also old road-shape copies, beyond full-state copies.
 support=[r for r in rows if r.get('E',0)>0 and not r['old_state_d4'] and not r['old_shape_d4']];family_groups={f:sorted({r['shape_group'] for r in support if r['family']==f}) for f in ('I','L','Z')}
 cross=any(a!=b and ga!=gb for a in family_groups for b in family_groups for ga in family_groups[a] for gb in family_groups[b])
 totals={}
 for key in ('ppcpp_metrics','optimal_metrics','fixed_original_metrics','fixed_near_metrics'):
  ms=[r[key] for r in rows if key in r]
  if not ms:continue
  fields=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','initial_credit','target_arrivals','duplicate_target_arrivals']
  totals[key]=dict(N=len(ms),**{k:sum(m[k] for m in ms) for k in fields});m=totals[key];m.update(weighted_active=m['active_covered']/m['active_targets'],weighted_published=m['published_covered']/m['published_targets'],weighted_overlap=m['duplicate_target_arrivals']/m['target_arrivals'] if m['target_arrivals'] else None)
 rechecks=read(H/'recheck_summary.json');qs=[read(p) for p in (H/'exact').glob('*/*.json') if p.name not in ('mapping.json',) and not p.name.endswith('.request.json')]
 ledger=dict(preparation_ppcpp=len(list((H/'prep').glob('*.json'))),formal_ppcpp=len(list((H/'execution').glob('*.json'))),wrapper_gate_ppcpp=len(read(H/'gates.json')),formal_exact=x['exact_queries'],independent_formal_rechecks=rechecks['calls'],completed_independent_rechecks=rechecks['completed'],gate_exact_calls=273,gate_independent_oracle_calls=270,gate_checks=279,query_statuses=dict(Counter(q['status'] for q in qs)),query_max_seconds=max(q['seconds'] for q in qs),query_max_states=max(q['discovered'] for q in qs),ppcpp_max_entry=max(r['entry_seconds'] for r in rows if 'entry_seconds' in r))
 save(H/'analysis.json',dict(states=rows,summary=summary(rows),strata=strata,geometry_groups=groups,selected=select(rows),family_support_groups=family_groups,cross_shape_criterion_met=cross,metric_totals=totals,ledger=ledger,review_status='执行完成，待负责人审核'))
 save(H/'call_ledger.json',ledger);print(json.dumps(dict(summary=summary(rows),strata=strata,support=family_groups,cross=cross,selected=select(rows),ledger=ledger),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
