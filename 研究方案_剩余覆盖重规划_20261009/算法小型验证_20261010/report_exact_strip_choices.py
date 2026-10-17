from pathlib import Path
from collections import defaultdict
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
from scenarios import deserialize
from supplement_route_metrics import metrics
from audit import audit

D=Path(__file__).parent;O=D/'results/run_31_exact_strip_choices_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
rows=read(O/'results.json');summary=read(O/'summary.json');completion=read(O/'completion.json');protocol=read(O/'protocol.json')
assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in protocol['input_sha256'].items())
assert protocol['script_sha256']==hashlib.sha256((D/'exact_strip_choices.py').read_bytes()).hexdigest()
snaps={}
for p in ['run_21_micro_global_optimum','run_26_unified_new_maps']:
    for r in read(D/'results'/p/'snapshots.json'):
        raw=r.get('snapshot',r);snaps[raw['name']]=(deserialize(raw),r.get('metadata',raw.get('metadata')))
exact={r['case']:r for r in read(D/'results/run_21_micro_global_optimum/results.json') if r['algorithm']=='EXACT_GRID'}
strong={(r['case'],r['repeat'],r['variant']):r for r in read(D/'results/run_29b_p2_search_audit_20261012/runs.json') if r['batch']=='new' and r['budget']==20}
micro=[r for r in rows if r['batch']=='micro'];medium=[r for r in rows if r['batch']=='medium']
names={'fixed':'固定顺序＋固定方向','direction':'固定顺序＋方向可选','order':'顺序可选＋固定方向','joint':'顺序与方向联合选择','prefix_only':'先求巡检路程最短，再返航'}

def plot(r,a,b,pa,pb,title,path):
    s,meta=snaps[r['case']];routes=[list(map(tuple,pa)),list(map(tuple,pb))]
    bounds=set(s.targets)|set(s.covered)|set().union(*(set(z) for z in routes))|set(map(tuple,meta['obstacles']))
    x0=min(x for x,y in bounds)-1;x1=max(x for x,y in bounds)+1;y0=min(y for x,y in bounds)-1;y1=max(y for x,y in bounds)+1
    scale=min(820/(x1-x0+1),390/(y1-y0+1));top=130;bottom=int(top+(y1-y0+1)*scale)
    im=Image.new('RGB',(1800,bottom+230),'white');dr=ImageDraw.Draw(im)
    dr.text((24,15),title,font=font(26),fill='#14334b');dr.text((24,52),r['case']+f"；分条轴={r['axis']}；条带数={r['n_blocks']}",font=font(20),fill='#344054')
    for i,(label,route) in enumerate(zip([a,b],routes)):
        left=25+i*890;dr.text((left,91),label,font=font(24),fill='#14334b')
        xy=lambda p:(left+(p[0]-x0+.5)*scale,top+(y1-p[1]+.5)*scale)
        obs=set(map(tuple,meta['obstacles']));initial=set(map(tuple,meta['initial_targets']))
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                p=(x,y);cx,cy=xy(p);color='#f3f4f6' if p in s.free else '#b6bbc1'
                if p in s.targets:color='#d6e8f7' if p in initial else '#c8efd3'
                if p in s.targets&s.covered:color='#c4c8cf'
                if p in obs:color='#26313c'
                dr.rectangle((cx-scale/2,cy-scale/2,cx+scale/2,cy+scale/2),fill=color,outline='#e2e5e9')
        m=metrics(route,s.targets,s.covered);seen=set(s.covered)|{s.current}
        for j,(u,v) in enumerate(zip(route,route[1:]),1):
            col='#374151' if j>m['completion_step'] else '#9947ad' if v not in s.targets else '#df7925' if v in seen else '#2675c9'
            dr.line((xy(u),xy(v)),fill=col,width=4);seen.add(v)
        for p,label2 in [(s.current,'S'),(s.base,'B')]:
            cx,cy=xy(p);dr.ellipse((cx-10,cy-10,cx+10,cy+10),fill='#d9364c' if label2=='S' else '#111827');dr.text((cx-6,cy-9),label2,font=font(15),fill='white')
        for k,t in enumerate([f"总步数 {m['length']}；完成巡检前 {m['completion_step']}；返航尾段 {m['return_tail_steps']}",f"历史重复 {m['historical_target_steps']}；本轮重复 {m['repeated_new_target_steps']}；非目标移动 {m['non_target_steps']}"]):dr.text((left,bottom+20+34*k),t,font=font(21),fill='#344054')
    dr.text((25,bottom+110),'底色：蓝＝旧待检；绿＝新增；灰＝已检；黑＝障碍。S＝当前位置；B＝基地。',font=font(21),fill='#344054')
    dr.text((25,bottom+145),'线：蓝＝首次覆盖；橙＝重复目标；紫＝非目标移动；深灰＝完成后的返航。同边重走可能相互覆盖。',font=font(21),fill='#344054')
    im.save(path)

