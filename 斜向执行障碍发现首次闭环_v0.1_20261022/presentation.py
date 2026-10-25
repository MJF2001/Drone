"""Saved evidence -> reports/route figures. Presentation only, no query algorithms."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,math,html
from PIL import Image,ImageDraw,ImageFont
from loop_utils import HERE,ROOT,read,dump,sha,now

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
    canvas=Canvas(1500,920)
    canvas.text((40,22),world['id']+' '+world['label']+'：实际轨迹与中断余段',29)
    canvas.text((40,69),'评估图显示隐藏真值；规划时只知道公开名义边界和当时已发现障碍。',21)
    for panel,method in enumerate(('H1','P2')):
        s=next(x for x in sessions if x['job']['method']==method)
        public=s['public_initial'];truth=read(HERE/s['private_truth_file'])['O_truth'];final=s['final']
        offset=panel*740;scale=110
        def screen(p):
            return (offset+130+float(p[0])*scale,590-float(p[1])*scale)
        canvas.text((offset+45,113),method+' + 首连接 + 直达',24)
        for x,y in public['F_nominal']:
            x0,y0=screen((x-.5,y+.5));x1,y1=screen((x+.5,y-.5))
            canvas.rect((x0,y0,x1,y1),'#edf2f7')
        for x,y in truth:
            a=screen((x-.5,y+.5));b=screen((x+.5,y-.5))
            canvas.rect((*a,*b),'#f6b4af','#c73035',2)
            a=screen((x-.625,y+.625));b=screen((x+.625,y-.625))
            canvas.rect((*a,*b),None,'#cc6262',2,True)
        for p in public['P']:
            blocked=p in truth
            canvas.circle(screen(p),8,'#bd3435' if blocked else '#fff','#8b2337' if blocked else '#738499',2)
        found=False;gamma=True;segment=0
        for record in s['records']:
            if record['kind']!='move' or 'actual' not in record:
                continue
            a,b=map(point,record['actual'])
            if a==b:
                continue
            segment+=1
            color='#1168bd' if not found else ('#864cc2' if gamma else '#07816c')
            canvas.line([screen(a),screen(b)],color,4,arrow=True)
            if found:
                gamma=False
            if record['status']=='detected':
                proposed=point(record['proposed'][1])
                canvas.line([screen(b),screen(proposed)],'#8c959f',2,True)
                found=True
        for p in final['H']:
            canvas.circle(screen(p),5,'#087e5a')
        canvas.circle(screen(public['base']),13,'#14263e')
        bx,by=screen(public['base']);canvas.text((bx-8,by-13),'B',17,'#fff')
        for d in s['independent_execution']['detections']:
            xy=screen(point(d['S']));canvas.circle(xy,9,'#f5a623','#9b5400',2)
            # A fixed callout panel keeps exact S readable even on retraced lines.
            canvas.text((offset+45,692),'停止 S = '+ptext(d['S']),21)
        canvas.text((offset+45,735),'完成返航；已采 '+str(len(final['H']))+'，暂缓 '+str(len(final['D']))+'；规划 2 次',21)
        canvas.text((offset+45,775),'实际长度 '+f'{approx(final["M"]["exact"]):.6f}'+'；'+str(segment)+' 条非零段',21)
        for x in sorted({p[0] for p in public['F_nominal']}):
            sx,sy=screen((x,0));canvas.text((sx-5,660),str(x),16,'#687789')
        for y in sorted({p[1] for p in public['F_nominal']}):
            sx,sy=screen((0,y));canvas.text((offset+37,sy-10),str(y),16,'#687789')
    canvas.line([(30,839),(1470,839)],'#d8e0eb',2)
    canvas.text((40,855),'蓝：发现前实飞  绿：接续实飞  紫：实飞 S→q  灰虚：检测段未飞余段  橙点：停止',20)
    canvas.text((40,888),'红格：隐藏障碍  红虚框：L∞ 1/8 探测带  绿点：有效采集格心  B：起点及返航基地',19)
    directory=HERE/'figures';directory.mkdir(exist_ok=True)
    canvas.save(directory/(world['id']+'_实际路线'))

def main():
    assert not (HERE/'final_receipt.json').exists(),'sealed'
    reg=read(HERE/'registration.json');batch=read(HERE/'batch_receipt.json')
    assert not batch['stopped_on_exception']
    sessions=[read(HERE/'sessions'/(j['id']+'.json')) for j in reg['jobs']]
    plans=[read(HERE/row['file']) for s in sessions for row in s['plans']]
    native=sumc(s['native_counts'] for s in sessions)
    wrapper=sumc(p['wrapper_counts'] for p in plans)
    pipeaudit=sumc(p['independent']['counts'] for p in plans)
    execution=sumc(s['main_execution_counts'] for s in sessions)
    exaudit=sumc(s['independent_execution']['counts'] for s in sessions)
    technical=read(HERE/'technical_rounds/round_1/receipt.json')
    publicprep=read(HERE/'technical_rounds/round_1/T01.json')['contract_probe']['counts']
    verify=read(HERE/'verification_runs/verify_1.json');assert verify['passed']
    accounts={'utc':now(),'technical':technical['counts'],'technical_public_preparation':publicprep,
              'world_construction_checks':read(HERE/'technical_freeze.json')['world_construction'],
              'real_native':dict(native),'real_wrapper':dict(wrapper),'real_execution':dict(execution),
              'real_pipeline_independent':dict(pipeaudit),'real_execution_independent':dict(exaudit),
              'saved_only_verify_1':verify['counts'],'core_calls':native['core_started'],
              'true_sessions':len(sessions),'technical_sessions':12,'fixed_stub_responses':12,
              'planning_wait_records':execution['planning_wait_records']}
    dump(HERE/'调用与查询总账.json',accounts)
    rows=[]
    details=[]
    for s in sorted(sessions,key=lambda s:(s['job']['world'],s['job']['method'])):
        f=s['final'];a=s['independent_execution'];p=[read(HERE/row['file']) for row in s['plans']]
        d=a['detections'][0]
        elapsed=sum(x['timing']['pipeline_seconds'] for x in p)
        rows.append('|'+ '|'.join([s['job']['id'],str(len(s['public_initial']['P'])),str(len(f['H'])),str(len(f['D'])),
                    '是' if d['interior_diagonal'] else '否',ptext(d['S']),exact_text(f['M']['exact'])+f' ≈ {approx(f["M"]["exact"]):.6f}',
                    f'2 / {elapsed:.6f}s','完成'])+'|')
        re=p[1];raw=re['snapshot']['input']
        details.append(f"- {s['job']['id']}：实停 S={ptext(raw['S'])}，真实来向 h={ptext(raw['h'])}；原 H={raw['H']}，D={raw['D']}；唯一 q={re['q']}，付费接入后 h_entry={ptext(re['h_entry'])}。首连接信用只在实飞中心到达后提交。")
    figures='\n\n'.join('![世界'+w['id']+'实际路线]('+str((HERE/'figures'/(w['id']+'_实际路线.png')).as_posix())+')' for w in reg['worlds'])
    report='''# 首次有限闭环结果：六会话完成，已停止交审

本轮按执行稿完成三个事前固定微型世界 × H1/P2，共六会话、十二次真实核心入口，达到授权上限即停。六会话均在途中发现初始已存在的隐藏障碍，从真实停止点重规划一次，完成当前可检任务并实际返航。失败/中止/未运行均为0，无补图、补种子、补跑或第二事件。

六次发现中，W3 两方法共两次发生在斜向线段内部；另外四次为轴向。六次停止均在障碍闭格之外。主执行及独立解析回放没有发现碰障、漏检、预测信用误提交、距离或资源账不一致。这里的安全仅指本轮点模型及固定 L∞ 探测带假设下六条保存轨迹。

## 每个世界实际完成了什么

|会话|名义目标 P|实际已采 H|障碍暂缓 D|斜段内发现|真实停止 S|实际总路程（格长）|规划次数 / 管线累计秒|状态|
|---|---:|---:|---:|---|---|---|---|---|
'''+ '\n'.join(rows)+'''

W1 每法服务9格、障碍遮挡1格；W2 每法服务5格，障碍本来就不是目标；W3 每法服务4格、遮挡1格。暂缓格仍在发布责任 P 中，未记为完成。所有实际可检目标均完成，实际回到基地，E 非负。三个世界工作量不同，分列而不平均排名。W3 的两条实际路线相差2格，只是这个固定个例；不能据此声称普遍质量/速度优势。

管线时间包括该次首连接、真实核心、直达、主审核和编码；不含冷导入及独立审核。十二次管线均低于30秒，核心均正常完成且低于各自传入的20秒上限，未缩短 P2 预算。正常较早完成不是强行跑满20秒；P2 五次最终保留 common_fallback、一次 H_scan_opt，核心是否完成与最终候选来源分开记录。计时仅用于本轮截止验收，不作性能结论。

## 实际状态接续证据

'''+ '\n'.join(details)+'''

H1 的冻结来源枚举仍叫 synthetic_direction_fixture，因为世界是手工技术世界；向量的 execution_evidence 和日志尾 hash 绑定已执行非零段，既不编造 previous 邻格，也不把下一条预测边称为实际历史。非零付费 S→q 后的预测来向另存 h_entry，实际 h 在该连接真正执行前保持原值。W2 发现时目标已全部采完，仍从真实停止位置连接并实际返航，不把“无剩余目标”当作已到基地。

## 门槛与费用

十二项事前手算探测/执行门槛首轮全通过，只用12纯会话/12固定手写响应，没有第二轮。包含闭盒相切、带内零时刻、前缀信用、预测隔离、资源原子拒绝、已知障碍去重、空任务返航和 unsafe 优先采集负例。同一导入顺序下审核包身份、list/tuple 与整数值 Fraction 边界均通过。纯公开准备15候选/16几何；纯执行主盒29/真值几何13/距离14/服务16，独立盒29/几何13/距离14/服务19。纯门槛真实核心/后处理/图搜索0。三世界构造各做一次有限连通分量检查，独立单列。

正式：核心开始/返回/完成均12（H1 6，P2 6），后处理12；图搜索133＝context BFS12＋距离行 BFS29＋A*92，均完成。原核心内部主审核162次均合法，distance8293/path662；首连接记录74候选，包含6次无运动零接入及68次已知方向候选检查。不能再报零实验或把这些成本省略。

正式公开管线主几何340、距离328、服务609；直达 source/candidate/output 几何120/105/67，服务338、区间68。正式实际执行63动作（6次起点采集＋57条非零飞行段）、12条等待记录；主探测/安全盒32/63、真值几何63、距离63、服务144。六次发现后31次已知障碍安全检查不重新触发重规划。

运行时独立公开审核几何407/距离340/服务2228，实际日志独立审核几何63/距离63/服务405，探测/安全盒32/63；H1 首评分与方向审核6份、单位边62条。最终保存回放另外审核12份计划、6份实飞及12份纯夹具：新增独立几何483/距离417/服务2652，探测/安全盒46/78，新增核心/选择器/后处理/图搜索均0。全部原始分类计数、逐管线和逐动作计数见调用与查询总账.json及保存返回，不能把几何调用与内部盒/采样点检查混成同一口径。

## 三个世界路线图

图只累计已执行线段；灰虚余段没有飞行也没有提交信用。红色真值为事后评估展示，不表示规划器提前知道。PNG 和 SVG 均保留。

'''+figures+'''

## 能说明与不能说明

首次有限的“实际飞行—发现一个隐藏障碍—精确停止—保留历史—从真实 S 接续—完成可检任务—实际返航”链条已在这六个会话通过。执行日志独立回放从初态和每个动作重建，未从终态倒填；未执行预测路线只保存在计划返回中。世界和探测参数在求解前固定，正式开始后冻结代码与输入未改，旧冻结源码/输入/结果保持原字节。

这不是任意时刻新生障碍、一般无理停止点、现场安全、全未知探索、规模性能或论文创新的证明。1/8 是 L∞ 格盒外探测技术参数，不是现实传感器或欧氏制动距离。未扩展目标区域、未使用留出、未启动优化或性能批、未推送。完成封存后停止，交负责人审核。
'''
    (HERE/'00_通俗报告与闭环结果.md').write_text(report,encoding='utf-8')
    for w in reg['worlds']:
        figure(w,[s for s in sessions if s['job']['world']==w['id']])
    packet='''# Review packet

先读 00_通俗报告与闭环结果.md，再看 figures 的三世界实飞图、合同与查询上限.md、registration.json。六会话完整初态/动作/终态及运行时独立审核在 sessions；逐行 flush 的同一 hash 链在 logs/*_actions.jsonl。十二真实公开输入在 calls/*_public_input.json，原生/后处理原文在 calls/*_return.json，完整计划及主/独立审计在 outputs。已执行前缀与预测路线分开，不求预测长度之和。

worlds_public 与 worlds_private 分开；private 仅环境和审核使用。bindings.json 为逐文件上游来源；原数值管线四函数源码段未改说明及接入 diff 一并保留。H1/P2 核心/奖励/直达及公共资源/几何来自已验收冻结来源，未作算法优化。audit_expected_identity.json、每会话和计划的模块/函数身份，以及 real_freeze.json 证明求解前绑定和前后未变。

technical_freeze.json 固定地图、夹具、合同与初始源码；technical_rounds/round_1 有十二纯会话和手算结果、源 hash、无核心调用收据。真实开始前 real_freeze.json 二次冻结执行器和源码；real_started.json 及 batch_receipt.json 固定六会话一次执行，十二入口已到上限，无真实补跑。old_files.json/external_source_guards.json 保护历史1277记录及外部加载依赖。

调用与查询总账.json 分开纯门槛、世界结构检查、真实管线/执行、运行时审核和保存复核。保存 verify 为独立解析回放，禁止算法入口、选择器、后处理和图搜索；第一次实际收据在 verification_runs/verify_1.json。每次再次 verify 会另存新收据并如实产生新的保存审核几何查询，不是零计算。

本机只读核验命令（不重跑算法）：

    .\\运行环境\\python\\python.exe -B -X utf8 '斜向执行障碍发现首次闭环_v0.1_20261022/verify.py'

manifest.json 绑定封存文件，final_receipt.json 绑定清单及首次 verify；verification_runs 新收据是后续附加审查，不改封存结果。root_before.md/root_after.md 是根进度前后快照，不要求实时根进度永远不变。presentation.py 仅在结果完成后读取保存证据生成文图，无任何算法或几何查询，不属于正式求解后修补。完成即停止交审。
'''
    (HERE/'review_packet.md').write_text(packet,encoding='utf-8')
    print(json.dumps({'reports':2,'figures':3,'real_core_calls':native['core_started'],'complete_sessions':6,'diagonal_detections':2},ensure_ascii=False))

if __name__=='__main__':
    main()
