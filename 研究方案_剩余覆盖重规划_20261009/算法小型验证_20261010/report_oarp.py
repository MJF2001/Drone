"""Freeze transparent core-adaptation results and two illustrative path pairs."""
from collections import Counter
import csv
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont


root = Path(__file__).resolve().parent
folder = root/'results/run_16_oarp_default_v3'
summary = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
verification = json.loads((folder/'independent_verification.json').read_text(encoding='utf-8'))
assert not verification['errors']
rows = json.loads((folder/'results.json').read_text(encoding='utf-8'))
baseline = json.loads((folder/'baseline_results.json').read_text(encoding='utf-8'))
snapshots = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
with (folder/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer = csv.DictWriter(f,fieldnames=['case','algorithm','family','status','length','source','seconds','rank_cap','rank_count','new_rank_count','blocks','certification_repair'])
    writer.writeheader()
    for r in rows:
        detail = r['detail']
        writer.writerow({'case':r['case'],'algorithm':r['algorithm'],'family':r['family'],
            'status':r['status'],'length':r['audit']['length'] if r['audit'] else None,
            'source':r.get('source'),'seconds':r['seconds'],'rank_cap':detail.get('rank_cap'),
            'rank_count':detail.get('rank',{}).get('metrics',{}).get('rank_count'),
            'new_rank_count':detail.get('rank',{}).get('metrics',{}).get('new_rank_count'),
            'blocks':detail.get('tour',{}).get('block_count'),
            'certification_repair':detail.get('rank',{}).get('certification_repair',False)})

fontfile = 'C:/Windows/Fonts/msyh.ttc'
font = ImageFont.truetype(fontfile,20)
small = ImageFont.truetype(fontfile,15)
cases = ('v3_open_straight_L18_W6_p25','v3_open_corner_L18_W6_p75')
canvas = Image.new('RGB',(1320,1030),'white')
draw = ImageDraw.Draw(canvas)
draw.text((20,10),'单格覆盖：P2与OARP核心适配版2的自建案例（不是原论文图例）',font=font,fill='black')
draw.text((20,43),'绿：已检查　黄：旧待检　蓝：新增目标　黑：障碍　S：当前位置　B：基地',font=small,fill='black')
for row,name in enumerate(cases):
    d = next(s for s in snapshots if s['name']==name)
    m = d['metadata']
    domain = set(map(tuple,m['domain']))
    published = set(map(tuple,m['published_targets']))
    covered = set(map(tuple,d['covered']))
    added = published-set(map(tuple,m['initial_targets']))
    blocked = set(map(tuple,m['obstacles']))
    xmax,ymax = max(x for x,y in domain),max(y for x,y in domain)
    ymin = min(y for x,y in domain)
    scale = min(18,350//(ymax-ymin+1))
    title = '直线扩展：适配版较短' if row==0 else '拐角扩展：P2较短'
    draw.text((20,85+row*460),title,font=font,fill='black')
    for column,(alg,records) in enumerate((('P2',baseline),('OARP_CORE_2',rows))):
        r = next(v for v in records if v['case']==name and v['algorithm']==alg)
        ox,oy = 25+column*650,150+row*460
        def box(p):
            x,y=p
            return ox+x*scale,oy+(ymax-y)*scale,ox+(x+1)*scale,oy+(ymax-y+1)*scale
        def centre(p):
            a,b,c,e=box(p)
            return (a+c)//2,(b+e)//2
        draw.text((ox,120+row*460),f'{alg}：{r["audit"]["length"]}步',font=small,fill='black')
        for p in domain:
            colour = '#eeeeee'
            if p in published: colour='#fff1c5'
            if p in added: colour='#cce8ff'
            if p in covered: colour='#cbe6cb'
            if p in blocked: colour='#333333'
            draw.rectangle(box(p),fill=colour,outline='#c9c9c9')
        path = list(map(tuple,r['route']))
        draw.line([centre(p) for p in path],fill='#c72b3b' if column==0 else '#165bac',width=2)
        for label,p,colour in (('S',tuple(d['current']),'#dd7600'),('B',tuple(d['base']),'black')):
            x,y=centre(p)
            draw.ellipse((x-4,y-4,x+4,y+4),fill=colour)
            draw.text((x+4,y-20),label,font=small,fill=colour)
draw.text((20,1000),'两例仅用于解释路径差异；不能代表总体优势。完整结果见逐例CSV。',font=small,fill='black')
canvas.save(folder/'path_examples.png')

lines = ['# OARP-Replan核心实现、验证与首轮对照', '', '2026-10-10。', '',
    '## 先看结论', '',
    '**两阶段核心代码和单格场景适配已完成，并通过核验；不能称为原论文端到端完整复现。** 两个适配版本均完成64个快照，但整体未优于P2。这个结果用于筛选研究方向，尚未形成创新结论。', '',
    '## 1. 实际完成内容', '',
    '- 条带方向/端点分区、ILP-1新增条带精确匹配、ILP-2端点变化上界、预算与小权重目标；SCIP先解LP，检查整数性，不直接四舍五入。',
    '- 未改变条带对应的连续旧路径包；新条带与路径包的两方向GTSP；人工起终点、GLNS求解、A*连接及实际路线展开。',
    '- 经验运行时间标定与预算反查；合法旧路线/工程绕行候选、当前位置、覆盖账本、新区域与返航的单格场景接口。',
    '- 原生OARP初始条带的小例、独立穷举、BFS回放、精确GTSP检查、可追踪源码与求解器版本。', '',
    '详细机制、代码入口、运行方法和原文式号对应见[实现说明](../算法小型验证_20261010/oarp_replan/README.md)。', '',
    '## 2. 复现与适配的边界', '',
    '| 部分 | 当前状态 |', '| --- | --- |',
    '| 两种数学分区模型、路径包与GTSP结构 | 已实现核心机制；非法解会拒绝并记录 |',
    '| SCIP | PySCIPOpt 6.2.1 / SCIP 10.0.2 |',
    '| GLNS | 作者维护的C++ 0.1.0端口，default配置；不是原论文Julia运行版本 |',
    '| 连接成本 | 四邻接单位步数，属于场景适配；未复现原文加速度和转弯时间模型 |',
    '| 初始旧路线 | 64例使用共同P2历史，服务段身份由实际轨迹恢复；不是OARP原生初始化 |',
    '| 原生初始化演示 | 另做7×5小例，用OARP分区与GTSP产生原生条带身份 |',
    '| 区域扩展 | 新增适配，不是原文已验证功能 |',
    '| 完整Algorithm 1：遭遇点循环、边走边算、新事件打断 | 未复现；本轮是固定当前位置的快照核心比较 |',
    '| 原保密地图、ROS和实机实验 | 未复现 |', '',
    '因此本文统一称OARP_CORE_1/2。不能以当前结果直接宣布原论文OARP-Replan优于或劣于P2。', '',
    '## 3. 验证证据与一个重要边界情况', '',
    '- 50项单元检查通过，其中OARP相关14项。552个小规模模型/预算组合采用独立直线条带完整划分穷举核对；包含旧切口，不能只枚举横纵方向后强制合并。',
    '- 混合旧方向的48个组合中，有2个未经强化的模型解未通过完整覆盖解码检查。显式合法性修正后，与穷举结果一致；其中一个修正后判为当前条带预算下不可行。原始输入和修正标志均保留。',
    '- 这不能直接称为论文错误：没有作者代码与作者确认，且部分测试超出原生初始化条件。它是需要记录的本地公式实现/解码边界。合法性强化不是论文原有机制，不作为创新。',
    '- 当前64例×2版本均未触发合法性强化或整数回退，128条输出路线均有效。独立核对128个中间条带/GTSP方案，无错误。',
    f'- {verification["exact_GTSP_checks"]}个执行实例的访问单元数不超过12，使用独立BFS代价和精确动态规划复核，全部GTSP代价差为0。它只证明固定条带/路径包下的访问顺序与方向最优，不证明完整覆盖全局最短；这些执行实例也不是112张独立地图。',
    '- 原生7×5演示中，两种模型在新增条带预算0、1时无解，在2、6、20时返回合法40步路线。无解是模型预算不足，不等于地图不可达。', '',
    '## 4. 与P1/P2的对照结果', '',
    '全部使用run_14冻结的单格地图、目标、覆盖历史、当前位置与基地；不改动P1/P2规则。P1/P2路线复用其已审计保存结果，不跨运行比较耗时。两种新版本每例5秒、单次执行，顺序交替。', '',
    '| 比较 | 共同成功例数 | 核心适配版较短 | 相同 | 原参照较短 |',
    '| --- | ---: | ---: | ---: | ---: |']
for name,c in summary['comparisons'].items():
    w=c['wins']
    lines.append(f'| {name} | {sum(w.values())} | {w.get("core_shorter",0)} | {w.get("equal",0)} | {w.get("baseline_shorter",0)} |')
lines += ['', 'P1原有5例超时保留，不纳入双方成功的步数排名；P2与两个适配版均64例成功。CORE_1总步数10192，CORE_2为10188，P2为10144；两者分别多48步和44步。合计不是统计显著性结论。', '',
    '两个适配版各有28例选中了RANK＋TOUR、28例选中了工程绕行候选、8例保留合法旧后缀。因此“适配版获胜”不能全部归功于论文的条带优化。CORE_2的7个胜例中，1例最终选择的是工程备用路线。', '',
    '纯障碍的24例中，两版对P2均0例较短、12例相同、12例较长；获胜案例出现在扩展或组合事件。这个现象值得分析，但不能据探索集直接确立“区域扩展创新”。', '',
    '预算标定为24次本机合成运行。64例中，两个模型的新增条带预算均为43且没有取等，故当前批次不能证明预算控制提高了效率；紧预算能力仅由小例核验。', '',
    '## 5. 路径例子与研究判断', '',
    '![两个自建路径例子](../算法小型验证_20261010/results/run_16_oarp_default_v3/path_examples.png)', '',
    '第一个例子中CORE_2为144步、P2为158步；第二个例子中CORE_2为154步、P2为130步。两者都完成相同有效目标并返航，区别在条带划分和保留路径包形成的访问限制。', '',
    '当前证据支持保留这一文献核心作为规范参照；不支持直接选它作论文主算法。112个固定访问单元的排序已精确核对，仍出现整体不占优，说明不能把问题都归因于GTSP排序不够好。后续应检查条带数目标与步数目标的差别、路径包约束，以及对P2初始历史的适配影响。', '',
    '要进一步定位原因，应先对同一分区比较“保留旧包”和“拆成独立条带”，并将核心输出与备用路线分开统计。该对照是下一步机制诊断，不是已验证的创新。', '',
    '## 6. 文件与复现', '',
    '- [逐例CSV](../算法小型验证_20261010/results/run_16_oarp_default_v3/results.csv)',
    '- [独立核查](../算法小型验证_20261010/results/run_16_oarp_default_v3/independent_verification.json)',
    '- [精确GTSP核验](../算法小型验证_20261010/results/run_16_oarp_default_v3/exact_GTSP_checks.json)',
    '- [原生核心小例](../算法小型验证_20261010/oarp_replan/native_core_example.json)',
    '- [混合方向核验记录](../算法小型验证_20261010/oarp_replan/mixed_orientation_validation.json)',
    '- [求解器与输入源码清单](../算法小型验证_20261010/results/run_16_oarp_default_v3/manifest.json)', '',
    'run_15是缩短GLNS搜索的调试批次，保留但不作为最终结果。run_16采用default配置；不将两批成绩混合，不声称独立留出验证。', '']
content='\n'.join(lines)
(folder/'结果报告.md').write_text(content.replace('../算法小型验证_20261010/','../../'),encoding='utf-8')
bundle=root.parent/'论文资料汇总_三篇文献与论文主题_20261009'
(bundle/'21_OARP核心实现验证与首轮对照_20261010.md').write_text(content,encoding='utf-8')
print(bundle/'21_OARP核心实现验证与首轮对照_20261010.md')