selected=[]
configs=[(max(medium,key=lambda r:(r['outputs']['order']['length']-r['outputs']['joint']['length'],r['case'])),'order','joint','方向自由度：在已允许重排的基础上比较'),
         (max(micro,key=lambda r:(r['outputs']['prefix_only']['length']-r['outputs']['joint']['length'],r['case'],r['axis'])),'prefix_only','joint','返航联合考虑：微型状态中的最大差异'),
         (max(micro,key=lambda r:(r['outputs']['joint']['length']-r['outputs']['joint']['grid_optimum'],r['case'],r['axis'])),'joint','grid','固定条带约束仍可能损失路线质量')]
for i,(r,a,b,title) in enumerate(configs,1):
    ra=r['outputs'][a]['route'];rb=exact[r['case']]['route'] if b=='grid' else r['outputs'][b]['route']
    assert audit(snaps[r['case']][0],tuple(map(tuple,ra)))['valid'];assert audit(snaps[r['case']][0],tuple(map(tuple,rb)))['valid']
    plot(r,names[a],'格级全覆盖精确最优' if b=='grid' else names[b],ra,rb,title,O/f'example_{i}.png')
    selected.append(dict(case=r['case'],axis=r['axis'],title=title,a=a,b=b,length_a=len(ra)-1,length_b=len(rb)-1,image=f'example_{i}.png'))
bycase=defaultdict(list)
for r in micro:bycase[r['case']].append(r)
micro_deltas=[min(r['outputs']['joint']['length'] for r in rs)-rs[0]['outputs']['joint']['grid_optimum'] for rs in bycase.values()]
comparisons=[]
for v in ['multi','TREE']:
    ds=[r['outputs']['joint']['length']-strong[r['case'],rep,v]['independent_audit']['length'] for r in medium for rep in [0,1]]
    comparisons.append(dict(method=v,win_tie_loss=[sum(d<0 for d in ds),sum(d==0 for d in ds),sum(d>0 for d in ds)],delta=sum(ds)))
