"""Offline tables/acceptance curves; no optimizer calls."""
from pathlib import Path
import json,csv,statistics,hashlib,itertools,html
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,rows):
 if rows:
  with (D/name).open('x',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 pr=read(D/'protocol.json');attempts=[json.loads(x) for x in (D/'formal/attempts.jsonl').read_text(encoding='utf-8').splitlines()];assert len(attempts)==200
 assert len({r['run_id'] for r in attempts})==200
 lookup={};rows=[];curves=[];scopes=['RANGE_SEED','RANGE_PLUS1','RANGE_PLUS2','RANGE_ALL'];methods=scopes+['P2_MULTI']
 for entry in attempts:
  j=entry['job'];x=read(entry['result_path']);raw=x['raw'];check=x['independent_route_check'];valid=bool(check.get('valid'))
  row=dict(run_id=j['run_id'],map_id=j['map_id'],method=j['method'],budget=j['budget'],repeat=j['repeat'],seed=j['seed'],valid=valid,steps=check.get('steps') if valid else None,seconds=raw['seconds'],source=raw.get('source'),status=raw['status'],active_stage=raw.get('active_stage'),core_exists=bool(raw.get('core_route')),core_steps=len(raw['core_route'])-1 if raw.get('core_route') else None,global_fallback=raw.get('source') in ('old_suffix','common_fallback'),overrun_gt_10ms=raw['seconds']>j['budget']+.01,overrun_seconds=max(0,raw['seconds']-j['budget']))
  rows.append(row);lookup[j['map_id'],j['budget'],j['repeat'],j['method']]=row
  accepts=raw.get('improvements',[]) if j['method']=='P2_MULTI' else raw['detail']['acceptances']
  for e in accepts:
   assert 0<=e['seconds']<=j['budget']
   curves.append(dict(run_id=j['run_id'],map_id=j['map_id'],budget=j['budget'],repeat=j['repeat'],method=j['method'],seconds=e['seconds'],steps=e['steps'],source=e.get('source',e.get('label')),time_origin='P2_inner_search_entry_unaligned_to_public_entry' if j['method']=='P2_MULTI' else 'public_candidate_entry',public_elapsed_seconds=None if j['method']=='P2_MULTI' else e['seconds']))
 save('all_results.csv',rows);save('accepted_complete_routes.csv',curves)
 maps=sorted({r['map_id'] for r in rows});pairs=[(scopes[1],scopes[0]),(scopes[2],scopes[1]),(scopes[3],scopes[2]),(scopes[3],scopes[1])]+[(m,'P2_MULTI') for m in scopes]
 paired=[];mapmeans=[];summaries=[]
 for b in (1,20):
  for cand,ref in pairs:
   ds=[];rel=[]
   for mid in maps:
    xs=[];ys=[]
    for rep in (0,1):
     x=lookup[mid,b,rep,cand];y=lookup[mid,b,rep,ref];ok=x['valid'] and y['valid'];delta=x['steps']-y['steps'] if ok else None
     paired.append(dict(map_id=mid,budget=b,repeat=rep,candidate=cand,reference=ref,common_valid=ok,candidate_steps=x['steps'],reference_steps=y['steps'],delta=delta,candidate_seconds=x['seconds'],reference_seconds=y['seconds'],candidate_source=x['source'],reference_source=y['source'],candidate_active_stage=x['active_stage'],reference_active_stage=y['active_stage'],candidate_soft_overrun=x['overrun_gt_10ms'],reference_soft_overrun=y['overrun_gt_10ms'],candidate_core_exists=x['core_exists'],reference_core_exists=y['core_exists']))
     if ok:ds.append(delta);xs.append(x['steps']);ys.append(y['steps'])
    if len(xs)==2:
     ratio=statistics.mean(xs)/statistics.mean(ys)-1 if statistics.mean(ys)!=0 else None
     mapmeans.append(dict(map_id=mid,budget=b,candidate=cand,reference=ref,common_seed_pairs=2,candidate_mean_steps=statistics.mean(xs),reference_mean_steps=statistics.mean(ys),relative_delta=ratio))
     if ratio is not None:rel.append(ratio)
   summaries.append(dict(budget=b,candidate=cand,reference=ref,common_valid_seed_pairs=len(ds),full_seed_map_pairs=len(rel),short=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),long=sum(d>0 for d in ds),total_step_delta=sum(ds),median_delta=statistics.median(ds) if ds else None,maximum_degradation=max(ds) if ds else None,equal_map_mean_relative_delta=statistics.mean(rel) if rel else None,zero_denominator_policy='excluded from relative mean; retained in absolute comparisons'))
 save('paired_seed_results.csv',paired);save('paired_map_means.csv',mapmeans);save('paired_summary.csv',summaries)
 save('all_vs_p2.csv',[r for r in paired if r['candidate']=='RANGE_ALL' and r['reference']=='P2_MULTI'])
 wide=[]
 for mid in maps:
  for b in (1,20):
   for rep in (0,1):
    wr=dict(map_id=mid,budget=b,repeat=rep)
    for m in methods:
     row=lookup[mid,b,rep,m]
     for key in ('steps','seconds','source','valid','core_steps','global_fallback'):wr[m+'_'+key]=row[key]
    wide.append(wr)
 save('state_scope_comparison.csv',wide)
 bymethod=[]
 for b in (1,20):
  for m in methods:
   rr=[r for r in rows if r['method']==m and r['budget']==b];bymethod.append(dict(budget=b,method=m,tasks=len(rr),valid=sum(r['valid'] for r in rr),total_steps=sum(r['steps'] for r in rr if r['valid']),mean_seconds=statistics.mean(r['seconds'] for r in rr),soft_overruns=sum(r['overrun_gt_10ms'] for r in rr),max_overrun_seconds=max(r['overrun_seconds'] for r in rr),cores=sum(r['core_exists'] for r in rr),global_fallbacks=sum(r['global_fallback'] for r in rr)))
 save('method_summary.csv',bymethod)
 aliases=[];structure_rows=[];struct=read(D/'input_scope_gates.json')['states']
 for state in struct:
  mid=state['map_id'];plans=state['plan']['plans']
  for scope,cfg in plans.items():
   structure_rows.append(dict(map_id=mid,scope=scope,left=cfg['left'],right=cfg['right'],local_targets=cfg['required_count'],pending_targets=cfg['pending_count'],local_target_fraction=cfg['required_count']/cfg['pending_count'] if cfg['pending_count'] else None,modifiable_old_blocks=cfg['modifiable_blocks'],total_old_blocks=cfg['block_count'],prefix_steps=cfg['prefix_steps'],suffix_steps=cfg['suffix_steps'],alias_of=state['aliases'][scope]))
  for a,z in itertools.combinations(scopes,2):
   ca=plans[a.replace('RANGE_','R_')];cz=plans[z.replace('RANGE_','R_')]
   if ca==cz:
    for b in (1,20):
     for rep in (0,1):
      x=lookup[mid,b,rep,a];y=lookup[mid,b,rep,z];aliases.append(dict(map_id=mid,budget=b,repeat=rep,method_a=a,method_b=z,same_structure=True,steps_a=x['steps'],steps_b=y['steps'],step_delta=x['steps']-y['steps'] if x['valid'] and y['valid'] else None,interpretation='separate timed repetitions of identical structure; not range-effect evidence'))
 save('range_structure_table.csv',structure_rows);save('identical_structure_variation.csv',aliases)
 oracle=[];oracle_summary=[]
 global_complete=[m for m in scopes if all(lookup[mid,b,rep,m]['valid'] for mid in maps for b in (1,20) for rep in (0,1))]
 global_best=min(global_complete,key=lambda m:sum(lookup[mid,b,rep,m]['steps'] for mid in maps for b in (1,20) for rep in (0,1))) if global_complete else None
 for b in (1,20):
  complete=[m for m in scopes if all(lookup[mid,b,rep,m]['valid'] for mid in maps for rep in (0,1))]
  best=min(complete,key=lambda m:sum(lookup[mid,b,rep,m]['steps'] for mid in maps for rep in (0,1))) if complete else None
  for mid in maps:
   for rep in (0,1):
    ok=[lookup[mid,b,rep,m] for m in scopes if lookup[mid,b,rep,m]['valid']];x=min(ok,key=lambda r:r['steps']) if ok else None
    oracle.append(dict(map_id=mid,budget=b,repeat=rep,posthoc_best_method=x['method'] if x else None,posthoc_min_steps=x['steps'] if x else None,best_budget_fixed_method=best,best_fixed_steps=lookup[mid,b,rep,best]['steps'] if best else None,step_gap=lookup[mid,b,rep,best]['steps']-x['steps'] if best and x else None,best_whole_batch_fixed_method=global_best,whole_batch_fixed_steps=lookup[mid,b,rep,global_best]['steps'] if global_best else None,whole_batch_fixed_gap=lookup[mid,b,rep,global_best]['steps']-x['steps'] if global_best and x else None,not_online_equal_budget=True))
  rr=[r for r in oracle if r['budget']==b];oracle_summary.append(dict(budget=b,best_fixed_method=best,posthoc_total_steps=sum(r['posthoc_min_steps'] for r in rr if r['posthoc_min_steps'] is not None),best_fixed_total_steps=sum(r['best_fixed_steps'] for r in rr if r['best_fixed_steps'] is not None),gap=sum(r['step_gap'] for r in rr if r['step_gap'] is not None),states_with_gap=sorted({r['map_id'] for r in rr if (r['step_gap'] or 0)>0})))
 save('posthoc_selection_space.csv',oracle)
 # Each vector chart starts at its first accepted complete route; early missing intervals stay blank.
 figs=D/'acceptance_curves';figs.mkdir(exist_ok=False);links=[];colors=['#0f766e','#2563eb','#9333ea','#ea580c','#111827']
 for mid in maps:
  for b in (1,20):
   for rep in (0,1):
    cc=[r for r in curves if r['map_id']==mid and r['budget']==b and r['repeat']==rep and r['method'] in scopes]
    if not cc:continue
    lo=min(r['steps'] for r in cc);hi=max(r['steps'] for r in cc);span=max(1,hi-lo)
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600">','<rect width="100%" height="100%" fill="white"/>',f'<text x="50" y="30" font-size="20">{mid} / {b}s / seed index {rep}</text>','<path d="M80 70 V510 H950" fill="none" stroke="#555"/>']
    for mi,m in enumerate(scopes):
     seq=sorted((x for x in cc if x['method']==m),key=lambda x:x['seconds']);pts=[]
     for k,e in enumerate(seq):
      xx=80+870*e['seconds']/b;yy=500-400*(e['steps']-lo)/span
      if k:pts.append((xx,pts[-1][1]))
      pts.append((xx,yy))
     if pts:pts.append((950,pts[-1][1]));out.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)+f'" fill="none" stroke="{colors[mi]}" stroke-width="2"/>')
     out.append(f'<text x="{80+mi*175}" y="550" fill="{colors[mi]}" font-size="13">{m}</text>')
    out += [f'<text x="80" y="585" font-size="14">x: public-entry elapsed seconds [0,{b}]; y: accepted complete-route steps [{lo},{hi}]. Early missing is blank.</text>','</svg>']
    name=f'{mid}_b{b}_r{rep}.svg';(figs/name).write_text('\n'.join(out),encoding='utf-8');links.append(f'<li><a href="{name}">{name}</a></li>')
 (figs/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Four-range public-entry acceptance curves</h1><p>P2 engine-relative acceptance records are supplied in accepted_complete_routes.csv. Its wrapper-entry offset was not logged, so it is not overlaid on these public-entry axes.</p><ul>'+''.join(links)+'</ul>',encoding='utf-8')
 summary=dict(formal_tasks=len(rows),formal_valid=sum(r['valid'] for r in rows),formal_core_routes=sum(r['core_exists'] for r in rows),soft_overruns=sum(r['overrun_gt_10ms'] for r in rows),maximum_overrun_seconds=max(r['overrun_seconds'] for r in rows),preflight_calls=10,parameterized_fixture_calls=34,deadline_injection_fixture_calls=4,checker_fixtures=6,worker_pre_solver_failure_fixtures=1,related_regression_tests=25,oracle_warning='Each of four ranges had its own full budget. Posthoc minimum is not an equal-budget online method, global optimum, promised gain or theoretical bound.',posthoc_selection=oracle_summary,paired_summaries=summaries,holdout_used=False)
 (D/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 report=['# 主线固定范围对照验收稿','',f'正式任务 {len(rows)}，合法 {summary["formal_valid"]}；10 次正式地图预检分开保存。合成参数化调用34次，截止注入4次；既有25项回归和6项检查器/故障夹具另列。没有新增初始准备或使用留出。','',f'软预算超过10ms为 {summary["soft_overruns"]} 次，最大超时 {summary["maximum_overrun_seconds"]:.6f} 秒；这是软截止，不能称硬实时保证。','', '## 配对结果','', '|预算|候选|参照|短/平/长|总步差|地图等权平均相对差|','|---|---|---|---|---:|---:|']
 for q in summaries:report.append(f'|{q["budget"]}|{q["candidate"]}|{q["reference"]}|{q["short"]}/{q["equal"]}/{q["long"]}|{q["total_step_delta"]}|{100*q["equal_map_mean_relative_delta"]:.3f}%|' if q['equal_map_mean_relative_delta'] is not None else str(q))
 report+=['','## 事后选择空间','',summary['oracle_warning'],'']
 for q in oracle_summary:report.append(f'{q["budget"]}秒：最佳整批单一固定范围 {q["best_fixed_method"]}，总步数 {q["best_fixed_total_steps"]}；四范围事后最小总步数 {q["posthoc_total_steps"]}，差 {q["gap"]} 步；存在差距的状态 {q["states_with_gap"]}。')
 report+=['',f'跨两预算整批的最佳单一固定范围：{global_best}；相对四范围事后最小值总步差 {sum(r["whole_batch_fixed_gap"] for r in oracle if r["whole_batch_fixed_gap"] is not None)}。各任务值见 posthoc_selection_space.csv。']
 supports=any(q['gap']>0 and len(q['states_with_gap'])>1 for q in oracle_summary)
 report+=['',('这些开发结果支持进一步提出有界的在线选择研究问题；具体依据是上述状态/预算下存在固定范围的互补。尚不支持选择器有效性或创新成立。' if supports else '本批结果不足以支持在线选择有效性；应收缩为固定配置与限时波动诊断。即使有个例差距，也不是在线选择收益承诺。'),'','范围变化共同改变任务规模、接口和保留约束，本轮不分配它们的因果贡献。ALL/P2的包装器比较见 paired_summary；相同结构配置见 identical_structure_variation，差异只能作为限时波动线索。完整最终保底与范围核心分别列出，不把最终保底相等解释为局部机制改善。','', '证据限制：冻结P2的improvements秒数从内部搜索入口起计，baseline_suite公共包装器没有保存入口偏移；这部分不能精确转换成公共入口时间。四范围曲线使用公共候选入口；P2原始接受序列单独标注内部时间，未与四范围叠加。完整路线和总求解秒数仍可审核，但未满足执行稿对P2接受曲线公共入口精确对齐的全部要求。没有为补曲线改正式求解语义、猜测偏移或追加求解。','', '历史70号日志缺口保持历史缺口；本轮独立记录，不回填旧结论。完成规定批次后停止，不扩展地图、种子、范围、预算、锚点、多窗口或自适应机制。','', '只读复核：在本目录用便携 Python 执行 `-B -X utf8 verify_delivery.py`。所有逐项JSON、启动参数、UTC时刻、pid、实际模块路径与哈希、看门狗和尝试记录见 formal/。']
 (D/'主线固定范围对照验收稿.md').write_text('\n'.join(report),encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
