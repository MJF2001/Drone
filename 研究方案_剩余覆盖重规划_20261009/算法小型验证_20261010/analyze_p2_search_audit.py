from pathlib import Path
from collections import defaultdict,Counter
import json
from scenarios import deserialize
from supplement_route_metrics import metrics
D=Path(__file__).parent;O=D/'results/run_29b_p2_search_audit_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
rows=json.loads((O/'runs.json').read_text(encoding='utf-8'));groups=defaultdict(list)
snapshots={}
for name in ('run_20_new_structure_comparison','run_26_unified_new_maps'):
    for r in json.loads((D/'results'/name/'snapshots.json').read_text(encoding='utf-8')):
        s=deserialize(r.get('snapshot',r));snapshots[s.name]=s
for r in rows:
    s=snapshots[r['case']];r['metrics']=metrics(r['route'],s.targets,s.covered)
for r in rows:groups[r['batch'],r['budget'],r['variant']].append(r)
summary=[]
for (batch,budget,variant),rs in sorted(groups.items()):
    term=Counter(e['termination'] for r in rs for e in r.get('events',[]) if 'termination' in e)
    summary.append(dict(batch=batch,budget=budget,variant=variant,n=len(rs),valid=sum(r['independent_audit']['valid'] for r in rs),
        steps=sum(r['independent_audit']['length'] for r in rs),seconds=sum(r['seconds'] for r in rs),
        deadline=sum(r['status'] in ('deadline','planned_at_timeout','timeout') for r in rs),
        core_finished=sum(r.get('core_finished',False) for r in rs) if variant!='TREE' else None,
        finished=sum(r['status']=='finished' for r in rs) if variant!='TREE' else None,terminations=dict(term),
        overlap=sum(r['metrics']['duplicate_target_arrivals'] for r in rs)/sum(r['metrics']['target_arrivals'] for r in rs),
        turns90=sum(r['metrics']['turns90'] for r in rs),turns180=sum(r['metrics']['turns180'] for r in rs)))
lookup={(r['case'],r['budget'],r['repeat'],r['variant']):r for r in rows if r['batch']=='new'}
comparisons=[]
for budget in (5,10,20):
    for method,reference in [('deep128','base8'),('multi','base8'),('multi','deep128'),('multi','TREE')]:
        pairs=[(r,lookup[r['case'],budget,r['repeat'],reference]) for r in rows if r['batch']=='new' and r['budget']==budget and r['variant']==method]
        ds=[a['independent_audit']['length']-b['independent_audit']['length'] for a,b in pairs]
        comparisons.append(dict(budget=budget,method=method,reference=reference,win_tie_loss=[sum(d<0 for d in ds),sum(d==0 for d in ds),sum(d>0 for d in ds)],sum_delta=sum(ds)))
budget_pairs=[]
for variant in ('base8','deep128','multi','TREE'):
    for budget in (10,20):
        ds=[lookup[r['case'],budget,r['repeat'],variant]['independent_audit']['length']-r['independent_audit']['length']
            for r in rows if r['batch']=='new' and r['budget']==5 and r['variant']==variant]
        budget_pairs.append(dict(variant=variant,budget=budget,vs5=[sum(d<0 for d in ds),sum(d==0 for d in ds),sum(d>0 for d in ds)],sum_delta=sum(ds)))
for name,data in [('summary.json',summary),('comparisons.json',comparisons),('budget_pairs.json',budget_pairs)]:
    (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# P2搜索完成度与增强搜索检查（2026-10-12）','',
    '## 实验问题和方法','',
    '分别检查5秒是否导致原P2未完成，以及提高搜索深度/增加初始解能否改善。新批24状态×5/10/20秒×2重复×4方法，共576次；旧批24状态仅对base8与deep128各做5秒一次，共48次。总624次。4个状态在20秒下与原实现逐点回归一致后，才冻结协议运行。','',
    '- base8：原P2顺序和最多8轮2-opt，增加阶段完成/中断日志。','- deep128：先完成并保留base8全部结果，再对四条优化后序列分别增加最多120轮。',
    '- multi：先完成base8及加深搜索，再依次尝试横/纵逆序、横/纵各四次随机片段反转、两个随机排列；每个额外初始解最多32轮。',
    '- TREE：原MST加2-opt同预算复跑，不在搜索充分度检查中给树额外免费计算。','',
    '所有初始化、距离、搜索、展开和候选检查计入预算，独立审计另计；使用共同BFS距离与固定A*连接规则、每次空缓存、相同种子、轮换次序、串行执行。只接收截止前完成展开并检查的候选，中断的2-opt内部序列不免费转成最终路线。','',
    '## 搜索完成情况与路线质量','',
    '|批次|预算|方法|有效|总步数|触及截止次数|核心完成|全部完成|计算总秒|','|---|---:|---|---:|---:|---:|---:|---:|---:|']
for r in summary:lines.append(f'|{r["batch"]}|{r["budget"]}|{r["variant"]}|{r["valid"]}/{r["n"]}|{r["steps"]}|{r["deadline"]}|{r["core_finished"]}|{r["finished"]}|{r["seconds"]:.3f}|')
lines+=['','## 同预算配对','',
    '每项48对（24状态×2次），小者为优。重复不是新增独立地图。','',
    '|预算|候选|参照|优/平/劣|总步数差（候选−参照）|','|---:|---|---|---|---:|']
for r in comparisons:lines.append(f'|{r["budget"]}|{r["method"]}|{r["reference"]}|'+ '/'.join(map(str,r['win_tie_loss']))+f'|{r["sum_delta"]}|')
lines+=['','## 更多预算是否有用','',
    '|方法|预算|相对5秒：优/平/劣|步数差|','|---|---:|---|---:|']
for r in budget_pairs:lines.append(f'|{r["variant"]}|{r["budget"]}|'+ '/'.join(map(str,r['vs5']))+f'|{r["sum_delta"]}|')
lines+=['','## 2-opt退出原因','',
    'no_improving_2opt_move指当前访问序列的严格负增量2-opt邻域没有改进，不代表实际覆盖路线或全局最优；pass_limit指达到人为轮数上限。一次运行包含多次2-opt调用。','',
    '|批次|预算|方法|各退出原因调用次数|','|---|---:|---|---|']
for r in summary:
    if r['variant']!='TREE':lines.append(f'|{r["batch"]}|{r["budget"]}|{r["variant"]}|{r["terminations"]}|')
lines+=['','## 严格解释边界','',
    '多初始解和更深2-opt属于常规强基线，不是论文创新。额外初始解的选择与轮数预先固定，没有按结果选图或调参。两次重复不足以充分表征随机搜索方差。','',
    '如果增强P2胜过树，过去相对原P2的优势就不足以支撑树的独特性；若仍未胜过，也不能证明树全局更优。达到20秒而未完成，仅说明当前增强搜索未结束；不能把20秒当现实无人机必须满足的硬上限。','',
    '协议审查中主动停止过run_29：原设计直接替换8轮，可能在限时下丢失原基线结果。正式run_29b改为先完成原搜索再增强；run_29部分数据保留但不纳入任何本报告结论。',
    '本轮仍是开发地图诊断，未增加真实施工数据、动力学、能耗或连续事件验证。原始路线、完整阶段日志、种子规则和哈希见results/run_29b_p2_search_audit_20261012/。']
(B/'39_P2搜索完成度与增强搜索检查_20261012.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False));print(json.dumps(comparisons,ensure_ascii=False));print(json.dumps(budget_pairs,ensure_ascii=False))
