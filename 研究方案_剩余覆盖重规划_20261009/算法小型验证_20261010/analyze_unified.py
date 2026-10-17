from pathlib import Path
import json
from collections import Counter
from PIL import Image,ImageDraw,ImageFont
from scenarios import deserialize

D=Path(__file__).parent;O=D/'results'/'run_26_unified_new_maps'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
def read(name):return json.loads((O/name).read_text(encoding='utf-8'))
rows=read('runs.json');refs=read('references.json');summ=read('summary.json');frozen=read('snapshots.json')
lookup={(r['case'],r['budget'],r['repeat'],r['algorithm']):r for r in rows}
snaps={r['snapshot']['name']:r for r in frozen}
methods=['P2_SHARED','STRIP_HV','TREE_MST'];names=list(snaps)
extras={}
for budget in (.1,.5,5):
    for method in methods[1:]:
        pairs=[[lookup[n,budget,k,method]['audit']['length']-lookup[n,budget,k,'P2_SHARED']['audit']['length'] for k in (0,1)] for n in names]
        extras[f'{budget}_{method}']={'stable_wins':sum(max(p)<0 for p in pairs),'stable_ties':sum(p==[0,0] for p in pairs),
            'stable_losses':sum(min(p)>0 for p in pairs),'mixed':sum(not(max(p)<0 or p==[0,0] or min(p)>0) for p in pairs)}
refmap={r['case']:r for r in refs}
extras['P2_reference_steps']=sum(r['audit']['length'] for r in refs)
extras['source_counts_5s']={m:dict(Counter(r['source'] for r in rows if r['budget']==5 and r['algorithm']==m)) for m in methods}
extras['P2_5s_vs_20s']={
    'shorter':sum(lookup[n,5,k,'P2_SHARED']['audit']['length']<refmap[n]['audit']['length'] for n in names for k in (0,1)),
    'equal':sum(lookup[n,5,k,'P2_SHARED']['audit']['length']==refmap[n]['audit']['length'] for n in names for k in (0,1)),
    'longer':sum(lookup[n,5,k,'P2_SHARED']['audit']['length']>refmap[n]['audit']['length'] for n in names for k in (0,1))}
extras['reference_valid']=sum(r['independent_audit']['valid'] for r in refs)
extras['max_seconds_over_budget']=max(r['seconds']-r['budget'] for r in rows)
extras['family_5s']={f:{m:sum(r['audit']['length'] for r in rows if r['budget']==5 and r['algorithm']==m and r['metadata']['family']==f)
    for m in methods} for f in ('straight','obstacle','corner_obstacle')}
(O/'analysis.json').write_text(json.dumps(extras,ensure_ascii=False,indent=2),encoding='utf-8')

