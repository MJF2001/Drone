from pathlib import Path
import json,hashlib
from collections import defaultdict
D=Path(__file__).parent;O=D/'results/run_29b_p2_search_audit_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
read=lambda n:json.loads((O/n).read_text(encoding='utf-8'))
rows=read('runs.json');follow=read('followup60.json');summary=read('summary.json')
assert len(rows)==624 and len(follow)==8 and all(r['independent_audit']['valid'] for r in rows+follow)
p=read('protocol.json');assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['hashes'].items())
for r in rows:
    if r['batch']=='new' and r['variant'] in ('deep128','multi'):
        base=next(a for a in rows if a['batch']=='new' and a['case']==r['case'] and a['budget']==r['budget'] and a['repeat']==r['repeat'] and a['variant']=='base8')
        assert r['independent_audit']['length']<=base['independent_audit']['length']
report=B/'39_P2搜索完成度与增强搜索检查_20261012.md'
text=report.read_text(encoding='utf-8')
lead='''
## 主要判断

正式624次求解全部通过独立核验，另做8次定向完成性复查。原P2在新批5/10/20秒共144次均正常结束，路线长度逐例一致；旧批5秒24次也正常结束。因此对本批原P2，不能把劣势归因于5秒中断原定搜索。

但“算完原定流程”不等于“搜索充分”。5秒加深版将总步数8948降到8808；多初始解版降到8618；20秒多初始解降到8612。原来的树候选8576步相对原P2少372步，相对增强P2仅少36步（约0.42%）。常规增强搜索消除了约90.3%的原总步数差距。

同预算20秒下，增强P2对树的48次配对为16优、16平、16劣。不能再宣称树存在明确普遍优势；总量上的36步差异不足以证明创新或统计显著性。

20秒下增强P2总体覆盖重叠率2.85%，低于树的3.36%，但90°转弯1814次多于树的1202次，180°折返21次略少于树的22次。多指标上存在取舍，且不推导真实能耗。

我的评审建议：保留增强P2作为正式强对照，暂不把MST加2-opt定为论文主算法。当前需要研究适用条件与新的结构机制，而不能依赖对较弱搜索配置的优势。
'''
text=text.replace('## 实验问题和方法',lead+'\n## 实验问题和方法',1)
text+='\n## 60秒定向完成性复查\n\n所有20秒时触及截止的4次multi均纳入复查，种子及算法不变；各配对树也用60秒预算。事后按截止状态选取，仅诊断中断影响，不是新的独立测试或全批60秒对照。\n\n'
text+='|状态|重复|方法|状态结果|20秒步数|60秒步数|实际秒|\n|---|---:|---|---|---:|---:|---:|\n'
deltas=[]
for r in follow:
    prev=next(a for a in rows if a['case']==r['case'] and a['repeat']==r['repeat'] and a['variant']==r['variant'] and a['budget']==20)
    a=prev['independent_audit']['length'];b=r['independent_audit']['length']
    if r['variant']=='multi':deltas.append(b-a)
    text+=f'|{r["case"]}|{r["repeat"]}|{r["variant"]}|{r["status"]}|{a}|{b}|{r["seconds"]:.3f}|\n'
text+=f'\n四次增强P2相对20秒的步数变化合计：{sum(deltas)}；正常结束{sum(r["status"]=="finished" for r in follow if r["variant"]=="multi")}/4。即使全部正常结束，也只完成本次有限初始解与局部搜索，仍无全局最优保证。\n'
text+='\n## 后续取舍\n\n优先冻结增强基线并验证独立地图，再考虑针对扩张后残余覆盖结构的机制改进。两次随机重复与两批模板地图不能支撑算法普遍优越性；本轮不预定论文创新点。\n'
report.write_text(text,encoding='utf-8')
print('PASS 632 valid routes, source/input hashes unchanged, enhanced candidates never worse than base8')
print('followup multi deltas',deltas)
