"""Seal evidence, provenance and honest three-column accounts; no algorithm calls."""
from collections import Counter
from pathlib import Path
from v02_utils import HERE,ROOT,read,dump,sha,now
from verify import physical_pairs,assert_saved_identity

def main():
    assert not (HERE/'completion_manifest.json').exists(),'refuse reseal'
    reg=read(HERE/'registration.json')
    stage=read(HERE/'batch_status.json')
    assert len(stage['completed'])==11 and stage['failed']==stage['not_run']==0
    assert stage['attempted']==[j['id'] for j in reg['resume_jobs']]
    freeze=read(HERE/'real_freeze.json')
    for name,digest in freeze['files'].items():
        assert sha(HERE/name)==digest,('real_start_freeze_changed',name)
    for row in read(HERE/'bindings.json'):
        assert sha(HERE/row['copy'])==sha(ROOT/row['source'])==row['sha256']
    original=read(HERE/'original_registration.json')
    for name in original:
        assert reg[name]==original[name]
    ready=read(HERE/'reuse_ready.json')
    old=read(ROOT/ready['source'])
    assert old['passed'] is False and ready['status']=='reused_saved_reaudited'
    assert sha(ROOT/ready['source'])==ready['source_sha256']
    data_by_id={'01_H1':old}
    nc,wc,ic=Counter(),Counter(),Counter()
    rows=[]
    for job in reg['resume_jobs']:
        data=read(HERE/'outputs'/(job['id']+'.json'))
        assert data['passed'] is True and data['precore_ready'] is True
        assert_saved_identity(data)
        nc.update(data['native_counts'])
        wc.update(data['wrapper_counts'])
        ic.update(data['independent']['counts'])
        data_by_id[job['id']]=data
        rows.append({'id':job['id'],'method':job['method'],'passed':True,'core_started':data['native_counts']['core_started'],
            'native_source':data['native_source'],'fallback_selected':data['native_fallback_selected'],
            'native_edges':data['native_raw_edges'],'post_edges':len(data['post']['vertices'])-1,
            'full_edges':len(data['full_route'])-1,'timing':data['timing'],
            'input_sha256':data['input_sha256'],'output_sha256':sha(HERE/'outputs'/(job['id']+'.json'))})
    assert nc['core_started']==nc['core_returned']==nc['core_complete']==11
    assert sum(r['method']=='H1' for r in rows)==5 and sum(r['method']=='P2' for r in rows)==6
    pairs=physical_pairs(data_by_id,reg['cases'])
    assert len(pairs)==6 and not pairs[0]['same_round_timing_pair']
    dump(HERE/'六对物理状态与来源.json',pairs)
    mapping=[]
    table=['# 原12槽最终证据来源','',
           '旧01_H1仍为v0.1 failed；v0.2单列保存返回复核后复用，未新求解。','',
           '|槽|预期类别|证据来源|本轮核心|有效证据状态|','|---|---|---|---:|---|']
    for job in reg['jobs']:
        data=data_by_id[job['id']]
        reuse=job['id']=='01_H1'
        case=next(c for c in reg['cases'] if c['id']==job['case'])
        source=ready['source'] if reuse else str((HERE/'outputs'/(job['id']+'.json')).relative_to(ROOT))
        mapping.append({'job':job,'source':source,'sha256':sha(ROOT/source),
             'v01_original_status':'failed' if reuse else 'not_run',
             'v02_status':'reused_saved_reaudited' if reuse else 'passed',
             'new_core_calls':0 if reuse else 1,
             'reuse_receipt':ready['precheck'] if reuse else None,'original_failure_unchanged':reuse})
        table.append(f'|{job["id"]}|{case["label"]}|'+('v0.1原返回＋v0.2 A04复核' if reuse else 'v0.2新运行')+
                     '|'+('0' if reuse else '1')+'|'+('reused_saved_reaudited（旧failed保留）' if reuse else 'passed')+'|')
    dump(HERE/'12槽最终来源与输出哈希.json',mapping)
    (HERE/'12槽最终来源表.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    # Record actual proof for the two diagonal first-score fixtures and both empty returns.
    focused=[]
    for ident in ('02_H1','04_H1','06_H1','06_P2'):
        data=data_by_id[ident]
        raw=data['native_entry']['raw']
        core=raw['branches']['P0'] if data['method']=='H1' else raw
        record={'id':ident,'core_status':core['status'],'core_source':data['native_source'],
                'pending_in_request':sorted(list(map(list,set(map(tuple,data['core_request']['targets']))-set(map(tuple,data['core_request']['covered']))))),
                'q':data['q'],'base':data['core_request']['base'],'native_route':core['route'],
                'actual_ledger_unchanged':data['actual_before']==data['actual_after']}
        if data['method']=='H1':
            record['first_trace']=core['trace'][0]
        focused.append(record)
    dump(HERE/'斜向首评分与空任务真实返回证据.json',focused)
    phase=read(HERE/'phase_A_counts.json')
    graph=nc['context_BFS_started']+nc['distance_row_BFS_started']+nc['Astar_started']
    wrapper_geo=sum(v for k,v in wc.items() if k.endswith('_geometry'))
    post_geo=sum(nc.get('post_'+p+'_geometry',0) for p in ('source','candidate','output'))
    total_before_verify=phase['counts']['independent_geometry']+wrapper_geo+post_geo+ic['independent_geometry']
    account={'utc':now(),'three_columns':{
         'v01_history':{'gate_failed':1,'native_core':1,'H1':1,'P2':0,'selector':1,'frozen_post':1,
                       'graph_search':2,'old_status_unchanged':True,'source':'真实停止点接入H1_P2最小验收_v0.1_20261022/全部调用与失败分母.json'},
         'v02_old_saved_reaudit':{'core':0,'selector':0,'postprocess':0,'graph_search':0,
                                'phase_A_processes':6,'saved_audits':6,'counts':phase['counts'],
                                'distinct_old_native_outputs_reused':1,'reuse_receipt':ready['precheck']},
         'v02_new':{'slots':11,'passed':11,'failed':0,'not_run':0,'H1':5,'P2':6,'native_core':11,
                    'selector':wc['selector'],'frozen_post':nc['post_entry_calls'],'graph_search':graph}},
         'cross_version_real_entries':12,'cross_version_H1':6,'cross_version_P2':6,
         'cross_version_real_postprocess':12,'cross_version_real_graph_search':2+graph,
         'new_stub_calls':0,'old_wrapper_checks_hash_reused':11,'new_wrapper_checks_rerun':0,
         'phase_A':phase,'new_native_and_post_counts':dict(nc),'new_wrapper_counts':dict(wc),
         'new_runtime_independent_counts':dict(ic),'new_direct_geometry_before_final_verify':total_before_verify,
         'geometry_components':{'phase_A_saved':phase['counts']['independent_geometry'],'new_main_wrapper':wrapper_geo,
                                'new_frozen_post':post_geo,'new_runtime_independent':ic['independent_geometry']},
         'native_new_routes':11,'postprocessed_new_suffixes':11,'full_new_routes':11,'pairs_equal':6,
         'maximum_new_pipeline_seconds':max(r['timing']['pipeline_seconds'] for r in rows),
         'pipeline_late_new':sum(bool(r['timing']['pipeline_late']) for r in rows),
         'new_fallback_sources':{r['id']:r['native_source'] for r in rows if r['fallback_selected']},
         'final_verify_saved_rechecks':'Separately recorded in verify_receipts; never new core/selector/post calls.',
         'new_rows':rows,'detector':0,'closed_loop':0,'holdout':0,'push':0}
    assert graph==54 and total_before_verify==582
    dump(HERE/'三栏调用与几何实际账.json',account)
    dump(HERE/'真实开始后冻结未变.json',{'all_files_unchanged':True,'files':len(freeze['files']),
         'all_six_inputs_byte_identical':True,'all_original_jobs_seeds_limits_unchanged':True,
         'old_01_H1_still_failed':True,'algorithms_resources_credit_geometry_shortcut_unchanged':True})
    report='''# 模块隔离修复及原11槽接续：有限验收报告

本轮通过了给定公开确定地图、有理安全停止快照的真实管线有限验收。v0.2新增11槽全部符合原预期（H1 5、P2 6），旧01_H1完整保存返回经新审核器复核后单列复用，六组物理状态配对一致。跨版本实际核心12入口，不能称v0.2新跑12入口；旧v0.1首槽仍failed，历史状态没有回写。

## 三栏结果

|口径|核心/首连接/真实直达|完整结果与边界|
|---|---|---|
|v0.1历史|1 / 1 / 1|真实H1返回且主管线完成，但外部审核同名冲突导致原槽failed，旧包保留|
|v0.2旧返回复核复用|0 / 0 / 0|6个独立进程各审核同一保存载荷1次，A04为复用凭证；不是6条新路线|
|v0.2新增11槽|11 / 11 / 11|全部通过，新增失败0、未运行0、无补跑；H1 5、P2 6|

六对S/h、gamma、q、H_pred/E_pred、实际信用/资源、任务和基地逐字段相同。第一对旧H1与新P2不属于同轮计时配对。保留算法专用请求字段，不把P2不使用来向混同于物理输入差异。见12槽最终来源表.md及六对物理状态与来源.json。

## 只修了什么

新增唯一包h1p2_gate_audit_v02_20261022，以绝对路径绑定。主审核、几何、H1方向、后处理审核、路径helper均用包内相对依赖；冻结基线的sys.modules['audit']始终属于原source/audit.py，未删除/覆盖，也未为审核器调整sys.path。worker在求解前加载、验证__file__/loader origin/hash与函数身份，求解后和独立审核后再次逐项确认相同，避免上一轮先求解后解析audit的故障。

六输入、12槽顺序/seed、首连接、资源/信用、H1/P2核心及奖励、主几何、冻结直达和全部时间/查询上限保持原字节或明确绑定。主管线pipeline和native_loader/observe均原字节；audit_route/audit_one及冻结后处理audit_one源码段完全相同，改变只有依赖与load_auditor解析。49项真实开始前冻结均保持不变。旧11包装检查只hash复用，新桩响应0，无新算法/数值规则。

阶段A固定6个独立进程，原native先、审核先、H1/P2符号、真实worker前置、verify前置、helpers稳定性均首轮通过；没有进入第二/第三修复轮。记录实际模块路径/hash/loader及函数对象前后身份，不仅检查函数存在。真实核心/选择器/直达/图搜索0；保存审核6次，几何90、距离72、服务交点198。它们是同一旧载荷的技术检查，不是独立地图或质量样本。

## 真实接口证据及调用账

新增核心开始/返回/完成各11。两项斜向H1在q处确实发生首轮带h1_certificate的方向评分并通过独立决策审核；轴向/零接入、已采入口、暂缓目标及空剩余任务返航均有真实返回。空任务的H1走原return分支，P2真实执行multi并返回common_fallback；没有用手写返航替代。P2共4槽选择内部common_fallback，2槽H_scan_opt，来源原样保存，选保底不等于核心未运行。

新增上下文BFS11、距离行BFS10、A*33均完成，共54次图搜索；加旧首槽2次，跨版本56。原内部主审核160次均合法，几何distance查询977、path调用466，H1奖励11次/邻格评分12行、来向更新25次。首连接候选/几何/资源检查各51，排序比较72（角度分支12是子计数）；直达source/candidate/output几何50/34/34，服务92。每请求使用独立缓存，未要求两法内部次数相同。

新包装主几何187、距离构造176、服务交点195，主原/直达/全路线审核各11次；运行时独立整管线审核11次，几何187、距离153、服务交点497、H1方向审核5次/单位边25。阶段A保存90＋新包装187＋新直达118＋运行时独立187＝本版最终verify前直接几何582。最终verify对旧1＋新11保存结果复核的几何/距离/信用另列收据，新增算法/首连接/直达/搜索均0，不能把几何查询说成0。

11条新主管线无迟到，最大观测约58.35毫秒，原30秒/核心20秒/总28秒停止新直达候选规则未改；这只是有限正确性保护的计时记录，不作速度排名、硬实时或一般规模保证。q锁定、首连接计费，完整路线从原S到原基地，原格点后缀先满足整数额度才后处理；不跨gamma删q，不用后处理挽救原超额路线。实际S/h/H/E/M规划前后完全相同，仅预测更新，没有移动执行器。

## 结论边界与停止

成功只针对六个预登记微型手工合成快照，旧失败保留、第一对跨轮复用。证明了本轮接口正确性，不证明任意实数/无理停点、真实探测、未知地图、未来隐藏障碍安全或连续事件闭环，也不形成性能排名或创新结论。留出未使用、未推送。完成封存后停止，由负责人决定下一阶段探测/事件协议；不追加地图、seed或批次。最终独立verify及文件封存状态见final_receipt.json。
'''
    (HERE/'00_通俗报告与三栏结果.md').write_text(report,encoding='utf-8')
    review=r'''# 负责人审核入口

先读00_通俗报告与三栏结果.md、12槽最终来源表.md和三栏调用与几何实际账.json。最终状态看final_receipt.json及verify_receipts/verify_001.json。

- 旧v0.1仍failed；reuse_source/reuse_ready绑定旧原生返回及A04复核凭证，没有01_H1新worker或新首连接/核心/直达。
- registration/original_registration/input_byte_identity：原六输入、顺序/seed/预算不变，resume_jobs只含原11未跑槽。
- prechecks/round_1：六独立进程、每个一次保存复核，实际解析路径/hash/loader/函数身份全部前后一致；核心/选择器/直达/搜索/桩0。
- audit_expected_identity、审核器仅导入隔离.diff、audit_numerical_functions_unchanged：唯一包及全部相对依赖，审核算法不改；冻结基线audit未覆盖。
- 模块绑定与接续包装.diff、real_freeze、真实开始后冻结未变：求解前绑定、后验稳定与11槽一次性接续。
- outputs：每槽原始请求/原生返回先保存，直达原文、完整拼接、实际/预测账、主审核、独立审核和模块身份齐备；两项真实斜向首评分与空任务分支另有聚焦证据。
- bindings/old_files/external_source_guards/源码输入输出哈希：跨版本来源及旧包只读保护。旧11桩只hash复用。
- verify仅加载唯一独立审核包，读取旧1＋新11保存数据，重新计数保存几何；不调用核心/主选择器/后处理或图搜索。实时根进度可继续更新，核验只绑定历史前后快照。

```powershell
.运行环境pythonpython.exe -B -X utf8 '真实停止点接入H1_P2最小验收_v0.2_20261022/verify.py'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

只有新11槽全通过、旧完整返回重审及六物理配对均通过才计有限验收成功；单纯hash verify通过不代替这些条件。封存停止，不自动启动探测/未知地图/连续闭环或性能比较。
'''
    (HERE/'review_packet.md').write_text(review,encoding='utf-8')
    progress='''# 最新完成：H1/P2审核隔离v0.2修复及原11槽接续通过（2026-10-22）

真实停止点接入H1_P2最小验收_v0.2_20261022 已按稿完成，先看00_通俗报告与三栏结果.md、12槽最终来源表.md及review_packet.md，最终独立核验状态见final_receipt.json。新增11槽全部符合原预期：H1 5、P2 6，失败/未运行0，无补跑。旧01_H1保存完整返回经v0.2新审核器复核后单列reused_saved_reaudited，不重跑首连接/核心/直达；旧v0.1仍failed。跨版本真实核心12，不称v0.2新12。六物理状态配对一致，第一对旧H1＋新P2不是同轮计时配对。

唯一审核包及全部相对依赖按绝对路径加载；求解前绑定验证模块__file__/loader origin/hash及函数身份，主管线后和独立审核后身份相同。冻结基线sys.modules['audit']始终原来源，未覆盖/删除、未借sys.path抢占审核器。审核audit_route/audit_one及冻结后处理audit_one源码段不改；六输入、12槽顺序/seed、pipeline/native_loader/observe、核心/奖励、首连接、几何、资源/信用、直达及原预算均字节或明确绑定，49项真实开始冻结不变。

阶段A六独立进程首轮全通过，每个只审核一次旧首槽保存载荷；几何90/距离72/服务198，新核心/选择器/直达/搜索0。旧11包装检查只hash复用、新桩0。两项真实斜向H1首评分、零接入、已采入口、暂缓及空任务返航均实际验收，所有路线仍是预测，实际S/h/H/E/M不改，无移动执行器。

新增核心开始/返回/完成11；上下文BFS11＋距离行BFS10＋A*33＝54搜索均完成，跨版本加旧2＝56。新内部审核160合法、distance977/path466，首连接51候选，直达source/candidate/output50/34/34。运行时独立几何187/距离153/服务497；本版阶段A＋新包装/直达＋运行时独立直接几何582，最终verify新增保存查询另见收据，不是新增算法。11新管线无迟到，计时只供有限保护核验，不作性能排名。

完成封存后停止交审，不追加地图/seed。成功边界仅六个给定公开确定地图、有理安全合成快照的真实管线有限验收；探测距离、任意无理停点、未知地图/隐藏障碍、连续事件闭环、真实安全、速度优势与创新仍未完成/确认。留出未用、旧源/结果不改、无推送。

---
'''
    path=ROOT/'当前进度与下一步.md'
    path.write_text(progress+path.read_text(encoding='utf-8'),encoding='utf-8')
    (HERE/'root_after.md').write_bytes(path.read_bytes())
    dump(HERE/'源码输入输出哈希.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
         if p.is_file() and (p.suffix=='.py' or 'inputs' in p.parts or 'outputs' in p.parts)})
    excluded={'completion_manifest.json','final_receipt.json','封存只读核验.log'}
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
           if p.is_file() and p.name not in excluded and 'verify_receipts' not in p.parts}
    dump(HERE/'completion_manifest.json',{'utc':now(),'status':'SEALED_FINITE_REAL_PIPELINE_ACCEPTANCE_PASSED_STOP',
         'files':files,'root_before':sha(HERE/'root_before.md'),'root_after':sha(HERE/'root_after.md'),
         'real_acceptance_passed':True,'new_core_calls':11,'old_core_reused_without_retry':1,'cross_version_core_calls':12,
         'old_status_failed_unchanged':True,'new_failed':0,'new_not_run':0,'physical_pairs':6})
    print({'sealed_files':len(files),'new_real_calls':11,'old_reused':1,'cross_version_real':12,
           'pairs':6,'new_graph_search':graph,'new_direct_geometry_before_verify':total_before_verify})

if __name__=='__main__':
    main()
