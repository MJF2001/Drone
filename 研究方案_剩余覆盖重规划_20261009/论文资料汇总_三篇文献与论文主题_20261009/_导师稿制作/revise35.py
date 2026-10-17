from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RESULTS=ROOT.parent/'算法小型验证_20261010'/'results'
FONT='C:/Windows/Fonts/msyh.ttc'
palette={'flight':'#f6f7f9','pending':'#d5dbe2','covered':'#81b7df','new':'#f1c465','obstacle':'#333333'}
def pts(xs):return {tuple(p) for p in xs}
def draw(canvas,s,title,before=False,route=None,offset=0):
    d=ImageDraw.Draw(canvas)
    m=s['metadata']; domain=pts(m['domain']); old=pts(m['initial_targets'])
    published=old if before else pts(m['published_targets'])
    covered=pts(s['covered']); blocked=set() if before else pts(m['obstacles'])
    x0=min(x for x,y in domain);x1=max(x for x,y in domain)
    y0=min(y for x,y in domain);y1=max(y for x,y in domain)
    scale=min(1100/(x1-x0+1),620/(y1-y0+1))
    ox=offset+600-(x1-x0+1)*scale/2;oy=120+(620-(y1-y0+1)*scale)/2
    def center(p):return ox+(p[0]-x0+.5)*scale,oy+(p[1]-y0+.5)*scale
    for x,y in sorted(domain):
        color=palette['flight']
        if (x,y) in published:color=palette['covered'] if (x,y) in covered else palette['new'] if (x,y) not in old else palette['pending']
        if (x,y) in blocked:color=palette['obstacle']
        px,py=ox+(x-x0)*scale,oy+(y-y0)*scale
        d.rectangle((px,py,px+scale,py+scale),fill=color,outline='white',width=1)
    if route:
        d.line([center(p) for p in route],fill='#9a3d8e',width=5)
    bx,by=center(s['base']);f=ImageFont.truetype(FONT,40)
    d.text((bx,by),'★',font=f,fill='#142d4d',anchor='mm')
    cx,cy=center(s['current']);r=11
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#c0392b',outline='white',width=2)
    d.text((offset+600,40),title,font=ImageFont.truetype(FONT,33),fill='black',anchor='mt')
def save_pair(name,panels,route=None,micro=False):
    canvas=Image.new('RGB',(2400,860),'white')
    for i,(s,title,before) in enumerate(panels):draw(canvas,s,title,before,route if i==1 else None,i*1200)
    d=ImageDraw.Draw(canvas);font=ImageFont.truetype(FONT,29)
    legends=[(palette[k],v) for k,v in [('pending','原区域未检'),('covered','已完成'),('new','新增待检'),('obstacle','障碍')]]+[('#c0392b','当前位置'),('#142d4d','★ 基地')]
    for i,(color,label) in enumerate(legends):
        x=270+i*320;d.rectangle((x,795,x+28,823),fill=color)
        d.text((x+40,789),label,font=font,fill='black')
    canvas.save(HERE/name)

medium=json.loads((RESULTS/'run_20_new_structure_comparison/snapshots.json').read_text(encoding='utf-8'))
opened=next(s for s in medium if s['name']=='holdout_open_L21_W5_h0_corner_obstacle')
corridor=next(s for s in medium if s['name']=='holdout_corridor_L21_W5_h0_corner_obstacle')
save_pair('experiment_domains.png',[(opened,'开放飞行域样本',False),(corridor,'走廊飞行域样本',False)])
save_pair('experiment_event.png',[(opened,'事件发布前 已检39格 原区域105格',True),(opened,'同一状态发布拐角扩展与新障碍',False)])
micro=json.loads((RESULTS/'run_21_micro_global_optimum/snapshots.json').read_text(encoding='utf-8'))
small=next(s for s in micro if s['name']=='micro_open_L4_W2_p50_corner_obstacle')
rs=json.loads((RESULTS/'run_21_micro_global_optimum/results.json').read_text(encoding='utf-8'))
ex=next(r for r in rs if r['case']==small['name'] and r['algorithm']=='EXACT_GRID')
assert ex['length']==14 and ex['pending']==9
save_pair('experiment_exact.png',[(small,'小规模事件后地图 剩余9个目标',False),(small,'精确最优路线 14步并返回基地',False)],route=ex['route'],micro=True)