(O/'strong_comparisons.json').write_text(json.dumps(comparisons,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'selected.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 固定条带的顺序、方向与返航联合选择验证（2026-10-12）','',
'## 结论先说','',
'**方向与访问顺序需要配合选择，但这项常规机制尚未超过现有强基线，不能据此确立论文创新。**','',
'- 微型状态中，返航联合优化有时能省路；中等规模纳入的16个状态中，未发现额外收益。','- 固定条带完整执行，即使顺序和方向都求到精确最优，也可能比允许自由逐格覆盖的路线更长。','- 因此不建议现在把“给条带加方向和返航优化”定成论文主算法。','',
'## 这次到底改变什么','',
'每个状态先冻结当前位置、已检进度、合法地图、可检目标与基地。把剩余目标按行或列切成最大的连续直条带；障碍、已检格和边界会将条带断开。重规划起点若是待检格，视为已当场完成，不重复生成任务。','',
'比较如下五种设置。入口出口只能取每条直条带的两个端点；改变方向就是交换这两个端点。','',
'|设置|条带访问顺序|每条条带方向|选择路线时的目标|','|---|---|---|---|',
'|fixed|按行/列坐标固定|按条带编号交替正反|出发＋全部条带＋返航|',
'|direction|固定|可选|同上|','|order|可选|固定|同上|','|joint|可选|可选|同上|',
'|prefix_only|可选|可选|先最小化出发＋全部条带，再接返航|','',
'prefix_only若巡检阶段成本相同，选择返航最短的一条，避免用不利的平局规则人为制造差距。所有输出最终都返航。','',
'采用子集动态规划精确求解：状态记录已执行哪些条带、最后一条是哪条以及执行方向。连接使用当前地图上的最短路。条带完整执行一次，即使连接途中已经覆盖其中一些格子，也不缩短后续服务；不会调用跳过已检格的解码器。','',
'优化目标中的巡检阶段是“完成全部规定条带服务之前的路程”，可能晚于最后一个目标首次被覆盖。图中“完成巡检前”则按最后一个未检目标首次被覆盖统计，与之前的路线指标保持一致。二者不能混称；prefix_only并不是原始自由覆盖问题的最早完成策略。','',
'**这里的精确最优只属于上述固定条带模型，不是全局栅格覆盖最优。** 放宽方向/顺序约束后最优值不增是数学上的必然；实验的意义是测量严格改善有多大，而不是证明这一常识。','',
'## 数据与核验','',
f"共{completion['partitions']}组固定划分、{completion['routes']}条路线，全部通过独立移动、碰撞、可检覆盖及返航核验；其中{completion['brute_checks']}次求解另用排列与方向穷举核对最优目标值。穷举与动态规划独立实现优化过程，但共享几何距离接口，不夸大为完全独立的全栈实现。",'',
'- 微型：已有48个状态，每个分别横向、纵向切条，产生96组划分；同一状态的两种划分不是两张独立地图。另与已保存且审计通过的格级精确最优值比较。','- 中等规模：已有24个状态按横向切条，事先设上限12条；16个符合条件、8个排除。被排除的全部是拐角扩展＋障碍，因此本轮中等规模结论仅适用于直线扩展和纯障碍。','- 所有数据均为参与过分析的开发地图。本轮不是新地图泛化检验，不是同预算速度比较，不对真实电量作推断。','',
'## 顺序与方向的作用','',
'|数据组/固定划分数|固定顺序固定方向|只放开方向|只放开顺序|顺序方向联合|只优化巡检后返航|','|---|---:|---:|---:|---:|---:|']
for g in summary:lines.append(f"|{g['batch']} / {g['n']}|"+'|'.join(str(g['totals'][k]) for k in ['fixed','direction','order','joint','prefix_only'])+'|')
lines+=['','这些是各设置的总步数。固定设置是机制对照，刻意限制了自由度，不能把相对它的大幅改善宣传为战胜先进方法。','',
'|数据组|在允许顺序优化后，再允许方向选择：改善/相同/变差|节省总步数|将返航联合考虑：改善/相同/变差|节省总步数|','|---|---|---:|---|---:|']
for g in summary:
    q=next(p for p in g['pairs'] if p['candidate']=='joint' and p['reference']=='order');t=next(p for p in g['pairs'] if p['reference']=='prefix_only')
    lines.append(f"|{g['batch']}|"+'/'.join(map(str,q['win_tie_loss']))+f"|{-q['delta']}|"+'/'.join(map(str,t['win_tie_loss']))+f"|{-t['delta']}|")
lines+=['','## 与现有强基线相比','',
'中等规模16状态分别配对原20秒结果的两次重复，共32对；这不代表32个独立状态。条带模型在自己的约束下已求精确最优，强基线是可自由逐格覆盖的启发式，所以这里只比较最终合法路线质量，不作速度或优化器公平性的主张。','',
'|固定条带联合最优相对谁|更短/相同/更长|总步数差：条带减对方|','|---|---|---:|']
for c in comparisons:lines.append('|'+{'multi':'增强P2','TREE':'MST＋2-opt'}[c['method']]+'|'+'/'.join(map(str,c['win_tie_loss']))+f"|{c['delta']}|")
lines+=['',f"微型48状态中，事后取横纵两种划分的较短联合最优路线，有{sum(d==0 for d in micro_deltas)}状态达到格级精确最优，剩余{sum(d>0 for d in micro_deltas)}状态合计仍多{sum(micro_deltas)}步。该事后最小值是结构能力诊断，不是有免费计算的最终算法。此前P2在这48状态均达到格级最优。",'',
'## 三个代表例子','',
'代表例按对应成本差最大选择，只用于展示机制，不用于估计普遍收益。']
for i,item in enumerate(selected,1):
    lines+=['',f"### 例{i}：{item['title']}",'',f"左图 {item['length_a']} 步，右图 {item['length_b']} 步。",'',f"![例{i}]({(O/item['image']).as_posix()})"]
lines+=['','## 研究取舍','',
'本轮证据支持把访问顺序与方向联合选择作为算法需要具备的基本能力；不支持以此单独立项为创新，也不支持预定返航联合优化一定带来额外收益。','',
'更值得继续检验的缺口是条带表示本身的限制：允许条带在合适位置拆开或重新组合，能否减少固定完整执行造成的额外往返，尤其是本轮尚未覆盖的中等规模拐角扩展。该思路与OARP-Replan已有内容相近，必须与既有机制区分，不能仅换名称。','',
'建议下一轮只做一个明确的候选：在事件附近允许局部拆分、在未受影响处保留连续覆盖块，使用共同的排序和方向求解器；与不拆分及全部拆分作对照，并同时保留增强P2与MST。先检验路线质量与计算代价的取舍，再决定是否有足够的新机制继续。当前尚未实施这一候选，不承诺优势。','',
'此前第22、23份报告已经研究过解除旧路径段约束及途中覆盖后的跳过服务，不能把这些已有试验再当作新发现。下一轮若继续，应先逐项对照那些实现，明确新增的是事件附近的划分变化及计算开销控制；若只是重复原有机制，就不应再跑一轮相同实验。','',
'原始输入哈希、预先落盘协议、排除列表、完整路线及核验结果均保存在本轮结果目录；代码不修改历史实验数据。']
report=B/'41_固定条带顺序方向与返航联合选择验证_20261012.md';report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(comparisons=comparisons,micro_best_gap=sum(micro_deltas),examples=selected,report=str(report)),ensure_ascii=False,indent=2))
