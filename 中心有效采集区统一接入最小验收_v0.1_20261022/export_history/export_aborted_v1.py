"""Independent aborted-report export from saved evidence only."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,math,html
from PIL import Image,ImageDraw,ImageFont
from center_credit_v01_20261022.utils import HERE,ROOT,read,dump,sha,now

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

def world_figure(world,session,plan):
    c=Canvas(1500,925)
    c.text((40,24),world['id']+' '+world['label']+'：注册几何与中止状态',29)
    c.text((40,72),'浅蓝小方区为严格中心采集区；红格是环境真值，未提前传给算法。',21)
    public=world['public'];truth=world['private']['O_truth']
    for panel,method in enumerate(('PPCPP-H1','P2')):
        offset=740*panel
        def xy(p):
            return (offset+130+110*float(p[0]),590-110*float(p[1]))
        c.text((offset+40,118),method+' + 中心区信用适配',23)
        for x,y in public['F_nominal']:
            c.rect((*xy((x-.5,y+.5)),*xy((x+.5,y-.5))),'#f0f3f7')
        for x,y in truth:
            c.rect((*xy((x-.5,y+.5)),*xy((x+.5,y-.5))),'#f6b4af','#c73035',2)
        for x,y in public['P']:
            c.rect((*xy((x-.2,y+.2)),*xy((x+.2,y-.2))),'#dce9ff','#4a80c7',1)
            c.circle(xy((x,y)),4,'#42648c')
        active=world['id']=='W1' and panel==0
        if active:
            predicted=[point(p) for p in plan['full_route']]
            c.line([xy(p) for p in predicted],'#818994',2,True,False)
            c.circle(xy((0,0)),12,'#087e5a')
        else:
            c.circle(xy((0,0)),12,'#7f8da2')
        bx,by=xy((0,0));c.text((bx-7,by-13),'B',17,'#fff')
        for x in sorted({p[0] for p in public['F_nominal']}):
            px,py=xy((x,0));c.text((px-5,659),str(x),16,'#687789')
        for y in sorted({p[1] for p in public['F_nominal']}):
            px,py=xy((0,y));c.text((offset+35,py-10),str(y),16,'#687789')
        if active:
            c.text((offset+40,705),'已尝试：原生/直达返回，独立计数断言失败',21,'#ad3732')
            c.text((offset+40,747),'实际只在 B 显式采集；位移 0，发现 0',21)
            c.text((offset+40,789),'灰虚线为保存预测，全部未飞行',21)
        else:
            c.text((offset+40,705),'未运行：首槽真实异常后按稿停止',22,'#687789')
            c.text((offset+40,747),'仅展示预登记地图；无路线或采集结果',21)
    c.line([(30,840),(1470,840)],'#d8e0eb',2)
    c.text((40,861),'1米格；中心区 |x−cx|<1/5 且 |y−cy|<1/5。图示尺度不改变探测带。',21)
    c.text((40,895),'本图不是六会话闭环成功图；未执行的预测和未运行会话均明确分开。',19)
    directory=HERE/'figures';directory.mkdir(exist_ok=True)
    c.save(directory/(world['id']+'_注册与中止状态'))

def pure_figure(case):
    c=Canvas(1100,750)
    c.text((35,20),'纯案例 C13：斜段不经格心，但进入严格中心区',27)
    c.text((35,67),'这是手写纯门槛正控制；不冒充真实算法路线。',21)
    def xy(p):
        return (130+250*float(p[0]),620-250*float(p[1]))
    for x in range(3):
        for y in range(3):
            c.rect((*xy((x-.5,y+.5)),*xy((x+.5,y-.5))),'#f5f7fb')
    c.rect((*xy((.8,1.2)),*xy((1.2,.8))),'#dce9ff','#2776c5',2)
    a,b=map(point,case['records'][0]['actual'])
    c.line([xy(a),xy(b)],'#1168bd',4,arrow=True)
    ev=case['records'][0]['credits'][0]['evidence']
    w=point(ev['witness']['point'])
    c.circle(xy((1,1)),6,'#17263c')
    c.circle(xy(w),8,'#ed9822')
    c.text((730,200),'格心 (1,1)',21)
    c.text((730,245),'轨迹 y=9x/10',21)
    c.text((730,300),'交区间 (4/9, 3/5)',21)
    c.text((730,345),'见证 t=47/90',21)
    c.text((730,390),'w=(47/45,47/50)',20)
    c.text((730,450),'见证为严格内部点',20)
    c.text((730,490),'不称首次内部时刻',20)
    c.text((35,704),'黑点：格心（轨迹未经过）  橙点：内部证明点  蓝区：0.4×0.4米中心区（边界不采集）',19)
    c.save(HERE/'figures/C13_纯斜向正控制')

def main():
    assert not (HERE/'final_receipt.json').exists()
    reg=read(HERE/'registration.json');batch=read(HERE/'batch_receipt.json')
    assert batch['stopped_on_exception'] and len(batch['attempted'])==1
    session=read(HERE/'sessions/W1_H1.json');plan=read(HERE/'outputs/W1_H1_plan_1.json')
    technical=read(HERE/'technical_rounds/round_1/receipt.json')
    verify=read(HERE/'verification_runs/verify_1.json')
    replay=read(HERE/'readonly_failure_replay_v1.json')
    assert technical['passed'] and verify['passed'] and replay['reproduced_original_failure']
    assert not session['passed'] and not plan['passed']
    counts={'utc':now(),'technical_recorded':technical['counts'],'true_native_recorded':session['native_counts'],
        'true_wrapper_recorded':plan['wrapper_counts'],'true_execution_recorded':session['main_execution_counts'],
        'post_engine_recorded':plan['post']['counts'],'saved_verify_1_new_queries':verify['counts'],
        'saved_failed_auditor_replay_v1_new_queries':replay['counts'],
        'runtime_independent_original_counter_persisted':False,
        'runtime_independent_deterministically_reconstructed_counts':replay['counts'],
        'runtime_independent_reconstruction_basis':'same frozen auditor/payload executed to the same last assertion; reconstructed, not an original counter record',
        'new_core_calls':1,'new_H1_calls':1,'new_P2_calls':0,'real_post_calls':1,'true_nonzero_segments':0,
        'real_discoveries':0,'real_replans':0,'technical_cases':35,'negative_audits':2,
        'world_construction_checks':read(HERE/'technical_freeze.json')['world_construction']}
    dump(HERE/'调用与查询中止总账.json',counts)
    table=[]
    for j in reg['jobs']:
        attempted=j['id']=='W1_H1'
        table.append('|'+ '|'.join([j['id'],j['display_method'],'失败：查询计数审核断言' if attempted else '未运行',
            '1' if attempted else '0','1/0' if attempted else '—','0' if attempted else '—',
            '0/0' if attempted else '—','(0,0)' if attempted else '—'])+'|')
    imgs='\n\n'.join('!['+w['id']+'注册与中止状态]('+str((HERE/'figures'/(w['id']+'_注册与中止状态.png')).as_posix())+')' for w in reg['worlds'])
    report='''# 中心有效采集区统一接入：纯门槛通过，首个真实槽中止

本轮没有通过真实接入或闭环验收。固定合同已独立接入代码，16类35个纯案例首轮通过；首个 W1_H1 真实槽在独立查询计数断言失败，按稿立即停止后五会话，没有修复正式源码或补跑。已执行 H1 核心1次、P2 0次、直达1次；不是六会话完成。失败槽保持 passed=false。

## 中止在哪里，影响是什么

W1_H1 的原生核心正常完成并返回，直达和主管线审核/编码完成，主管线约0.104595秒，传入核心20秒上限未超。失败位于冻结 audit/_audit.py 第172行：比较观察器 post_service_intersections 与后处理自己的服务查询数。

保存的观察器是135，后处理引擎90，主管线 post_main_audit 是45，135=90+45。两者都调用同一生产中心区 intersection，且 phase 都叫 post；观察器按 phase='post' 过滤，把主管线后处理路线审核的45次也算进引擎后处理项。冻结审核器因此拒绝。这个计数作用域错误来自本次适配；不是已发现 H1 搜索失败、区域几何反例或新模型无效，但本轮真实验收仍然失败，不能改报通过。

纯阶段验证了服务谓词、执行、独立审核、导入和序列化，没有运行真实后处理，未覆盖“引擎与主管线共用服务函数”的观察器作用域。这是门槛覆盖缺口。正式开始后不修此问题；只能交负责人审核以后另立版本是否接续。

失败发生在计划等待/实飞之前：实际只有起点 collect_here，S=(0,0)、h=null、H={(0,0)}、D为空、E=100、M=0。没有非零飞行、发现、停止或重规划，实际转弯为0。保存的完整预测路线/区域见证没有进入实际账。其余五会话未运行，剩余11入口不自动使用。

|会话|对照名称|状态|真实核心|实际已采/暂缓|实际距离|非零段/转弯|实际终点|
|---|---|---|---:|---|---:|---|---|
'''+ '\n'.join(table)+'''

## 统一信用合同和适配范围

1米任务格沿用整数格心；有效采集区严格满足每轴偏移<1/5米，边与角不采集，无epsilon。已执行非零前缀与开区相交，保存区间开闭端及严格内部见证；见证不是最早内部时刻。事件前缀先截断并使用不含事件端点的参数域，结算后才更新地图；实际状态读取前均已结算。零移动仅显式 collect_here 允许采集。发布本身不加H；已完成后遮挡不删H，未完成遮挡留D。

统一接入覆盖 connector 的首连接预测、pipeline 的各条预测路线、post.engine 的输出责任证明、executor 的实际提交；独立审核采用不同的解析边参数划分。预测不改实际。保留 H1/P2 冻结原生格点核心、评分、搜索、随机规则与预算，保留 S→q、精确欧氏根式资源。单位四邻接格心核心的端点服务是该表示上的保守实现；直达仍锁定原名义格心锚点，可能冗余访问已被途中采集的任务，本轮没有加入跳过/重排优化。

这两种新适配名称不能当作旧冻结算法已原生支持区域信用。旧格心结果保留，不与本批作同模型质量/速度比较。探测带仍是闭障碍格外 L∞ 1/8，未把成像区当成传感范围。相机/高度不参与本轮实验。

## 纯门槛到底证明了什么

35个预登记案例覆盖16类，首轮全部符合手算预期，技术修复0轮，无追加案例，低于总48上限。包括8条边/角负例、不经过格心的轴向和斜向穿越、极短非空/空交集、零移动/显式动作、重复/非目标、发布不追溯、遮挡保留信用、预测隔离、进入前/内部/离开后停止、同刻安全顺序、不同分段同H同精确距离、首连接及返航信用/资源/来向。

C13 的手写斜段 (0,0)→(2,9/5) 不经过格心(1,1)，却有严格交区间 (4/9,3/5)，见证参数47/90、坐标(47/45,47/50)。这是新旧规则差异的纯正控制。C35 两次预登记负控制均被拒绝：篡改见证并重算hash链、增加未执行信用。tuple/list、整数值Fraction/非整数拒绝、序列化往返、无副作用导入、主守卫及唯一审核模块身份通过。

本轮尚无真实斜段获得不经格心的区域信用，也没有发现后真实H接续。这两项目标均未验，不用纯正控制替代。地图未按结果移动，三世界没加图或新种子。

## 查询与核验口径

纯阶段记录43个执行动作、4次纯地图发布、1次固定预测等待、1次25候选纯首连接；主探测/安全盒43/46、真值几何39，另首连接输入/候选几何1/25；主区域服务18、固定预测1、首连接预测1。独立含2个篡改拒绝审核：几何69、距离68、区域服务29、区域点测试134、边参数64、探测/安全盒45/48。真实核心/后处理/图搜索0。世界构造3次有限连通性检查单列，不冒充算法求解。

真实：核心开始/返回/完成1、后处理1；context BFS1＋A*1=2图搜索，行BFS0，内部审核2合法；首连接零接入候选1。主公开几何31、距离30、区域服务144（9预测＋45原生＋45直达路线审核＋45全路线）；主区域内部点测试36。后处理引擎 source/candidate/output 几何10/10/10、区域查询90、初始内部点9。观察器135这一项已标记混账，不作为引擎实际次数。实际执行只有起点动作1，探测/安全盒1/1、真值几何1、距离1（零长度核算）、内部点10。

运行时独立审核因异常未持久化传入Counter，不能冒称完整原始计数已记录。随后只对保存载荷调用同一冻结审核器一次，复现同一最后断言，此前的路线/责任/资源/方向断言通过；这次新增保存查询几何41、距离31、区域服务400、区域点877、边参数780。按相同确定性遍历可重建原运行时相同计数，但总账明确标记为“重建，非原始Counter记录”，不把它算成零费用或另一次真实通过；失败状态不回写。

原保存verify已通过35纯案例及首槽已执行日志/失败状态的保留，新增独立几何70、距离69、区域服务29、区域点144、边参数64、探测/安全盒46/49；失败计划被单列 retained_failure，并未被该verify当作通过管线。上述失败审核重放单独保存 readonly_failure_replay_v1.json；两个只读入口新增核心/选择器/后处理/图搜索均0。完整分类计数在调用与查询中止总账.json，保存审核会产生新几何/区域查询，不能称零计算。

## 图和交付

下图明确区分注册地图、未执行预测和实际初始点。三世界仍按预登记几何保存，未运行面板没有伪造路线。

'''+imgs+'''\n\n![C13纯斜向正控制]('''+str((HERE/'figures/C13_纯斜向正控制.png').as_posix())+''')

合同、适配diff、保留机制源码段、固定案例/预期、35纯日志、首次真实原生/后处理返回、完整预测见证、实际初始账/动作、失败栈、调用账、只读verify及失败重放、哈希/审核入口均已保存。正式实现与输入未改、旧源码及结果未改。完成中止封存后停止，交负责人审核；不追加性能批、留出、真实视觉或相机实验，不推送。
'''
    (HERE/'00_通俗中止报告.md').write_text(report,encoding='utf-8')
    for world in reg['worlds']:
        world_figure(world,session,plan)
    pure_figure(read(HERE/'technical_rounds/round_1/C13.json'))
    packet='''# 中止 review packet

先看00_通俗中止报告.md和final_receipt.json。合同与纯门槛完成，真实接入失败、真实闭环未验，勿将封存verify通过当成实验通过。

统一信用合同与上限.md、registration.json、适配源码.diff、保留机制源码段.json说明模型与修改位置。全部新实现采用center_credit_v01_20261022命名空间；源头和字节保护在source_bindings.json及external_source_guards.json。旧结果未复制为本轮结果，worlds_public/private只复用固定几何和初始物理条件，新H独立生成。

technical_freeze.json固定35案例及预期，technical_rounds/round_1保存35条纯案例、准备/源身份/序列化与计数；C13为斜向差异正控制，C35存两份篡改负控制和拒绝计数。真实前real_freeze.json冻结实现和输入，real_started.json固定六会话顺序，batch_receipt.json记录首槽失败和五未运行。

calls/W1_H1_plan_1_*为唯一真实输入及原生/直达原返回；outputs/W1_H1_plan_1.json的passed仍false，main_passed仅表示主管线已完成，失败原因为独立计数断言。sessions/W1_H1.json及logs/W1_H1_actions.jsonl仅起点collect_here，绝无飞行或发现。所有预测区域见证在输出中，不在实际H中。

首次保存verify在verification_runs/verify_1.json：失败计划保留，已执行日志与纯门槛回放通过，没有改失败状态。readonly_failure_replay_v1.py是中止后的独立报告工具，只用原冻结审核器复现同一断言；原审核器及观察器未修复，原生/后处理未重跑。运行时独立Counter未持久化这一缺口在调用与查询中止总账.json明确标记；保存复核新增查询单列。

本机保存verify命令：

    .\\运行环境\\python\\python.exe -B -X utf8 '中心有效采集区统一接入最小验收_v0.1_20261022/run_center.py' verify

后续再次verify另存收据并产生新的保存审核查询；不要重跑real、worker或已独占创建的只读失败重放。封存清单覆盖报告、四张PNG/SVG、原始返回/失败/输入和代码。root_before/root_after为根进度历史快照。export_aborted_v1.py及seal_aborted_v1.py仅报告/封存工具，不属于正式后修复；不含算法入口。

建议负责人裁决后另立版本，修正观察器服务计数作用域并增加对应无核心的组合桩门槛，再讨论剩余额度接续。本包不实施建议、不自动接续或覆盖历史。
'''
    (HERE/'review_packet.md').write_text(packet,encoding='utf-8')
    print(json.dumps({'status':'aborted_report_exported','technical_passed':35,'true_core_calls':1,'failed_sessions':1,'unrun_sessions':5,'world_figures':3,'pure_control_figures':1},ensure_ascii=False))

if __name__=='__main__':
    main()