old='34_导师汇报稿_算法实现与实验流程说明_20261011'
new='35_导师汇报稿_实验设计图解版_20261011'
s=(ROOT/(old+'.md')).read_text(encoding='utf-8')
# Apply both comments to the latest version while preserving its implementation explanations.
s=s.replace('**为什么比较**：P2用于检验“直接重新求解剩余问题是否已经足够”。它保留已完成覆盖记录；“整体重算”指重新安排未完成任务，不是让无人机重新检查全部道路。P2也不保证全局最优。\n\n','')
s=s.replace('它采用预定方向的简单划分，用于单独检验条带表示和方向选择，不包含OARP的完整条带重划模型。','')
s=s.replace('MST候选不具备TRACE的层次分解树更新或C*的覆盖图维护机制，其成绩不能代表这两篇文献。','')
start=s.index('### 6 计算限时与共同保底规则')
end=s.index('## 五 前期实验结果与阶段性发现')
section='''## 四 实验设计与地图示例

### 1 地图是什么样的

实验将道路离散成方格，采用一条长方形道路作为初始待检区域，再设置向前直线延伸或向侧方转弯的新增区域。无人机每移动一格计一步，能够检查正下方的一格；障碍格不能飞入，其遮挡的未检路面暂缓检查。

![两种飞行域](experiment_domains.png)

图2 中等规模实验中的真实地图样本

**开放飞行域**允许无人机在道路周围较大的区域内绕行；**走廊飞行域**仅允许在道路及其邻近一格的范围内移动。图中浅色背景格表示可飞行但不要求检查的空间，空白处表示飞行域之外。两图分别取自各自实验样本，并非同一地图的配对结果。

当前地图中的可飞行范围预先固定，事件发布时增加的是其中的待检路面。实验尚未同时模拟电子围栏向外扩大。

### 2 什么时候加入障碍和新增区域

**按覆盖进度触发事件**：先执行初始路线，达到预设的已检比例后，发布新增区域或新障碍。达到比例指“已检格数÷初始待检格数”，不是已飞行时间或已走路线的比例。

![事件加入前后](experiment_event.png)

图3 同一实验样本的事件发布前后

图3样本的触发阈值约为36.24%。初始道路共有105格，实际执行至已检39格时首次达到阈值，此时保持无人机位置和已检记录不变，发布拐角新增区域及3格障碍。其中1格遮挡未检路面，该目标转为暂缓；其余可执行目标参加重规划。

**一次实验的顺序**：执行原路线 → 达到覆盖比例 → 发布变化 → 保存此刻状态 → 各算法分别重规划 → 检查剩余覆盖与返航路线。保存的状态称为“快照”，包含地图、当前位置、已检格和剩余目标。

基础64例使用18×6、24×9格初始道路，在达到25%或75%覆盖时发布事件。事件分为无变化、直线扩展、拐角扩展、近处障碍、远处障碍、窄通道障碍，以及扩展与通道障碍组合，共8类；另设开放与走廊两种飞行域。因此为2种尺寸×2种飞行域×2个阶段×8类事件＝64例。

### 3 中等规模同预算实验怎样设计

**地图和事件**：初始道路为21×5或29×7格，直线新增段长度或拐角新增臂长取6、8、11格之一。每种尺寸设置开放、走廊两种飞行域，再设置两种执行阶段：一组从30%—48%之间抽取触发比例，另一组从57%—78%之间抽取。前一组使用横向初始扫描，后一组使用纵向初始扫描；阶段与扫描方向在本批中联动，未单独分离其影响。

**共24个状态**：每种尺寸、飞行域和执行阶段分别产生直线扩展、仅出现障碍、拐角扩展并出现障碍这3类事件。障碍优先放在旧路线尚未执行部分经过的位置，形状为1×3或3×1格，并避开当前位置和基地。因此为2种尺寸×2种飞行域×2组阶段×3类事件＝24例。

**同预算怎样比较**：对每个状态，分别运行P2整体重算、横纵条带候选和MST树候选，各给5秒总计算预算。三种方法使用相同的地图、当前位置、已检记录、剩余目标和基地；先尝试相同的基础可行候选，再开展各自搜索。表中的P2_SHARED即采用这一共同起始规则的P2。

每个状态在该轮每种方法运行一次，共24×3＝72次求解；逐例轮换算法运行顺序。保存输出路线并独立检查，比较合法路线的剩余覆盖与返航总步数。5秒是统一的搜索预算，实际耗时另行记录，并检查超时情况。

**这组实验要回答**：在相同计算机会下，条带或树组织方式是否比直接重算得到更短的剩余路线？其目的不是证明任何方法达到全局最优。

### 4 小规模最优实验怎样设计

**为什么缩小地图**：中等规模难以直接求出全局最少步数。为判断P2是否还有改进空间，另建足够小的地图，允许精确算法穷尽必要状态，求出完成全部剩余覆盖并返航的最少步数。

![小规模地图与精确路线](experiment_exact.png)

图4 小规模真实样本及精确求得的最优路线

图4左图来自4×2格初始道路，在50%覆盖阶段发布拐角扩展与障碍，事件后剩余9个可执行目标。右图紫线为保存的精确最优路线，共14步，起于红点并返回星形基地；线条重合表示重复经过，不代表漏计步数。

**48例怎样组成**：初始道路取4×2、6×2、4×3格，分别设置两种飞行域、50%和75%两个覆盖阶段，以及无变化、直线扩展、仅障碍、拐角扩展加障碍四类事件。因此为3种尺寸×2种飞行域×2个阶段×4类事件＝48例，每例剩余目标不超过12格。

**怎样求最少步数**：精确搜索同时记录“无人机在哪一格”和“哪些剩余目标已经经过”，按移动步数逐层搜索。只有全部目标已检查且回到基地才算完成，第一次找到的完成状态给出全局最少步数。它能识别途中顺便覆盖，也会计入重复移动。

**怎样核对算法**：精确搜索每例最多给30秒；三种启发式仍各给5秒，与对应最优步数逐例比较。两类时间不是公平竞速预算：精确方法用于确定答案，启发式用于评价路线质量。随后再用目标间最短距离上的独立精确访问排序交叉核验。

另外96例小规模结构压力测试，用于检查P2在预设困难结构下是否仍接近最优，与48例是两批数据，结果分别报告。

### 5 怎样理解这些实验结果

主要指标只统计事件发布后的全部移动，包括绕行、经过已检区域和最终返航；各方法共同的事件前轨迹不重复计入。路线须通过逐格检查，确认无碰撞、无遗漏且满足移动上限。障碍遮挡而暂缓的任务不能计为已经完成。

上述均为人工生成的算法开发场景，未使用真实施工事件分布。24个中等规模状态后来又用于不同预算和实现效率诊断，多次运行不能当作新增独立地图。现阶段结论限于这些地图和单次更新后的重规划，不直接外推连续事件、真实能耗或现场收益。

'''
s=s[:start]+section+s[end:]
(ROOT/(new+'.md')).write_text(s,encoding='utf-8')
builder=(HERE/'build_report34.py').read_text(encoding='utf-8-sig').replace(old,new)
builder=builder.replace("if line=='<!-- pagebreak -->':continue", "if line=='<!-- pagebreak -->':doc.add_page_break();continue")
builder=builder.replace("str(Path(__file__).resolve().parent/'events_schematic.png')", "str(Path(__file__).resolve().parent/line.rsplit('(',1)[1].rstrip(')'))")
builder=builder.replace("if line.startswith('图1 '):", "if re.match(r'图[0-9]+ ',line):")
(HERE/'build_report35.py').write_text(builder,encoding='utf-8')
print(ROOT/(new+'.md'))