def gap(n,m):return sum(lookup[n,5,k,m]['audit']['length']-lookup[n,5,k,'P2_SHARED']['audit']['length'] for k in (0,1))/2
best=min(names,key=lambda n:gap(n,'STRIP_HV'))
worst=max(names,key=lambda n:max(gap(n,'STRIP_HV'),gap(n,'TREE_MST')))
selected=list(dict.fromkeys([best,worst]))
assets=B/'_统一实现复核图';assets.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
figures=[]
for index,n in enumerate(selected,1):
    record=snaps[n];s=deserialize(record['snapshot']);meta=record['metadata']
    domain=set(map(tuple,meta['domain']));xs=[p[0] for p in domain];ys=[p[1] for p in domain]
    cell=min(16,630//(max(xs)-min(xs)+1));w=700;h=max(360,(max(ys)-min(ys)+1)*cell+115)
    image=Image.new('RGB',(w*3,h),'white');draw=ImageDraw.Draw(image)
    for j,m in enumerate(methods):
        r=lookup[n,5,0,m];ox=j*w+24;oy=65
        for p in domain:
            x,y=p;box=(ox+(x-min(xs))*cell,oy+(y-min(ys))*cell,ox+(x-min(xs)+1)*cell-1,oy+(y-min(ys)+1)*cell-1)
            color='#f1f3f5'
            if p in s.targets:color='#ffffff'
            if p in s.covered:color='#c4d8e8'
            if p in s.targets and p not in set(map(tuple,meta['initial_targets'])):color='#d5efd1'
            if p in set(map(tuple,meta['obstacles'])):color='#444444'
            draw.rectangle(box,fill=color,outline='#dddddd')
        coords=[(ox+(x-min(xs)+.5)*cell,oy+(y-min(ys)+.5)*cell) for x,y in r['route']]
        draw.line(coords,fill=['#1565c0','#d45b17','#7b359a'][j],width=2)
        for p,color in ((s.base,'#e53935'),(s.current,'#00a89b')):
            x,y=p;cx=ox+(x-min(xs)+.5)*cell;cy=oy+(y-min(ys)+.5)*cell
            draw.ellipse((cx-4,cy-4,cx+4,cy+4),fill=color)
        draw.text((j*w+24,12),f'{m}：{r["audit"]["length"]}步',font=font,fill='#111111')
    draw.text((24,h-37),'蓝灰：已覆盖  绿：新增待检  深灰：障碍  红点：基地  青点：当前位置；路线含返航',font=small,fill='#222222')
    p=assets/f'case_{index}.png';image.save(p)
    figures.append((n,p))

lines=['# 统一实现与新地图复核结果（2026-10-11）','',
'## 主要判断','',
'本轮432次等预算运行和24次长预算参照全部通过独立核验。5秒预算下，MST加2-opt总步数8576，比P2的8948少4.16%；条带候选8736，少2.37%。这是值得继续追查的算法实现差距，尚不是论文创新性证据。','',
'MST加2-opt在24个状态中有15个两次均优于P2、5个均平、4个均劣；0.1秒下总步数却比P2多9.53%。条带在短预算下更有优势。计算预算与初始化结构可能存在互补，但不能仅取各图事后最好结果，就宣称形成了新算法。','',
'## 本轮目的','',
'排除距离计算实现不同带来的比较偏差，检查P2、横纵条带候选与MST候选在新参数地图上的差距。此次没有提出或验证新的覆盖算法。','',
'## 统一了什么','',
'三种方法共享按需BFS最短距离、固定选择规则的A*连接路径、途中经过目标即完成覆盖的规则、候选路线检查及共同保底路线。每次运行使用独立空缓存。MST原来独立构造BFS，现在调用共同距离接口。历史代码及结果保留。','',
'连接路径采用端点坐标排序后的固定方向计算，再按需要反转，避免算法查询先后改变同长最短路径。这改变了旧实验的路径选择细节，因此本轮数据用于内部公平对照，不能直接与旧轮次相减来宣称算法改进。','',
'候选有效性检查计入预算；输出后另用历史独立检查器核验覆盖、合法移动和返航。截止时间为协作式软限制，实际耗时和超时均保留。','',
'## 地图和实验安排','',
'初始道路23×6或35×8格；开放飞行域或道路走廊飞行域；初始横向牛耕路线覆盖约35%或70%时发布事件。事件为直线新增区域、2×2障碍、拐角新增区域与障碍同时出现，共24个状态。扩展长度从7、10、13格按预先固定种子选取。飞行域预先固定，扩展的是待检目标范围。','',
'障碍出现位置按固定随机顺序选取，不覆盖当前位置或基地，并通过可达性检查。障碍下尚未检查的目标记为暂不可检，不计入当次可完成目标；绝不记成已完成。暂不模拟障碍消失。','',
'同一地图历史产生三个事件状态，因此24个状态来自8段初始历史，不能当作24个完全独立现场。它们是熟悉形状下的新参数开发验证集，尚非最终留出测试集。','',
'每状态采用0.1、0.5、5秒预算，三种方法各重复2次，共432次；方法与预算顺序轮换，顺序执行。另做24次20秒P2参照。随机种子、地图和源码SHA256在正式运行前写入protocol.json与snapshots.json；本轮未根据结果调整参数。','',
'## 结果','',
'步数为24状态×2次运行的总和，均包含完成剩余覆盖后的返航。重复运行不是新增独立样本。','',
'|预算/秒|方法|有效/48|总步数|优/平/劣于同预算P2|累计计算秒|超预算10ms次数|',
'|---|---|---:|---:|---|---:|---:|']
for r in summ:
    lines.append(f'|{r["budget"]}|{r["method"]}|{r["valid"]}|{r["total_steps"]}|'+ '/'.join(map(str,r['win_tie_loss_vs_P2']))+f'|{r["total_seconds"]:.3f}|{r["overruns"]}|')
lines+=['','5秒预算下，两次重复均优/均平/均劣/其他：','']
for m in methods[1:]:
    e=extras[f'5_{m}']
    lines.append(f'- {m}：均优{e["stable_wins"]}、均平{e["stable_ties"]}、均劣{e["stable_losses"]}、其余{e["mixed"]}个状态。')
lines+=['','按事件拆分5秒总步数（各8状态×2次）：','',
    '|事件|P2|条带|MST加2-opt|','|---|---:|---:|---:|']
for f,values in extras['family_5s'].items():lines.append('|'+f+'|'+ '|'.join(str(values[m]) for m in methods)+'|')
lines+=['',f'20秒P2的24状态总步数：{extras["P2_reference_steps"]}；5秒P2的48条路线长度全部与对应20秒结果一致。这仅说明当前搜索流程已结束，不能说明全局最优。',
f'参照结果独立核验有效：{extras["reference_valid"]}/24。最大预算超出：{extras["max_seconds_over_budget"]:.4f}秒。','',
'## 代表路线（从结果中选取，属于诊断展示）','',
'选择条带相对P2差距最小的状态，以及两候选相对P2差距最大的状态。图示为5秒预算第一次重复；不是随机抽样，也不是额外验证。']
for n,p in figures:
    lines+=['',f'### {n}','',f'![三种路线对照]({p.as_posix()})','',
        '|方法|步数|重复访问位置次数|方向改变次数|最终来源|','|---|---:|---:|---:|---|']
    for m in methods:
        r=lookup[n,5,0,m];a=r['independent_audit']
        lines.append(f'|{m}|{a["length"]}|{a["revisited_positions"]}|{a["direction_changes"]}|{r["source"]}|')
lines+=['','## 解释边界与下一步','',
'附加诊断：在上述两个展示状态上，将P2四类初始序列的2-opt上限由8轮提高到128轮，共16次求解，路线长度均未继续改善，且全部有效。因此这两个例子的差距不由8轮上限解释。该检查为看到结果后的定向分析，不并入432次公平对照，也不能外推其他地图。完整记录见posthoc_depth_check.json。','',
'直线扩展展示例中，P2为231步、条带203步、MST加2-opt195步；拐角加障碍展示例中，P2为170步，另两者分别182和172步。两类相反例子说明继续研究需要解释适用条件，不能简单替换基线。','',
'这些结果能判断具体实现的路线质量和有限计算表现，不能替代原论文复现。横纵条带候选并非完整OARP-Replan，MST候选更不是TRACE或C*。','',
'总步数优势必须结合逐状态胜负判断；某方法在个别图上获胜，不能直接推出一种表示整体更好。路线图的往返、交叉仅是现象；判断原因需要进一步做保留结构、排序和途中覆盖规则的单独消融。','',
'建议下一步先做初始化结构消融：固定同一局部搜索和实际路线评价，比较扫描、条带、树产生的初始解；分别记录初始步数、搜索后步数和耗时，判断优势来自初始化、搜索还是途中覆盖处理。当前MST的44/48条5秒输出来自2-opt之后，不能把优势全部归于树本身。','',
'同时在预先固定的独立地图上复核；优先保留树初始化与条带快速初始化两个候选，暂不搭建复杂融合算法。新增方向须超过普通多初始解加2-opt这一强对照，并解释机制，才值得讨论论文贡献。若优势不能复现，应停止该路线。','',
'原始记录：算法小型验证_20261010/results/run_26_unified_new_maps/。summary.json为汇总，analysis.json记录重复一致性，runs.json和references.json保留全部路线与审计结果。']
report=B/'36_统一实现与新地图复核结果_20261011.md'
report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(extras,ensure_ascii=False,indent=2))
print(report)
