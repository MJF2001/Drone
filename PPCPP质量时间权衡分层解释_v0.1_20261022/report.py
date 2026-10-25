from pathlib import Path
from collections import Counter
import json,statistics,shutil
H=Path(__file__).resolve().parent;R=H.parent
def read(n):return json.loads((H/n).read_text(encoding='utf-8-sig'))
def md(n,s):(H/n).write_text(s,encoding='utf8')
def main():
    strata=read('原标签完整分层.json');pairs=read('162重建配对.json');states=read('54重建状态均值.json');ex=read('极值与全部seed证据.json');changes=read('54新旧来源核对.json');q=read('四象限.json');conc=read('时间节省集中度.json');summary=read('统计核对摘要.json')
    main='''# 固定开发批质量—时间权衡：分层判断

从原始保存流水线重新构造162个同状态同seed配对、54个三seed状态均值，再由独立80位区间算术和原始时序字段核验通过。新增规划、后处理、几何、候选、新路线和输入变换全部0；未运行原verify或修改旧报告。

总体状态等权额外路程14.700%，总距离加权19.285%，不能互换。状态等权平均节省计算0.918081秒，但54个状态均值的中位数仅0.141394秒；162次配对的中位数为0.139521秒。均值受较长运行例影响，不适合称为“每次通常省约0.9秒”。原PPCPP是主要速度基础，直达增加计算，未得到速度创新证明。

已测尺度中：中图平均额外路程8.214%，平均节省0.280547秒；小图13.270%、0.018583秒；大图22.615%、2.455114秒。中图在平均路程代价上相对温和；大图的绝对时间节省更大，但路程代价也明显；小图通常只省毫秒到几十毫秒，不应只展示时间倍率。它们不是可接受性结论，且尺度内差异仍须看全表。

事件标签中，障碍组平均额外路程4.921%、省0.497205秒；直线组18.342%、省1.093649秒；拐角组20.836%、省1.163389秒。这仅描述原开发模板各18状态，不证明障碍导致收益，也不外推显著性。I/L/Z分层详表完整保留。

54状态四象限为：更快但更长45，更快且不长8，更慢且不长1，更慢且更长0；时间相等0、距离未确定0。“不长”在本批状态均值中均为等长。慢例small_I_obstacle_p70平均慢0.636733毫秒，不能隐藏，也不能据一次小差异声称稳定落后。全部162次的慢例及seed另表逐条保留。

大图贡献有符号总时间节省的89.139%，节省最多的5个状态贡献59.093%，第一名large_Z_corner_p30占18.212%。集中度的分母包括负值，前三/前五只是预定义排名描述，不是新增分组实验。最大状态额外路程47.314%发生在large_I_straight_p70；最大绝对额外路程99.913055在large_Z_corner_p30。不能笼统称“只损失很少路程”。

新旧差异已定位：旧rep0与新rep0均44长9平1短，两方法54个同seed原路线全部未改变。medium_L_straight_p70的20261020/21配对分别短0.716974/0.561430，20261022则长3.132605；三seed平均转为长，故新状态均值为45长9平。这来自已有seed路线差异与聚合，不是计时改变路线、覆盖旧结论或重跑挑seed。

在没有应用最大允许路程损失与响应需求前，以上只能支持“各已测类别的权衡代价不同”。不从76.467%减14.700%合成净收益，不宣布合格或现场实时，不推能耗。所有耗时为本次已记录暖入口，模块导入另列，进程创建未单测。结果是固定54开发状态的工程证据，独立留出与算法创新尚未确认。

交付完成后停止，不自动提出或启动下一轮归因、顺序设计或新实验，交负责人和用户讨论后续。
''';md('00_通俗报告.md',main)
    tab='|原维度/标签|状态/配对数|等权额外路程%|总量加权%|省时均值/状态中位ms|配对省时中位ms|PPCPP后处理均值/配对中位ms|省时正/负/零状态|路程长/平/短/未知状态|最坏状态/单次额外路程%|\n|---|---|---:|---:|---|---:|---|---|---|---|\n'
    for s in strata:
        d=s['distance_sign_states'];tab+=f"|{s['dimension']}/{s['label']}|{s['states']}/{s['seed_pairs']}|{100*s['state_equal_extra_ratio']:.3f}|{100*s['total_length_weighted_extra_ratio']:.3f}|{1000*s['saved_seconds_mean_state']:.3f}/{1000*s['saved_seconds_median_state']:.3f}|{1000*s['saved_seconds_median_pair']:.3f}|{s['B_post_ms_mean_state']:.3f}/{s['B_post_ms_median_pair']:.3f}|{s['time_positive_states']}/{s['time_negative_states']}/{s['time_zero_states']}|{d.get('longer',0)}/{d.get('equal',0)}/{d.get('shorter',0)}/{d.get('uncertain',0)}|{100*s['worst_state_extra_ratio']:.3f}/{100*s['worst_pair_extra_ratio']:.3f}|\n"
    md('01_完整分层与口径.md','''# 原标签分层与口径

三seed先在状态内平均，状态间等权；“等权额外路程”是逐配对比例的状态等权均值，“总量加权”是总B/总C−1。时间均值和中位数明确按状态均值或162配对分别计算，不直接相除。后处理增量包括当次转换/解析/验收/编码，未免费使用初始解；P2也应用同一后处理。

每原维度各18状态/54配对，共3尺度、3形状、3事件。各维度覆盖同一54状态，不能把不同维度行数相加当独立样本。只列旧标签，没有结果驱动阈值、显著性测试或事后合格线。零分母本批未出现；通用指标不适用时不能记零。

'''+tab+'\n原标签完整分层.json/CSV另保留正负配对数量、时间总和及所有最坏值；162重建配对和54重建状态均值JSON/CSV为完整明细。\n')
    qt='|象限|54状态数|162配对数|\n|---|---:|---:|\n'
    for label in ('faster_not_longer','faster_longer','slower_not_longer','slower_longer','time_equal','distance_uncertain'):qt+=f"|{label}|{q['state_counts'].get(label,0)}|{q['pair_counts'].get(label,0)}|\n"
    slow='|状态|seed|C−B时间ms|额外路程%|\n|---|---:|---:|---:|\n'
    for p in pairs:
        if p['saved_seconds']<=0:slow+=f"|{p['case']}|{p['seed']}|{1000*p['saved_seconds']:.6f}|{100*p['extra_ratio']:.6f}|\n"
    md('02_四象限与极值.md','# 四象限与固定极值\n\n时间以保存测量C−B精确符号分正负，不加人为噪声阈值；小差异不解释为稳定或因果。路程符号来自认证区间或精确边平方多重集合等长证据。\n\n'+qt+'\n全部非正时间配对（保留所有seed）：\n\n'+slow+'\n极值为预定最大状态路程比例、最大状态绝对差、最大/最小状态省时、最大单次路程比例；并列按ID、seed排序。选择用于解释，非代表样本。\n\n')
    with (H/'02_四象限与极值.md').open('a',encoding='utf8') as f:
        for e in ex:
            f.write(f"{e['criterion']}：{e['case']}，值{e['value']:.9f}。全部seed：\n\n|seed|原PPCPP/P2长度|B/C长度|额外距离|额外比例%|B/C耗时ms|C−B ms|\n|---|---|---|---:|---:|---|---:|\n")
            for p in e['all_three_seeds']:f.write(f"|{p['seed']}|{p['A_length']}/{p['C0_length']}|{p['B_length']:.6f}/{p['C_length']:.6f}|{p['extra_distance']:.6f}|{100*p['extra_ratio']:.3f}|{1000*p['B_seconds']:.3f}/{1000*p['C_seconds']:.3f}|{1000*p['saved_seconds']:.6f}|\n")
            f.write('\n')
    ch=[c for c in changes if c['old_rep0_sign']!=c['new_three_seed_state_sign']];assert len(ch)==1 and ch[0]['case']=='medium_L_straight_p70'
    md('03_新旧差异与集中度.md','''# 新旧来源核对与时间集中度

旧有限诊断用每状态rep0的同输入PPCPP/P2路线，补等长证书后44长9平1短。此次同seed20261020的54配对仍44长9平1短；PPCPP及P2各54条原顶点序列逐点相同，并非重新计时导致路线变了。三seed状态均值45长9平是另一个聚合问题，不覆盖旧结果。

唯一符号翻转medium_L_straight_p70：seed20261020差−0.716973621，20261021差−0.561430218，20261022差+3.132604892；均值约+0.618067018。PPCPP在此三seed保持相同原路线，P2各seed的保存路线/长度可不同，第三seed得到较短P2路线，使平均符号转正。完整原长度、新长度和全部时间见极值与54新旧来源核对.json中seed_evidence，不为匹配旧数重跑或挑seed。

P2当次162份状态全finished，阶段日志来自同次native.raw.events，计时来自timing原入口/后处理/累计封套。不是等足20秒，也不是把旧生成时间拼接新直达时间。独立审核回执的历史几何查询仅作为已保存证据，本轮不重验几何。

时间节省分母为54状态平均省时的有符号总和，负值仍计入：大图89.139%、中图10.186%、小图0.675%；排名最高1/3/5状态贡献18.212%/43.353%/59.093%。这说明绝对时间均值集中在大图和较长运行例，不能据此归因于某结构或外推到其他机器。

旧54、新rep0、新三seed均值完整并列于54新旧来源核对.json；来源哈希、原输入相同、原始路线相同与计时字段分别核对，不混为同一种等价性。
''')
    shutil.copyfile(R/'PPCPP质量时间权衡负责人审核与分层解释执行稿_给sol_20261022.md',H/'执行稿原文快照.md');shutil.copyfile(R/'PPCPP直达质量时间开发比较_v0.1_20261022/质量时间图.png',H/'54状态原散点图.png')
    md('review_packet.md','''# 审核入口

00_通俗报告.md为一页判断；01_完整分层与口径.md保留10行总体/原标签表；02_四象限与极值.md列全部慢配对、固定极值及每例全部seed；03_新旧差异与集中度.md解释聚合差异与绝对省时集中度。

机器证据：162重建配对、54重建状态均值、原标签完整分层各JSON/CSV；极值与全部seed证据、54新旧来源核对、四象限、时间节省集中度及统计核对摘要JSON。全部从保存原输出重建，不仅读旧summary自证。原散点图按字节复制，保留全部54点，不绘制新候选或替代路线。

![原54状态散点](54状态原散点图.png)

verify.py不导入分析脚本或生产模块，独立用80位Decimal长度区间、原始时序和集合/输入哈希重建核验162配对、54均值、分层、四象限、极值和新旧rep0。零新增求解账和来源hash绑定证据；没有新求解/几何/后处理。旧包/源/留出不改，不提交推送，封存后停止，不自动建议下一轮实验。
''')
    print('Reports generated from saved evidence; new planner/geometry/postprocessing 0.')
if __name__=='__main__':main()
