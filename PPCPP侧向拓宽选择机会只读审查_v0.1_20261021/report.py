"""New prose/pointer exports from saved review JSON only; no algorithm imports."""
from pathlib import Path
import json,collections,statistics,datetime,hashlib
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def text(p,x):
    with Path(p).open('x',encoding='utf8') as f:f.write(x)
def main():
    a=read(H/'analysis.json');variants={v['state']:v for v in a['variants']};states={s['state']:s for s in a['states']};events=[s for s in a['states'] if s['condition']!='CONTROL'];comp=[d for d in a['decisions'] if d['is_competition']]
    assert all(s['three_PP_seeds_equivalent'] for s in a['states'])
    firsts=[v['first_competition'] for v in variants.values() if v['first_competition']];saved_unique_new=all(len(d['new_options'])==1 for d in firsts);ties=sum(d['cross_class_highest_score_tie'] for d in comp);choicecounts=dict(collections.Counter(d['chosen_class'] for d in comp))
    condtable='\n'.join('|'+ '|'.join(map(str,[c['condition'],c['states'],c['with_competition_states'],c['without_competition_states'],c['first_competition_choice_state_counts'],c['first_entry_mode_state_counts'],round(c['existing_mean_D'],4)]))+'|' for c in a['conditions'])
    rows=[];case_lines=['# 固定三组：首竞争与首次入A的原始证据','','固定g00_b009、g04_b028、g01_b009，各组全部四条件。复用原v0.4图，不生成新图/新路线。三份PPCPP路线与非时间trace已逐状态完全一致，以下指针用seed20261020代表，三份原输出hash见三seed等价表。','']
    for gid in ('g00_b009','g04_b028','g01_b009'):
        items=[];case_lines += [f'## {gid}','']
        for cond in ('CONTROL','H_SIDE','MIXED_SIDE','U_SIDE'):
            sid=gid+'_'+cond;v=variants[sid];s=states[sid];first=v['first_competition'];entry=v['first_A_entry'];old=v['previous_first_A_event'];items.append(dict(state=sid,condition=cond,representative_seed=20261020,equivalent_seeds=v['equivalent_seeds'],first_competition=first,first_A_entry=entry,prior_first_A_event=old,source_existing_figure=str(B/'figures'/f'{sid}.png'),existing_by_seed=s['existing_by_seed']))
            case_lines += [f'### {cond}', '',f'竞争机会{v["competition_count"]}个；首次采集阶段原PPCPP={s["PP_sequence_patterns"]}，P2各自路线={s["P2_sequence_patterns"]}。既有D/ΔC/ΔR（三seed）：`{json.dumps(s["existing_by_seed"],ensure_ascii=False)}`。','',f'[复用原输入与路线图]({(B/"figures"/(sid+".png")).as_posix()})','']
            if first:
                case_lines += [f'首竞争：[{Path(first["source_output"]).name}]({Path(first["source_output"]).as_posix()})，`{first["trace_pointer"]}`；route.index={first["route_index"]}，current={first["current"]}，previous={first["previous"]}，旧/新增pending={first["old_pending_count"]}/{first["new_pending_count"]}。实际goal={first["goal"]}，类={first["chosen_class"]}；此前已采A={first["A_already_collected"]}；跨类最高分并列={first["cross_class_highest_score_tie"]}。','', '已保存两类选项及奖励（原样引用，不重算）：','', '```json',json.dumps(dict(old=first['old_options'],new=first['new_options']),ensure_ascii=False,indent=2),'```','',f'该local字面段：`{json.dumps(first["literal_segment"])}`。','']
            else:case_lines += ['首竞争：无。CONTROL无A不适用；事件条件若无机会也保留，不以“全局还有旧任务”补造竞争。','']
            if entry:
                case_lines += [f'首次入A：route.index={entry["route_index"]}，模式={entry["mode"]}；原条目`{entry["owner_pointer"]}`，是否竞争={entry["was_competition"]}，local且只有new选项={entry["local_only_new_options"]}。','',f'所属原条目的完整字面段：`{json.dumps(entry["literal_segment"])}`。段内多步不拆成local选择。','']
            else:case_lines += ['首次入A：无A，不适用。','']
            case_lines += [f'原报告first_A_event另存指针：`{old.get("pointer") if old else None}`；只表示首次涉及A，不代替本次竞争定义。','']
        rows.append(dict(group=gid,states=items))
    save(H/'固定三组案例指针.json',rows);text(H/'固定三组详细案例.md','\n'.join(case_lines))
    evidence=dict(event_states=36,control_states=12,base_geometries=6,PP_saved_calls=144,P2_saved_routes=144,all48_PP_three_seed_routes_and_traces_equal=True,canonical_events=len(a['decisions']),canonical_competitions=len(comp),competition_state_count=sum(s['any_competition'] for s in events),first_competition_unique_new_option_in_all_states=saved_unique_new,canonical_competition_choice_counts=choicecounts,cross_class_highest_score_ties=ties,all_event_PP_patterns_old_then_new=all(s['PP_sequence_patterns']==['old→new'] for s in events),all_event_first_A_entries_recovery=all(s['first_entry_mode']=='recovery' for s in events),counterfactual_executed=False)
    save(H/'结论核对数字.json',evidence)
    report=f'''# 侧向拓宽新旧任务选择机会：只读审查结论

**实际存在干预入口，但不在首次入A的恢复段内。** MIXED_SIDE、U_SIDE的全部24状态均遇到过old/new两类未检邻格同时合法可选；H_SIDE的12状态没有。首次竞争均实际选old，首次入A则在36个事件状态中全部属于recovery。这证明有可定位的local入口，不证明改选new能缩短完整路线。

本轮仅复用v0.4。读取48状态×3seed的全部144条PPCPP保存trace，以及144条P2完整路线；原48状态PPCPP三seed路线与全部非时间P0 trace完全一致，故逐决策主表按48状态各一份，保留三份原输出hash与逐seed核对。共{len(a['decisions'])}个去重trace条目，竞争{len(comp)}个（MIXED 72、U 120）；这些是决策条目，样本仍为24个有机会状态、六基础几何，不把条目数或三重复当独立地图。

|条件|状态数|有竞争|无竞争|首竞争实际选择（按状态）|首次入A模式（按状态）|复用既有平均D|
|---|---|---|---|---|---|---|
{condtable}

每条件仍为12状态、各3seed；D=PPCPP−P2的36个原及时配对均保留。H_SIDE原版每配对短2步，MIXED/U为差距例；12个无A控制不进入事件竞争分母。

## 1. 是否真有新旧目标同时可选

有。24状态覆盖g00至g05全部六基础几何、两历史切点及MIXED/U两个条件。判定使用当前公开F、实际H与各自路线前缀：当前位置已信用后，对四邻格检查old_pending/new_pending，再与原local options.cell逐项核对。没有搜索、奖励函数调用或新增规划候选。

所有首竞争都出现在首次采集A之前，当时A已采数0；它们均不是首次入A动作。192个竞争机会的实际选择分布为{choicecounts}，跨类最高分并列{ties}，因此本数据没有把跨类并列打破方式当作解释的依据。这里只比较已保存的score字段，不重算奖励，不推断未保存选项。

H_SIDE没有local竞争，首次入A为recovery。MIXED/U虽然此前有竞争，但其后来首次入A也全部是recovery；恢复段中的相邻移动没有被误计为新的local选择。首次入A为local且只有new邻格的状态数为0，起点位于A的状态数为0；这些分类保留在完整表中，并非遗漏。无竞争事件12个，加无A控制12个，均完整保留。

## 2. 优势与差距是否能靠选择或阶段序列区分

机会是否出现，可以区分这批H_SIDE与MIXED/U；但不能据此认定机会导致差距，因为位置、当前/基地距离和布局也同步变化。

**全部36事件状态的原PPCPP首次采集标签阶段都是old→new。** 同一阶段序列既出现在H_SIDE的原版优势状态，也出现在MIXED/U的差距状态。MIXED与U首竞争同样选old，平均D却分别为11.6111和26.4444步。因此不能写成“选old就导致路线长”，也不能把更少阶段交替称为更短路线的保证。

P2在H_SIDE也为old→new，却仍比原PPCPP多2步；MIXED/U的P2保存序列含更多交替，部分U路线从new开始。它们是各自轨迹的任务序列，不是PPCPP某个决策状态下的替代动作。每阶段采集数量与起止route.index及每个首次采集格，详见两方法288条首次采集阶段序列.json。既有D/ΔC/ΔR只复用，不重复扩展成本归因。

## 3. 是否足以表述下一项可关闭的反事实问题

足以**把问题写具体**，尚不足以支持优先策略或收益结论。可交负责人考虑的问题是：“仅在首次已核实的local双类竞争点，暂时改走当时已保存的new邻格一步，随后恢复原PPCPP，完整路线是否改善？”这24个状态的首竞争保存new选项是否均唯一：{saved_unique_new}。若负责人决定研究，触发必须只用当前输入与当时合法选项；关闭时应完全回到原版，H_SIDE无触发状态可保留为保护参照。不得借P2未来路线选动作或用本轮关联代替反事实验证。

本轮没有实现该动作、没有试走备选、没有运行新PPCPP，也未批准长期优先new或old的规则。是否值得实施由负责人另行裁决；原“H_SIDE比U_SIDE更值得关注”方向假设继续关闭。

## 证据与边界

固定详细案例仍为g00_b009、g04_b028、g01_b009，各组四条件；详见固定三组详细案例.md及固定三组案例指针.json。直接链接原v0.4图，未挑新反例、未画新路线。

本审查覆盖36事件状态，不以三组例子代替全表；六图仅直线多格宽带、实际历史覆盖10%至22.22%，位置变化有距离与布局混杂。没有确认因果、可删步数、最优性、主算法或创新。

新增真实入口/核心/候选/路线补全/覆盖精确/反事实/BFS/Dijkstra均0。不导入规划器，不运行原verify（其24次BFS没有再次发生），原实验及负责人审核图搜索账保持各自原值。只读新核验用独立完整前缀集合与逐目标首次索引实现，结果以verify_execution.log为准。

旧包、冻结实现、留出不动，Git不提交推送。完成后封存停止，等待审核，不自动开展下一实验。
'''
    text(H/'审查结论.md',report)
    text(H/'review_packet.md','''# 审核入口

先读审查结论.md、48状态完整汇总.csv及36事件状态主表.csv；再看固定三组详细案例.md、固定三组案例指针.json。

原始来源hash见source_hash_manifest.json；三seed等价表保留每份输出hash。逐决策机会账保留5688去重条目及192个竞争标志，完整144条trace均核对；两方法288条首次采集阶段序列保留全部seed，不借P2构造PPCPP替代动作。

只读核验.ps1运行本目录verify.py，使用独立全前缀集合/逐目标首次索引，只读核对来源、trace、选项、入口归属、序列、统计与CSV。不会调用原v0.4 verify或新增BFS。最终completion_manifest绑定全部脚本与工件，核验日志和零调用账单列。

本包是原开发数据的机制前提审查，不是新算法、新地图或反事实实验。所有后续实施待负责人另行裁决。
''')
    text(H/'technical_attempts.md','''# 技术尝试与范围

本包audit.py与verify.py、report.py仅导入Python标准库；没有导入原实验common/analysis或规划模块。主审查使用增量pending集合沿实际路线更新；独立核验从每个完整前缀重新做集合扣除，采集序列则逐目标查其首次索引，未调用搜索。

首次审查运行成功，无解析失败、源码修复或原证据冲突；日志保留。后续独立核验的实际退出结果另见verify_execution.log与收据，不以本说明冒充通过。未执行原v0.4 verify，避免其24次BFS。

原native源码与reward_options源码仅为理解trace契约进行文本阅读；未导入、执行或调用评分。保存options原样归类；独立四邻格枚举只是检查已运行选择，不生成算法候选或路线。

return条目按原源码不保存previous，本包明确核对其零pending/当前位置/返航目标，而非把缺失字段误当新的local证据。local/recovery的previous均与保存路线或输入previous逐项核对。技术脚本和标准库import审查纳入独立verify。
''')
    print('PASS readonly report exports: fixed3 groups/all4 conditions, first-competition and first-entry source pointers; no new route/graph/planner/counterfactual',flush=True)
if __name__=='__main__':main()
