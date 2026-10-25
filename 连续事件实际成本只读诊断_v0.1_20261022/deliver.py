"""Report existing costs and source anchors. No new route or graph operation."""
from common import *
import datetime
def main():
    violations=install_guard();index=require_sources();sessions=read(H/'三段实际账与完成尾段.json');layers=read(H/'最后事件三层一致性.json');costs=read(H/'六世界成本守恒分解.json');timeline=read(H/'两对遮挡信用时间线.json');detail=read(H/'I_M不同历史实际证据.json');by={r['session']['id']:r for r in sessions};same=[r for r in costs if r['same_final_H_D']];samephysics=[r for r in layers if r['all_physical_fields_equal']];assert [r['world'] for r in samephysics]==['L_S','L_M','T_M']
    # Read a frozen loader only as text to anchor check_contract/core provenance.
    extra={};seal=read(S/'seal.json');loader=R/'基线复现准备_20261019/ppcpp_independent.py';extra[str(loader)]=sha(loader);assert seal['files'][str(loader)]==sha(loader)
    imports=read(S/'outputs/I_M_PPCPP_t048.json')['imports'];core=next(Path(p) for p in imports if Path(p).name=='candidate_ppcpp_core4_20261014.py');assert imports[str(core)]==seal['files'][str(core)]==sha(core);extra[str(core)]=sha(core)
    save(H/'补充冻结来源hash.json',dict(files=extra,reason='Frozen native loader and CORE4 source identity, text only, never imported'))
    for p in extra:put(H/'readonly_source_text'/('extra_'+Path(p).name),Path(p).read_bytes())
    # Name the exact source lines without executing any function from them.
    anchors=[]
    for row in index['frozen_source_text']:
        p=Path(row['source']);lines=p.read_text(encoding='utf8').splitlines();matches=[dict(line=i,text=t) for i,t in enumerate(lines,1) if any(x in t for x in ('check_contract(','s.old_route','predator','previous','seed_used','Random(seed)','c[\'initial_targets\']','c[\'previous\']','c[\'predator\']'))];anchors.append(dict(path=str(p),sha256=sha(p),lines=matches))
    usage=[dict(field='initial_targets',PPCPP='Passed to shared contract: covered must be subset; P0 remaining-task order uses targets-covered. No OARP reconstruction.',P2_MULTI='Same shared validity check; not an ordering argument of p2_search_audit.solve.'),dict(field='old_route',PPCPP='Snapshot carries it but native P0 does not read it to select route.',P2_MULTI='Used by old_suffix offer and common_fallback task ordering; selected output label saved, not proof this field caused outcome.'),dict(field='predator',PPCPP='Fixed outside-domain predator, used by reward options.',P2_MULTI='Not passed from JSON to P2 solver; runtime.snapshot omits it.'),dict(field='previous',PPCPP='Validated adjacency, used as incoming heading for first decision, then route[-2].',P2_MULTI='Not passed to P2 search; runtime.snapshot omits it.'),dict(field='seed',PPCPP='Saved seed_used=False; deterministic P0 selection for these inputs.',P2_MULTI='random.Random(seed) used in extra candidate generation.'),dict(field='budget',PPCPP='Shared20s wrapper, remaining forwarded to native and checked.',P2_MULTI='Shared20s wrapper, remaining forwarded; original internal fallback/search retained.'),dict(field='physical state F/P/H/U/D/current/base/E',PPCPP='Active targets/free/history/current/base/resource define requested current residual task.',P2_MULTI='Same physical task fields; D/P bookkeeping is validated and active targets passed through Snapshot.')]
    save(H/'接口字段实际使用与源码锚点.json',dict(usage=usage,anchors=anchors,only_source_reading=True,no_single_field_causal_conclusion=True))
    # Exclusive credits retain saved credit/action/response/trace pointers.
    from analyze import move_pointer
    exclusive=[]
    for method,other in (('PPCPP','P2_MULTI'),('P2_MULTI','PPCPP')):
        s=read(S/'sessions'/('I_M_'+method+'.json'))['sessions'][method];points=detail['last_event_physical_state_differences']['H']['PPCPP_only' if method=='PPCPP' else 'P2_only']
        for p in points:
            ci,c=next((i,c) for i,c in enumerate(s['credits']) if c['point']==p);ai=next(i for i,a in enumerate(s['actions']) if a['kind']=='move' and a['end']==p and a['arrival_tick']==c['tick']);exclusive.append(dict(method=method,point=p,first_credit=c,credit_pointer=f'/sessions/{method}/credits/{ci}',source_file=str(S/'sessions'/('I_M_'+method+'.json')),movement_source=move_pointer('I_M_'+method,s,ai)))
    save(H/'I_M独有采集格及原始输出指针.json',exclusive)
    lines=['# 六世界实际成本位置：只读结论','',f'交付UTC：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。本次只读取已有六世界；规划、核心、候选、覆盖精确、BFS/Dijkstra/A*、反事实路线、新世界、新路线和模拟闭环均0。原verify未运行。','', '裁决建议：**A得到主要支持；B仅保留I_M的有限历史线索；C适用于I_S/T_S的任务信用比较边界。当前不支持另立连续事件新机制，建议不继续按奖励或局部步骤细分。**','', 'L_S、L_M、T_M最后发布时，F、P、H、U、D、current、previous、base、E及零移动信用处理全部逐成员相同；三对各6步差恰好就是最后获准完整路线的长度差，且响应全部实际执行，无后续事件、等待或废弃后缀。现有证据更接近最后一次剩余规划质量差异，不能包装成已证明的连续事件专属问题。old_route不同、算法本身不同，不能归因为单一字段。','', 'I_M的12步发生在已形成不同位置/方向/覆盖布局之后，保留“不同历史累积”的观察线索，但未识别历史影响与算法选择各占多少。禁止从本账推断交换历史后能节省多少；若与旧单事件残余规划问题没有实质区别，就不建议为保留B路线继续细分。I_S/T_S则完成工作量不同，先说明评价目标，不能拿其差值支撑同工作量优势。','', '## 三段边界与全六世界实际账','', '移动按出发tick唯一归段：[0,t1)、[t1,t2)、[t2,结束)。到达边界tick的信用按移动前地图，属于上一段；边界发布/当前格的零移动信用归下一段，二者不重复。前两段段末状态取边界发布前、该次到达信用之后；最后段末为终止状态。转弯用真实相邻移动方向，跨段、等待和重规划不清零。首次信用及逐成员H/U/D/current/previous/E全存于三段实际账与完成尾段.json。','', '|世界/方法|段1 M|段2 M|段3 M|总M|等待三段|首次信用三段|','|---|---:|---:|---:|---:|---|---|']
    for r in sessions:lines.append(f"|{r['session']['id']}|"+'|'.join(str(p['moves']) for p in r['segments'])+f"|{r['summary']['M']}|{[p['waits'] for p in r['segments']]}|{[p['first_credit_count'] for p in r['segments']]}|")
    lines += ['', '全部会话无等待，到同一固定事件tick的累计移动自然相同。前两段移动差为0是该时钟与无等待的恒等式，不代表历史决策没有影响。I_M在相同步数中已采到不同任务，见后文。','', '|会话/段|首次采集移动|初始历史|会话重复|非目标|90°/180°|零移动信用|','|---|---:|---:|---:|---:|---|---:|']
    for r in sessions:
        for p in r['segments']:
            c=p['move_classes'];lines.append(f"|{r['session']['id']}/{p['index']+1}|{c['fresh_target']}|{c['initial_historical']}|{c['session_repeat']}|{c['non_target']}|{p['turns90']}/{p['turns180']}|{p['zero_move_credit_count']}|")
    lines += ['', '## 最后事件三层一致性','', '|世界|物理任务逐成员相同|initial_targets|old_route|捕食者/共同20秒/seed|完整末响应相同|响应全部执行|','|---|---|---|---|---|---|---|']
    for r in layers:
        ie=r['interface_field_equal'];lines.append(f"|{r['world']}|{r['all_physical_fields_equal']}|{ie['initial_targets']}|{ie['old_route']}|{ie['predator'] and ie['entry_budget'] and ie['seed']}|{r['result']['last_routes_identical']}|True|")
    lines += ['', '六对的实际转交内部预算数值都不同，因为实际前处理耗时不同；共同总入口上限仍是20秒。逐次前处理/内部余量均保留，不能称所有输入完全相同。PPCPP/P0不以old_route选路，但用previous/捕食者；P2使用old_route作内生保底及访问顺序参考，P2不接收previous/捕食者。initial_targets对这两个入口主要承担H子集契约，不能把未启用的OARP语义混入。PPCPP记录seed_used=False，P2用固定seed生成内部额外候选。详见接口字段实际使用与源码锚点.json；这些只是代码用途，不是因果消融。','', '## 四对同信用配对的两种成本分解','', '以下Δ均为PPCPP−P2。四类移动是一种分区；采完前/返航是另一种分区，两表分别守恒，不能重复相加。','', '|世界|ΔM|三段ΔM|首次采集Δ|初始历史Δ|会话重复Δ|非目标Δ|最后末响应Δ|','|---|---:|---|---:|---:|---:|---:|---:|']
    for r in same:
        c=r['all_four_class_delta'];lines.append(f"|{r['world']}|{r['delta_M']}|{r['three_segment_delta_M']}|{c['fresh_target']}|{c['initial_historical']}|{c['session_repeat']}|{c['non_target']}|{r['last_response_length_delta']}|")
    lines += ['', '四对描述性合计：首次采集移动差0、初始历史0、会话重复−15、非目标+45，合为+30。不能把这些结果简化为“PPCPP重复采集更多”；三对同物理状态案例中，PPCPP会话重复反而更少，非目标移动更多。非目标通行可能是覆盖/返航所需，未证明它不必要。','', '|世界|最后发布后采完前移动(PPCPP/P2)|采完后返航移动(PPCPP/P2)|Δ采完前+Δ返航|最终采集位置(PPCPP/P2)|','|---|---|---|---|---|']
    for r in same:
        a,b=[by[r['world']+'_'+m]['final_completion'] for m in ('PPCPP','P2_MULTI')];lines.append(f"|{r['world']}|{a['to_completion']['moves']}/{b['to_completion']['moves']}|{a['after_completion_to_base']['moves']}/{b['after_completion_to_base']['moves']}|{r['last_event_to_completion_delta']}+{r['after_completion_return_delta']}={r['delta_M']}|{a['completion_position']}/{b['completion_position']}|")
    lines += ['', '每个完成边界均由最后发布时剩余U的实际首次信用逐格定位；采完移动包含最后一次采集到达，之后的出发移动才归返航。无剩余任务时边界定义为最后发布tick，本批所有末次发布均还有U，因此未出现该空集情形。完整十二会话完成tick、末格、等待和原始信用索引已保存。没有独立最短距离证据，不称上述返航片段最短、绕路或可删。','', '## 保存片段的具体证据','', '每方法每类按“连续实际步数最长，并列取最早tick”列一个保存片段。全部连续重复/非目标片段及完整点序列和原决策/输出指针均保留，未拼接替代路线。分类“重复”指重访已取得信用的目标，不等于重复边，也不自动代表浪费。','', '|世界/方法|分类|出发至到达tick|实际步数|片段起点→终点|原动作索引|','|---|---|---|---:|---|---|']
    for r in same:
        for m in ('PPCPP','P2_MULTI'):
            rec=by[r['world']+'_'+m]
            for kind in ('session_repeat','non_target'):
                runs=[x for x in rec['all_repeat_and_non_target_runs'] if x['classification']==kind]
                if runs:
                    x=min(runs,key=lambda a:(-a['steps'],a['depart_start_tick']));lines.append(f"|{rec['session']['id']}|{kind}|{x['depart_start_tick']}→{x['arrival_end_tick']}|{x['steps']}|{x['path'][0]}→{x['path'][-1]}|{x['action_indices'][0]}..{x['action_indices'][-1]}|")
    lines += ['', '## I_M：不同历史的实际内容','', '事件1为tick12，首次真实动作分歧发生于出发tick13：两者都从(11,4)出发，PPCPP到(12,4)，P2到(11,3)。前者原P0 trace[1]为已保存的local选择；后者来自保存的H_scan_opt输出第1→2段。该指针只说明已返回且执行了哪一步，不评价另一动作会怎样。','', 'tick48发布后，PPCPP current=(11,7)、previous=(12,7)、H=43、U=69；P2 current=(27,5)、previous=(27,4)、H=41、U=71。F/P/D及E相同，位置/方向/H/U不同。PPCPP独有18格历史，P2独有16格；互为对方剩余任务。','', 'PPCPP独有：'+str(detail['last_event_physical_state_differences']['H']['PPCPP_only'])+'。','', 'P2独有：'+str(detail['last_event_physical_state_differences']['H']['P2_only'])+'。','', '对应的每格首次信用时间、真实移动、末次响应来源和PPCPP决策索引见I_M独有采集格及原始输出指针.json。PPCPP此前采了上沿目标，P2此前采了新增下方任务，不能只比较H数量断言哪个历史更好。其后78/71步采完、12/7步返航是实测分区；不能把7+5的12步直接分配给“历史造成多少”和“算法造成多少”。控制历史或算法后的反事实成本未知。','',f"![I_M已保存前缀注记]({(H/'I_M保存轨迹注记.png').as_posix()})",'', '## I_S/T_S：遮挡信用时间线','', '|世界|目标|原始公开|PPCPP首次采集|遮挡发布|P2首次信用|最终归属|','|---|---|---:|---:|---|---|']
    for r in timeline:
        for x in r['blocked_target_timeline']:lines.append(f"|{r['world']}|{x['point']}|初始|{x['first_credit']['PPCPP']['credit']['tick']}|{x['blocked_at']}|无|PPCPP保留H，P2计D|")
    lines += ['', '四条信用均是事件前真实arrival，不是事后补信用，也没有以经过过目标/基地追溯完成。P2按当前协议仍完成当前可检任务并返航，不能自动判失败；PPCPP多完成两格也不能自动判为浪费。这两对的8/2步差不并入同工作量30步。','', '## 证据缺口与停止建议','', 'A：三对共18步的现象表现为同物理任务下末次剩余规划差，算法和old_route参考仍不同，尚无单字段因果识别；不据此立项新连续机制。B：I_M真实历史不同，可作为以后讨论控制问题的有限线索，但没有交换历史、固定算法或干预收益证据；本轮不自动拟新实验。C：两对信用不等价，先明确任务评价目标，不为保住路线结论改遮挡或时钟。','', '建议以A为当前主要解释，B保留未解决而不继续细分，C限定两对工作量比较。若进一步问题仍只是同一残余任务上的路线选择，应明确归回已有单事件/静态剩余规划问题，不能以连续事件包装新意。六模板单seed不是普遍结论，未确认主算法或创新。','', '来源hash、原指针和独立核验均在本包；来源包和冻结源码未修改，原单步候选关闭，留出不用，未提交推送。完成封存停止，不追加任务、改奖励或改事件。']
    put(H/'通俗结论与裁决建议.md',('\n'.join(lines)+'\n').encode('utf8'))
    save(H/'交付零调用账.json',zeros('saved_evidence_delivery',violations));print('Delivered read-only findings A primary/B limited/C scoped; no new calls',flush=True)
if __name__=='__main__':main()
