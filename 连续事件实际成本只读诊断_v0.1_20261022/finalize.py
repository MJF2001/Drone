"""Archive already-saved bytes, human entry points and final manifest only."""
from common import *
import datetime,ast
def main():
    violations=install_guard();index=require_sources()
    for p,v in read(H/'补充冻结来源hash.json')['files'].items():assert sha(p)==v
    for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    copies=[];names=['worlds.json','world_metadata.json','session_order.json','call_slots.json','actual_attempts.jsonl','actual_sessions.jsonl']
    for sj in read(S/'session_order.json'):names.append(str(Path('sessions')/(sj['id']+'.json')))
    for slot in read(S/'call_slots.json'):
        rid=slot['id'];names.extend(str(Path(folder)/(rid+suffix)) for folder,suffix in (('inputs','.json'),('outputs','.json'),('jobs','.json'),('logs','.txt'),('logs','.receipt.json')))
    for name in names:
        source=S/name;dest=H/'原始证据字节副本'/name;dest.parent.mkdir(parents=True,exist_ok=True);put(dest,source.read_bytes());assert sha(dest)==index['files'][str(source)];copies.append(dict(source=str(source),copy=str(dest.relative_to(H)),sha256=sha(dest),byte_identical=True))
    save(H/'原始证据副本清单.json',copies)
    sessions=read(H/'三段实际账与完成尾段.json');rows=['# 三段末状态索引','', '前两段状态均为到达边界并记arrival信用后、边界事件发布前。逐成员H/U/D见JSON指针，未仅按数量比较。','', '|会话/段|段末tick|H/U/D数量|current|previous|E|JSON指针|','|---|---:|---|---|---|---:|---|']
    for i,s in enumerate(sessions):
        for j,p in enumerate(s['segments']):
            q=p['end_state'];rows.append(f"|{s['session']['id']}/{j+1}|{p['depart_tick_range'][1]}|{len(q['H'])}/{len(q['U'])}/{len(q['D'])}|{q['current']}|{q['previous']}|{q['E']}|/{i}/segments/{j}/end_state|")
    put(H/'三段末状态索引.md',('\n'.join(rows)+'\n').encode('utf8'))
    put(H/'review_packet.md',('# 审核入口\n\n1. 通俗结论与裁决建议.md：A为主要支持，B仅I_M线索，C限定两对信用差异。\n2. 三段实际账与完成尾段.json、三段末状态索引.md：36段及末次采完/返航边界。\n3. 最后事件三层一致性.json、接口字段实际使用与源码锚点.json。\n4. 六世界成本守恒分解.json：四类移动与采完/返航两种独立分区，勿重复相加。\n5. I_M不同历史实际证据.json、I_M独有采集格及原始输出指针.json、I_M保存轨迹注记.png。\n6. 两对遮挡信用时间线.json。\n7. source_hashes.json、补充冻结来源hash.json：366+2来源；原始证据副本清单.json/原始证据字节副本保存198个原字节文件。\n8. 零调用总账.json、verify_execution.log、verify_final_execution.log、final_verification_receipt.json。\n\n运行只读核验.ps1只进行hash、保存路线索引、集合和算术重建，不导入原求解模块、不运行旧verify、不新增图搜索或模拟闭环。完成封存停止，不启动实验。\n').encode('utf8'))
    put(H/'只读核验.ps1',("$ErrorActionPreference = 'Stop'\n& (Join-Path $PSScriptRoot '..\\运行环境\\python\\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')\nif ($LASTEXITCODE -ne 0) { throw '只读核验失败' }\n").encode('utf8'))
    # Preparation is byte/hash only. Every stage has zero authorized executions.
    ledgers=[read(H/n) for n in ('main_zero_ledger.json','figure_zero_ledger.json','交付零调用账.json')];ledgers.append(zeros('archive_and_finalization',violations));save(H/'零调用总账.json',dict(all_new_planning_core_candidates_graph_counterfactual_worlds_routes_stub_closed_loops=0,source_package_old_verify_runs=0,stages=ledgers,independent_verifications='See verify logs and final_verification_receipt.json; their all-zero ledgers are printed there',archived_original_byte_files=len(copies),native_modules_imported=0))
    progress=R/'当前进度与下一步.md';put(H/'root_progress_before.md',progress.read_bytes());msg='# 最新完成：已有六世界实际成本位置只读定位（2026-10-22）\n\n全六世界/12会话/36响应只读重建，1992条实际移动、1724次首次信用及36段账通过两种独立方法核对。A为主要解释：L_S/L_M/T_M最后事件F/P/H/U/D/current/previous/base/E等物理任务状态同集合，其各6步差完全对应最后完整响应实际执行长度差，更接近末次剩余规划质量差，不能包装成连续事件专属问题；old_route及算法仍不同，不作单字段因果归因。I_M的12步保留不同历史线索但未证明交换历史或干预收益；I_S/T_S两对2格信用均在tick14/15先采后于tick24遮挡，工作量不同单列。四对30步账为非目标+45、会话重复−15，不自动称绕路或可省。规划/核心/候选/覆盖精确/BFS/Dijkstra/A*/反事实/新世界新路线/模拟闭环均0，未跑旧verify、未导入原求解模块。见连续事件实际成本只读诊断_v0.1_20261022/通俗结论与裁决建议.md。原包/冻结源/留出未改，原单步候选关闭，未提交推送，已封存停止待审，不自动细分或新实验。\n\n---\n\n';progress.write_bytes(msg.encode('utf8')+progress.read_bytes());put(H/'root_progress_after.md',progress.read_bytes())
    files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in ('completion_manifest.json','final_verification_receipt.json') and not (p.parent==H and p.name.endswith('_execution.log'))};save(H/'completion_manifest.json',dict(files=files,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stopped=True,new_graph_and_solver_calls=0));print('Sealed readonly diagnostic',len(files),'files; original byte copies',len(copies),'; no graph or solver calls',flush=True)
if __name__=='__main__':main()
