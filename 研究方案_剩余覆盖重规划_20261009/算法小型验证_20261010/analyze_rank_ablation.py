from pathlib import Path
from collections import defaultdict
import json,statistics
D=Path(__file__).parent;O=D/'results/run_28_rank_ablation_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
read=lambda n:json.loads((O/n).read_text(encoding='utf-8'))
rows=read('runs.json');seeds=read('initializations.json');completion=read('completion.json')
groups=defaultdict(list)
for r in rows:groups[(r['phase'],r['batch'],r['budget'],r['variant'],r['algorithm'])].append(r)
summary=[]
for key,rs in sorted(groups.items()):
    phase,batch,budget,variant,method=key
    summary.append(dict(phase=phase,batch=batch,budget=budget,variant=variant,method=method,n=len(rs),
        valid=sum(r['independent_audit']['valid'] for r in rs),steps=sum(r['independent_audit']['length'] or 0 for r in rs),
        seconds=sum(r['seconds'] for r in rs),overruns=sum(r['overrun_gt_10ms'] for r in rs)))
sg=defaultdict(list)
for r in seeds:sg[(r['batch'],r['seed'],r['stage'])].append(r)
seed_summary=[dict(batch=b,seed=s,stage=t,n=len(rs),steps=sum(r['independent_audit']['length'] for r in rs),
    valid=sum(r['independent_audit']['valid'] for r in rs)) for (b,s,t),rs in sorted(sg.items())]
pair=defaultdict(dict)
for r in rows:
    if r['phase']=='cross':pair[r['batch'],r['case'],r['budget'],r['repeat'],r['variant']][r['algorithm']]=r['independent_audit']['length']
win=defaultdict(lambda:[0,0,0])
for (batch,case,budget,repeat,variant),values in pair.items():
    for m in ('STRIP_HV','TREE_MST'):
        d=values[m]-values['P2_SHARED'];win[batch,budget,variant,m][0 if d<0 else 1 if d==0 else 2]+=1
for name,data in [('summary.json',summary),('seed_summary.json',seed_summary),('paired.json',[{'key':k,'win_tie_loss':v} for k,v in sorted(win.items())])]:
    (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 排名变化与初始化结构消融（2026-10-12）','',
    '## 目的与结论边界','',
    '交叉使用历史run_20与run_26的各24个状态，检验地图批次、距离实现、同长最短路径选择及初始化/局部搜索的影响。固定协议在运行前落盘，不修改历史数据或按结果调参。此为开发诊断，不是独立留出测试。','',
    '两批地图同时改变道路尺寸、障碍形状、初始扫描方向与进度。批次效应仅能归于这一组合，不能解释为某一个几何因素的因果作用。','',
    f'完成记录：{completion}。共同检查合法移动、全部可检目标覆盖及返航。计算预算为软截止，等待与飞行动力学未模拟。','',
    '## 1．旧实现锚点复查','',
    '原structure_candidates在旧地图以原种子3000+编号重新运行一次。与历史结果逐例核对另见结果记录；GLNS及软时间限制可能导致运行差异。','',
    '|方法|24例总步数|计算总秒|有效|','|---|---:|---:|---:|']
for r in summary:
    if r['phase']=='anchor':lines.append(f'|{r["method"]}|{r["steps"]}|{r["seconds"]:.3f}|{r["valid"]}/{r["n"]}|')
lines+=['','## 2．同一实现下地图批次与连接规则交叉','',
    'legacy_ties：同长最短路径由第一次查询的方向决定；canonical_ties：按端点坐标固定计算方向。两者最短距离相同，但可能经过不同格子，从而影响顺路覆盖与跳过服务。两者均使用BFS距离及相同验证器。','',
    '每行48次，即24状态×2次。相同种子配对；方法/规则次序轮换。','',
    '|地图批次|预算|连接规则|方法|总步数|对P2优/平/劣|有效|','|---|---:|---|---|---:|---|---:|']
for r in summary:
    if r['phase']=='cross':
        counts=win.get((r['batch'],r['budget'],r['variant'],r['method']),[0,48,0])
        lines.append(f'|{r["batch"]}|{r["budget"]}|{r["variant"]}|{r["method"]}|{r["steps"]}|'+ '/'.join(map(str,counts))+f'|{r["valid"]}/{r["n"]}|')
lines+=['','## 3．距离计算实现配对','',
    '只针对P2，固定legacy连接规则、相同算法及验证器，比较逐对A*与按源点BFS距离。各24次、5秒预算。若路线长度一致而时间下降，可视为实现加速；限时下路线差异不能自动归于规划创新。','',
    '|地图批次|距离实现|总步数|总计算秒|有效|','|---|---|---:|---:|---:|']
for r in summary:
    if r['phase']=='distance':lines.append(f'|{r["batch"]}|{r["variant"]}|{r["steps"]}|{r["seconds"]:.3f}|{r["valid"]}/{r["n"]}|')
lines+=['','## 4．初始化与相同2-opt消融','',
    '共享canonical连接，五类初始序列为横扫、纵扫、最近邻、树正序、树逆序；分别展开检查原路线，再做最多8轮相同2-opt并再次展开。这里允许搜索结束，不设置计算预算，用于机制诊断，不用于限时性能比较。共480条路线。树生成包含当前位置，扫描生成排除已在当前位置完成的目标，均遵守相同实际覆盖规则。','',
    '2-opt优化访问序列距离，最终评价实际展开覆盖路线。序列目标与途中覆盖后的实际成本可能不同，所以优化后实际路线未必更短。原路线仍应保留为候选。','',
    '|批次|初始化|搜索前总步数|搜索后总步数|变化（后−前）|','|---|---|---:|---:|---:|']
ss={(r['batch'],r['seed'],r['stage']):r['steps'] for r in seed_summary}
for b in ('old','new'):
    for s in ('H_scan','V_scan','nearest','tree_forward','tree_reverse'):
        a=ss[b,s,'before'];c=ss[b,s,'after'];lines.append(f'|{b}|{s}|{a}|{c}|{c-a:+}|')
lines+=['','## 5．应怎样使用本轮结论','',
    '比较同一行条件下的三方法才能判断相对优劣，不能直接比较两批总步数大小，因为待检工作量不同。每个方法的公开名称仍是工程候选；MST不是TRACE、C*或标准STC。','',
    '初始化消融不含GLNS条带排序，不能解释条带方法全部收益；没有保留全部搜索过程的完整轨迹，也不能声称已分离每一种操作的贡献。对最终方法仍需同预算配对、机制消融和独立地图检验。','',
    '原始路线、独立审计、源文件与输入哈希见算法小型验证_20261010/results/run_28_rank_ablation_20261012/。']
(B/'38_排名变化与初始化结构消融_20261012.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False));print(json.dumps(seed_summary,ensure_ascii=False))
