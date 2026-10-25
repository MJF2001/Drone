"""Saved-data publication and honest stop; never executes an algorithm."""
from util import *
from analysis import collect
import datetime
def ledger(z):
    markers=dict(entries=0,core_starts=0,core_returns=0,entry_returns=0);graph={};failures=[]
    for row in z['slots']:
        q=row['receipt']
        if not q:continue
        for k,v in q['markers'].items():markers[k]+=v
        for k,v in q.get('native_graph',{}).items():graph[k]=graph.get(k,0)+v
        if q['exit_code']!=0:failures.append(dict(id=row['slot']['id'],receipt=q))
    bfs_main=0
    for sj in read(H/'session_order.json'):
        p=H/'sessions'/(sj['id']+'.json')
        if p.exists():bfs_main+=len(read(p)['environment_BFS'])
    audits=[json.loads(x) for x in (H/'independent_audit_BFS.jsonl').read_text(encoding='utf8').splitlines()] if (H/'independent_audit_BFS.jsonl').exists() else []
    technical=[dict(round=p.parent.name,**read(p)) for p in (H/'technical_rounds').glob('round_*/result.json')];static=sum(r['static_BFS'] for r in technical);verifies=[]
    for p in sorted(H.glob('verify*_execution.log')):
        try:verifies.append(dict(log=p.name,**json.loads(p.read_text(encoding='utf8').strip().splitlines()[-1])))
        except (ValueError,IndexError):pass
    return dict(real_cap=36,nominal_slots=36,attempted_processes=sum(bool(r['attempt']) for r in z['slots']),unused_slots=sum(not r['attempt'] for r in z['slots']),**markers,process_failures=failures,native_internal_graph=graph,main_environment_BFS=bfs_main,independent_actual_audit_BFS=sum(r['BFS'] for r in audits),independent_audit_calls=audits,static_geometry_BFS=static,readonly_verifications=verifies,technical_rounds=technical,new_stub_responses=0,new_coverage_exact_searches=0,no_old_verify_rerun=True)
def analyze():
    z=collect();save(H/'完整开发分析.json',z);save(H/'36槽计划与实际账.json',z['slots']);save(H/'逐事件历史分歧.json',z['event_history_comparison']);save(H/'实际执行段与未执行后缀.json',z['actual_and_unexecuted_segments']);save(H/'三视图汇总.json',z['views']);print('Saved all denominators, histories and actually executed route portions',flush=True)
