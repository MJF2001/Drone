"""Build advisor-facing result report from saved baseline data and new OARP runs."""
import collections,hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
RERUN=WORK/'OARP新版道路复验_汇报用_20261018';DEV=WORK/'DeepSeek_底层算法开发比较_20261018'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    rows={};casewise=collections.defaultdict(dict);provenance={}
    for method in ('P2_MULTI','TREE_MST','PPCPP_CORE4'):
        records=[]
        for p in sorted((DEV/'runs/LONG120/results').glob('*.json')):
            d=load(p)
            if d['method_id']!=method:continue
            assert d['audit']['valid'] and d['resource_check']['ok']
            records.append({'case':d['case_id'],'seed':d['seed'],'steps':d['route_steps'],'seconds':d['call_total_seconds'],
                            'timely':bool(d['within_budget']),'fallback':bool(d['fallback_used'])})
            provenance[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        assert len(records)==20;rows[method]=records
    records=[]
    for j in load(RERUN/'protocol.json')['planned']:
        p=RERUN/'results'/f"{j['plan_id']}.json";d=load(p)
        assert d['flags']['route_valid']
        records.append({'case':j['case'],'seed':j['seed'],'steps':len(d['route'])-1,'seconds':d['public_seconds'],
                        'timely':bool(d['flags']['within_budget']),'fallback':bool(d['flags']['fallback_selected']),
                        'core_complete':d['core_complete'],'core_steps':len(d['core_plan']['route'])-1 if d['core_plan'] else None})
        provenance[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(records)==20;rows['OARP_FULL_SCENE']=records
    keys={(d['case'],d['seed']) for d in records}
    assert all({(d['case'],d['seed']) for d in rs}==keys for rs in rows.values())
    summaries={m:{'n':20,'total_steps':sum(d['steps'] for d in rs),'total_seconds':sum(d['seconds'] for d in rs),
                  'mean_seconds':statistics.mean(d['seconds'] for d in rs),'timely':sum(d['timely'] for d in rs),
                  'fallback':sum(d['fallback'] for d in rs)} for m,rs in rows.items()}
    for m,rs in rows.items():
        for d in rs:casewise[d['case']].setdefault(m,[]).append(d)
    (ROOT/'汇报版数据依据.json').write_text(json.dumps({'summary':summaries,'records':rows,'input_sha256':provenance,
        'new_OARP_configuration':'FULL rank0, all remaining atomic strips; not OARP_CORE2 or author full reproduction',
        'old_three_methods_reused':True,'new_OARP_calls':20},ensure_ascii=False,indent=2),encoding='utf-8')
    labels={'P2_MULTI':'P2_MULTI','TREE_MST':'TREE_MST','PPCPP_CORE4':'PPCPP_CORE4','OARP_FULL_SCENE':'OARP（新版整体条带适配版）'}
    order=['P2_MULTI','TREE_MST','PPCPP_CORE4','OARP_FULL_SCENE']
    table=['| 方法 | 总步数 | 总规划耗时/秒 | 平均每次耗时/秒 | 120秒内合法返回 |',
           '|---|---:|---:|---:|---:|']
    for m in order:
        s=summaries[m];table.append(f"| {labels[m]} | {s['total_steps']} | {s['total_seconds']:.3f} | {s['mean_seconds']:.3f} | {s['timely']}/20 |")
    detail=['| 状态 | P2 | TREE_MST | PPCPP | 新版OARP |','|---|---:|---:|---:|---:|']
    for case in sorted(casewise,key=lambda c:({'small':0,'medium':1,'large':2}[c.split('_')[0]],c)):
        values=[]
        for m in order:
            rs=sorted(casewise[case][m],key=lambda d:d['seed']);a,b=(x['steps'] for x in rs)
            values.append(str(a) if a==b else f'{a}/{b}')
        detail.append('| '+case.removesuffix('_development')+' | '+' | '.join(values)+' |')
    note='；'.join(f"{labels[m]}有{20-summaries[m]['timely']}次超时返回" for m in order if summaries[m]['timely']<20)
    core=sum(d['core_complete'] for d in records)
    o=summaries['OARP_FULL_SCENE'];p=summaries['P2_MULTI']
    conclusion=f"本批汇总中，新版OARP比P2多走{o['total_steps']-p['total_steps']}步（{100*(o['total_steps']/p['total_steps']-1):.2f}%），总规划耗时减少{100*(1-o['total_seconds']/p['total_seconds']):.2f}%。PPCPP耗时最低，但总步数最多。"
    text='''# 剩余覆盖路径规划研究汇报

2026年10月18日

研究面向无人机已经完成部分巡检后，出现新增障碍或待检区域扩展的情况。任务是从当前位置完成所有当前可检的剩余目标并返航。在此基础上，研究整体与局部重规划的适用条件，以及局部重规划范围的确定。

## 一、文献采用的基线算法

| 文献 | 实验采用的基线或比较参照 |
|---|---|
| [OARP-Replan，2024](https://arxiv.org/html/2311.17837v2#S7) | 在线比较：OARP-Original、HR、SB、GD；离线比较：BCD-Offline、LC-Offline、OARP-Offline。 |
| [TRACE，2026预印本](https://arxiv.org/html/2609.21777v1) | BINN、BA*、ε*、PPCPP、IBINN；另有离线TSP/Lin–Kernighan–Helsgaun参照。 |
| [C*，2505.13782v3](https://arxiv.org/html/2505.13782v3#S5) | 单机比较：PPCPP、ε*、BA*、NNCPP、BM、BSA、FSSTC；离线参照：Concorde TSP。能源扩展：ε*+、ECOCPP；多机扩展：Dec-PPCPP、APF-CPP。 |
| [CAP，2025预印本](https://arxiv.org/html/2503.00647v1#S4.SS1) | ε*、BSA、BA*、BINN、PPCPP。 |
| [ε*，2018](https://linkslab.engr.uconn.edu/wp-content/uploads/sites/246/2018/11/e_star_Preprint.pdf) | FS-STC、BSA。 |
| [PPCPP，作者接受稿](https://opus.lib.uts.edu.au/bitstream/10453/138103/6/PPCPP%20A%20Predator.pdf) | BA*、随机邻居；另一个案例比较神经网络方法、Qiu等2006年的神经网络与滚动规划组合。 |
| [BA*](https://link.springer.com/article/10.1007/s10489-012-0406-4) | 完整实验比较名单未确认。 |
| [Yang等，2024，DOI 10.1177/17568293241262323](https://journals.sagepub.com/doi/abs/10.1177/17568293241262323) | 在线STC。 |
| [Hierarchical Coverage Path Planning，2609.12595v1](https://arxiv.org/html/2609.12595v1) | ε*、BINN、PPCPP。 |
| [BCD-GTSP](https://arxiv.org/html/1907.09224v1#S5.SS1) | one_dir单扫描方向配置；另比较区域分解方式和GTSP求解配置。 |
| [FC-Vision](https://arxiv.org/html/2602.13720v2) | Colli-Free、Tar-Aware；实飞比较Colli-Free。 |
| [Adaptive Planning Framework，2504.09294v1](https://arxiv.org/html/2504.09294v1#S4) | 所读实验部分未列出命名的外部算法比较。 |
| [Luna等，DOI 10.1002/rob.22342](https://onlinelibrary.wiley.com/doi/10.1002/rob.22342) | 引用Xie与Chen 2022、Vasquez-Gomez等2018的CPU时间，属于跨论文耗时比较。 |
| [D-STC](https://ieeexplore.ieee.org/document/11029278/) | 正文列出的比较类别包括VFH、APF、DWA、VO、TEB、MPC及学习和图搜索类方法；不统一视为完整覆盖算法。 |
| [MRSimEx-DSTC](https://ieeexplore.ieee.org/document/11165016/) | MR-SimExCoverage、MAC-Planner、STC、Predictive D*-CPP，多机器人比较。 |
| [D2CP](https://ieeexplore.ieee.org/document/11618062/) | 实验比较名单未确认。 |

TRACE和C*共同使用BA*、ε*、PPCPP；ε*又使用FS-STC和BSA。PPCPP、ε*等方法作为覆盖规划比较对象，有较明确的文献依据。BINN与NNCPP在上述文献中对应同一项工作，名称不同不重复计为两种算法。

我们当前用于数值比较的基线如下。

| 方法 | 基本思路 |
|---|---|
| P2_MULTI | 扫描和最近邻生成初始路线，再用多起点与2-opt改善。 |
| TREE_MST | 最小生成树生成访问顺序，再用2-opt改善。 |
| PPCPP_CORE4 | 用局部奖励和死端恢复组织覆盖，适配四邻接移动。 |
| 新版OARP整体条带适配版（FULL） | 将剩余任务划成横纵条带，重新选择条带访问顺序和方向。 |

P2与TREE_MST是自建工程基线；PPCPP与OARP是文献方法的场景适配。ε*修正版尚无本批可比数据，C*与TRACE暂未纳入本表的数值排名。

## 二、空白无障碍区域的路径规划方法

可采用的方法包括：

- 牛耕式往返扫描。
- 螺旋式覆盖。
- 生成树覆盖STC及其变体。
- 单元分解后逐区扫描。
- 条带划分与GTSP访问排序。
- 目标点TSP访问排序。
- 最近邻与2-opt局部优化。
- 波前或距离场引导覆盖。
- ε*、PPCPP等逐步决策覆盖方法。

**对于我们当前的长方形空白、无障碍区域，采用牛耕式往返扫描作为基础覆盖方法即可。**具体比较横向、纵向扫描，并安排好当前位置的接入与覆盖完成后的返航。

## 三、基线算法的步数与时间比较

采用相同10个开发状态，每种方法运行两个种子，共20次。均要求四邻接合法运动、完成全部当前可检目标、满足剩余资源并返航。下表比较完整剩余路线的总步数和总规划耗时，单次软上限120秒。

{TABLE}

{CONCLUSION}

{NOTE}。超时返回的合法路线仍列入总步数作质量比较，但不计入预算内返回数。P2、TREE与PPCPP使用已有同状态结果，OARP使用本轮20次补跑结果；时间均为完整规划入口耗时，依赖预加载另计。

下面列出各状态的路线步数。两种子相同只列一个数，不同时列“A/B”。

{DETAIL}

OARP采用新版整体条带配置（FULL），20次结果全部合法；其中{FALLBACK}次最终选用合法保底候选。

## 四、选择OARP的依据与下一步目的

### 4.1 选择依据

**任务结构接近。**OARP-Replan处理已有覆盖计划被新发现障碍打断后的重规划，与我们的执行中剩余覆盖任务联系直接。

**适合长条与长方形区域。**它先组织连续直线覆盖段，再安排这些条带的访问，有利于结合规则区域的扫描和不规则剩余任务的衔接。

**便于研究路线质量与计算时间。**条带能压缩访问问题的规模，也能表达哪些旧段保留、哪些段允许调整，为后续局部重规划提供结构基础。最终效果仍以完整步数和实际耗时判断。

**存在可验证的改进方向。**在受控对照中，旧路径块绑定和条带划分选择都会影响实际路长，能够分别评价其作用，而不只调整求解时间。

### 4.2 接下来的研究目的

第一步，改进底层路径规划。以新版整体条带配置为参照，让条带划分、访问顺序和旧连接的保留共同服务于完整飞行步数，而不是仅追求条带少或改动少。所有新增计算开销一起评价。

第二步，在底层方法确定后，研究障碍或区域扩展出现时，整体重规划和局部重规划怎样选择，以及局部范围应该多大。既比较哪个范围能得到更短路线，也比较局部稍长时能节省多少计算时间。

### 4.3 当前结果提供的依据

受控矩形实验中，同样五根条带，保留旧连接的核心路线为57步，允许重新连接后为41步；另一个状态中，重新连接为99步，换一种同样五根条带的划分可达到97步。这些固定结构的访问问题已经过精确核验，说明差距与结构选择有关。

目前优先研究按实际路线代价选择划分与连接，暂不优先增加GLNS搜索轮数。上述发现限定于已测用例，后续在道路开发状态上继续验证，再形成最终算法与范围选择方法。
'''
    text=text.replace('{TABLE}','\n'.join(table)).replace('{CONCLUSION}',conclusion).replace('{NOTE}',note or '本批各方法均在预算内返回')
    text=text.replace('{DETAIL}','\n'.join(detail)).replace('{CORE}',str(core)).replace('{LEGAL}','20').replace('{FALLBACK}',str(o['fallback']))
    direction=ROOT/'第四节_底层算法研究方向.md'
    if direction.exists():text=text[:text.index('## 四、')]+direction.read_text(encoding='utf-8')
    next_plan=ROOT/'第五节_下一步规划.md'
    if next_plan.exists():text+='\n'+next_plan.read_text(encoding='utf-8')
    target=ROOT/'导师汇报稿_汇报版_20261018.md';target.write_text(text,encoding='utf-8')
    assert '？' not in text and 'D:/' not in text and '第60份' not in text
    if (WORK/'OARP新版道路复验_短预算_20261018/manifest.json').exists():
        import 更新三档对照
        更新三档对照.main()
    print(json.dumps(summaries,ensure_ascii=False,indent=2));print('report',str(target),'characters',len(target.read_text(encoding='utf-8')))
if __name__=='__main__':main()
