"""Offline SVG illustrations, balanced report and sealed review packet."""
import json,statistics,html
from pathlib import Path
from bridge_analysis import H,R,read,save,sha,csv_write
def fmt(x):return f'{x:.4f}' if isinstance(x,float) else str(x)
def svg_example(cases,path,title):
    W=1500;cellw=500;cellh=420;elements=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="900" viewBox="0 0 {W} 900"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Arial,Microsoft YaHei,sans-serif;font-size:14px}}</style>',f'<text x="15" y="24">{html.escape(title)}; rep=0; blue route, red bridges, black B, green H, orange pending</text>']
    for col,name in enumerate(cases):
        c=read(H/'inputs'/f'{name}.json');st=read(H/'structure'/f'{name}.json');before=read(H/'bases'/f'{st["base_id"]}.json')['input']['free']
        f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']));ob=set(map(tuple,st['obstacles']));xs=[p[0] for p in before];ys=[p[1] for p in before];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        scale=min(460/(xmax-xmin+2),340/(ymax-ymin+2))
        for row,method in enumerate(('PPCPP','P2_MULTI')):
            ox=col*cellw+20;oy=row*cellh+65
            def xy(p):return ox+(p[0]-xmin+.5)*scale,oy+(ymax-p[1]+.5)*scale
            for p in sorted(f|ob):
                x,y=xy(p);color='#111' if p in ob else '#5bad68' if p in covered else '#f4ad45' if p in t else '#e3e5e8'
                elements.append(f'<rect x="{x-scale*.45:.2f}" y="{y-scale*.45:.2f}" width="{scale*.9:.2f}" height="{scale*.9:.2f}" fill="{color}"/>')
            for e in st['structure']['cuts']['edges']:
                x,y=xy(e['edge'][0]);xx,yy=xy(e['edge'][1]);elements.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="#d00000" stroke-width="3"/>')
            jid=f'{name}__r0__{method}';o=read(H/'outputs'/f'{jid}.json');route=o['result']['raw'].get('route',[])
            if route:
                pp=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,route));elements.append(f'<polyline points="{pp}" fill="none" stroke="#174bc8" stroke-width="1.1" opacity="0.75"/>')
            for label,p,color in [('S',c['current'],'#b000a5'),('B',c['base'],'#001d4c')]:
                x,y=xy(p);elements.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/><text x="{x+4}" y="{y-4}">{label}</text>')
            cuts=read(H/'route_cuts'/f'{jid}.json') if route else None;ex=sum(g['excess_min'] for g in cuts['groups']) if cuts else None
            elements.append(f'<text x="{ox}" y="{oy-14}">{st["layout"]} / {method}: steps={len(route)-1 if route else "missing"}, excessGroups={ex}</text>')
            elements.append(f'<text x="{ox}" y="{row*cellh+452}">d(S,B)={st["structure"]["start_base_distance"]}, diameter={st["structure"]["diameter"]}, bridges={st["structure"]["bridge_count"]}, B={len(ob)}</text>')
    elements.append('</svg>');path.write_text('\n'.join(elements),encoding='utf8')
