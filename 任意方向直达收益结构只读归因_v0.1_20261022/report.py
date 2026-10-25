"""Saved route/edge drawing and report; no geometry queries or new route."""
from pathlib import Path
from collections import Counter,defaultdict
import json,shutil
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;B=H.parent/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def md(n,t):(H/n).write_text(t,encoding='utf8')
def mid(v):return (v[0]+v[1])/(2*S)
def show(v):return f'{mid(v):.6f}'
def plot(jobs,rid,kind,dest,paired_id=None):
    job=jobs[rid];src=read(B/job['payload']);o=read(B/'outputs'/(rid+'.json'));c=src['input'];F=set(map(tuple,c['free']));U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));P=set(map(tuple,c['published_targets']));xmin=min(x for x,y in F);xmax=max(x for x,y in F);ymin=min(y for x,y in F);ymax=max(y for x,y in F)
    im=Image.new('RGB',(1900,1080),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);d.text((28,15),rid,fill='black',font=font)
    if paired_id:
        p=read(B/'outputs'/(paired_id+'.json'));cp=read(B/jobs[paired_id]['payload'])['input'];assert cp['free']==c['free'] and cp['current']==c['current'] and cp['base']==c['base'] and set(map(tuple,cp['targets']))==set(map(tuple,c['targets']))
        panels=[('Saved PPCPP shortcut',o['vertices'],None,'#1c64ad'),('Saved P2 shortcut',p['vertices'],None,'#b25723')]
    else:panels=[('Saved original, highlighted '+kind,src['raw']['route'],'old','#999999'),('Saved shortcut, highlighted '+kind,o['vertices'],'new','#73a7d4')]
    for panel,(title,path,mode,color) in enumerate(panels):
        left=panel*950+35;top=100;scale=min(875/(xmax-xmin+2),840/(ymax-ymin+2));cx=left+(875-scale*(xmax-xmin+1))/2;cy=top+(840-scale*(ymax-ymin+1))/2
        def xy(p):return (cx+(p[0]-xmin+.5)*scale,cy+(ymax-p[1]+.5)*scale)
        d.text((left,63),title,fill='black',font=font)
        for x in range(xmin,xmax+1):
            for y in range(ymin,ymax+1):d.rectangle([xy((x-.5,y+.5)),xy((x+.5,y-.5))],fill='#444444' if (x,y) not in F else ('#fff4d3' if (x,y) in P else '#f4f4f4'),outline='#d2d2d2',width=1)
        if len(path)>1:d.line([xy(p) for p in path],fill=color,width=2)
        if mode:
            for e in o['edges']:
                if e['kind']!=kind:continue
                segment=src['raw']['route'][e['left']:e['right']+1] if mode=='old' else [e['a'],e['b']]
                if len(segment)>1:d.line([xy(p) for p in segment],fill='#a62678',width=4)
        for p in U:
            x,y=xy(p);rr=max(2,min(3.5,scale/6));d.ellipse((x-rr,y-rr,x+rr,y+rr),outline='#008340',width=1)
        for point,label in ((c['current'],'S'),(c['base'],'B')):
            x,y=xy(point);d.rectangle((x-4,y-4,x+4,y+4),outline='black',width=2);d.text((x+5,y+3),label,fill='black',font=small)
    d.text((28,982),'Green rings: required centers / nominal anchors. Purple: selected saved segment category. x right, y up.',fill='black',font=small)
    d.text((28,1010),'Dark cells: forbidden complement of F inside the display. These are not all claimed to be newly added obstacles.',fill='black',font=small)
    d.text((28,1038),'Only existing saved routes are drawn. No visibility test, counterfactual path or endpoint replacement was calculated.',fill='black',font=small)
    im.save(dest)
