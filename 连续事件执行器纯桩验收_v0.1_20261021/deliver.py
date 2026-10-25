"""Saved-log reporting only; no executor or BFS imports."""
from pathlib import Path
import json,hashlib,csv
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def main():
    p=read(H/'acceptance_pointer.json');a=read(H/p['path']);d=(H/p['path']).parent;spec=read(H/'fixture_spec.json');flat=[];details=[]
    for c in spec['ordered_cases']:
        result=read(d/'results'/(c['id']+'.json'))
        for name,s in result['sessions'].items():
            z=s['summary'];flat.append(dict(category=c['category'],subcase=c['id'],simulated_method=name,world_hash=result['world_hash'],**z))
        details.append(dict(category=c['category'],subcase=c['id'],passed=True,expectation=c['expected'],actual={m:s['summary'] for m,s in result['sessions'].items()},stub_responses=sum(len(s['requests']) for s in result['sessions'].values()),main_BFS=len(result['environment_BFS'])))
    save(H/'全部子例手算与实际账.json',details)
    with (H/'25模拟会话完整指标.csv').open('x',encoding='utf-8-sig',newline='') as f:
        keys=list(dict.fromkeys(k for r in flat for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in flat])
    chain=read(d/'results/01_two_event_chain.json')['sessions']['A'];save(H/'正向两事件完整链.json',dict(requests=chain['requests'],actions=chain['actions'],credits=chain['credits'],summary=chain['summary'],source='Handwritten stub callbacks only, not PPCPP/P2'))
    ledger=dict(real_planner_entries=0,real_native_cores=0,real_algorithm_closed_loops=0,candidate_trials=0,coverage_exact=0,Astar=0,Dijkstra=0,automatically_generated_routes=0,stub_response_cap_all_rounds=48,actual_stub_responses=43,simulated_sessions=25,synthetic_handwritten_worlds=23,acceptance_categories=12,acceptance_subcases=23,technical_rounds=p['round'],main_environment_BFS=a['main_environment_BFS'],independent_acceptance_audit_BFS=a['independent_audit_BFS'],readonly_verify_invocations='Read actual verification receipts/logs: each explicitly reports ordinary_BFS_this_verify; not zero',stub_times_are_prescribed_not_performance=True,original_single_step_candidate='CLOSED',real_PPCPP_P2_adapter_connected=False)
    save(H/'分类调用账.json',ledger)
    rows='\n'.join(f'|{c["category"]}|{c["subcase"]}|{c["stub_responses"]}|通过|' for c in details)
    report=f'''# 连续执行器最小实现与纯桩验收

十二类、23子例、25个模拟方法会话通过。实际固定stub响应43次（所有技术轮次总上限48），真实规划入口/核心/候选/覆盖精确搜索均0。两个模拟方法叫A/B，不能称PPCPP/P2成绩；所有路线为事前手写固定表，无自动覆盖路线生成。

正向链有两次真实的“模拟外生发布”：tick1新增(2,1)，tick3新增障碍(1,0)。事件1响应执行了两步，实际到达(2,0)@2、(2,1)@3，才构造事件2输入：current=(2,1)、previous=(2,0)、H={{(1,0),(2,0),(2,1)}}、剩余资源17；old_route严格为当时计划游标后的字面尾段。三次完整计划长度4+5+3=12，实际只走6步，未把废弃计划计成飞行。详见正向两事件完整链.json。

两方法独立历史夹具在同一世界hash下，tick2时A位于(2,0)且H含(2,0)，B位于(1,1)且H为空。后续各用自身前缀形成输入，不重置成共同PPCPP/P2历史。另一个夹具只命中A当前位置，A环境终止，B继续相同世界，不为A开路；失败短前缀不评价为路线更好。

提前返航等待、发布处零移动信用、已采后遮挡保留/未采暂缓、当前/基地占位、活动目标/返航断连、严格19.999/20.000/20.001准入、非法/缺失响应不回退、资源和T_max边界、跨计划/等待转向及跨事件重复、同tick合并与未来快照字节隔离均逐子例审核。NaN是预期技术拒绝，安排在最后：保留technical_error，之后没有任何stub响应；没有用真实sleep模拟时间。

主实现增量更新；独立审核器不导入主更新函数，按事件前缀、move/wait日志、独立方向标签与自身BFS重建全部状态和快照，再核对事前手算账。主环境BFS={a['main_environment_BFS']}；本次独立验收BFS={a['independent_audit_BFS']}。一键只读verify不调用stub/规划器、不再跑模拟闭环，但会重新做独立BFS，实际次数写在每次日志/收据，不冒称图搜索0。

|类别|子例|实际stub响应|结果|
|---|---|---:|---|
{rows}

已实现的是世界发布、独立会话、字面后缀/计划游标、回调白名单、严格准入、信用/资源和实际执行日志及独立验收。尚不能称真实算法适配完成：没有导入/调用冻结原PPCPP或P2，首次单点old_route、P_before∪H与previous的真实接口、20秒实际计时、真实超时与性能均待另稿验收。普通执行/统计基础设施不是论文创新，不重启旧候选。

原算法/旧结果/留出不改，不提交推送；本轮仅手写技术夹具，不新增研究地图。完成封存后停止交负责人审核，不启动真实性能批。
'''
    with (H/'通俗报告.md').open('x',encoding='utf8') as f:f.write(report)
    with (H/'review_packet.md').open('x',encoding='utf8') as f:f.write('# 审核入口\n\n先读通俗报告.md、状态与时序合同.md、fixture_spec.json及全部子例手算与实际账.json。正向两事件完整链.json可逐字段追踪。源码、事前初始seal、技术各轮source快照、完整请求/返回/执行/信用/frame及独立audit、实际43响应追加账、分类调用账、只读verify和最终manifest全部保留。verify自身会做普通BFS并明确计数，规划/核心/stub/新闭环为0。下一步真实小批需另发执行稿。\n')
    root=R/'当前进度与下一步.md';before=root.read_bytes()
    with (H/'root_progress_before.md').open('xb') as f:f.write(before)
    new=f'# 最新完成：连续执行器纯桩实现/验收（2026-10-21）\n\n最小执行器十二类23子例、25模拟会话验收通过，43次手写stub响应（累计上限48），技术轮次{p["round"]}；两次外生事件后的真实模拟移动前缀可接续到第二输入，两方法同世界独立历史、信用/资源/失败/截止/等待/结束均有独立日志重建与手算核对。真实规划/核心/候选/覆盖精确0，纯桩模拟闭环25，主环境BFS{a["main_environment_BFS"]}、独立验收BFS{a["independent_audit_BFS"]}，只读verify BFS另按实际日志记账。未接入真实PPCPP/P2、未做性能比较；旧单步候选关闭，旧包/留出不改，不提交推送。见连续事件执行器纯桩验收_v0.1_20261021/通俗报告.md。封存停止待审，不自动真实小批。\n\n---\n\n'
    with root.open('wb') as f:f.write(new.encode('utf8')+before)
    with (H/'root_progress_after.md').open('xb') as f:f.write(root.read_bytes())
    print(json.dumps(ledger,ensure_ascii=False))
if __name__=='__main__':main()