def report():
    a=read(H/'analysis.json');supp=read(H/'supplement.json');(H/'figures').mkdir();illustrations=[]
    for sel in a['selections']:
        for kind in ('maximum','minimum','first_no_excess'):
            item=sel[kind]
            if item is None:illustrations.append(dict(family=sel['family'],kind=kind,missing=True));continue
            name=item if isinstance(item,str) else item['case'];st=read(H/'structure'/f'{name}.json');prefix=f'{st["base_id"]}_p{st["progress"]}_{st["level"]}'
            cases=[prefix+'_'+layout for layout in ('dispersed','single','multi')];file=f'{sel["family"]}_{kind}.svg';svg_example(cases,H/'figures'/file,sel['family']+' '+kind+' '+prefix)
            ledger=[]
            for case in cases:
                s=next(s for s in a['states'] if s['case']==case);st=read(H/'structure'/f'{case}.json')
                ledger.append(dict(case=case,structure=st,metrics_rep0={m:next(r for r in a['rows'] if r['case']==case and r['rep']==0 and r['method']==m) for m in ('PPCPP','P2_MULTI')},cut_rep0={m:read(H/'route_cuts'/f'{case}__r0__{m}.json') for m in ('PPCPP','P2_MULTI')},seed_pair_results=s['pairs']))
            save(H/'figures'/file.replace('.svg','.json'),ledger);illustrations.append(dict(family=sel['family'],kind=kind,cases=cases,file='figures/'+file))
    save(H/'example_index.json',illustrations)
    p=a['summary']['PPCPP'];q=a['summary']['P2_MULTI'];pm=p['metric_mean'];qm=q['metric_mean'];signal=a['signal']
    matched=a['matched'];both=sum(x['signal'] for x in matched);neg=sum(x['length_gap_increase']<0 for x in matched if x['length_gap_increase'] is not None)
    structure_rows=[read(p) for p in sorted((H/'structure').glob('*.json'))]
    csv_write(H/'72状态结构表.csv',[dict(**{k:s[k] for k in ('id','base_id','family','size','progress','level','layout','obstacle_count','obstacle_ratio')},**{k:v for k,v in s['structure'].items() if k!='cuts'}) for s in structure_rows])
    numeric=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps','turns90','turns180','active_coverage','remaining_completion_fraction','published_coverage','deferred','overlap_ratio']
    lines=['# 施工障碍连接结构诊断结果','', '2026-10-21。已封存，待负责人审核。','',
        ('固定开发信号达到门槛，但仅支持交负责人讨论机制设计；不能据此确认上层区域决策有价值。' if signal['passed'] else '固定开发信号未达到门槛，本轮停止该假设，不追加地图寻找正例。'),'',
        f'六基础图、72事件状态；6历史准备＋12门槛＋432正式入口＝450真实入口。精确搜索0、额外重试0、留出0。两方法各216次正式；PPCPP合法{p["valid"]}、及时{p["timely"]}；P2合法{q["valid"]}、及时{q["timely"]}。预设不可达负例两次无路线是门槛预期，不混入正式成功率。','',
        '## 核心观察','',f'48个single/multi对dispersed匹配对照中，{both}个同时增大三种子均值路程差与超额桥组差；路程差缩小的对照有{neg}个。满足信号的不同基础几何为{signal["bases"]}，结构族为{signal["families"]}。三种子所有符号与均值/范围见analysis.json、匹配布局差异.csv，未选最好种子。进度、障碍档和嵌套桥组不当作新地图。','',
        f'两方法超额组数主统计均值分别{fmt(p["excess_group_mean"])}与{fmt(q["excess_group_mean"])}；存在{len(a["same_excess_different_length"])}个“超额组统计相同但路程不同”的状态/种子配对。这些反例说明桥割穿越不是完整代价的充分解释。','',
        '## 完整代价（每次正式入口均值）','', '|指标|PPCPP|P2_MULTI|PPCPP−P2|','|---|---:|---:|---:|']
    for k in numeric:lines.append(f'|{k}|{fmt(pm[k])}|{fmt(qm[k])}|{fmt(pm[k]-qm[k]) if pm[k] is not None and qm[k] is not None else "缺失"}|')
    lines+=['',f'四类移动步数互斥分解：新采{fmt(pm["fresh_target_steps"]-qm["fresh_target_steps"])}/历史重复{fmt(pm["historical_target_steps"]-qm["historical_target_steps"])}/本轮重复{fmt(pm["repeated_new_target_steps"]-qm["repeated_new_target_steps"])}/非目标{fmt(pm["non_target_steps"]-qm["non_target_steps"])}。另一个分解为采完前{fmt(pm["completion_step"]-qm["completion_step"])}与返航尾段{fmt(pm["return_tail_steps"]-qm["return_tail_steps"])}；两种分解不能相加，也不是因果份额。','',
        '## 输入与范围','', '三族各小中两图，每图12个宽4或6格的施工待检矩形支路，宽3格通行干线；不是一格宽道路模型。障碍只在非目标且未执行历史格中，两个预登记数量档：小6/9、中10/15。三布局同任务/同真实历史/同起终点/同旧计划/同捕食者/同资源。72状态deferred全0，这只是本轮控制，不改变一般遮挡暂缓语义。布局生成受到历史前缀限制；未对现场障碍分布抽样。','',
        '72状态结构表.csv给出实际障碍比例、连通分量、精确全点对平均距离/直径、起终点最短距离和桥数。single固定1个、multi固定2个含待检目标的闭合支路；增加障碍数量主要是额外分散障碍，不代表增加瓶颈。桥边按全部四邻接边删除复核。无桥不等于没有窄走廊。','',
        '桥组主量为每签名组的最小超额次数之和，另保存每组最大值和边数。它保守地归并连续桥边，可能掩盖组内部分边的额外往返；不将组内桥边当独立缺陷。切分另一侧统一为不含起点的一侧；起终点跨侧LB1，起终点同侧且另一侧有待检LB2，否则LB0。超额不是可删步数，未构造全局可行重排或最优证明。所有逐桥首次进入、退出余任务、最后完成和最终退出及未完退出再入在route_cuts。','',
        '## 分层与数量档','', '|分层|PPCPP平均步数|P2平均步数|差|','|---|---:|---:|---:|']
    for field in ('family','size','progress','level','layout'):
        for value,g in a['strata'][field].items():
            pl=g['PPCPP']['metric_mean']['length'];ql=g['P2_MULTI']['metric_mean']['length'];lines.append(f'|{field}={value}|{fmt(pl)}|{fmt(ql)}|{fmt(pl-ql)}|')
    highlow=[]
    states={(s['base_id'],s['progress'],s['layout'],s['level']):s for s in a['states']}
    for m in ('PPCPP','P2_MULTI'):
        ds=[states[(base,pct,layout,'high')]['methods'][m]['metric_mean']['length']-states[(base,pct,layout,'low')]['methods'][m]['metric_mean']['length'] for base in sorted({s['base_id'] for s in a['states']}) for pct in (30,70) for layout in ('dispersed','single','multi')]
        highlow.append(dict(method=m,n=len(ds),high_longer=sum(d>0 for d in ds),equal=ds.count(0),high_shorter=sum(d<0 for d in ds),mean_delta=statistics.mean(ds),all_deltas=ds))
    save(H/'high_low_count_comparison.json',highlow)
    lines+=['',f'按相同base/进度/布局配对比较高减低数量档：{highlow}。不能把高档一概称为更难。各图均12状态×3重复、样本数平衡，所以全体入口均值与六几何等权均值一致；独立几何等权结果另在analysis.json明确保存。失败若有保留分母，路线量不补0。','',
        '## 时间与来源','']
    for method,s in a['summary'].items():lines.append(f'{method}入口秒均值/中位/P95/最大：{s["seconds"]}；原生状态{ s["statuses"]}。P2软截止与外部及时分别保留，不能把native finished当最优。')
    lines+=['', '沿用上一正式比较实际runtime PPCPP分支与p2_adapter入口，冻结PPCPP/P2/core哈希未改。没有调用LAST、旋转接口或局部P2。解码/构造/完整求解/完整raw编码均在20秒共同暖入口内；启动导入/磁盘/离线复核在外。串行新进程、单线程、90秒看门狗。实际导入源hash和输入hash逐调用保留，参数根据封存job/input和代码推导；没有额外独立参数receipt。Windows系统DLL不是全机字节封存。','',
        'prep_seal在六次历史前；event_seal在真实历史与结构核验后、12门槛和432正式前。准备后发现未调用的原事件封存函数会误封追加台账，新增bridge_event_seal.py明确排除动态actual_order，再由最终manifest覆盖；原程序保留。无失败求解或重跑。见封存实现补充.md。','',
        '## 预定正反图与证据','']
    for ex in illustrations:lines.append(f'- {ex["family"]}/{ex["kind"]}：缺失' if ex.get('missing') else f'- [{ex["family"]}/{ex["kind"]}]({ex["file"]})：三布局×两方法，固定重复0，配套JSON含最短距离、桥账和全部种子差。')
    lines+=['','图只展示轨迹和结构，不凭绕行外观断言浪费。六图均是本轮开发数据，结构与通行距离同时改变；不能把伴随关系说成唯一拓扑因果，不能推广为所有施工地图，也不能证明PPCPP需要区域图或任何新算法。','',
        ('本批确实出现了跨几何的相伴信号，原PPCPP在部分此类结构上的代价值得负责人进一步审查；P2也可能超额，信号本身没有证明可实现的在线改进。' if signal['passed'] else '当前固定信号不足，不能说已证实PPCPP存在需上层决策解决的稳定问题；本方向暂不追加开发投入。'),'', '已封存，待负责人审核。不自动开始下一轮。']
    lines+=['','## 完整种子范围与及时口径补充','',f'两方法桥超额发生账：{supp["bridge_relation"]}。三种子完整指标均值范围.csv给出每状态/方法的每个指标均值、最小、最大和rep0/1/2原值。', '',f'预算内合法路线单独口径：排除迟到ID={supp["timely_view"]["excluded_ids"]}；三种子共同及时的匹配信号={supp["timely_view"]["signal"]}。原P2软截止输出仍全部保留，不偷偷删失。', '', 'example_shortest_path_ledger.json按预定图例的实际首次新采位置和基地列出连接段原步数、独立BFS距离及具体最短路径；仅是相同端点的离线距离账，不是新规划器或完整覆盖最优证明。精确覆盖次序搜索0，普通图BFS不计作覆盖最优搜索。', '', '已封存，待负责人审核。']
    lines+=['', '离线静态检查发现桥表内存tuple与保存JSON list的比较会造成伪差异，封存原bridge_analysis.py保留，bridge_analysis_v02仅在只读比较前做JSON规范化；统计值、规则、求解与输入不变。详细一处diff及边界见离线表示规范化说明.md；只读verify核对后继仅此一处替换。未产生额外规划调用或求解重跑。']
    (H/'诊断结果报告.md').write_text('\n'.join(lines),encoding='utf8')
    save(H/'call_ledger.json',dict(history_preparation=6,gates=12,formal=432,total_real_entries=450,exact_search=0,extra_retries=0,holdout=0))
    (H/'review_packet.md').write_text('# 审核入口\n\n先看诊断结果报告.md，再看protocol.md、封存实现补充.md、matching_review.json、analysis.json/matched和signal、fixed_examples.json及figures；原始inputs/outputs/prep_outputs/actual_order保留。逐桥和分组进出账在route_cuts，结构审查在structure。两个阶段封存与manifest可追溯。\n\n只读复核：运行环境/python/python.exe -B -X utf8 本目录/bridge_verify.py；不调用规划器或精确搜索。verify.log不进入自指manifest，记录实际核验输出。无失败生成/正式失败时仍保存空失败列表。\n\n已封存，待负责人审核。\n',encoding='utf8')
    save(H/'generation_failure_index.json',read(H/'stage_A.json')['failed'])
    print('REPORT WRITTEN; final manifest follows artifact rendering; signal',signal,flush=True)
if __name__=='__main__':report()
