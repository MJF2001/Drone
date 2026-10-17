import json
from pathlib import Path
from collections import defaultdict
D=Path(__file__).parent;O=D/'results/run_28_rank_ablation_20261012'
read=lambda n:json.loads((O/n).read_text(encoding='utf-8'))
summary=read('summary.json');runs=read('runs.json');seeds=read('initializations.json')
for r in summary:
    if r['budget']==5:print(r)
# Candidate best comparisons are diagnostics, not an algorithm timing result.
by=defaultdict(dict)
for r in seeds:by[r['batch'],r['case'],r['stage']][r['seed']]=r['independent_audit']['length']
out=[]
for batch in ('old','new'):
    for stage in ('before','after'):
        entries=[v for (b,c,t),v in by.items() if b==batch and t==stage]
        scan=[min(v[k] for k in ('H_scan','V_scan','nearest')) for v in entries]
        tree=[min(v[k] for k in ('tree_forward','tree_reverse')) for v in entries]
        out.append(dict(batch=batch,stage=stage,scan_best=sum(scan),tree_best=sum(tree),
            tree_win_tie_loss=[sum(t<s for s,t in zip(scan,tree)),sum(t==s for s,t in zip(scan,tree)),sum(t>s for s,t in zip(scan,tree))]))
print('INITIALIZATION',json.dumps(out))
anchor={r['case']+'|'+r['algorithm']:r for r in runs if r['phase']=='anchor'}
old=json.loads((D/'results/run_20_new_structure_comparison/results.json').read_text(encoding='utf-8'))
anchor_matches={m:sum(anchor[r['case']+'|'+m]['independent_audit']['length']==r['audit']['length'] for r in old if r['algorithm']==m) for m in ('P2_SHARED','STRIP_HV','TREE_MST')}
print('ANCHOR_LENGTH_MATCHES',anchor_matches)
(O/'diagnostic_best_seeds.json').write_text(json.dumps({'best_seeds':out,'anchor_length_matches':anchor_matches},ensure_ascii=False,indent=2),encoding='utf-8')
rp=B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'/'38_排名变化与初始化结构消融_20261012.md'
text=rp.read_text(encoding='utf-8')
keys={(r['phase'],r['batch'],r['budget'],r['variant'],r['method']):r for r in summary}
cross={}
for r in runs:
    if r['phase']=='cross':cross[r['batch'],r['case'],r['budget'],r['repeat'],r['algorithm'],r['variant']]=r
changes={}
for method in ('P2_SHARED','STRIP_HV','TREE_MST'):
    matched=[(r,cross[b,c,t,k,m,'canonical_ties']) for (b,c,t,k,m,v),r in cross.items() if v=='legacy_ties' and m==method and t==5]
    changes[method]=dict(pairs=len(matched),different_lengths=sum(a['independent_audit']['length']!=b['independent_audit']['length'] for a,b in matched),
        different_routes=sum(a['route']!=b['route'] for a,b in matched))
text+='\n## 6．本轮归因证据\n\n'
text+=f'原实现锚点逐例长度复现数量（各24）：{anchor_matches}。\n\n'
text+='5秒预算同长路径规则配对：'+json.dumps(changes,ensure_ascii=False)+'。条带包含限时随机求解，少量路线差异不能仅凭一次配对归因于连接规则。\n\n'
text+='|批次|统一连接下P2总步数|MST总步数|MST相对变化|\n|---|---:|---:|---:|\n'
for b in ('old','new'):
    a=keys['cross',b,5,'canonical_ties','P2_SHARED']['steps'];t=keys['cross',b,5,'canonical_ties','TREE_MST']['steps']
    text+=f'|{b}|{a}|{t}|{(t/a-1):+.2%}|\n'
text+='\n同一实现中，若旧批P2胜而新批MST胜，说明地图/覆盖历史组合足以产生排名反转，无需诉诸超过20秒计算或换用GPU。仍未分离组合内部的尺寸、方向、进度与障碍形状效应。\n\n'
text+='|批次|阶段|扫描/最近邻候选最佳总步数|两种树序最佳总步数|树优/平/劣状态数|\n|---|---|---:|---:|---|\n'
for r in out:text+=f'|{r["batch"]}|{r["stage"]}|{r["scan_best"]}|{r["tree_best"]}|'+ '/'.join(map(str,r['tree_win_tie_loss']))+'|\n'
text+='\n每状态事后取候选最小值仅用于分离初始化与搜索影响；不是有额外免费计算的最终规划算法。主对照保留相同计算预算。扫描候选有3个、树候选有2个，不能把候选数量差异忽略。\n'
rp.write_text(text,encoding='utf-8')
print('CONNECTOR_PAIRS',changes)
