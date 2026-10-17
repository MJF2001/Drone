"""Derive paired comparisons and append interpretation; never modify solver data."""
import json
from pathlib import Path
D=Path(__file__).parent;O=D/'results'/'run_27_supplement_metrics_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
rows=json.loads((O/'per_run.json').read_text(encoding='utf-8'))
lookup={(r['case'],r['repeat'],r['budget'],r['algorithm']):r for r in rows if r['kind']=='comparison'}
paired={}
for method in ('STRIP_HV','TREE_MST'):
    rs=[r for r in rows if r['kind']=='comparison' and r['budget']==5 and r['algorithm']==method]
    paired[method]={}
    for metric in ('length','overlap_ratio','turns90','turns180','non_target_steps'):
        ds=[r[metric]-lookup[r['case'],r['repeat'],5,'P2_SHARED'][metric] for r in rs]
        paired[method][metric]={'better':sum(d<0 for d in ds),'equal':sum(d==0 for d in ds),'worse':sum(d>0 for d in ds)}
(O/'paired_5s.json').write_text(json.dumps(paired,ensure_ascii=False,indent=2),encoding='utf-8')
report=B/'37_路径质量指标补充统计_20261012.md'
text=report.read_text(encoding='utf-8')
text+='''
## 补充指标后的判断

1. 5秒预算下，MST加2-opt总长度更短，同时总体重叠率、90°转弯、180°折返和非目标转移也较少。因此本批总量结果没有出现“省步数却增加这些辅助代价”的反转；这不是每个地图均胜出的结论。
2. MST相对P2少372步，分解为历史重复少310步、本轮重复少8步、非目标转移少54步。主要差距在历史已检区域穿行，不应把它解释成基础采集工作量减少；三种方法新覆盖步数均为8008。
3. 条带相对P2少212步：历史重复少314步，但本轮重复多117步，非目标转移少15步。总体重叠降低并不意味着两类重复同时降低。
4. 条带90°转弯1090次，低于MST的1202次；180°折返44次，高于MST的22次。不能只用合并后的转弯次数描述两者，也不赋予能耗结论。
5. 短预算排序仍不同：0.1秒条带重叠率4.95%，P2为13.69%，MST为22.10%。树候选需要足够计算才能表现较好；具体收益来自树初始化还是2-opt，需要后续消融。

### 5秒逐次配对胜负（小者为优）

每个指标均与同状态、同重复的P2比较，共48对；这不是48个独立地图。

|候选|指标|优/平/劣于P2|
|---|---|---|
'''
labels={'length':'长度','overlap_ratio':'覆盖重叠率','turns90':'90°转弯','turns180':'180°折返','non_target_steps':'非目标转移'}
for method,values in paired.items():
    for metric,value in values.items():text+=f'|{method}|{labels[metric]}|{value["better"]}/{value["equal"]}/{value["worse"]}|\n'
text+='''
下一步仍优先做初始化结构消融，解释历史重复路径减少的机制，然后在预先固定的新地图上复核。当前指标补算不要求重跑旧求解。
'''
report.write_text(text,encoding='utf-8')
print(json.dumps(paired,ensure_ascii=False,indent=2))
