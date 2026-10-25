from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction
import json,csv,statistics,math
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def md(n,x):(H/n).write_text(x,encoding='utf8')
def pct(xs):return sorted(xs)[math.ceil(.95*len(xs))-1] if xs else None
def main():
    plan=read(H/'plan.json');status=read(H/'status.json');entries=[];allcounts=Counter();stop=status['failure'];success=set(status['completed']);allrows=[]
    for j in plan['technical']+plan['formal']:
        p=H/'outputs'/(j['id']+'.json')
        if not p.exists():continue
        x=read(p);r=x['post'];t=x['timing'];row={'id':j['id'],'case':j['case'],'seed':j['seed'],'rep':j['rep'],'phase':j['phase'],'method':j['method'],'original_distance':r['L4'],'shortcut_distance':r['Lshortcut_display'],'shortcut_lower':r['Lshortcut_interval'][0],'shortcut_upper':r['Lshortcut_interval'][1],'original_seconds':t['original_seconds'],'post_increment_seconds':t['post_increment_seconds'],'pipeline_seconds':t['pipeline_seconds'],'post_ms':1000*t['post_increment_seconds'],'saved_distance':r['saving_display'],'reduction_ratio':r['saving_ratio_display'],'time_multiplier':t['pipeline_seconds']/t['original_seconds'],'original_status':t['original_status'],'termination':t['termination'],'original_late':t['original_late'],'post_late':t['post_late'],'actual_order_changed':r['actual_order_changed'],'fallback':r['fallback'],'cold_import_seconds':x['cold_import_seconds'],'independent_audit_seconds':x['audit']['seconds'],'original_turns':r['turns_original']['nonzero_direction_changes'],'shortcut_turns':r['turns_new']['nonzero_direction_changes'],'original_total_angle':r['turns_original']['total_turn_radians'],'shortcut_total_angle':r['turns_new']['total_turn_radians']};allrows.append(row)
        allcounts.update(r['counts']);allcounts['independent_geometry']+=x['audit']['counts']['geometry'];allcounts['independent_service_intersections']+=x['audit']['counts']['service_intersections'];allcounts['independent_original_adjacent_edges']+=r['L4']
    rows=[r for r in allrows if r['phase']=='formal'];dump('全部流水线.json',allrows)
    if rows:
        with (H/'正式全表.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    groups=defaultdict(dict)
    for r in rows:groups[(r['case'],r['seed'])][r['method']]=r
    pairrows=[]
    for (case,seed),d in groups.items():
        if len(d)!=2:continue
        b,c=d['PPCPP'],d['P2_MULTI'];lo=Fraction(b['shortcut_lower'])-Fraction(c['shortcut_upper']);hi=Fraction(b['shortcut_upper'])-Fraction(c['shortcut_lower']);sign='longer' if lo>0 else ('shorter' if hi<0 else 'uncertain')
        # Exact equality only for matching saved squared edge length multisets.
        if sign=='uncertain':
            xb=read(H/'outputs'/(b['id']+'.json'))['post'];xc=read(H/'outputs'/(c['id']+'.json'))['post'];sq=lambda x:Counter((e['b'][0]-e['a'][0])**2+(e['b'][1]-e['a'][1])**2 for e in x['edges'])
            if sq(xb)==sq(xc):sign='equal'
        pairrows.append({'case':case,'seed':seed,'B_distance':b['shortcut_distance'],'C_distance':c['shortcut_distance'],'extra_distance':b['shortcut_distance']-c['shortcut_distance'],'extra_distance_ratio':(b['shortcut_distance']-c['shortcut_distance'])/c['shortcut_distance'] if c['shortcut_distance'] else None,'B_seconds':b['pipeline_seconds'],'C_seconds':c['pipeline_seconds'],'saved_seconds':c['pipeline_seconds']-b['pipeline_seconds'],'speed_ratio':c['pipeline_seconds']/b['pipeline_seconds'] if b['pipeline_seconds'] else None,'time_saved_ratio':1-b['pipeline_seconds']/c['pipeline_seconds'] if c['pipeline_seconds'] else None,'difference_lower':str(lo),'difference_upper':str(hi),'interval_sign':sign})
    dump('同状态同seed配对.json',pairrows);states=[]
    for case in sorted({p['case'] for p in pairrows}):
        ps=[p for p in pairrows if p['case']==case];assert len(ps)==3,'partial state cannot enter success means';a={k:statistics.mean(p[k] for p in ps) for k in ('extra_distance','extra_distance_ratio','saved_seconds','speed_ratio','time_saved_ratio','B_distance','C_distance','B_seconds','C_seconds')};signs=[p['interval_sign'] for p in ps];sl=sum(Fraction(p['difference_lower']) for p in ps);su=sum(Fraction(p['difference_upper']) for p in ps);state_sign='longer' if sl>0 else ('shorter' if su<0 else ('equal' if all(v=='equal' for v in signs) else 'uncertain'));a.update(case=case,seed_count=3,sign=state_sign);states.append(a)
    dump('54状态等权视图.json',states);summary={}
    for m in ('PPCPP','P2_MULTI'):
        rr=[r for r in rows if r['method']==m]
        if not rr:continue
        old=sum(r['original_distance'] for r in rr);new=sum(r['shortcut_distance'] for r in rr);summary[m]={'n':len(rr),'original_total_distance':old,'shortcut_total_distance':new,'distance_reduction_weighted':1-new/old,'post_ms_median':statistics.median(r['post_ms'] for r in rr),'post_ms_p95':pct([r['post_ms'] for r in rr]),'original_seconds_median':statistics.median(r['original_seconds'] for r in rr),'original_seconds_p95':pct([r['original_seconds'] for r in rr]),'original_seconds_max':max(r['original_seconds'] for r in rr),'mean_time_multiplier':statistics.mean(r['time_multiplier'] for r in rr),'reliability_denominator':162,'complete_valid':len(rr),'resource_satisfied':len(rr),'pipeline_seconds_median':statistics.median(r['pipeline_seconds'] for r in rr),'pipeline_seconds_p95':pct([r['pipeline_seconds'] for r in rr]),'pipeline_seconds_max':max(r['pipeline_seconds'] for r in rr),'natural_finished':sum(r['termination']=='natural' for r in rr),'budget_hit':sum(r['termination']=='budget' for r in rr),'original_late':sum(r['original_late'] for r in rr),'post_late':sum(r['post_late'] for r in rr),'order_changed':sum(r['actual_order_changed'] for r in rr),'fallback':sum(r['fallback'] is not None for r in rr)}
    if states:
        summary['B_vs_C']={'states':len(states),'state_equal_mean_extra_distance_ratio':statistics.mean(s['extra_distance_ratio'] for s in states),'state_equal_mean_saved_seconds':statistics.mean(s['saved_seconds'] for s in states),'state_equal_mean_speed_ratio':statistics.mean(s['speed_ratio'] for s in states),'state_equal_mean_time_saved_ratio':statistics.mean(s['time_saved_ratio'] for s in states),'total_distance_weighted_extra_ratio':sum(p['B_distance'] for p in pairrows)/sum(p['C_distance'] for p in pairrows)-1,'state_signs':dict(Counter(s['sign'] for s in states)),'worst_extra_distance_ratio':max(p['extra_distance_ratio'] for p in pairrows),'pair_saved_seconds_median':statistics.median(p['saved_seconds'] for p in pairrows),'pair_saved_seconds_p95':pct([p['saved_seconds'] for p in pairrows])}
    dump('summary.json',summary);attempts=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf8').splitlines()];ledger={'planned_technical':12,'planned_formal':324,'started_technical':sum(a['phase']=='technical' for a in attempts),'started_formal':sum(a['phase']=='formal' for a in attempts),'saved_valid_pipelines':len(allrows),'core_entries':len(attempts),'postprocess_returns':len(allrows),'queries_in_successful_pipelines':dict(allcounts),'failure':stop,'unrun':336-len(attempts),'stub_responses':4,'stub_empty_postprocess_returns':2,'stub_geometry_and_service_queries':0,'core_internal_events':'Native P2 events/improvements and PPCPP phase_seconds/branches retained unchanged; one frozen core invocation per planner entry.','audit_queries_in_verify':0};dump('调用账.json',ledger)
    text='# PPCPP直达与充分配置P2：开发集质量—时间比较\n\n'
    text+=f"技术真实12槽、正式324槽；实际开始{len(attempts)}，保存独立审核合法流水线{len(allrows)}。失败{int(stop is not None)}，未运行{336-len(attempts)}。所有结果针对固定54开发状态，三seed不当作独立地图。\n\n"
    for m,s in summary.items():
        if m=='B_vs_C':continue
        text+=f"{m}：正式{s['n']}次；原/直达总距{s['original_total_distance']:.6f}/{s['shortcut_total_distance']:.6f}，减少{100*s['distance_reduction_weighted']:.3f}%；后处理增量中位数{s['post_ms_median']:.3f}ms。原/累计耗时中位数{s['original_seconds_median']:.6f}/{s['pipeline_seconds_median']:.6f}s，累计P95 {s['pipeline_seconds_p95']:.6f}s、最大{s['pipeline_seconds_max']:.6f}s；自然完成{s['natural_finished']}、预算触顶{s['budget_hit']}、原阶段迟到{s['original_late']}、处理阶段迟到{s['post_late']}。\n\n"
    if 'B_vs_C' in summary:
        s=summary['B_vs_C'];text+=f"B对C：先每状态三seed平均，再54状态等权，平均额外路程比例{100*s['state_equal_mean_extra_distance_ratio']:.3f}%，平均节省计算{s['state_equal_mean_saved_seconds']:.6f}s，平均时间倍率{s['state_equal_mean_speed_ratio']:.3f}；按总距离加权的额外路程为{100*s['total_distance_weighted_extra_ratio']:.3f}%。状态较长/等长/较短/未确定：{s['state_signs']}。最坏单次额外路程比{100*s['worst_extra_distance_ratio']:.3f}%。所有负值保留。\n\n"
    text+='A→B包含四邻接到任意方向的模型放宽；B/C同样用冻结直达，P2仍是离散顺序搜索加相同后处理。A/B、C0/C均来自同次流水线，没有拼接历史时间。增量是后处理计算成本；主要速度来源不能全归给直达。时间百分比与路程百分比不相减，也不据此判综合优越或现场实时。P2有限流程自然完成不是收敛/最优，其20秒是搜索保护，后处理另20秒，总流水线不称共同20秒。\n\n'
    text+='冷模块导入逐次单列于全表；进程创建本身未单独测得，不把暖入口时间当完整冷启动时间。独立审计与落盘在主计时外，主入口已含解析、契约、预处理、搜索、主审核、转接口和输出编码。方向变化次数和总角度保存，但不与旧90度转弯直接混比，不推能耗。未修改核心增加中间轨迹，原P2 improvements仅为已有日志描述，不能推最小达到质量时间。\n\n工程效果与算法创新分开；本批不是留出或全局结论。完成或触发停止后封存，不加预算、不调参、不自动启动顺序优化。\n';md('00_通俗报告.md',text)
    md('review_packet.md','''# 审核入口

00_通俗报告.md给目的、绝对量与结论边界；01_终止语义与预登记.md记录P2流程、源码行和阶段预算；plan/preregistration_seal登记完整顺序、seed与P95。outputs保存同一次原输出、新折线、计时、现有核心日志、按原边数生成的审核上限和独立回执。技术入口12、stub4与正式324分开计数。

全部流水线.json/正式全表.csv、同状态同seed配对.json、54状态等权视图.json、summary.json与调用账.json保留分母和负值。独立verify仅核验保存结果及绑定，不重跑规划、后处理或几何；新独立几何查询均保存在每次audit回执并计费。输入与源码哈希每worker检查，新进程清空缓存。冻结算法、旧证据及留出未改，不推送。
''')
    if states:
        im=Image.new('RGB',(1300,850),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);d.text((50,15),'54 development states: each point averages 3 predeclared seeds',fill='black',font=f);xs=[s['C_seconds']-s['B_seconds'] for s in states];ys=[100*(s['B_distance']-s['C_distance'])/s['C_distance'] for s in states];xmin=min(0,min(xs));xmax=max(xs)*1.05 or 1;ymin=min(0,min(ys));ymax=max(ys)*1.1 or 1
        d.line((100,60,100,750,1250,750),fill='black',width=2)
        for s,x,y in zip(states,xs,ys):xx=100+(x-xmin)/(xmax-xmin)*1100;yy=750-(y-ymin)/(ymax-ymin)*650;d.ellipse((xx-4,yy-4,xx+4,yy+4),fill='#176db0')
        for k in range(6):
            x=xmin+(xmax-xmin)*k/5;y=ymin+(ymax-ymin)*k/5;d.text((100+220*k,758),f'{x:.3f}',fill='black',font=f);d.text((20,740-130*k),f'{y:.1f}',fill='black',font=f)
        d.text((420,805),'Actual C - B computation seconds (higher = B faster)',fill='black',font=f);d.text((110,65),'Extra distance B versus C (%)',fill='black',font=f);im.save(H/'质量时间图.png')
    print(json.dumps({'formal_outputs':len(rows),'state_pairs':len(states),'status':'reported saved results only'},ensure_ascii=False))
if __name__=='__main__':main()
