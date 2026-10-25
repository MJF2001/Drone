"""Saved-output reports and figures; no planner or graph imports."""
from common import *
from drawing import draw
import html,datetime
def main():
    a=read(H/'analysis.json');assert 'ALL PASS' in (H/'verify_execution.log').read_text(encoding='utf8');states=read(H/'states.json');links=[]
    for s in states:
        file=draw(s,a);links.append(f'<h3>{s["id"]}</h3><img style="max-width:100%" src="figures/{file}"/>')
    with (H/'48实际OFF_ON路线图.html').open('x',encoding='utf8') as f:f.write('<!doctype html><meta charset="utf-8"><title>新开发48状态实际路线</title>'+''.join(links))
    fixed=['g00_b012','g03_b018','g05_b032'];details=['# 固定三组案例','','全部四条件，固定seed20261020绘图；全三seed保留。',''];data=[]
    for gid in fixed:
        ss=[s for s in a['states'] if s['group']==gid];assert len(ss)==4;details += [f'## {gid}','']
        for s in ss:
            ps=[p for p in a['pairs'] if p['state']==s['id']];data.append(dict(state=s,pairs=ps));p=next(p for p in ps if p['seed']==20261020)
            details += [f'### {s["condition"]}','',f'三seed差值：`{json.dumps(s["by_seed"],ensure_ascii=False)}`；均值/范围：`{s["mean_delta"]}` / `{s["range_delta_L"]}`。','',f'前缀、一步信用和接回状态检查：`{json.dumps(p["action_proof"],ensure_ascii=False)}`。','',f'干预原始日志：`{json.dumps(p["ON"].get("audit",{}).get("intervention_log",[]),ensure_ascii=False)}`。','',f'[输入和实际路线](figures/{s["id"]}.svg)','']
    save(H/'固定三组完整案例.json',data)
    with (H/'固定三组案例.md').open('x',encoding='utf8') as f:f.write('\n'.join(details))
    receipts=[read(p) for p in (H/'logs').glob('*.receipt.json')];outs=[read(p) for p in (H/'outputs').glob('*.json')];orders=read(H/'prep_order.json')+read(H/'gate_order.json')+read(H/'order.json')
    counts={phase:dict(planned=plan()['counts'][phase],processes=sum(r['job']['phase']==phase for r in receipts),entries=sum(r['markers']['entries'] for r in receipts if r['job']['phase']==phase),cores=sum(r['markers']['cores'] for r in receipts if r['job']['phase']==phase),valid=sum(r.get('valid',False) for r in receipts if r['job']['phase']==phase),timely=sum(r.get('timely',False) for r in receipts if r['job']['phase']==phase)) for phase in ('prep','gate','formal')}
    rounds=[read(p) for p in (H/'technical_rounds').glob('*/round_result.json')]
    ledger=dict(cap=390,phases=counts,attempted_processes=len((H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()),real_entries=sum(r['markers']['entries'] for r in receipts),real_cores=sum(r['markers']['cores'] for r in receipts),native_reachability_BFS_started=sum(o['native_geometry_account']['reachability_BFS_started'] for o in outs),native_distance_row_BFS_completed=sum(o['native_geometry_account']['distance_row_BFS_completed'] for o in outs),native_Astar_path_searches_completed=sum(o['native_geometry_account']['Astar_path_searches_completed'] for o in outs),external_generation_BFS=read(H/'generation_ledger.json')['ordinary_BFS'],external_independent_input_audit_BFS=read(H/'input_audit.json')['ordinary_BFS'],external_feasibility_DFS_walks=read(H/'generation_ledger.json')['external_feasibility_walks'],external_final_verify_BFS=0,external_action_audit_BFS=0,external_Dijkstra=0,new_P2=0,new_coverage_exact=0,technical_rounds=rounds,stub_calls_by_round=[read(p) for p in (H/'technical_rounds').glob('*/chain.json')],production_inventory_imports=2,no_retry=True)
    save(H/'call_ledger_final.json',ledger);save(H/'390槽完整状态.json',[dict(job=j,receipt=next((r for r in receipts if r['job']['id']==j['id']),None),status='RAN' if any(r['job']['id']==j['id'] for r in receipts) else 'NOT_RUN') for j in orders])
    layers=[]
    for dimension in ('geometry','L','w','boundary_count','condition'):
        for value in sorted({s[dimension] for s in a['states']}):
            for trigger in (True,False):
                ss=[s for s in a['states'] if s[dimension]==value and s['trigger_expected']==trigger]
                if not ss:continue
                complete=[s for s in ss if s['three_seeds_complete_legal_timely']];ds=[s['mean_delta']['length'] for s in complete]
                layers.append(dict(dimension=dimension,value=value,trigger=trigger,planned=len(ss),complete=len(complete),short=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),long=sum(d>0 for d in ds),net=sum(ds) if len(ss)==len(ds) else None,worst=max(ds) if ds else None))
    csvsave(H/'全部几何长度宽度切点条件分层.csv',layers)
    old=read(D/'analysis.json');sig=a['signal'];tr=a['strata']['triggered'];otr=old['strata']['triggered']
    comparison=dict(old=dict(matrix=[[l,w] for l in (18,30,42) for w in (3,5)],strata=old['strata'],signal=old['signal'],timing=old['timing'],timing_design='OFF then ON; descriptive only'),new=dict(matrix=[[l,w] for l in (24,36,48) for w in (4,6)],strata=a['strata'],signal=sig,timing=a['timing'],timing_design='fixed interleaved'),pooled=False)
    save(H/'新旧两批分别比较.json',comparison)
    table='\n'.join(f'|{k}|{v["planned_states"]}|{v["complete_states"]}|{v["states_shorter"]}|{v["states_equal"]}|{v["states_longer"]}|{v["state_equal_weight_sum_delta_L"]}|{v["worst_increase_steps"]}|' for k,v in a['strata'].items())
    bad=[s for s in a['states'] if s['mean_delta'] and s['mean_delta']['length']>0];negative='\n'.join(f'|{s["id"]}|{s["mean_delta"]["length"]}|{s["range_delta_L"]}|' for s in bad)
    report=f'''# 固定单步实现的新开发尺寸验证

真实入口{ledger['real_entries']}/390，核心{ledger['real_cores']}：6次原版历史准备、96次原版/OFF等价门槛、288次交错OFF/ON正式比较。调用和失败账见call_ledger_final.json与390槽完整状态.json，无补跑。

固定最低继续信号：**{sig['registered_pass']}**。24触发状态按状态等权、三seed均值的净差合计为 **{sig['trigger_state_equal_weight_net_sum_delta_L']}步**，负表示较短；支持几何{sig['support_geometries']}，长度{sig['lengths']}，宽度{sig['widths']}。全部等价/保护/合法及时条件见signal.json。

|分层|计划状态|完整三seed状态|更短|平局|更长|等权净差合计|最坏单配对增加|
|---|---|---|---|---|---|---|---|
{table}

新批变长比例为{tr['states_longer']}/24，最坏增加{tr['worst_increase_steps']}步；旧批分别为{otr['states_longer']}/24、{otr['worst_increase_steps']}步，净差−166步。两批各自展示，不合并样本或用旧收益抵消新损失。是否扩大最坏损失：{tr['worst_increase_steps']>otr['worst_increase_steps']}。

全部变长状态如下，较长ON均保留：

|状态|三seed平均delta|三seed范围|
|---|---|---|
{negative}

副指标触发组均值delta：{json.dumps(tr['mean_delta'],ensure_ascii=False)}。C为采完前步数，R为返航尾段；四类移动和90/180转弯、重复率、覆盖/暂缓/返航/资源与及时见288调用完整指标.csv及144全部OFF_ON配对.csv。未把转弯或时间合成为能耗评分。

正式时间均值/中位/P95/最大（秒）：{json.dumps(a['timing'],ensure_ascii=False)}。正式交错顺序在seal2前固定，可作同批描述性比较；单机小耗时不外推实时保证。

native、动作钩子、candidate、暖入口runtime及独立动作审计文件均原字节复用，algorithm.diff为空；copy_manifest.json给出旧/新hash。只新增生成、调度、阶段/路径绑定和报告。完整非时间决策/options/score/route逐条等价；只按原显式白名单排除独立计时及诊断标识。原算法和旧包保持原样。

输入只有当前公开地图。新目标仅由published_targets−initial_targets产生；历史来自六条原版真实完整轨迹的最早边界切点，新增目标不追认历史信用。独立历史/位置/合同/可行性审核通过；新旧原始hash及平移规范化签名无直接重复。矩阵仍同一直线带族，由已知旧结果者制定，不是统计独立泛化、跨形状验证或最终留出。

独立动作审计重建每个前缀pending与原奖励，仅允许首次新旧竞争处唯一new的一次例外，核查一步信用、previous、资源；随后恢复原策略，不强接旧后缀。24保护状态完整路线/原决策/指标全等。接回记录必须匹配current/previous/pending，资源单列，同坐标不算完整状态相同。核验不调用规划器；普通图搜索按内部/外部单独记账。

固定L24/w4第一个切点、L36/w6第一个切点、L48/w6第二个切点，各四条件见固定三组案例.md，全部48保存路线见48实际OFF_ON路线图.html。全部三seed原值/均值/范围与分层无省略。新旧两批完整分别比较见新旧两批分别比较.json。

有限信号{'保留，供负责人审核是否讨论下一步' if sig['registered_pass'] else '未达到，关闭当前固定单步候选的新开发继续信号'}；不确认论文主算法、普遍收益或部署资格。原H_SIDE方向假设仍关闭，不按负例加规则，不扩充地图，不用留出。封存后停止，等待负责人审核。
'''
    with (H/'通俗报告与完整结果.md').open('x',encoding='utf8') as f:f.write(report)
    with (H/'review_packet.md').open('x',encoding='utf8') as f:f.write('# 审核入口\n\n先读通俗报告与完整结果.md、signal.json、48状态三seed原值均值范围.csv及固定三组案例.md。原始输出/动作日志、实现copy_manifest与空algorithm.diff、binding_and_reporting.diff、技术各轮原始失败/回归、两seal、96等价与72保护配对、390计划/实际与内部外部搜索账均保留。只读核验.ps1和verify_execution.log用于复核，规划器调用0。\n')
    root=R/'当前进度与下一步.md';before=root.read_bytes()
    with (H/'root_progress_before_completion.md').open('xb') as f:f.write(before)
    addition=f'# 最新完成：固定单步实现新开发尺寸验证（2026-10-21）\n\n真实入口{ledger["real_entries"]}/390、核心{ledger["real_cores"]}；6历史准备＋96等价门槛＋288交错正式比较。新矩阵L24/36/48、w4/6；实现原字节复用。24触发状态{tr["states_shorter"]}短{tr["states_equal"]}平{tr["states_longer"]}长、等权净差{tr["state_equal_weight_sum_delta_L"]}步、最坏+{tr["worst_increase_steps"]}，有限继续信号={sig["registered_pass"]}；24保护全等，完整合法及时与只读verify通过。新旧两批分别报告，仍同一直线带族开发验证，不是留出、独立泛化或主算法验收。见PPCPP首次新旧竞争单步新开发验证_v0.1_20261021/通俗报告与完整结果.md。原H_SIDE方向假设关闭；旧包/冻结源不改，留出不用，不提交推送，已停止待审核。\n\n---\n\n'
    with root.open('wb') as f:f.write(addition.encode('utf8')+before)
    with (H/'root_progress_after_completion.md').open('xb') as f:f.write(root.read_bytes())
    print(json.dumps(dict(status='COMPLETE_STOPPED_FOR_REVIEW',ledger=ledger,signal=sig),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
