"""Final reports, actual saved OFF/ON diagrams and separate call/search ledgers."""
from common import *
import html,datetime
def draw(st,a):
    job=next(r['job'] for r in a['rows'] if r['job']['state']==st['id']);c=read(H/job['input']);F=set(map(tuple,c['free']));T=set(map(tuple,c['targets']));old=set(map(tuple,c['initial_targets']));A=T-old;hist=set(map(tuple,c['covered']));s=12;pw=(st['L']+8)*s+30;height=(st['w']+8)*s+115;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw*3}" height="{height}"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Microsoft YaHei,Arial,sans-serif;font-size:11px}}</style>']
    for k,mode in enumerate(('INPUT','OFF','ON')):
        x0=k*pw+12;y0=44;row=None;r=[]
        if mode!='INPUT':
            row=next(r for r in a['rows'] if r['job']['state']==st['id'] and r['job']['seed']==20261020 and r['job']['mode']==mode);file=H/'outputs'/f'{row["job"]["id"]}.json'
            if file.exists():r=read(file)['result']['raw'].get('route',[])
        text=st['id'] if mode=='INPUT' else f'{mode} L={row["metrics"]["length"] if row["metrics"] else "NA"}, timely={row["timely"]}'
        parts.append(f'<text x="{x0}" y="16">{html.escape(text)}</text>')
        if row and row.get('audit'):parts.append(f'<text x="{x0}" y="32">C={row["metrics"]["completion_step"]}, R={row["metrics"]["return_tail_steps"]}, trigger={row["audit"]["trigger_count"]}</text>')
        for x,y in sorted(F):
            p=(x,y);fill='#ffb64d' if p in A else '#8bb7ec' if p in hist else '#ffeaaa' if p in T else '#f4f4f4';parts.append(f'<rect x="{x0+x*s}" y="{y0+y*s}" width="{s}" height="{s}" fill="{fill}" stroke="#ccc" stroke-width=".4"/>')
        if r:
            C=row['metrics']['completion_step']
            for rr,color,dash in [(r[:C+1],'#206b34',''),(r[C:],'#b51c3e','stroke-dasharray="3 2"')]:
                pts=' '.join(f'{x0+(p[0]+.5)*s},{y0+(p[1]+.5)*s}' for p in rr);parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.7" {dash}/>')
            if mode=='ON' and row['audit']['intervention_log']:
                ev=row['audit']['intervention_log'][0];pts=' '.join(f'{x0+(p[0]+.5)*s},{y0+(p[1]+.5)*s}' for p in (ev['current'],ev['forced_selected']));parts.append(f'<polyline points="{pts}" stroke="#a400ff" stroke-width="4" fill="none"><title>唯一强制一步</title></polyline>')
        for p,color in [(c['base'],'black'),(c['current'],'#e50070')]:parts.append(f'<circle cx="{x0+(p[0]+.5)*s}" cy="{y0+(p[1]+.5)*s}" r="3.5" fill="{color}"/>')
    parts.append(f'<text x="12" y="{height-18}">固定seed20261020；橙新任务／蓝历史／黄旧待检；绿采集段／红虚线返航／紫唯一干预步；全部实际保存路线。</text></svg>');p=H/'figures'/f'{st["id"]}.svg'
    with p.open('x',encoding='utf8') as f:f.write(''.join(parts))
    return p.name
