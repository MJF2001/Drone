"""Pure saved-evidence delivery; no new planning or simulation."""
from util import *
import datetime
def main():
    attempts=[json.loads(x) for x in (H/'actual_attempts.jsonl').read_text(encoding='utf8').splitlines()] if (H/'actual_attempts.jsonl').exists() else []
    stubs=(H/'technical_stub_journal.jsonl').read_text(encoding='utf8').splitlines() if (H/'technical_stub_journal.jsonl').exists() else []
    a=read(H/'acceptance.json') if (H/'acceptance.json').exists() else None
    rows=[];totals=dict(entries=0,core_starts=0,core_returns=0,entry_returns=0);graph={};used={v['id']:v for v in attempts}
    for slot in read(H/'call_slots.json'):
        p=H/'logs'/(slot['id']+'.receipt.json');q=read(p) if p.exists() else None
        rows.append(dict(slot=slot,attempt=used.get(slot['id']),receipt=q,unused_reason=None if q else ('not reached: see STOP/session termination' if slot['id'] not in used else 'process started, missing completion receipt')))
        if q:
            for k,v in q['markers'].items():totals[k]+=v
            for k,v in q.get('native_graph',{}).items():graph[k]=graph.get(k,0)+v
    main_bfs=sum(p['independent_log_audit']['main_environment_BFS'] for p in a['proofs']) if a else None
    verifies=[]
    for p in sorted(H.glob('verify*_execution.log')):
        try:verifies.append(dict(log=p.name,**json.loads(p.read_text(encoding='utf8').strip().splitlines()[-1])))
        except (ValueError,IndexError):pass
    chain_files=list((H/'technical_rounds').glob('round_*/chain.json'));tech=[read(p) for p in chain_files]
    tech_worlds=[]
    for p in (H/'technical_rounds').glob('round_*/chain/SYNTHETIC_TECHNICAL_NOT_REAL/sessions/*.json'):
        r=read(p)
        if isinstance(r,dict) and 'environment_BFS' in r:tech_worlds.append(dict(source=str(p.relative_to(H)),ordinary_environment_BFS=len(r['environment_BFS'])))
    counts=dict(actual_process_attempts=len(attempts),**totals,new_stub_API_calls=len(stubs),technical_rounds=len(list((H/'technical_rounds').glob('round_*'))),native_graph=graph,main_environment_BFS=main_bfs,independent_acceptance_BFS=a['independent_audit_BFS'] if a else None,readonly_verifications=verifies,technical_synthetic_graph_ledger=tech,technical_worlds_including_failed=tech_worlds)
    save(H/'18槽实际调用账.json',rows);save(H/'分类计数与图搜索账.json',counts)
    lines=['# 连续事件真实接口有限验收报告','',f"实际交付时间：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。目录日期沿用执行稿。",'',f"整体接口验收：{'通过' if a and a['interface_pass'] else '未通过／已停止'}。真实进程尝试 {len(attempts)}/18，暖入口 {totals['entries']}，核心开始/返回 {totals['core_starts']}/{totals['core_returns']}；新增手写技术桩 {len(stubs)}/24。",'', '以下步数和耗时仅用于核对执行账，不据此排名。三个微型世界只验证接口和两次事件接续。','', '|会话|状态|实际移动|等待tick|响应|跨两事件来源链|', '|---|---|---:|---:|---:|---|']
    if a:
        for p in a['proofs']:
            s=p['summary'];lines.append(f"|{p['session']['id']}|{s['status']}|{s['M']}|{s['waits']}|{s['response_calls']}|{bool(p['two_event_chain'])}|")
        lines+=['',f"W3 两方法均实际触发 tick4 基地发布零移动信用：{a['W3_zero_credit_paths_all_covered']}。未触发时明确保留为真实路径覆盖缺口，不追加输入或改事件。",'', '逐响应保存 inputs 原字节、outputs 完整 native 原路线/trace、实际导入哈希、计时和 core 标记；sessions 保存逐tick状态、移动/等待、信用、计划游标和每事件快照。每个事件2输入由本方法事件1获准路线实际移动前缀重建；两方法若路线相同不强造差异。', '', '独立 auditor 从世界表和实际动作重建全程，未调用 executor/contracts；单次完整路线用既有两套纯指标独立核对。执行器及合同与已审核纯桩包原字节相同；审计器仅移除手写返回/手算结果的绑定，diff已保存。']
    lines+=['','计时：新增权威快照JSON编码、原暖入口、完整返回JSON编码/解码和响应编码均在共同20秒内；原入口获得20秒扣除新增预处理后的余量。严格总时间<20秒才准入。进程启动、导入、传输文件和外部审计在暖入口外，另保存回调总墙钟。单线程，90秒看门狗，无重试，无执行层补全。','',f'图搜索分账见分类计数与图搜索账.json：真实主环境普通BFS {main_bfs}；真实独立验收BFS {a["independent_audit_BFS"] if a else None}；原算法内部图搜索单列；技术桩的代理构造不是实际算法搜索。每次只读verify新增BFS另记，未来复核须自行登记。','', '边界：原PPCPP/P0及P2_MULTI固定入口；单步ON、LAST、四方向均关闭，未使用留出，未新增研究地图、精确搜索或性能批。旧包、冻结源码和历史结果不改，未提交推送。完成即停止，交负责人审核。']
    put(H/'通俗报告.md',('\n'.join(lines)+'\n').encode('utf8'))
    put(H/'review_packet.md',('# 审核入口\n\n1. 通俗报告.md\n2. acceptance.json（六会话独立审计、双指标和第二事件来源链）\n3. 18槽实际调用账.json、分类计数与图搜索账.json\n4. technical_rounds（含失败日志）及技术桩逐次账\n5. seal.json、import_inventory.json、copy_manifest.json、auditor_binding.diff\n6. 只读核验.ps1（不产生新响应；新增普通BFS需登记）\n\n仅接口有限验收，不自动进入下一批。\n').encode('utf8'))
    progress=R/'当前进度与下一步.md';put(H/'root_progress_before.md',progress.read_bytes())
    msg=f"# 最新完成：连续事件真实接口有限验收（实际执行2026-10-22）\n\n整体接口验收{'通过' if a and a['interface_pass'] else '未通过／停止'}；真实入口{totals['entries']}/18、核心开始/返回{totals['core_starts']}/{totals['core_returns']}，新增技术桩{len(stubs)}/24，技术轮次{counts['technical_rounds']}。三个固定微型世界、原PPCPP/P0与P2_MULTI六个独立会话；仅核验真实接口和两事件接续，不排名、不确认研究价值。W3基地发布信用路径两方法均覆盖={a['W3_zero_credit_paths_all_covered'] if a else None}。执行器/合同原字节复用，旧包/冻结源/留出不改，原单步候选关闭，未提交推送。见连续事件真实接口验收_v0.1_20261021/通俗报告.md。已封存停止待审核，不自动启动下一批。\n\n---\n\n"
    progress.write_bytes(msg.encode('utf8')+progress.read_bytes());put(H/'root_progress_after.md',progress.read_bytes())
    exclude={'completion_manifest.json','final_verification_receipt.json'}
    files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in exclude and not (p.parent==H and (p.name.endswith('_execution.log') or p.name=='运行状态.json'))}
    save(H/'completion_manifest.json',dict(files=files,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stopped=True));print('DELIVERED and stopped; no further calls',flush=True)
if __name__=='__main__':main()
