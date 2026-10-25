"""Independent aborted-report export from saved evidence only."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,math,html
from PIL import Image,ImageDraw,ImageFont
from center_credit_v02_20261022.utils import HERE,ROOT,read,dump,sha,now

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
    c.text((35,896),'旧首槽保留failed；W1_H1首计划是保存复用，非v0.2新增核心。',19)
    (HERE/'figures').mkdir(exist_ok=True);c.save(HERE/'figures'/(world['id']+'_接续实际状态'))

def main(seal=False):
    assert not (HERE/'final_receipt.json').exists()
    reg=read(HERE/'registration.json');batch=read(HERE/'batch_receipt.json')
    sessions=[read(HERE/'sessions'/(j['id']+'.json')) for j in batch['attempted']]
    plans=[read(HERE/row['file']) for s in sessions for row in s['plans'] if row.get('provenance')!='reused_saved_reaudited']
    native=sumc(s['native_counts'] for s in sessions)
    wrapper=sumc(p['wrapper_counts'] for p in plans)
    independent=sumc(p['independent_counts_actual_even_on_exception'] for p in plans)
    actual=sumc(s['main_execution_counts'] for s in sessions)
    verify=read(HERE/'verification_runs/verify_1.json');reuse=read(HERE/'reuse_receipt.json')
    rows=[];turns={}
    for j in reg['jobs']:
        s=next((s for s in sessions if s['job']['id']==j['id']),None)
        if not s:
            rows.append('|'+j['id']+'|未运行|0|—|—|—|—|');continue
        ds=[]
        for r in s['records']:
            if r['kind']=='move' and 'actual' in r:
                a,b=map(point,r['actual'])
                if a!=b:ds.append((b[0]-a[0],b[1]-a[1]))
        t=sum(a[0]*b[1]!=a[1]*b[0] or a[0]*b[0]+a[1]*b[1]<0 for a,b in zip(ds,ds[1:]))
        turns[j['id']]={'nonzero_direction_changes':t,'diagnostic_direction_pair_tests':max(0,len(ds)-1)}
        rows.append('|'+ '|'.join([j['id'],'完成返航' if s['passed'] else '失败停止',str(s['native_counts']['core_started']),str(len(s['final']['H']))+'/'+str(len(s['final']['D'])),exact_text(s['final']['M']['exact']),str(t),ptext(s['final']['S'])])+'|')
    account={'new_native_observed':dict(native),'new_wrapper_observed':dict(wrapper),'new_plan_independent_actual_including_exception':dict(independent),
       'new_execution_observed_excluding_old_base_action':dict(actual),'old_base_action_reused_once':1,'turns_saved_diagnostic':turns,
       'precheck':read(HERE/'precheck.json'),'saved_reuse':reuse,'verify_new_queries':verify['counts'],
       'old_core_calls':1,'new_core_calls':native['core_started'],'cross_version_core_calls':1+native['core_started'],
       'old_post_calls':1,'new_post_calls':native['post_entry_calls'],'old_failure_independent_counter_still_missing':True}
    dump(HERE/'三栏调用与查询账.json',account)
    report='''# 中心区观察器v0.2：两会话完成，新零查询计数错误后停止

本轮按接续稿完成观察器作用域修复、六项零核心组合预检和旧首槽保存复核。正式接续的 W1_H1、W1_P2 完成可检任务并返航；W2_P2 发现后第二份计划在独立计数守恒审核处遇到新的零值字段错误，立即停止。W2_H1、W3_H1、W3_P2未运行。本版未通过全部有限闭环验收，没有修补正式源码或补跑。

## 三栏结果与来源

|来源|结果|算法调用口径|
|---|---|---|
|v0.1原失败|W1_H1首槽仍failed，完整返回/135混账及原计数缺失保留|旧H1核心1、直达1，未重跑|
|保存结果复核复用|完整输入、初态/配置、路线/见证/资源全部审核通过，标reused_saved_reaudited|新增核心/选择器/直达/图搜索0；旧计数派生分类非原trace|
|v0.2新增执行|2会话完成，1会话失败，3未运行|新增核心5：H1 1、P2 4；新增直达5；跨版本核心6/上限12|

旧首槽135原值仍在来源记录中。派生引擎90、主管线post审核45来自各自已保存计数及完整返回，未硬减常数；全量审核保留精确相等断言。基地旧collect_here日志原hash链恢复并只计一次，未重跑初始规划；后续新显式动作分别记账，重复采集不增加H。旧首槽与新调用不拼成同轮计时性能配对。

|会话|状态|新核心|实际已采/暂缓|实际长度|转弯次数|当前实际S|
|---|---|---:|---|---|---:|---|
'''+ '\n'.join(rows)+'''

W1各9个可检目标完成，遮挡1格仍在D，两法均实际返回基地、路程51/4。W2_P2已采5格、D空，但停在(2,21/8)，路程59/8，尚未返航，故不能算完成。其第二份计划只是预测，未提交其信用或距离。三次真实发现均为轴向；已完成的两会话发现后真实H接续通过。真实“不经格心的斜向段采集”本轮未发生/未验，W3未运行，不补图追触发。

## 修了什么，为何又停止

生产采集谓词、执行器、首连接/主管线、后处理路线选择、区域独立几何、核心评分/搜索/seed/地图/预算均不改。只改observe、必要计数守恒断言、异常Counter落盘及接续包装，见修复.diff和changes.json。新观察器沿调用栈按engine.credits、pipeline.main_audit、pipeline.run的函数code身份归类，不凭共享phase决定归属；phase只用于已识别主管线的细分。原1200总体保护继续覆盖“引擎＋主管线post审核”，引擎分类另有原保护，不增加预算。

新记录全服务查询473，分为引擎174、首连接预测21、原生审核98、主管线post审核86、全路线审核94，合计守恒；原post总体保护项260=174+86。引擎精确相等检查在已有查询的返回中通过。

W2_P2重规划时全部可检目标已经完成，后处理区域查询为0。Counter未生成 shared_region_queries_total 字段，转为普通dict后，新增审核用[]取该键，在audit/_audit.py:170抛KeyError。空集合“零查询”表示未被组合预检覆盖，是本次计数审核适配的技术错误，不是核心/路径/采集模型反例；失败仍照实保留。源程序在真实开始后完全不改，不现场改get默认值或补跑。

本次异常 finally 已实际持久化独立Counter：失败重规划审核几何29、距离26、区域查询75、区域点213、边参数170。旧v0.1异常Counter缺失仍保留为缺失，不能用本次完整记录覆盖旧缺口。

## 预检、复核和查询账

六项固定组合：仅引擎、仅主管线、串接、次数变化、嵌套/异常清理、序列化/模块身份，均以真实credit/main_audit函数和固定路线桩运行新旧观察器；共12分支、46区域查询，核心/后处理搜索/图搜索0。旧逻辑对主管线也计入post，新逻辑守恒。准备导入前发生一次标准库difflib等依赖未登记错误，尚未运行任何案例或核心；另存失败和旧hash清单后补登依赖，1轮技术修复，六项仅运行一轮。旧35纯案例只核hash复用，没有重做服务测试；本次计数以外源码一致性检查通过。

首槽保存完整复核新增独立几何41/距离31/区域查询400，点877/边参数780，核心/选择器/后处理/搜索0。原混计数与派生分类分开，证据强度不混。

新增真实核心开始/返回/完成5；图搜索90=context BFS5＋距离行BFS17＋A*68，内部审核102合法，distance7631/path502。旧首槽图搜索2另列，跨版本92。新增直达source/candidate/output45/48/31，服务174；主管线主几何144、距离139、服务299。新增运行时独立计划审核几何175/距离144/区域1124，包括失败一份；全部finally实际落盘。真实执行账另见总账：新动作36，旧基地动作1单列，共37条已记录执行动作；发现3、计划等待5，实际段统计按日志，不累加未执行计划。

保存verify复核5份接受的计划（其中1份保存复用）及3条实际执行日志；失败计划保留单列，不改通过。新增独立几何224/距离186/区域1714，点4099/边3406、探测/安全盒21/37；新增核心/选择器/后处理/图搜索0。只读核验通过意味着保存证据可重建，不意味着六会话实验通过。实际查询分类全量见三栏调用与查询账.json；原始异常、未运行和新失败不合并进成功汇总。

## 图与结束

'''+ '\n\n'.join('!['+w['id']+'接续状态]('+str((HERE/'figures'/(w['id']+'_接续实际状态.png')).as_posix())+')' for w in reg['worlds'])+'''

执行稿、统一合同、修复diff、六组合证据、旧35案例hash、首槽复核、实际日志/预测见证/原返回、输入来源及哈希、查询/转弯账、只读verify均保存。既有核心和区域语义未变，旧failed不回写。有限接口修复与两例完成不构成普遍质量、速度、创新或成像识别证据。封存更新根进度后停止交审，未追加性能、留出、seed、视觉或推送。
'''
    (HERE/'00_通俗接续与中止报告.md').write_text(report,encoding='utf-8')
    for w in reg['worlds']:figure(w,sessions)
    packet='''# v0.2 Review packet

先读00_通俗接续与中止报告.md、三栏调用与查询账.json、final_receipt.json。原失败保留、保存复核复用、新增执行是三种不同来源。v0.2也按新异常停止，不能当成六会话成功。

changes.json/修复.diff限制改动；采集/核心/路线机制不变。precheck_registration.json和precheck.json是六项12分支零核心预检；preparation_failure_1是预检前依赖登记错误及修复，旧35纯案例只hash复用。reuse_receipt.json及outputs/W1_H1_plan_1.json中的provenance保留原135、旧failed来源hash、派生分类及完整复核。reuse_session_seed.json是旧起点动作及状态，不是新核心。real_freeze.json证明真实开始后程序不变。

sessions/logs保存3条实际会话，两完成一失败；后三未运行在batch_receipt中。outputs中5份新计划含失败W2_P2_plan_2；每份independent_counts_actual_even_on_exception为finally真实落盘计数。calls保留5次新原生/后处理及公开输入；旧首槽原返回仍在v0.1，不拷旧结果冒充新增。实际等待记录绑定完整计划hash，失败的第二返回未执行。

保存核验命令：

    .\\运行环境\\python\\python.exe -B -X utf8 '中心有效采集区统一接入最小验收_v0.2_20261022/run_center.py' verify

verification_runs每次新收据有新增保存几何/区域查询，核心/选择器/后处理搜索0。失败计划未被保存核验改通过。manifest绑定封存原始证据；根进度前后快照不要求实时根文档永远相等。export_and_seal_v02只读取保存结果导出/结构封存，无算法入口。完成后不再修零值键、不自动用剩余额度或补跑。
'''
    (HERE/'review_packet.md').write_text(packet,encoding='utf-8')
    print({'exported':True,'new_core':native['core_started'],'completed':2,'failed':1,'unrun':3})
    if not seal:return
    for name,digest in read(HERE/'real_freeze.json')['files'].items():assert sha(HERE/name)==digest
    for name,digest in read(HERE/'external_source_guards.json').items():assert sha(name)==digest
    root=ROOT/'当前进度与下一步.md';before=root.read_bytes();assert before==(HERE/'root_before.md').read_bytes()
    header='''# 最新中止：中心区v0.2两会话完成，零查询计数字段失败后停止（2026-10-22）

中心有效采集区统一接入最小验收_v0.2_20261022 已封存交审，见00_通俗接续与中止报告.md、review_packet.md及final_receipt.json。六组合12新旧分支预检通过，核心/后处理搜索0，区域查询46；预检前依赖未登记错误修复1轮保留。35旧纯案例只hash复用。旧首槽完整保存复核通过（几何41/距离31/区域400），标reused_saved_reaudited，旧failed/135混账及异常Counter缺失不回写，新派生分类不冒充原trace。

恢复原基地动作后执行旧计划，没有重跑旧初始规划。新增核心5=H1 1/P2 4、新直达5；加旧首槽核心1/直达1，跨版本6/上限12。W1_H1/W1_P2均采9暂缓1并实际返航，路程各51/4；W2_P2发现后采5暂缓0、停(2,21/8)、路程59/8尚未返航，其第二计划计数审核KeyError，立即停止。W2_H1/W3_H1/W3_P2未运行，无补跑。真实发现3均轴向，两完成会话发现后H接续通过；真实斜向不经格心采集未验。

观察器已按函数code调用域分开，引擎174＋预测21＋原生98＋主管线post86＋全路线94=473守恒，原post总体1200保护保留；计数以外机制/地图/预算不改。新错误是空任务0查询时Counter不生成shared_region_queries_total，普通dict以[]取键失败。正式开始后源码未改，不修补重试。失败计划独立Counter终于实际finally保存：几何29/距离26/区域75；不能覆盖旧异常缺口。

新增图搜索90=context BFS5+行BFS17+A*68，内部审核102合法，旧图搜索2另列；新增独立计划审核几何175/距离144/区域1124含失败。保存verify核对5接受计划（含旧复用1）和3实际日志，新增几何224/距离186/区域1714、点4099/边3406、盒58，核心/选择器/后处理搜索0。实验仍是2完成/1失败/3未运行，不是六会话通过。三栏来源、原返回/前缀/中心区图/查询账/哈希已保存，停止交审，不推送、留出或性能批。

---
'''
    root.write_text(header+'\n'+before.decode('utf-8-sig'),encoding='utf-8');(HERE/'root_after.md').write_bytes(root.read_bytes())
    manifest={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and not p.is_relative_to(HERE/'verification_runs') and p.name not in ('manifest.json','final_receipt.json')}
    dump(HERE/'manifest.json',{'files':manifest})
    dump(HERE/'final_receipt.json',{'status':'STOPPED_NEW_ZERO_QUERY_COUNTER_KEY_FAILURE_SEALED','passed':False,'artifact_integrity_verified':True,
        'old_failed_retained':True,'saved_reuse':'reused_saved_reaudited','new_core_calls':5,'old_core_calls':1,'cross_version_core_calls':6,
        'new_H1':1,'new_P2':4,'completed_sessions':2,'failed_sessions':1,'unrun_sessions':3,'precheck_cases':6,'paired_branches':12,
        'technical_repairs_before_cases':1,'old_pure_cases_hash_reused':35,'new_runtime_failure':'zero-query dictionary key absent',
        'real_runtime_files_unchanged':len(read(HERE/'real_freeze.json')['files']),'sealed_files':len(manifest),
        'first_verify_file':'verification_runs/verify_1.json','first_verify_sha256':sha(HERE/'verification_runs/verify_1.json'),
        'manifest_sha256':sha(HERE/'manifest.json'),'stopped_for_owner_review':True,'new_algorithm_calls_during_export':0})
    for name,digest in manifest.items():assert sha(HERE/name)==digest
    print({'sealed':True,'files':len(manifest),'runtime_unchanged':True})

if __name__=='__main__':
    import sys
    main('--seal' in sys.argv)