def main():
    z=read(H/'完整开发分析.json');assert z==collect();counts=ledger(z);save(H/'分类入口与图搜索总账.json',counts);v=z['views'];stopped=(H/'STOP.json').exists();complete=(H/'acceptance.json').exists();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    lines=['# 连续事件六世界固定开发比较报告','',f'交付UTC：{now}。固定开发模板，不是独立现场抽样、留出或普遍性能验证。','',f"本批{'完整结束' if complete else '因技术异常停止'}；真实入口 {counts['entries']}/36，核心开始/返回 {counts['core_starts']}/{counts['core_returns']}，未运行槽 {counts['unused_slots']}。新增手写stub响应0；新增汇总单元夹具不调用执行器或求解器。",'','比较输入与实现事前锁定：I/L/T各S/M，seed20261022；原PPCPP/P0与P2_MULTI，独立历史；只有util配置断言的预算上限/种子发生绑定调整，其余九个复用执行与审计文件原字节相同。固定事件不按位置修改。', '', '## 全六世界分母','', '|方法|成功|环境终止|迟到|无解|资源|tick限制|非法路线|技术中止|未运行|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in ('PPCPP','P2_MULTI'):
        s=v['statuses_per_method'][m];lines.append('|'+m+'|'+'|'.join(str(s[k]) for k in ('success','environment_termination','deadline','solver_no_solution','resource_infeasible','tick_limit','invalid_route','technical_error','not_run'))+'|')
    lines+=['','失败前缀按实际记录，不视为路线优势，不填0或添加任意惩罚。每方法分母始终6，18名义响应槽；逐槽原因见36槽计划与实际账.json。','', '|世界|方法|状态/原因|实际M|结束tick|等待tick|90°/180°|H/U/D|响应|','|---|---|---|---:|---:|---:|---|---|---:|']
    for r in z['session_records']:
        s=r['summary'];lines.append(f"|{r['world']}|{r['method']}|{s['status']}/{s['reason']}|{s['M']}|{s['finish_tick']}|{s['waits']}|{s['turns90']}/{s['turns180']}|{len(s['H'])}/{len(s['U'])}/{len(s['D'])}|{s['response_calls']}|")
    for label,key in (('双方成功的条件性描述','both_success'),('双方成功且最终H和D集合相同的子集','same_final_H_D')):
        group=v[key];lines+=['',f"## {label}：{group['denominator']}/6",'', '|世界|PPCPP M|P2 M|ΔM=PPCPP−P2|H/D相同|','|---|---:|---:|---:|---|']
        for r in group['pairs']:
            lines.append(f"|{r['world']}|{r['methods']['PPCPP']['summary']['M']}|{r['methods']['P2_MULTI']['summary']['M']}|{r['delta_M_PPCPP_minus_P2']}|{r['final_H_D_identical']}|")
        lines+=['', '这是条件性子集，不能宣称无选择偏差。最终信用不同时，即使双方成功也不能称同工作量路线更短。完整H、U、D、已采后遮挡与零移动信用均在完整开发分析.json，未省略集合成员。']
    lines+=['','## 已执行路线与任务信用','', '|世界|最终P大小|H/D等价|首次实际动作差异tick|首次配对输入差异tick|','|---|---:|---|---|---|']
    for r,hist in zip(v['full_worlds'],z['event_history_comparison']):
        w=read(H/'worlds.json')[r['world']];p=set(map(tuple,w['published']))|{tuple(p) for e in w['events'] for p in e['add_targets']};lines.append(f"|{r['world']}|{len(p)}|{r['final_H_D_identical']}|{hist['first_observed_action_difference_tick']}|{hist['first_paired_input_difference_tick']}|")
    lines+=['', '逐事件历史分歧.json保存双方current、previous、H、资源、old_route、原输入hash及实际前缀；每个已审计会话从自己的动作重建输入。动作差异不自动等同某一奖励或重规划的因果解释。四类实际移动和重复率见下表，计划总长不计入M，未执行尾段只作描述。','', '|世界/方法|首次采集移动|初始历史|会话重复|非目标|重复率|零移动信用|已采后遮挡|','|---|---:|---:|---:|---:|---|---:|---:|']
    for r in z['session_records']:
        s=r['summary'];c=s['move_classes'];lines.append(f"|{r['session']}|{c['fresh_target']}|{c['initial_historical']}|{c['session_repeat']}|{c['non_target']}|{r['repeat_ratio']}|{s['zero_move_credits']}|{len(s['historical_now_blocked'])}|")
    lines+=['','## 计算成本','', '|会话|每次完整暖入口秒|均值|中位|最大|累计秒|累计回调墙钟秒|','|---|---|---:|---:|---:|---:|---:|']
    for r in z['session_records']:
        t=r['entry_timing'];lines.append(f"|{r['session']}|{', '.join(format(x,'.6f') for x in t['each'])}|{t['mean']}|{t['median']}|{t['maximum']}|{t['total']}|{r['callback_wall']['total']}|")
    lines+=['', '暖入口沿用上一验收口径：新增权威快照编码、原入口及其必要校验/内部保底、完整返回编码解码和响应编码计入共同20秒，原入口获得扣除预处理后的余量；严格总时间<20秒才执行。启动/导入/传输和外部审计不计，回调总墙钟另列，不与历史单快照耗时拼表。此小批的耗时差仅是当前固定条件下观察。', '',f"普通BFS：静态几何{counts['static_geometry_BFS']}，实际执行环境{counts['main_environment_BFS']}，独立实际审计{counts['independent_actual_audit_BFS']}；已发生只读复核逐次见分类入口与图搜索总账.json，封存后最终复核另见final_verification_receipt.json。原算法内部图搜索：{counts['native_internal_graph']}。没有新增覆盖最优搜索、候选试走、真实门槛调用或旧verify复跑。",'', '## 研究判断与限制','']
    if v['eligible_to_suggest_cost_location_discussion']:
        lines += [f"满足事前允许讨论条件：最终H/D相同的成功配对中，PPCPP实际M更长出现在不同形状族 {v['shapes_with_PPCPP_longer_in_comparable_pairs']}。可交负责人讨论共同成本位置；本批未诊断具体因果，不自动开发机制。"]
    else:lines += ['未满足“至少两个形状族、成功且H/D同集合、PPCPP实际M更长”的讨论条件。只报告本批观察和限制，不为达门槛补图、改事件或追加种子。']
    lines+=['', '环境/接口限制、实际路线差异、耗时差异、任务信用差异分别由上述全分母、M、入口时间及H/D账支持。只有六个固定模板，单一种子、单一预算，无显著性或普遍优越性结论。不把P2升级为论文主算法，不以速度代替路线质量；主算法和创新仍未确认。原单步候选关闭，未使用留出，旧包/冻结源码/历史结果不改，未提交推送。','', '## 六世界全部展示','']
    for wid in read(H/'worlds.json'):lines += [f'### {wid}','',f'![{wid} 全部输入事件与两方法实际轨迹](figures/{wid}.png)','']
    lines+=['图中完整矩形是初始可飞F0，蓝格为P0，橙格为事件1新增待检目标，黑格为事件2禁飞遮挡，线条只画实际移动；若失败则只画真实前缀及终点。原坐标、完整事件表和hash事前保存在worlds.json/world_metadata.json/seal.json。','', '完成或规则停止后即封存待审；不自动追加地图、预算、seed或下一批。']
    put(H/'通俗报告与完整结果.md',('\n'.join(lines)+'\n').encode('utf8'))
    put(H/'review_packet.md',('# 审核入口\n\n1. 通俗报告与完整结果.md（全六世界、两种成功配对、六张完整轨迹图）\n2. 三视图汇总.json、完整开发分析.json、逐事件历史分歧.json\n3. 36槽计划与实际账.json、分类入口与图搜索总账.json、final_verification_receipt.json\n4. inputs/outputs/sessions/logs：原字节、完整native输出/trace、实际执行账、独立审计及双指标\n5. 实际执行段与未执行后缀.json；只把实际移动计M\n6. worlds.json、world_metadata.json、session_order.json、call_slots.json、copy_manifest.json、binding_only.diff、seal.json\n7. technical_rounds及只读核验.ps1：只读verify新增普通BFS须自行登记，无新增求解或模拟响应\n\n本轮是首次六世界固定开发描述批，封存停止，由负责人决定下一步。\n').encode('utf8'))
    progress=R/'当前进度与下一步.md';put(H/'root_progress_before.md',progress.read_bytes())
    msg=f"# 最新完成：首个六世界固定连续事件开发描述批（2026-10-22）\n\n{'完整结束' if complete else '技术异常停止'}；真实入口{counts['entries']}/36，核心开始/返回{counts['core_starts']}/{counts['core_returns']}，未运行槽{counts['unused_slots']}；新stub响应0，技术轮次{len(counts['technical_rounds'])}。原PPCPP成功{v['statuses_per_method']['PPCPP']['success']}/6、P2成功{v['statuses_per_method']['P2_MULTI']['success']}/6；双方成功配对{v['both_success']['denominator']}/6，最终H/D均相同配对{v['same_final_H_D']['denominator']}/6。满足两形状族同信用PPCPP实际M更长的允许讨论条件={v['eligible_to_suggest_cost_location_discussion']}，不自动归因或开发机制。完整正负/失败与信用差异见连续事件六世界开发比较_v0.1_20261022/通俗报告与完整结果.md。固定开发模板，不是留出或现场验证；旧包/冻结源不改，单步候选关闭，未提交推送，已封存停止待审，不追加图/预算/seed。\n\n---\n\n"
    progress.write_bytes(msg.encode('utf8')+progress.read_bytes());put(H/'root_progress_after.md',progress.read_bytes())
    files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in ('completion_manifest.json','final_verification_receipt.json') and not (p.parent==H and p.name.endswith('_execution.log'))}
    save(H/'completion_manifest.json',dict(files=files,created_utc=now,stopped=True));print('DELIVERED and stopped; no further experiments',flush=True)
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--analyze']:analyze()
    else:main()