def main():
    routes=read(H/'117全量区间分解.json');rt={r['id']:r for r in routes};groups=read(H/'分层交叉汇总.json');pairs=read(H/'57配对成本位置与等长证据.json');edges=read(H/'逐边区间分解.json');examples=read(H/'解释实例固定选择.json');jobs={j['id']:j for j in read(B/'117固定清单.json')}
    def g(cohort,method,dim,label):return next(x for x in groups if (x['cohort'],x['method'],x['dimension'],x['label'])==(cohort,method,dim,label))
    total=g('54_states','PPCPP','all','all');ret=g('54_states','PPCPP','kind','last_to_base');between=g('54_states','PPCPP','kind','between_first_services');share=100*mid(ret['gain'])/mid(total['gain'])
    counts=Counter(e['class'] for e in edges);all_excess=sum(e['excess_ticks'] for e in edges);non_diagonal_saving=sum(e['gain_ticks'][0] for e in edges if e['class']!='diagonal');assert all_excess==0 and non_diagonal_saving==0
    md('00_通俗报告.md',f'''# 任意方向直达收益结构：只读归因

本轮仅读取原封存117条输入、输出及审核证据，拆解8112条已输出边。独立整数/区间核验通过；新增规划、图搜索、可视、捷径、候选、新路线和反事实全部0，未重跑原正式批或原几何verify。

54状态PPCPP共节省{show(total['gain'])}，其中返航{show(ret['gain'])}（占总节省{share:.3f}%），采集间{show(between['gain'])}，起始0。负责人原三段账得到复核。P2的同批节省分为起始23.708632、采集间66.935373、返航110.848347。六世界分成同输入三配对和非配对三条，详见完整表，不用PPCPP六条总量对比P2三条。

关键结构结果：8112条已输出边全部满足原区间长度l等于端点曼哈顿距离m，因此每条的l−m都精确为0。零位移边{counts['zero_displacement']}条；非零同轴边{counts['axis']}条且节省全0；斜向边{counts['diagonal']}条承担全部本批收益。故在这批已接受边上，全部节省均可代数记为m−d，未发现同轴回折/闭环删除收益。这个判断来自完整边账，不是从斜线图形猜测。

可以说“本固定批记录到的实际缩短均涉及斜向端点，且没有曼哈顿超额项”。不能据此说已隔离出斜飞能力的独立因果效应、任意曼哈顿折线都合法，或所有潜在收益都由斜飞决定。没有计算任何替代四邻接路线或其他候选；l−m的一般含义仅是相对端点曼哈顿下界的超额，障碍下该下界未必可达。

处理后PPCPP仍大多长于P2，成本位置主要在双方各自的末次采集到基地段；位置分账不等于更换末采集格就能省下同量。原large_I_obstacle_p70的跨零区间记录保留，新补充证书发现双方已保存边长平方多重集合完全一致，因而可精确证明总长相等。原报告未改；加入这项新证据后，54配对可归为44长、9平、1短，三组六世界配对仍均较长。

三个“最大收益”解释类别按规定都选中了large_Z_corner_p30的PPCPP；同轴/零位移正收益例不存在，明确留空，不另挑图制造多样性。例图仅解释已保存结果，不是代表性抽样或总体优势证据。

只建议一个下一步：若继续方法设计，优先审查“末次采集位置、此前覆盖代价与返航成本的耦合”是否存在区别于旧方法的具体机制，再决定是否值得另行实验。本轮不实现、不搜索，也不把上述成本差直接当作可取得收益。完成封存停止，交负责人审核。
''')
    table='|批次|方法|段类|路线分母|旧长|新长|节省|占该方法该批总节省|\n|---|---|---|---:|---:|---:|---:|---:|\n'
    for cohort in ('54_states','six_paired3','six_unpaired3'):
        for method in ('PPCPP','P2_MULTI'):
            avail=[x for x in groups if x['cohort']==cohort and x['method']==method and x['dimension']=='all']
            if not avail:continue
            denominator=mid(avail[0]['gain'])
            for kind in ('start_to_first','between_first_services','last_to_base'):
                a=g(cohort,method,'kind',kind);pct=f"{100*mid(a['gain'])/denominator:.3f}%" if denominator else '不适用(总节省0)'
                table+=f"|{cohort}|{method}|{kind}|{a['route_denominator']}|{a['old']}|{show(a['d'])}|{show(a['gain'])}|{pct}|\n"
    # Reproduce the owner's six-decimal display only as an approximate check.
    expected={('PPCPP','start_to_first'):'0.000000',('PPCPP','between_first_services'):'154.576668',('PPCPP','last_to_base'):'374.207355',('P2_MULTI','start_to_first'):'23.708632',('P2_MULTI','between_first_services'):'66.935373',('P2_MULTI','last_to_base'):'110.848347'}
    for (m,k),s in expected.items():assert show(g('54_states',m,'kind',k)['gain'])==s
    md('01_三段账与原标签分布.md','''# 三段账与固定原标签

下表显示值保留6位小数；所有临界判断及相加核对以JSON的有理整数区间为准。占比的分母是同方法同批总节省，非原长度。分层交叉汇总.json另保留旧/新长度区间、边数及零收益边数。空任务段没有真实样本，不补造。

'''+table+'\n54状态按旧ID的scale/shape/event/progress逐维描述，原有层级全部保留；没有挑显著分组或假设独立重复。六世界按world_metadata的shape/scale分列，原记录没有单一事件类型标签，event为null，不把末次响应重新命名成某个新事件组。六世界仅L_S/L_M/T_M配对，I_S/I_M/T_S为非配对三条。\n\n')
    labeltable='|批次|方法|旧维度|旧标签|路线数|旧长|新长|节省|\n|---|---|---|---|---:|---:|---:|---:|\n'
    for x in groups:
        if x['dimension'] in ('scale','shape','event','progress'):labeltable+=f"|{x['cohort']}|{x['method']}|{x['dimension']}|{x['label']}|{x['route_denominator']}|{x['old']}|{show(x['d'])}|{show(x['gain'])}|\n"
    with (H/'01_三段账与原标签分布.md').open('a',encoding='utf8') as f:f.write(labeltable+'\n逐维表的行会重复计入同一路线，不能把所有维度相加当作总量。\n')
    ctable='|批次|方法|端点类别|边数|旧长|新长|节省|l−m|m−d|\n|---|---|---|---:|---:|---:|---:|---:|---:|\n'
    for x in groups:
        if x['dimension']=='class':ctable+=f"|{x['cohort']}|{x['method']}|{x['label']}|{x['edges']}|{x['old']}|{show(x['d'])}|{show(x['gain'])}|{x['excess']/S:.6f}|{show(x['metric_gap'])}|\n"
    cross='|批次|方法|段类×端点类别|边数|节省|\n|---|---|---|---:|---:|\n'
    for x in groups:
        if x['dimension']=='cross':cross+=f"|{x['cohort']}|{x['method']}|{x['label']}|{x['edges']}|{show(x['gain'])}|\n"
    md('02_逐边结构与代数分解.md','''# 逐边结构与代数分解

每条新边保持原[left,right]证据，l=right−left，m=|dx|+|dy|，q=dx²+dy²。d为该条已经保存输出边的欧氏长度。以整数平方构造尺度10^60的有理包络，独立核验b²≤q·10^120≤u²；不是可视/碰撞判定，更没有求反事实路径。l−d区间与(l−m)+(m−d)区间逐项完全一致。相加还原每段、每路线及各不重叠分组原总收益，并包含于原50位保存长度区间。

逐边区间分解.json保留全部8112条，117全量区间分解.json及CSV保留全量路线，分层交叉汇总.json保留端点类别×三段账。零位移类在本批不存在，不能用“无类别行”暗示有零收益闭环。非零同轴类有边但收益均为精确0；所有正收益均在斜向类。

'''+ctable+'\n'+cross+'''
l−m不是可以直接实施的四邻接改进量；需要障碍可行性的额外证据才能说曼哈顿下界可取到。本批全部l−m为0，表明被接受的原区间恰是端点曼哈顿长度，而不是声称整条覆盖路线已经最优。m−d与l−m是代数项，非两个独立干预因果贡献。新折线不增/合法/信用完整沿用旧独立回执，不在本轮重验几何。
''')
    cost='|配对批次|段类|原PPCPP−P2|处理后PPCPP−P2|\n|---|---|---:|---:|\n'
    cost_values=[]
    for batch in ('54_states','6_last_responses'):
        ps=[p for p in pairs if p['batch']==batch]
        for kind in ('start_to_first','between_first_services','last_to_base'):
            xs=[x for p in ps for x in p['parts'] if x['kind']==kind];d=[sum(x['new_difference_ticks'][i] for x in xs) for i in (0,1)];old=sum(x['old_difference'] for x in xs);cost+=f'|{batch}|{kind}|{old}|{show(d)}|\n';cost_values.append({'batch':batch,'kind':kind,'old_difference':old,'new_difference_ticks':d})
        td=[sum(p['new_total_difference_ticks'][i] for p in ps) for i in (0,1)];cost+=f"|{batch}|合计|{sum(p['old_total_difference'] for p in ps)}|{show(td)}|\n"
    (H/'配对成本位置分批合计.json').write_text(json.dumps(cost_values,ensure_ascii=False,indent=2),encoding='utf8')
    cert=next(p for p in pairs if p['additional_exact_equal_certificate']);certtext=json.dumps(cert['additional_exact_equal_certificate']['squared_length_multiset'],ensure_ascii=False)
    md('03_参照差与补充等长证书.md','''# 参照差的成本位置

下表以双方各自起始/实际首次采集间/末次至基地的完整账本作差；任务与输入配对相同，但采集顺序及末采集点未强行相同。它是成本位置描述，没有改动任何端点或计算更换终点的路线。

'''+cost+f'''
54组总差从1134减至约806.708328。处理后返航成本差为约729.640992，采集间约170.358705，起始约−93.291368。起始负项表示此处PPCPP较短，不能把所有段都画成正的“损失百分比”。这些符号相加才是完整差，不是更换末采集格可省多少的承诺。

原large_I_obstacle_p70仍保留跨零数值区间；另有精确等长证书：双方输出边长平方多重集合（平方值:次数）均为 {certtext}。相同平方值对应同一非负平方根，逐项一一配对，故总长严格相等，不需要通用根式化简或新几何查询。该补充只写本包，不修改旧报告、旧配对标签和旧结果。

按原区间标签54组仍为44长/8平/1短/1未确定；加入本补充证书后为44长/9平/1短。六世界三配对仍3长。不能因为PPCPP自身减少比例更大而称其优于P2；本批没有顺序最优证书，剩余差不全归因于顺序。
''')
    (H/'figures').mkdir(exist_ok=True);extext='# 固定解释实例\n\n按执行稿在各类别节省最大者中取ID最小，区间认证排序及候选数均在解释实例固定选择.json；这是解释性选择，不是代表样本。三类最大者恰为同一路线，不为图形多样性换例。\n\n'
    for e in examples:
        if e['id'] is None:extext+='同轴/零位移正收益类别不存在，明确无例；不借技术夹具或新路线补位。\n\n';continue
        rid=e['id'];r=rt[rid];label=e['category'];filename=label+'.png'
        if label=='main_return':plot(jobs,rid,'last_to_base',H/'figures'/filename)
        elif label=='between_service':plot(jobs,rid,'between_first_services',H/'figures'/filename)
        else:p=next(p for p in pairs if p['PPCPP_id']==rid);plot(jobs,rid,None,H/'figures'/filename,paired_id=p['P2_id'])
        extra=''
        if label=='still_behind':extra='；保存新长度仍比同输入P2长约'+show(p['new_total_difference_ticks'])
        extext+=f"{label}：{rid}；类别节省{show(e['selection_score_ticks'])}{extra}。\n\n![{label}](figures/{filename})\n\n"
    extext+='原格心任务圈、F及其禁止补集、当前点S、基地B来自该真实保存输入。高亮均为实际旧路径片段或实际新边，未生成任何示意替代线。\n';md('04_可复核实例.md',extext)
    md('review_packet.md','''# 审核入口

00_通俗报告.md回答主要收益、端点结构、未知及唯一建议；01_三段账与原标签分布.md给分母明确的全量位置账及旧标签描述；02_逐边结构与代数分解.md给同轴/零位移/斜向交叉；03_参照差与补充等长证书.md保留原未知并新增精确证书；04_可复核实例.md展示固定解释选择的保存路径。

机器证据：逐边区间分解.json、117全量区间分解.json/CSV、分层交叉汇总.json、57配对成本位置与等长证据.json、解释实例固定选择.json、配对成本位置分批合计.json。来源hash.json绑定原封存包及原来源，零新增调用账.json明确本轮新增查询/规划/路径/反事实均0。

只读核验.ps1使用verify.py，仅哈希、整数平方、索引与有理区间核对；不导入本分析脚本或原生产/几何模块，不重跑旧verify。它独立验证逐边分解相加恢复原总收益、分层交叉、57对成本位置及补充等长证书。既有8112次独立几何是历史证据，本轮0次。

旧包、冻结源码及留出不改，未提交推送。封存后停止，未实现顺序搜索或新算法，唯一下一步建议尚未执行。
''')
    shutil.copyfile(H.parent/'任意方向直达结果负责人审核与收益归因执行稿_给sol_20261022.md',H/'执行稿原文快照.md')
    print(json.dumps({'saved_routes':len(routes),'edge_classes':dict(counts),'all_l_minus_m':all_excess,'return_share_percent':share,'report_only_new_queries':0},ensure_ascii=False))
if __name__=='__main__':main()
