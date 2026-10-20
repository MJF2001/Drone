"""Read-only merge, independent route audit summary, and paired statistics."""
from pathlib import Path
import json,hashlib,statistics,collections,csv
ROOT=Path(__file__).resolve().parent;ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009'/'算法小型验证_20261010';RUN=ALGO/'continuous_history_diagnostics'/'old_plan_warm_global_v0.1_20261017';REC=RUN/'recovery2'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=read(RUN/'protocol.json'); jobs=p['jobs']; data={};attempts={}
for j in jobs:
 rid=j['run_id']; options=[RUN/'runs'/(rid+'.json'),REC/'runs'/(rid+'.json')]
 chosen=None
 for f in options:
  if f.exists():
   q=read(f)
   if q.get('worker_status')=='returned' and q.get('independent_route_check',{}).get('valid'): chosen=q;break
 if not chosen: raise SystemExit('No valid result: '+rid)
 if chosen['case_sha256']!=sha(j['case']):raise SystemExit('case hash mismatch '+rid)
 data[rid]=(j,chosen)
 if j['method']=='P2_WARM_GLOBAL':
  events=chosen['raw'].get('events',[]);ev=next((e for e in events if e.get('stage')=='warm_sequence_audit'),None)
  if not ev or ev['duplicate_count'] or ev['missing_targets'] or ev['extra_targets'] or set(map(tuple,ev['sequence']))!=set(map(tuple,ev['covered_targets'])):raise SystemExit('warm sequence evidence failed '+rid)
  if not any(e.get('stage')=='warm_2opt' for e in events):raise SystemExit('warm stage evidence missing '+rid)
# enforce complete cartesian task matrix
assert len(data)==120
method_stats=[];pair_stats=[];by={}
for rid,(j,q) in data.items():by[(j['map_id'],j['repeat'],j['budget'],j['method'])]=q
for budget in (1,20):
 for method in p['methods']:
  vals=[(m,r,budget,method) for m in sorted({x[0] for x in by}) for r in (0,1) if (m,r,budget,method) in by]
  steps=[by[k]['independent_route_check']['steps'] for k in vals]
  secs=[by[k]['raw'].get('seconds') for k in vals]
  method_stats.append({'budget':budget,'method':method,'n':len(steps),'total_steps':sum(steps),'mean_seconds':statistics.mean(secs),'median_seconds':statistics.median(secs),'overrun_gt_10ms':sum(s>budget+.01 for s in secs),'max_overrun_ms':max([max(0,(s-budget)*1000) for s in secs],default=0),'sources':dict(collections.Counter(by[k]['raw'].get('source') for k in vals))})
 for a,b in [('P2_WARM_GLOBAL','P2_MULTI'),('LITERAL','P2_MULTI'),('LITERAL','P2_WARM_GLOBAL')]:
  deltas=[]; rel_state=[]; maprows=[]
  for m in sorted({x[0] for x in by}):
   aa=[by[(m,r,budget,a)]['independent_route_check']['steps'] for r in (0,1)];bb=[by[(m,r,budget,b)]['independent_route_check']['steps'] for r in (0,1)]
   ds=[x-y for x,y in zip(aa,bb)];deltas.extend(ds);maprows.append({'map_id':m,'a_mean_steps':statistics.mean(aa),'b_mean_steps':statistics.mean(bb),'delta_mean_steps':statistics.mean(ds),'relative_delta_pct':100*(statistics.mean(aa)-statistics.mean(bb))/statistics.mean(bb),'seed_deltas':ds})
  avg_rel=statistics.mean(x['relative_delta_pct'] for x in maprows)
  pair_stats.append({'budget':budget,'a':a,'b':b,'paired_n':len(deltas),'short_tie_long':[sum(d<0 for d in deltas),sum(d==0 for d in deltas),sum(d>0 for d in deltas)],'total_step_delta_a_minus_b':sum(deltas),'mean_relative_delta_pct_map_equal':avg_rel,'median_step_delta':statistics.median(deltas),'worst_degradation_steps':max(deltas),'map_rows':maprows})
# Accepted route improvements and warm stage diagnostics; retain missing early candidate semantics.
curves=[];warm=[]
for rid,(j,q) in data.items():
 if j['method']!='P2_WARM_GLOBAL':continue
 raw=q['raw'];events=raw.get('events',[]);imp=raw.get('improvements',[])
 warm_ev=next((e for e in events if e.get('stage')=='warm_2opt'),{})
 seq_ev=next(e for e in events if e.get('stage')=='warm_sequence_audit')
 warm.append({'run_id':rid,'map_id':j['map_id'],'budget':j['budget'],'repeat':j['repeat'],'sequence':seq_ev['sequence'],'passes':warm_ev.get('passes'),'swaps':warm_ev.get('swaps'),'termination':warm_ev.get('termination'),'warm_seconds':warm_ev.get('end',0)-warm_ev.get('start',0),'accepted_moves':warm_ev.get('accepted_moves',[]),'final_source':raw.get('source'),'solver_seconds':raw.get('seconds'),'improvements':imp,'events':events})
 for e in imp:curves.append({'run_id':rid,'map_id':j['map_id'],'budget':j['budget'],'repeat':j['repeat'],'seconds':e['seconds'],'steps':e['steps'],'source':e['source']})
result={'valid_unique_calls':len(data),'route_audit':'all outputs carry valid independent route_check and case hash matches','warm_sequence_checks':len(warm),'method_stats':method_stats,'paired':pair_stats,'warm_diagnostics':warm,'accepted_improvement_events':curves,'protocol_deviations':['initial dispatch sent LITERAL into baseline dispatcher; 10 initial calls returned exceptions before stop','first recovery had string-vs-Path bug; 60 failed recovery attempts retained','corrected second recovery produced valid outputs; all incomplete/failed rows recovered once; no valid algorithm output was rerun']}
(RUN/'audit_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
with (RUN/'paired_map_rows.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['budget','a','b','map_id','a_mean_steps','b_mean_steps','delta_mean_steps','relative_delta_pct','seed0_delta','seed1_delta'])
 for x in pair_stats:
  for m in x['map_rows']:w.writerow([x['budget'],x['a'],x['b'],m['map_id'],m['a_mean_steps'],m['b_mean_steps'],m['delta_mean_steps'],m['relative_delta_pct'],*m['seed_deltas']])
print(json.dumps({'valid_calls':len(data),'paired':[{k:v for k,v in x.items() if k not in ('map_rows',)} for x in pair_stats],'method_stats':method_stats},ensure_ascii=False))


