"""Independent aborted-report export from saved evidence only."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,math,html
from PIL import Image,ImageDraw,ImageFont
from center_credit_v03_20261022.utils import HERE,ROOT,read,dump,sha,now

FONT='C:/Windows/Fonts/msyh.ttc'
def fnt(size):
    return ImageFont.truetype(FONT,size)
def value(r):
    return Fraction(r['n'],r['d'])
def point(raw):
    return tuple(value(v) for v in raw)
def ptext(raw):
    return '('+', '.join(str(v) for v in point(raw))+')'
def exact_text(expr):
    terms=[]
    for row in expr['terms']:
        c=value(row['c']);r=row['r']
        terms.append(str(c) if r==1 else ('' if c==1 else str(c)+'·')+'√'+str(r))
    return ' + '.join(terms) or '0'
def approx(expr):
    return sum(float(value(t['c']))*math.sqrt(t['r']) for t in expr['terms'])
def sumc(rows):
    c=Counter()
    for row in rows:
        c.update(row)
    return c

class Canvas:
    def __init__(self,w,h):
        self.image=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.image)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(self,xy,text,size=20,fill='#17263c'):
        self.d.text(xy,text,font=fnt(size),fill=fill)
        self.svg.append(f'<text x="{xy[0]}" y="{xy[1]+size}" fill="{fill}" font-family="Microsoft YaHei,sans-serif" font-size="{size}">{html.escape(text)}</text>')
    def line(self,pts,fill,width=3,dash=False,arrow=False):
        pts=[(float(x),float(y)) for x,y in pts]
        if dash:
            for a,b in zip(pts,pts[1:]):
                length=math.dist(a,b)
                for j in range(0,int(length),12):
                    self.d.line([tuple(a[k]+(b[k]-a[k])*t/max(length,1) for k in (0,1)) for t in (j,min(j+6,length))],fill=fill,width=width)
        else:
            self.d.line(pts,fill=fill,width=width)
        dashed=' stroke-dasharray="6 6"' if dash else ''
        self.svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{fill}" stroke-width="{width}"{dashed}/>')
        if arrow and len(pts)==2:
            a,b=pts;dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length>15:
                mid=((a[0]+b[0])/2,(a[1]+b[1])/2);u=(dx/length,dy/length)
                wings=[(mid[0]-8*u[0]+4*u[1],mid[1]-8*u[1]-4*u[0]),mid,
                       (mid[0]-8*u[0]-4*u[1],mid[1]-8*u[1]+4*u[0])]
                self.line(wings,fill,width=2)
    def rect(self,box,fill,outline='#b7c2d0',width=1,dash=False):
        if dash:
            x0,y0,x1,y1=box
            self.line([(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)],outline,width,True)
        else:
            self.d.rectangle(box,fill=fill,outline=outline,width=width)
            self.svg.append(f'<rect x="{box[0]}" y="{box[1]}" width="{box[2]-box[0]}" height="{box[3]-box[1]}" fill="{fill or "none"}" stroke="{outline}" stroke-width="{width}"/>')
    def circle(self,xy,r,fill,outline='#fff',width=1):
        x,y=xy;self.d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=outline,width=width)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')
    def save(self,path):
        self.image.save(path.with_suffix('.png'))
        path.with_suffix('.svg').write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')

def figure(world,sessions):
    c=Canvas(1500,930)
    c.text((35,20),world['id']+' '+world['label']+'：中心区与实际接续状态',28)
    c.text((35,68),'红格是评估真值；蓝色小方区是严格中心区。只画实飞段，未执行计划不计路程。',20)
    for panel,method in enumerate(('H1','P2')):
        offset=740*panel
        def xy(p):return offset+130+110*float(p[0]),590-110*float(p[1])
        c.text((offset+35,114),('PPCPP-H1' if method=='H1' else 'P2')+' + 中心区信用适配',23)
        public=world['public']
        for x,y in public['F_nominal']:c.rect((*xy((x-.5,y+.5)),*xy((x+.5,y-.5))),'#f0f3f7')
        for x,y in world['private']['O_truth']:c.rect((*xy((x-.5,y+.5)),*xy((x+.5,y-.5))),'#f6b4af','#c73035',2)
        for x,y in public['P']:
            c.rect((*xy((x-.2,y+.2)),*xy((x+.2,y-.2))),'#dce9ff','#4a80c7',1)
        s=next((s for s in sessions if s['job']['world']==world['id'] and s['job']['method']==method),None)
        found=False
        if s:
            for row in s['records']:
                if row['kind']=='move' and 'actual' in row:
                    a,b=map(point,row['actual'])
                    if a!=b:c.line([xy(a),xy(b)],'#087f6b' if found else '#1769bb',4,arrow=True)
                    if row['status']=='detected':
                        found=True;c.circle(xy(b),8,'#eea128','#a85c00',2)
            for p in s['final']['H']:c.circle(xy(p),5,'#087e5a')
        c.circle(xy((0,0)),12,'#14263e');bx,by=xy((0,0));c.text((bx-7,by-13),'B',17,'#fff')
        for x in sorted({p[0] for p in public['F_nominal']}):
            px,py=xy((x,0));c.text((px-5,659),str(x),16,'#687789')
        if s:
            c.text((offset+35,703),'完成返航' if s['passed'] else '审核失败停止；仍在停止点，未返航',21,'#087e5a' if s['passed'] else '#b53232')
            c.text((offset+35,746),'已采 '+str(len(s['final']['H']))+' / 暂缓 '+str(len(s['final']['D']))+'；实际 S='+ptext(s['final']['S']),20)
            c.text((offset+35,788),'实际距离 '+f'{approx(s["final"]["M"]["exact"]):.6f}',20)
        else:c.text((offset+35,703),'未运行：新真实异常后按稿停止',22,'#687789')
    c.line([(30,840),(1470,840)],'#d8e0eb',2)
    c.text((35,858),'蓝：发现前实飞；绿：发现后实飞；橙点：发现停止点；B：基地；绿点：实际有效信用。',20)
    c.text((35,896),'两份旧失败返回仍保留；W1_H1首计划及W2_P2第二计划保存复用，非v0.3新增核心。',19)
    (HERE/'figures').mkdir(exist_ok=True);c.save(HERE/'figures'/(world['id']+'_接续实际状态'))

def main(seal=False):
    assert not (HERE/'final_receipt.json').exists()
    reg=read(HERE/'registration.json');verify=read(HERE/'verification_runs/verify_1.json')
    assert verify['passed'] and len(verify['checks'])==6
    sessions=[read(row['source']) for row in verify['checks']]
    assert all(s['passed'] and s['completed'] for s in sessions)
    new=[read(HERE/'sessions'/(j['id']+'.json')) for j in read(HERE/'batch_receipt.json')['attempted']]
    plans=[read(HERE/row['file']) for s in new for row in s['plans'] if not row.get('provenance')]
    native=sumc(s['native_counts'] for s in new);wrapper=sumc(p['wrapper_counts'] for p in plans)
    independent=sumc(p['independent_counts_actual_even_on_exception'] for p in plans)
    execution=sumc(s['main_execution_counts'] for s in new)
    pre=read(HERE/'precheck.json');reuse=read(HERE/'reuse_receipt.json')
    rows=[];turns={};timing=[]
    for source,s in zip(verify['checks'],sessions):
        vectors=[]
        for row in s['records']:
            if row['kind']=='move' and 'actual' in row:
                a,b=map(point,row['actual'])
                if a!=b:vectors.append((b[0]-a[0],b[1]-a[1]))
        t=sum(a[0]*b[1]!=a[1]*b[0] or a[0]*b[0]+a[1]*b[1]<0 for a,b in zip(vectors,vectors[1:]))
        ident=s['job']['id'];turns[ident]={'nonzero_direction_changes':t,'direction_pair_tests':max(0,len(vectors)-1)}
        original=Path(source['source']).parent.parent
        for row in s['plans']:
            f=original/row['file'];p=read(f)
            timing.append({'plan':row['id'],'source':str(f),'source_sha256':sha(f),'timing':p['timing'],
                           'provenance':row.get('provenance','original_saved_or_new_by_source_path')})
        newcore=0 if ident.startswith('W1') else next(n['native_counts'].get('core_started',0) for n in new if n['job']['id']==ident)
        rows.append('|'+ '|'.join([ident,'完成返航',str(newcore),str(len(s['final']['H']))+'/'+str(len(s['final']['D'])),
            exact_text(s['final']['M']['exact'])+f' ≈ {approx(s["final"]["M"]["exact"]):.6f}',str(t),ptext(s['final']['S'])])+'|')
    offcenter=sum(len(row['execution']['diagonal_offcenter_credits']) for row in verify['checks'])
    detections=sum(len(row['execution']['detections']) for row in verify['checks'])
    diagonal=sum(row['execution']['interior_diagonal_detections'] for row in verify['checks'])
    accounts={'v01':{'core':1,'post':1,'graph_search':2,'source':'v0.1 preserved failure; independent Counter missing stays missing'},
        'v02':{'core':5,'post':5,'graph_search':90,'source':str(ROOT/'中心有效采集区统一接入最小验收_v0.2_20261022/三栏调用与查询账.json')},
        'v03_native_actual':dict(native),'v03_wrapper_actual':dict(wrapper),'v03_independent_actual':dict(independent),
        'v03_execution_actual_excludes_old_prefix':dict(execution),'eight_prechecks':pre['tests'],
        'saved_W2_return_reaudit':reuse,'saved_final_verify_new_queries':verify['counts'],'cross_version_core_calls':12,
        'turns_saved_diagnostic':turns,'planning_timing_by_source_no_pooled_comparison':timing,
        'old_completed_W1_sessions_reused_without_execution':2,'newly_executed_continuation_sessions':4,
        'actual_diagonal_offcenter_credit_cases':offcenter,'actual_detections':detections,'diagonal_detection_cases':diagonal}
    dump(HERE/'三栏与跨版本查询总账.json',accounts)
    report='''# 中心区零查询契约与最终接续结果

跨版本完整六会话均完成当前可检任务并实际返航，保存独立回放通过。本轮 v0.3 新增真实核心6次（H1 4、P2 2），连同 v0.1 的1次、v0.2的5次，跨版本共12次，到原上限即停。没有重跑W1两会话，也没有重跑W2_P2第二次规划；旧失败状态和原始返回保持原样。

**仍有一项未验：实际“不经过目标格心的斜段区域采集”没有发生。** 两次真实斜段内障碍停止不等于这类采集，不能以纯斜向正控制或偏离格心的证明点替代。按稿不补地图、不追加调用。

## 三栏来源及六会话

|来源|保留或新增结果|调用口径|
|---|---|---|
|旧失败保留|v0.1首槽混计断言失败；v0.2的W2_P2第二返回缺键失败均保持failed|旧核心1+5，直达1+5，均不重跑|
|旧返回独立复核复用|W1_H1首计划在v0.2复用；W2_P2第二计划本版复核通过，标reused_saved_reaudited|本版复核核心/选择器/后处理/图搜索0；旧省略零字段及生命周期仅派生兼容，不冒充原trace|
|本版新实际执行|W2_P2从原停止点执行保存计划返航；随后完成W2_H1/W3_H1/W3_P2|W2_P2新增核心0，后三各2，本版6，跨版本12|

|会话|最终状态|v0.3新核心|实际已采/暂缓|实际总长度（米）|非零方向转弯数|实际终点|
|---|---|---:|---|---|---:|---|
'''+ '\n'.join(rows)+'''

W1各服务9格、障碍遮挡1格暂缓；W2各服务5格、暂缓0；W3各服务4格、遮挡1格暂缓。发布责任P没有删除，遮挡未完成格不记H，已完成信用不因后续发布删除。所有会话当前可检任务完成且实际S在基地，E非负。不同工作量分列，不平均排名；原保存计时和本版计时逐入口保存，不拼成同轮性能配对。

## 计数契约和兼容证据

计数契约.json逐项说明生产者、序列化与消费者。观察器初始化即写出shared总数、五个scope、引擎服务数、旧post总体保护数及started/finished/aborted字段，含零。审核要求字段完整、严格非负整数（bool拒绝）、未知scope拒绝、分类守恒、引擎精确相等、旧总体保护项相等并≤1200。未启动或异常退出不能当作正常零查询。没有把任意缺键统一get(0)，原相等断言与预算保护保留。

W2_P2第二份原返回main_complete，原核心开始/返回/完成和post_entry均1；真实停点(2,21/8)、原h=(0,-3/8)、已采5、D空、M=59/8、E=741/8，输入与当前实际状态一致。进入预测前后均无未采可检责任，后处理自己明确记录service_intersections=0；完整路线、资源、区域见证和来向复核通过，故仅对该旧Counter省略的必需查询键派生补0。legacy生命周期根据正常完整主管线证据另行派生，列明字段/证据/来源hash，未声称是旧运行时观测。原v0.1异常计数缺失继续披露，未用新schema覆盖。

恢复W2_P2原初态及已经执行的日志hash链，再恢复末端S/h/H/known/E/M；只追加保存第二计划的等待与实际后缀。旧飞行段、信用和距离不重复提交。W1两完成会话直接引用v0.2证据，只做保存审核，不再执行或求解。旧计数兼容仅作用于派生副本，不写回旧文件。

## 八项预检与真实判断

8个预登记案例首轮全通过，准备技术修复0轮：全零、单scope、多scope、空任务返航、零长度、序列化、异常/未启用/未知scope拒绝、缺键/不守恒/非法类型和值拒绝。7项预期负拒绝均成立。固定桩使用真实engine.credits、pipeline.main_audit和schema.validate，核心/后处理搜索/图搜索0；主几何3、距离3、服务5（引擎4、主管线1），无重做旧35纯案例或旧6组合测试。

逐项结论：

- 全部可检任务完成且实际返航：六会话均通过。
- 真实不经格心的斜段区域采集：0例，未验；虽然存在斜段停止，但本批取得新信用的实际段仍经过对应格心。
- 发现后真实历史接续：六会话均有一次发现及接续；其中W2_P2跨版本原停止点恢复后实际返航，非新规划。
- 资源与预测隔离：主/独立审核及保存回放一致；只实际执行前缀产生H/E/M/h，等待不移动，未执行预测不计信用或路程，没有碰障/漏检/距离或信用不一致的保存证据。

这些判断仅针对六个固定微型技术会话，不是普遍安全、性能、创新、一般无理停点或实际视觉识别的证明。中心区仍是每轴严格偏移<1/5米；探测仍为闭障碍格外L∞ 1/8，算法只得当前公开地图。核心、奖励、搜索、后处理路线选择、区域谓词、地图、seed和预算字节/机制保留，未新增跳过目标或中心区入口优化。

## 调用和审核费用

本版新核心开始/返回/完成6、新直达6，H1 4/P2 2。图搜索41=context BFS6＋距离行BFS12＋A*23，均完成；内部审核58合法、distance662/path159。跨版本图搜索2+90+41=133、内部审核2+102+58=162。跨版本12个核心调用包含两份旧failed返回复核复用，不能称本版新增12，也不能删去旧失败尝试。

本版主管线主几何165/距离159/区域服务166；直达source/candidate/output65/47/26、区域服务74。总共享区域查询240=引擎74＋预测14＋原生审核80＋主管线post35＋全路线37；旧post总体保护项109=74+35。六次观察器started/finished=6、aborted=0，包括零查询正常路径的完整schema。新计划独立审核几何191/距离165/区域704、点1849/边参数1606，均实际finally落盘；新实际执行动作38、等待7，探测/安全盒17/38、真值几何38/距离38、区域34。旧前缀费用不再计为新执行。

W2保存返回复核新增独立几何29/距离26/区域75、点213/边170，核心/选择器/后处理/搜索0。最终保存verify新增独立几何482/距离415/区域2633、点6594/边5522、探测/安全盒38/75；复核12份完整计划和六条实际历史，新核心/选择器/后处理/搜索0。全执行链共75条动作=57非零段+18显式零移动采集，12条等待；实际欧氏长度只来自实飞，未将中断计划累加。

旧v0.1/v0.2费用及未落盘计数缺口仍在各版原收据，本版三栏与跨版本查询总账.json按来源保存，不用保存复核冒充运行时trace。保存verify新增几何有费用，不称零计算。完整输出包含计数schema、diff、预检、兼容字段证据、真实请求/返回、独立计数、旧证据指针、实飞/中心区图及hash。

## 六会话实际路线图

'''+ '\n\n'.join('!['+w['id']+'中心区实飞]('+str((HERE/'figures'/(w['id']+'_接续实际状态.png')).as_posix())+')' for w in reg['worlds'])+'''

完成本轮既定接续并达到跨版本12入口后封存停止，根进度更新，交负责人审核。未运行额外验证批、改图、留出、性能批、相机/视觉实验或推送。
'''
    (HERE/'00_通俗最终接续报告.md').write_text(report,encoding='utf-8')
    for w in reg['worlds']:figure(w,sessions)
    packet='''# v0.3 最终接续 review packet

先读00_通俗最终接续报告.md、三栏与跨版本查询总账.json及final_receipt.json。跨版本六会话完成返航，但真实不经格心斜段信用0例未验，不能泛称所有覆盖目标均通过。

计数契约.json、schema修复.diff和changes.json列明修改范围。schema.py对新观测要求完整零schema/严格类型/守恒/原1200保护/已启用且正常完成；旧兼容层逐字段证据补齐，不任意缺失默认0。precheck_registration.json/precheck.json为八项首轮预检，旧测试仅核来源/适用范围不重跑。real_freeze.json证明真实开始后实现不变。

reuse_receipt.json、reuse_audit_actual_counts.json、outputs/W2_P2_plan_2.json保留兼容新增字段、原native_counts、来源sha及完整独立复核。原v0.2返回和会话仍failed。resume_seed/resume_plan_rows恢复旧日志链，首份计划引用绝对旧路径，第二份保存复用；没有重跑或复飞旧段。

W1两完成会话仍在v0.2目录；本版sessions含W2_P2续飞及后三新会话，旧来源通过verification_runs检查表source绝对指针完整引用。calls/outputs有6次新核心及直达原返回，原timing逐入口保留不混作同轮性能。失败来源与新实际执行三栏在报告和总账分开。每份新计划finally计数真实落盘，旧异常缺口不覆盖。

只读保存核验：

    .\\运行环境\\python\\python.exe -B -X utf8 '中心有效采集区统一接入最小验收_v0.3_20261022/run_center.py' verify

每次新增verification_runs收据及保存几何/区域查询，禁止核心/选择器/后处理/图搜索。manifest绑定封存文件；root_before/root_after是历史快照，不要求实时根文档永远不变。export_final_v03只读保存证据做文图和结构封存，不修运行时或重新求解。完成后停止，无自动追加批。
'''
    (HERE/'review_packet.md').write_text(packet,encoding='utf-8')
    print({'exported':True,'complete_sessions':6,'new_core_calls':6,'cross_version_core_calls':12,'actual_diagonal_offcenter_credit':offcenter})
    if not seal:return
    for name,digest in read(HERE/'real_freeze.json')['files'].items():assert sha(HERE/name)==digest
    for name,digest in read(HERE/'external_source_guards.json').items():assert sha(name)==digest
    root=ROOT/'当前进度与下一步.md';before=root.read_bytes();assert before==(HERE/'root_before.md').read_bytes()
    header='''# 最新完成：中心区v0.3六会话返航，斜段不经格心信用仍未验（2026-10-22）

中心有效采集区统一接入最小验收_v0.3_20261022 已完成最终有限接续并封存，见00_通俗最终接续报告.md、review_packet.md、final_receipt.json。本版只补计数完整零schema、必要兼容审核和接续；区域谓词/核心/评分/搜索/后处理路线/事件/地图/seed/预算不变。八项预检首轮通过（7项预期拒绝），核心/后处理搜索0；旧35纯/6组合只核来源，不重跑。

W2_P2第二保存返回完整复核通过，只有空责任等证据证明的旧Counter省略查询零字段才在派生兼容层补0，生命周期也明确为派生而非旧trace；新审核强制完整字段/严格非负整数/正常启用完成/守恒/引擎相等/原1200总体保护。旧两份失败和v0.1异常计数缺口原样保留。

W1两完成会话不重跑；W2_P2恢复原(2,21/8)、H5/D0/M59/8和日志链，用旧第二计划实际返航，新增核心0。随后W2_H1/W3_H1/W3_P2各2入口，本版新增核心6=H1 4/P2 2，新直达6；跨版本1+5+6=12，达到上限即停。六会话均完成可检任务并实际返航，旧前缀/信用/距离不重复提交。W1各H9/D1/L51/4，W2各H5/D0/L43/4+√10，W3各H4/D1，H1约16.025437/P2约14.025437，不作性能排名。

单独边界：六次发现后实际历史接续通过；两次为斜段内探测停止，但真实“不经格心斜段区域采集”0例，仍未验，不拿纯桩/偏离格心证明点替代、不改图追触发。实际资源、预测隔离及信用/距离回放一致，无碰障/漏检不一致保存证据，范围仅六技术世界会话，不代表创新或真实视觉/安全。

本版图搜索41=context BFS6+行BFS12+A*23，内部审核58合法；跨版本图搜索133/内部审核162。共享服务240=引擎74+预测14+原生80+主管线post35+全路线37，原post总体保护109；新独立计划几何191/距离165/区域704，实际finally落盘。W2保存复核新增几何29/距离26/区域75；最终verify通过12计划/6历史，新增独立几何482/距离415/区域2633、点6594/边5522、盒113，核心/选择器/后处理/搜索0。完整来源三栏、查询/转弯/计时、实飞图、schema/diff/哈希已存。完成即停止交审，无额外验证、留出、性能批或推送。

---
'''
    root.write_text(header+'\n'+before.decode('utf-8-sig'),encoding='utf-8');(HERE/'root_after.md').write_bytes(root.read_bytes())
    manifest={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and not p.is_relative_to(HERE/'verification_runs') and p.name not in ('manifest.json','final_receipt.json')}
    dump(HERE/'manifest.json',{'files':manifest})
    receipt={'status':'FINITE_CENTER_CREDIT_CONTINUATION_COMPLETED_VERIFIED_SEALED_STOP','artifact_integrity_verified':True,
        'completed_sessions_cross_version':6,'new_core_calls':6,'cross_version_core_calls':12,'new_H1':4,'new_P2':2,
        'old_failures_unchanged':True,'W1_completed_sessions_rerun':0,'W2_second_plan_new_core_calls':0,
        'eight_prechecks_passed':True,'technical_repairs':0,'real_new_failures':0,'all_serviceable_targets_and_return':True,
        'actual_diagonal_offcenter_credit_verified':False,'actual_diagonal_offcenter_credit_cases':offcenter,
        'history_continuation_verified':True,'resource_prediction_isolation_verified':True,
        'saved_verify_passed':True,'saved_verify_counts':verify['counts'],'first_verify_file':'verification_runs/verify_1.json',
        'first_verify_sha256':sha(HERE/'verification_runs/verify_1.json'),'manifest_sha256':sha(HERE/'manifest.json'),
        'runtime_frozen_files_unchanged':len(read(HERE/'real_freeze.json')['files']),'sealed_files':len(manifest),
        'stopped_for_owner_review':True,'no_extra_validation_batches':True,'seal_new_algorithm_calls':0}
    dump(HERE/'final_receipt.json',receipt)
    for name,digest in manifest.items():assert sha(HERE/name)==digest
    print({'sealed':True,'files':len(manifest),'runtime_unchanged':True})

if __name__=='__main__':
    import sys
    main('--seal' in sys.argv)