def main():
    a=read(H/'analysis.json');assert 'ALL PASS' in (H/'verify_execution.log').read_text(encoding='utf8');states=read(H/'states_metadata.json');links=[]
    for st in states:
        name=draw(st,a);links.append(f'<h3>{st["id"]}</h3><img style="max-width:100%" src="figures/{name}"/>')
    with (H/'48实际OFF_ON路线图.html').open('x',encoding='utf8') as f:f.write('<!doctype html><meta charset="utf-8"><title>固定48状态OFF与ON实际路线</title>'+''.join(links))
    fixed=[];details=['# 固定三组全部四条件','','仅实际保存结果；完整三seed值见48状态表。第一seed用于图示，不替换失败或挑最短。','']
    for gid in ('g00_b009','g04_b028','g01_b009'):
        details += [f'## {gid}',''];ss=[s for s in a['states'] if s['group']==gid]
        for s in ss:
            ps=[p for p in a['pairs'] if p['state']==s['id']];fixed.append(dict(state=s['id'],pairs=ps));details += [f'### {s["condition"]}','',f'三seed完整差值：`{json.dumps(s["by_seed"],ensure_ascii=False)}`。均值/范围：`{s["mean_delta"]}` / `{s["range_delta_L"]}`。','',f'[输入与OFF/ON实际路线](figures/{s["id"]}.svg)','']
            p=next(p for p in ps if p['seed']==20261020);row=p['ON'];log=row.get('audit',{}).get('intervention_log',[]);details += [f'干预日志：`{json.dumps(log,ensure_ascii=False)}`。','',f'前缀、一步信用和接回检查：`{json.dumps(p["action_proof"],ensure_ascii=False)}`。','']
    save(H/'固定三组完整案例.json',fixed)
    with (H/'固定三组案例.md').open('x',encoding='utf8') as f:f.write('\n'.join(details))
    receipts=[read(p) for p in (H/'logs').glob('*.receipt.json')];outs=[read(p) for p in (H/'outputs').glob('*.json')];ledger=dict(cap=288,attempted_processes=len((H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()),real_entries=sum(r['markers']['entries'] for r in receipts),real_cores=sum(r['markers']['cores'] for r in receipts),OFF_entries=sum(r['markers']['entries'] for r in receipts if r['job']['mode']=='OFF'),ON_entries=sum(r['markers']['entries'] for r in receipts if r['job']['mode']=='ON'),native_reachability_BFS_started=sum(x['native_geometry_account']['reachability_BFS_started'] for x in outs),native_distance_row_BFS_completed=sum(x['native_geometry_account']['distance_row_BFS_completed'] for x in outs),native_Astar_path_searches_completed=sum(x['native_geometry_account']['Astar_path_searches_completed'] for x in outs),external_BFS=0,external_Dijkstra=0,new_coverage_exact_searches=0,new_P2_entries=0,cold_dependency_import_checks=len(list((H/'technical_rounds').glob('*/B1.json'))),production_inventory_imports=1,real_worker_imports_outside_entry_timer=len(outs),no_retry=True)
    save(H/'call_ledger_final.json',ledger);save(H/'288槽完整状态.json',[dict(job=j,execution='RAN' if any(q['job']['id']==j['id'] for q in receipts) else 'NOT_RUN',receipt=next((q for q in receipts if q['job']['id']==j['id']),None)) for j in read(H/'order.json')])
    signal=a['signal'];strata=a['strata'];table='\n'.join(f'|{k}|{v["planned_states"]}|{v["complete_states"]}|{v["states_shorter"]}|{v["states_equal"]}|{v["states_longer"]}|{v["state_equal_weight_sum_delta_L"]}|{v["worst_increase_steps"]}|' for k,v in strata.items())
    report=f'''# 首次新旧竞争单步干预诊断结果

真实入口{ledger['real_entries']}/288、核心{ledger['real_cores']}；144 OFF等价门槛后再144 ON，未补跑。输入是已经看过的开发输入，动作来自开发证据，不是盲测或留出。原H_SIDE方向假设仍关闭。

主量delta=L_ON−L_OFF，负才是该动作收益。预登记有限继续信号registered_pass={signal['registered_pass']}，24触发状态等权三seed均值净差合计={signal['trigger_state_equal_weight_net_sum_delta_L']}步；支持几何={signal['support_geometries']}，长度={signal['lengths']}，宽度={signal['widths']}。完整判据见signal.json，保护组平局不算新增成功。

|分层|计划状态|完整三seed状态|均值更短|平局|更长|状态等权净差合计|最坏单配对增加|
|---|---|---|---|---|---|---|---|
{table}

全部正负状态、三seed原值与范围、C/R与四移动分解、90/180转弯、覆盖/暂缓/返航/资源/及时和耗时见48状态三seed原值均值范围.csv、288调用完整指标.csv及144全部OFF_ON配对.csv。较长ON未被替换成OFF，没有择优双跑。

独立审核从保存前缀重建pending，直接算原奖励并核对每个local选择；仅首次竞争的一条允许例外。重建的一步后previous/pending/资源须正确；其余选择、恢复与返航保持原规则。H_SIDE/CONTROL无触发保护完整路线/原决策/指标一致。接回只在current/previous/pending确实匹配时记录，剩余资源另列，不把同坐标说成完整运行状态相同。

核验实际通过，见verify_execution.log。OFF只剔除equivalence_exclusions.json逐项列出的时间和诊断标识/独立metadata，完整P0 trace/options/score/goal和所有非时间指标相同。新入口明确为{LABEL}，冻结原版不改；candidate原字节复制且只运行PPCPP/P0。

时间只描述：{json.dumps(a['timing'],ensure_ascii=False)}。OFF先于ON，不宣称公平速度优势；没有能耗综合评分。内部普通BFS/原A*过程及外部审计分别记call_ledger_final.json，本批外部奖励/距离审核利用已核对完整矩形的精确曼哈顿式，未新增BFS或路线搜索。

本有限信号仅供负责人决定是否值得另立独立开发验证，不证明普遍机制、可部署或主算法。若未达门槛即关闭本固定单步假设，不加第二步、不改触发时机、不改持续优先new、不挑目标重试。即便通过也不自动开新实验。

固定g00_b009/g04_b028/g01_b009全部四条件见固定三组案例.md，全部48实际路线见48实际OFF_ON路线图.html。旧包、冻结源码、留出不动，Git不提交推送。完成封存后停止交负责人审核。
'''
    with (H/'通俗报告与完整结果.md').open('x',encoding='utf8') as f:f.write(report)
    with (H/'review_packet.md').open('x',encoding='utf8') as f:f.write('# 审核入口\n\n先读通俗报告与完整结果.md、signal.json、48状态三seed原值均值范围.csv，再看固定三组案例.md与全部48实际路线图。技术来源/最小diff、动作桩、每轮整链日志、preseal、OFF_equivalence、protection_equivalence、all_action_audits、288槽账、verify日志和独立调用/搜索账均保留。只读核验.ps1不运行规划器。\n')
    root=R/'当前进度与下一步.md';before=root.read_bytes()
    with (H/'root_progress_before_completion.md').open('xb') as f:f.write(before)
    addition=f'# 最新完成：首次新旧竞争单步干预固定批（2026-10-21）\n\n真实入口{ledger["real_entries"]}/288、核心{ledger["real_cores"]}；144 OFF等价门槛后144 ON，原48已见输入/三seed不变，无额外原版/P2或补跑。有限继续信号registered_pass={signal["registered_pass"]}，触发24状态等权净差合计{signal["trigger_state_equal_weight_net_sum_delta_L"]}步，支持几何{signal["support_geometries"]}。独立原奖励/前缀/唯一次例外/一步信用与保护等价、双指标和只读verify通过；完整正负结果/成本/搜索账保留。见PPCPP首次新旧竞争单步干预诊断_v0.1_20261021/通俗报告与完整结果.md。仅固定开发诊断，不是留出或主算法验收；原H_SIDE方向假设关闭。旧包和冻结原件不改，留出不用，Git不提交推送，完成封存待审，不自动下一实验。\n\n---\n\n'
    with root.open('wb') as f:f.write(addition.encode('utf8')+before)
    with (H/'root_progress_after_completion.md').open('xb') as f:f.write(root.read_bytes())
    print(json.dumps(dict(status='COMPLETE_STOPPED_FOR_REVIEW',ledger=ledger,signal=signal),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
