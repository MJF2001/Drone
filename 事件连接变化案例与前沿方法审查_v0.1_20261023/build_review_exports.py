from pathlib import Path
import json,hashlib,datetime
H=Path(__file__).resolve().parent
def read(p):return json.loads((H/p).read_text(encoding='utf-8'))
def save(p,x):(H/p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def link(p,label):return '['+label+']('+str((H/p).resolve()).replace('\\','/')+')'
assert not (H/'02_六例三seed与12段记录.md').exists()
reg=read('case_registry.json');geo=read('geometry_receipt.json')
s=['# 六例三seed与12段现有连接记录','',
 '以下仅转录已保存数据，不重新运行几何/规划/信用检查。三seed一并列出；状态差为三个(B−C)/C的平均，不用平均距离的比值替代。完整对象列表、名义锚点、信用见证顺序、PPCPP trace、返航边和原路径见每例JSON；P2内部最终visits未保存，保持未核实。','',
 '|状态|seed|B总距离m|C总距离m|(B−C)/C|B共同端到端s|C共同端到端s|',
 '|---|---:|---:|---:|---:|---:|---:|']
for c in reg['cases']:
 for p in c['all_three_seed_pairs']:
  s.append(f"|{c['case']}|{p['seed']}|{p['B']:.9f}|{p['C']:.9f}|{p['B_C_distance_extra']:.6%}|{p['time_B']:.9f}|{p['time_C']:.9f}|")
s+=['','时间是原OFF包的共同端到端口径，含其必要包装，不是算法数学复杂度或无开销固有耗时。没有新计时。','',
 '## 当前状态与完整记录','',
 '|状态|当前S/来向点|基地/捕食者|输入targets数/H数/暂缓数|输入资源上限|全部语义/路径/返航|',
 '|---|---|---|---|---:|---|']
for c in reg['cases']:
 x=read('case_records/'+c['case']+'.json');a=x['after']
 s.append('|'+c['case']+'|'+str(a['current'])+' / '+str(a['previous'])+'|'+str(a['base'])+' / '+str(a['predator'])+'|'+str(len(a['targets']))+' / '+str(len(a['covered']))+' / '+str(len(a['deferred_targets']))+'|'+str(a['distance_budget'])+'|'+link('case_records/'+c['case']+'.json','原完整记录')+'|')
s+=['','targets/H/暂缓为实际输入字段计数，不将遮挡暂缓任务算作已采集；资源上限单位按原协议为米，非真实能耗。','',
 '## 12段转录及前后合法性','',
 '|状态|段类型/原字段及索引|端点a→b|前合法|后合法|关系|',
 '|---|---|---|---|---|---|']
for g in geo['records']:
 relation='新增任务关系，非旧连接失效' if g['relation_label']=='new_task_relation_not_old_task_connection' else '旧任务/基地通行关系'
 s.append(f"|{g['case']}|{g['kind']} / {g['field']}[{g['index']}]|{g['a']} → {g['b']}|{g['legal']['before']}|{g['legal']['after']}|{relation}|")
s+=['','原旧后缀线段选择若未触及删格按预登记回退首边；不得在本表之后再补段。下面hash为公开自由格集合的规范编码摘要；边界仍按闭禁飞格面域判定，不能仅按格心。实际地图快照文件的字节hash另保留在A_registration_freeze。','',
 '|状态|事件前F规范SHA256|事件后F规范SHA256|','|---|---|---|']
for c in reg['cases']:
 g=next(g for g in geo['records'] if g['case']==c['case'])
 s.append(f"|{c['case']}|{g['before_F_sha256']}|{g['after_F_sha256']}|")
s+=['','完整每段source_file、source SHA256、前后实际input路径及字节hash、端点是否原公开任务、新公开任务标记均见 '+link('geometry_receipt.json','几何原回执')+'。24次合法性调用，变化0；未作最短路/全边枚举。']
(H/'02_六例三seed与12段记录.md').write_text('\n'.join(s)+'\n',encoding='utf-8')
ledger={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'complete_pending_read_only_seal',
 'algorithm_counts':dict(planning_entry_calls=0,core_calls=0,path_searches=0,coverage_searches=0,candidate_routes_generated=0,new_routes=0,new_closed_loops=0),
 'geometry':geo['counts'],'existing_segment_pairs':len(geo['records']),'geometry_stage_executions':1,'geometry_replay_in_verify':0,
 'saved_development_states':54,'selected_cases':6,'saved_seed_pairs':18,'plot_seed':20261020,
 'literature_candidates':10,'deep_papers':4,'recommended_implementation_mechanisms':0,
 'web_tool_batches_saved':9,'direct_pdf_requests':4,'direct_metadata_version_requests':9,'direct_metadata_successes':8,'direct_metadata_failures':1,
 'document_tool_issues':['unavailable fitz import before processing; preserved failed source; switched to existing pypdf','one GBK stdout failure; re-read with -X utf8; no research data changed'],
 'read_only_source_issues':['web PDF/DOI/API opens failed, raw retained; primary PDF/metadata separately fetched','aaai24 branch name 404; actual aaai branch README identifies AAAI24 paper; commit fixed'],
 'new_maps':0,'holdout_used':False,'training_or_installation':False,'push':False,'stop_after_seal':True}
save('ledger.json',ledger)
save('sources/version_status_final.json',{'TRACE':{'paper':'2609.21777v1','source_code_status':'not independently located; not asserted nonexistent'},'OARP_Replan':{'paper':'2311.17837v2','full_code_status':'not independently located; solvers are not complete implementation'},'FALCON':{'branch':'ros1-noetic','commit':'312eb4d32c6c7af1a482f94a0a204aa2bb150cca','commit_date':'2025-05-16'},'LS_MCPP':{'default_README_branch_claim':'aaai24','claim_query_status':404,'actual_branch':'aaai','commit':'c7dec715d764d35593b40f32d49e70b7eb352455','commit_date':'2024-03-07','README_identifies_this_AAAI_paper':True,'master_extension_not_used_for_AAAI_technical_results':True},'paper_code_executed':False})
save('sources/document_stdout_issue.json',{'issue':'inspect_pages.py called without -X utf8 once; GBK stdout UnicodeEncodeError before output.','resolution':'same saved PDF text re-read with -X utf8; no file changed; no algorithm/geometry call.','algorithm_calls':0,'geometry_calls':0})
save('review_packet.json',{'stageA_frozen':True,'cases':read('stageA_summary.json')['cases'],'registered_connections_changed':0,'direct_causal_support':False,'post_event_association_cases':4,'counterexamples':2,'hypothesis_scope':'event-connection-loss trigger not supported by these registered examples; generic route improvement and untested edges remain unresolved','literature_candidates':10,'deep_papers':4,'mechanisms_to_implement':0,'algorithm_counts':ledger['algorithm_counts'],'geometry':ledger['geometry'],'deliverable':'00_通俗结论与审核入口.md','stop_after_seal':True})
print(json.dumps({'exported_seed_pairs':18,'segments':12,'deep_notes':4,'algorithm_calls':0,'additional_geometry_calls':0},ensure_ascii=False))
