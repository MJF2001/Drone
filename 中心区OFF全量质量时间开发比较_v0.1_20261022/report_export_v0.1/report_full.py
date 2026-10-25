"""Full OFF report from saved evidence only; all production execution is finished."""
from run_full import H,R,ON,CONTROL,C,read,dump,sha
from collections import Counter
from fractions import Fraction
import json,csv,math,statistics,importlib.util
spec=importlib.util.spec_from_file_location('_bound_static_figures',ON/'report_bench_v02.py')
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)

def stats(vals):
    vals=sorted(vals)
    return {'N':len(vals),'mean':statistics.mean(vals) if vals else None,'median':statistics.median(vals) if vals else None,
        'P95':vals[math.ceil(.95*len(vals))-1] if vals else None,'max':max(vals) if vals else None}
def avg(v):return sum(v)/len(v) if v else None
def num(v):return '未定义' if v is None else f'{v:.6f}'
def pct(v):return '未定义' if v is None else f'{v*100:.3f}%'
def export_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        keys=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def scatter(states,path,budget):
    c=V.Canvas(1320,850);c.text((35,20),'OFF全54状态：B相对C的距离与共同端到端时间',27)
    c.text((35,67),'横轴：B比C多走比例；纵轴：C/B耗时倍率（对数）。P2触顶 '+str(budget)+'/162。',20)
    xs=[100*s['B_C_distance_extra'] for s in states];ys=[math.log10(s['C_B_time_ratio']) for s in states]
    xmin,xmax=min(min(xs)-2,-2),max(xs)+2;ymin,ymax=min(min(ys)-.1,0),max(max(ys)+.15,.1)
    def xy(x,y):return 140+(x-xmin)/(xmax-xmin)*1040,700-(y-ymin)/(ymax-ymin)*550
    c.line([(140,150),(140,700),(1180,700)],'#4a596e',2)
    for k in range(6):
        x=xmin+(xmax-xmin)*k/5;sx,sy=xy(x,ymin);c.line([(sx,150),(sx,700)],'#dce4ed',1);c.text((sx-20,715),f'{x:.1f}%',17)
    for k in range(5):
        y=ymin+(ymax-ymin)*k/4;sx,sy=xy(xmin,y);c.line([(140,sy),(1180,sy)],'#dce4ed',1);c.text((35,sy-12),f'{10**y:.2f}×',17)
    if xmin<=0<=xmax:c.line([xy(0,ymin),xy(0,ymax)],'#b13f3f',2,True)
    if ymin<=0<=ymax:c.line([xy(xmin,0),xy(xmax,0)],'#b13f3f',2,True)
    colors={'small':'#2a7d9f','medium':'#8c61b0','large':'#c87935'}
    for s in states:c.circle(xy(100*s['B_C_distance_extra'],math.log10(s['C_B_time_ratio'])),5,colors[s['size']])
    c.text((160,780),'蓝small  紫medium  橙large；状态共享9基础地图及给定历史，不能当54独立实地图。',19)
    c.save(path)

def main(seal=False):
    assert not (H/'final_receipt.json').exists()
    status=read(H/'status.json');plan=read(H/'plan.json');verification=read(H/'verify_receipt.json');assert verification['passed']
    if status['failure'] is not None or len(status['formal_completed'])!=324:
        raise RuntimeError('Batch aborted: use separate partial export without rerunning any entry')
    metadata={x['id']:x for x in read(H/'history_evidence.json')};rows=[];loaded={};entryrows=[];maincounts=Counter();indcounts=Counter();scopes=Counter()
    attempts=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];ended={x['id']:x for x in attempts if x['event']=='ended'}
    for job in plan['formal']:
        file=H/'outputs'/(job['id']+'.json');x=read(file);assert x['passed'];assert x['native_counts_actual'] is None and x['native_observation']['counts'] is None
        t=x['timing'];indcounts.update(x['independent']['counts']);scopes.update(x['query_scope_schema'])
        entryrows.append({'job':job,'output_sha256':sha(file),'timing':t,'entry_ledger':x['entry_ledger'],'native_observation':x['native_observation'],
            'worker_wall_seconds':x['worker_wall_seconds'],'parent_wall_seconds':ended[job['id']]['wall'],'independent_seconds':x['independent_wall_seconds'],'cold_import_seconds':x['cold_import_seconds']})
        for view,record in x['views'].items():
            m=record['metrics'];raw=view in ('A','C0');tm=t['raw_common_end_to_end'] if raw else t['combined_end_to_end']
            row={'case':job['case'],'size':metadata[job['case']]['size'],'event':metadata[job['case']]['event'],'seed':job['seed'],'view':view,'method':job['method'],
                'configuration':'关闭核心详细profile','passed':x['passed'],'termination':t['termination'],'native_status':t['native_status'],'native_detail_status':'not_observed_profile_OFF','native_detailed_counts':None,
                'time_seconds':tm,'native_entry_seconds':t['native_entry_seconds'],'post_increment_seconds':0 if raw else t['post_increment'],
                'post_engine_seconds':0 if raw else t['post_engine_seconds'],'raw_necessary_wrapper_seconds':t['raw_necessary_wrapper_seconds'],
                'post_necessary_wrapper_seconds':0 if raw else t['post_necessary_wrapper_seconds'],
                'native_late':t['native_late'],'raw_stage_late':t['raw_stage_late'],'post_late':False if raw else t['post_late'],
                'combined_late':t['raw_stage_late'] if raw else t['combined_late'],'post_fallback':None if raw else x['post_envelope']['fallback'],**m}
            row.update({f'turns_{k}':m['turns'].get(k,0) for k in ('total','90','180','other')})
            if m['stages']:
                for k in ('to_first_witness','between_first_last_witness','after_last_witness_return'):
                    cert=m['stages'][k];row[k+'_meters']=(float(V.value(cert['low']))+float(V.value(cert['high'])))/2
            rows.append(row);maincounts.update(record['counts']);loaded[(job['case'],job['seed'],view)]={'row':row,'record':record,'input':x['input'],'time':tm,'termination':t['termination']}
    export_csv(H/'正式648视图完整指标.csv',rows);dump(H/'正式逐入口阶段与来源.json',entryrows)
    keys=('A_B_saving','B_C_distance_extra','B_C_time_saving','C_B_time_ratio','B_C_extra_meters','B_C_saved_seconds')
    pairs=[]
    for case in sorted(metadata):
        for seed in (20261020,20261021,20261022):
            data={v:loaded[(case,seed,v)]['row'] for v in ('A','B','C0','C')};a,b,c0,c=[data[v] for v in ('A','B','C0','C')]
            natural=all(data[v]['termination']=='natural' for v in ('B','C'));timely=natural and all(not data[v][k] for v in ('B','C') for k in ('native_late','raw_stage_late','post_late','combined_late'))
            pairs.append({'case':case,'size':metadata[case]['size'],'event':metadata[case]['event'],'seed':seed,'natural_pair':natural,'timely_natural_pair':timely,
                'A_B_saving':(a['length']-b['length'])/a['length'],'B_C_distance_extra':(b['length']-c['length'])/c['length'],
                'B_C_time_saving':(c['time_seconds']-b['time_seconds'])/c['time_seconds'],'C_B_time_ratio':c['time_seconds']/b['time_seconds'],
                'B_C_extra_meters':b['length']-c['length'],'B_C_saved_seconds':c['time_seconds']-b['time_seconds'],
                'A_B_exact_sign':V.compare_cert(a,b),'B_C_exact_sign':V.compare_cert(b,c),'A':a['length'],'B':b['length'],'C0':c0['length'],'C':c['length'],'time_B':b['time_seconds'],'time_C':c['time_seconds']})
    dump(H/'同状态同seed配对.json',pairs)
    def states_of(selection):
        out=[]
        for case in sorted({p['case'] for p in selection}):
            pp=[p for p in selection if p['case']==case];out.append({'case':case,'size':metadata[case]['size'],'event':metadata[case]['event'],'seed_count':len(pp),**{k:avg([p[k] for p in pp]) for k in keys}})
        return out
    states=states_of(pairs);dump(H/'54状态等权结果.json',states)
    def subset(selection):
        ss=states_of(selection)
        return {'pairs':len(selection),'states':len(ss),'excluded_pairs':162-len(selection),'state_equal_means':{k:avg([s[k] for s in ss]) for k in keys},
            'total_distance_A_B_saving':1-sum(p['B'] for p in selection)/sum(p['A'] for p in selection) if selection else None,
            'total_distance_B_C_extra':sum(p['B'] for p in selection)/sum(p['C'] for p in selection)-1 if selection else None,
            'A_B_shorter_equal_longer':[sum(p['A_B_exact_sign']==sign for p in selection) for sign in (1,0,-1)],
            'B_longer_equal_shorter':[sum(p['B_C_exact_sign']==sign for p in selection) for sign in (1,0,-1)],'B_slower_pairs':sum(p['B_C_saved_seconds']<0 for p in selection)}
    subsets={'full':subset(pairs),'natural':subset([p for p in pairs if p['natural_pair']]),'timely_natural':subset([p for p in pairs if p['timely_natural_pair']])}
    dump(H/'自然完成子集与排除.json',{'summaries':subsets,'excluded_natural':[p for p in pairs if not p['natural_pair']],'excluded_timely_natural':[p for p in pairs if not p['timely_natural_pair']],'denominator':'conditional subset averages retained seeds then states; never replaces full batch'})
    strata=[]
    for factor in ('size','event'):
        for value in sorted({s[factor] for s in states}):
            ss=[s for s in states if s[factor]==value];strata.append({'factor':factor,'value':value,'states':len(ss),**{k:avg([s[k] for s in ss]) for k in keys}})
    dump(H/'预定分层.json',strata)
    timefields=('time_seconds','native_entry_seconds','post_increment_seconds','post_engine_seconds','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds')
    timing={v:{**{k:stats([r[k] for r in rows if r['view']==v]) for k in timefields},
        **{k:sum(r[k] for r in rows if r['view']==v) for k in ('native_late','raw_stage_late','post_late','combined_late')},
        'budget':sum(r['termination']=='budget' for r in rows if r['view']==v),'post_fallbacks':dict(Counter(str(r['post_fallback']) for r in rows if r['view']==v))} for v in ('A','B','C0','C')}
    credit={v:{'task_occurrences':sum(r['diagonal_offcenter_first_credit_tasks'] for r in rows if r['view']==v),
        'states':len({r['case'] for r in rows if r['view']==v and r['diagonal_offcenter_first_credit_tasks']}),
        'state_seed_count':sum(r['diagonal_offcenter_first_credit_tasks']>0 for r in rows if r['view']==v),
        'never_center_occurrences':sum(r['never_center_in_whole_actual_history_tasks'] for r in rows if r['view']==v)} for v in ('A','B','C0','C')}
    totals={v:{'total_length':sum(r['length'] for r in rows if r['view']==v),'new_credit':sum(r['new_credit'] for r in rows if r['view']==v),
        'missing':sum(r['missing'] for r in rows if r['view']==v),'returned':sum(r['return_success'] for r in rows if r['view']==v),
        'turns':sum(r['turns_total'] for r in rows if r['view']==v),'touches':sum(r['center_region_touch_events'] for r in rows if r['view']==v),
        'repeated_touches':sum(r['repeated_touch_events'] for r in rows if r['view']==v),'no_new_credit_routes':sum(r['no_new_credit_route'] for r in rows if r['view']==v)} for v in ('A','B','C0','C')}
    comparisons=status['ON_OFF_comparisons'];dump(H/'旧ON与本OFF逐入口来源输出比较.json',comparisons)
    comp_summary={m:{'N':sum(c['method']==m for c in comparisons),'raw_routes_equal':sum(c['method']==m and c['raw_route_equal'] for c in comparisons),
        'post_routes_equal':sum(c['method']==m and c['post_route_equal'] for c in comparisons),'both_natural':sum(c['method']==m and c['both_natural'] for c in comparisons),
        'both_natural_decisions_equal':sum(c['method']==m and c['both_natural'] and c['canonical_decisions_equal'] for c in comparisons),
        'old_ON_budget_new_OFF_natural':sum(c['method']==m and c['old_ON_termination']=='budget' and c['new_OFF_termination']=='natural' for c in comparisons),
        'old_ON_natural_new_OFF_budget':sum(c['method']==m and c['old_ON_termination']=='natural' and c['new_OFF_termination']=='budget' for c in comparisons),
        'classifications':dict(Counter(c['classification'] for c in comparisons if c['method']==m))} for m in ('PPCPP','P2_MULTI')}
    dump(H/'ON_OFF来源差异与比较摘要.json',{'sources':read(H/'bindings.json'),'comparison_summary':comp_summary,'not_same_round_random_control':True,'no_exact_causal_time_attribution':True,'no_six_state_factor_correction':True})
    anomalies=[r for r in rows if r['termination']=='budget' or any(r[k] for k in ('native_late','raw_stage_late','post_late','combined_late'))]
    dump(H/'异常触顶迟到与未运行账.json',{'failure':status['failure'],'not_run':status['not_run'],'entries_or_views':anomalies,'negative_distance_pairs':[p for p in pairs if p['B_C_exact_sign']>0],'B_slower_pairs':[p for p in pairs if p['B_C_saved_seconds']<0]})
    accounts={'formal_entry_calls':324,'PPCPP':162,'P2':162,'technical':0,'warmup':0,'views':648,'post_calls':324,
        'attempts_consuming_slots':sum(e['event']=='started' for e in attempts),'entry_layer':{'started':324,'returned':324,'exceptions':0},
        'native_detail':{'observable':False,'status':'not_observed_profile_OFF','counts':None},'main_virtual_execution':dict(maincounts),'service_scopes':dict(scopes),'independent_actual':dict(indcounts),
        'wall_and_other':{k:stats([e[k] for e in entryrows]) for k in ('worker_wall_seconds','parent_wall_seconds','independent_seconds','cold_import_seconds')},
        'worker_wall_total':sum(e['worker_wall_seconds'] for e in entryrows),'parent_wall_total':sum(e['parent_wall_seconds'] for e in entryrows),
        'pure_prechecks':read(H/'prechecks.json'),'reused_controlled_72_not_rerun_sha256':sha(CONTROL/'final_receipt.json'),
        'final_verify_new_calls':{k:verification[k] for k in ('new_core_calls','new_post_calls','new_geometry_queries')}}
    dump(H/'入口与几何查询总账.json',accounts)
    assert len(rows)==648 and len(pairs)==162 and len(states)==54 and all(s['seed_count']==3 for s in states)
    assert len(comparisons)==324 and not any(c['substantive_difference'] for c in comparisons)
    assert all(r['missing']==0 and r['return_success'] and r['active_coverage']==1 for r in rows)
    summary={'configuration':'关闭核心详细profile配置','formal_calls':324,'technical':0,'warmup':0,'views':648,'subsets':subsets,'timing':timing,'credit':credit,'view_totals':totals,'strata':strata,'ON_OFF_comparison':comp_summary,'failure':None,'unrun':0}
    dump(H/'summary.json',summary)
    figures=H/'figures';figures.mkdir(exist_ok=True);scatter(states,figures/'54状态质量时间',timing['C']['budget']);V.strata_figure(strata,figures/'尺寸事件分层')
    worst=max(pairs,key=lambda p:p['B_C_distance_extra']);V.route_figure(worst,loaded,'OFF质量负例：全批最大B/C距离差（仅展示）',figures/'质量负例路线')
    positive=None;positive_view=None
    for view in ('B','C'):
        positive=next((p for p in pairs if loaded[(p['case'],p['seed'],view)]['record']['metrics']['diagonal_offcenter_first_credit_tasks']),None)
        if positive:positive_view=view;break
    if positive:
        V.route_figure(positive,loaded,'OFF新信用例：'+positive_view+'首条合格记录',figures/'新信用例路线',True)
        V.credit_detail(positive,positive_view,loaded,figures/'新信用局部证据')
    full=subsets['full'];natural=subsets['natural'];sv=full['state_equal_means'];nv=natural['state_equal_means']
    timetable='\n'.join('|'+ '|'.join([v,num(timing[v]['time_seconds']['mean']),num(timing[v]['time_seconds']['median']),num(timing[v]['time_seconds']['P95']),num(timing[v]['time_seconds']['max']),str(timing[v]['budget']),str(timing[v]['native_late']),str(timing[v]['post_late'])])+'|' for v in ('A','B','C0','C'))
    credittable='\n'.join('|'+ '|'.join([v,str(credit[v]['task_occurrences']),str(credit[v]['states']),str(credit[v]['state_seed_count']),str(credit[v]['never_center_occurrences'])])+'|' for v in ('A','B','C0','C'))
    comparetable='\n'.join('|'+ '|'.join([m,str(comp_summary[m]['N']),str(comp_summary[m]['raw_routes_equal']),str(comp_summary[m]['post_routes_equal']),str(comp_summary[m]['both_natural_decisions_equal'])+'/'+str(comp_summary[m]['both_natural']),str(comp_summary[m]['old_ON_budget_new_OFF_natural'])])+'|' for m in ('PPCPP','P2_MULTI'))
    report=f'''# 关闭核心详细profile配置：全量开发比较

本轮8纯门槛首轮通过、准备修复0；**324正式新入口**（PPCPP/P2各162），真实技术/热身0，A/B及C0/C共享核心形成648视图。全部路线通过独立合法性/资源/信用审核，完成当前可检责任并返航，失败/未运行0。到上限停止，不自动追加重复或其他批。

本批准确名称是**关闭核心详细profile配置**，仍包含必要保护、观察、包装和审核，不是零观测或纯算法时间。直接复用已验OFF原函数，只有产物目录重绑定；未改评分、搜索、信用、直达、格心锚点、预算或事件机制。

这是**给定相同外部初始历史的事件后快照比较**：54状态、原3seed、共享9基础地图和历史，输入字节与旧批相同。H有旧公开/自由格心前缀证据，当前collect_here幂等；没有以新区规则重放扩大H，不声称新连续事件收益或54独立真实地图。

## 三个主要问题

1. **相对原PPCPP，直达改善多少？** A→B总距离缩短{pct(full['total_distance_A_B_saving'])}，同seed配对后状态等权平均缩短{pct(sv['A_B_saving'])}；162配对缩短/相等/更长为{full['A_B_shorter_equal_longer']}。
2. **相对P2＋同版直达，距离—时间权衡怎样？** 全批B/C总距离比差{pct(full['total_distance_B_C_extra'])}，状态等权多走{pct(sv['B_C_distance_extra'])}，平均配对多走{num(sv['B_C_extra_meters'])}米，少用{num(sv['B_C_saved_seconds'])}秒共同端到端；状态等权时间节省比例{pct(sv['B_C_time_saving'])}。B更长/相等/更短{full['B_longer_equal_shorter']}，B更慢{full['B_slower_pairs']}组，均保留，不拿两个百分比大小证明综合胜出。
3. **新区判据是否实际利用？** 关键指标是实际执行斜段取得首次信用且整段不含目标格心，不能用偏离格心的见证点替代。B为{credit['B']['task_occurrences']}格次/{credit['B']['states']}状态；C为{credit['C']['task_occurrences']}格次/{credit['C']['states']}状态（格次含seed重复）。原名义锚点保留；全实际历史从未经过格心的任务数见下表，不因首次信用提前而冒称已释放锚点。

|视图|不含格心斜段首次信用格次|状态数/54|状态seed数/162|全历史从未过格心格次|
|---|---:|---:|---:|---:|
{credittable}

{('已有'+positive_view+'例图及保存交区间/内部见证局部放大；不能将C的例子算作B的收益。' if positive else '本批B/C均无符合关键指标的真实返回例；不造图或用纯桩替代。')}

## 完成状态与计时

{('PPCPP和P2全批均完成既定有限流程自然结束；这不等于全局最优或无限搜索收敛。' if timing['A']['budget']==0 and timing['C']['budget']==0 else '仍有触顶返回，全批保留预算参照，不能全部称充分自然完成。')}

P2触顶{timing['C']['budget']}/162；双方成功自然完成子集{natural['pairs']}/162配对、{natural['states']}/54状态，排除{natural['excluded_pairs']}组。其状态等权B/C距离差{pct(nv['B_C_distance_extra'])}、总距离差{pct(natural['total_distance_B_C_extra'])}，平均少用{num(nv['B_C_saved_seconds'])}秒。全部排除ID及自然且及时子集另存，不能用条件子集代全批。

|视图|共同端到端均值s|中位数s|P95s|最大s|预算触顶（共享核心）|原生迟到|post迟到|
|---|---:|---:|---:|---:|---:|---:|---:|
{timetable}

原生20秒保护不提高；直达18秒软停止新候选、4096候选、20秒仅迟到标记，**不是强制20秒中断**；父进程150秒兜底涵盖导入/执行/审核。所有迟到标志均保留。核心有限完成即返回，不空等。

主时间包含同一次原生入口、轻量唯一分派、返回后实际加载源码hash、原/直达路线的必要新区虚拟信用执行/指标/编码与直达。开始前hash及冷导入在外，native_raw/post_raw两次实测证据flush扣除，主必要编码保留；独立审核、完整落盘、进程创建在主计时外，worker/父墙钟、冷导入/审核/flush另列。A/B或C0/C共享核心不能重复求和。原生、raw包装、post engine、post增量、post必要包装和共同端到端的均值/中位数/P95/最大值见summary/CSV，其他费用见逐入口来源与总账。P95为nearest-rank，不事后变阈值。

核心细查询为null/不可观测，不能从空值填0；入口层、主执行、post及独立审核计数分别保留。B.load_native的无任务导入监视和来源校验仍存在，OFF只关闭核心详细profile。四项线程变量1、每入口新进程串行、无跨输入缓存；后台负载和文件冷热不保证消除，本批不是所有部署方式的固有速度。

## 与旧ON逐项对照

|核心|同输入seed入口数|原路线相同|直达路线相同|双方自然且决策相同/双方自然|旧ON触顶→新OFF自然|
|---|---:|---:|---:|---:|---:|
{comparetable}

逐项输入/原路线/直达/终止/规范化决策比较保存，规范化仅去预登记时钟字段，保留奖励trace、阶段状态、passes/swaps与改进记录。双方自然完成却出现未解释确定性记录差异会停批；本轮未触发该条件。预算状态变化导致的可用记录差异单列，不能因OFF路线变化就称算法改进。

旧ON报告原文/距离/信用/合法性和原始数据保留；新增《旧ON报告时间结论限定说明.md》，明确旧时间及触顶/预算下质量属于含详细profile配置。本轮新数据作为当前关闭核心详细profile配置下的全量开发时间参照。新旧不是同轮随机受控对照，不能把跨批耗时差精确全归因profile；没有使用受控六large状态倍率修正任何旧表，也不将旧格心模型数字作模型变化因果。

## 指标口径、图与证据

全部648视图的输入任务/初始已采/可检剩余/暂缓/新增/未完成、覆盖分母、返航终点/资源和完整合法性收据保留。可检覆盖100%不表示遮挡暂缓也完成；公开覆盖分母保留暂缓。总距离欧氏，未完成短路线不作优势。

起点至首次信用、采集间、末次信用后返航采用固定内部见证约定：首次相交实际段严格区间的中点，精确根式与认证区间保留；不冒称唯一物理首次进入时刻。无新增路线另列。触达/重复触达按每段每任务及显式初态动作事件记，依赖折线分段，不是额外飞行成本；无新增信用段长度是整段标签，不是逐点非采集距离。共线正向分段不制造转弯，90/180/其他角度统一统计，采集/等待不算转弯。

![54状态质量时间]({(figures/'54状态质量时间.png').as_posix()})

![尺寸事件分层]({(figures/'尺寸事件分层.png').as_posix()})

![质量负例]({(figures/'质量负例路线.png').as_posix()})

'''+(f"![新信用例]({(figures/'新信用例路线.png').as_posix()})\n\n![新信用局部证据]({(figures/'新信用局部证据.png').as_posix()})\n\n" if positive else '')+'''
按原尺寸/事件分层，先同状态三seed平均再层内状态等权；总距离比与状态等权比并列，不挑最佳层。负例按全批最大B/C距离差固定选择，仅展示不改样本。完整执行路径与信用事件/精确见证、原生返回和直达原文/独立回执、attempt/失败未运行账与源码/输入hash全部保留。

8纯门槛与控制72旧证据只读hash引用分开，不混正式分母。每份独立审核在主计时外实际运行并计费；最终verify只核绑定/已有独立回执，新增核心/后处理/几何0。报告/绘图只读保存数据，不重新求解或区域审核。完成封存、更新根进度后停止交审，不新增留出、地图、seed、预算、连续事件或机制批，不推送。
'''
    (H/'00_通俗全量开发比较报告.md').write_text(report,encoding='utf-8')
    (H/'review_packet.md').write_text('''# OFF全量开发比较 review packet

先读00_通俗全量开发比较报告.md、summary.json、final_receipt.json。配置名称是“关闭核心详细profile”，不是零观察或固有算法耗时。324新正式入口、真实技术/热身0，648视图；旧72受控与旧ON正式不混入。

run_full导入已验控制run_check的原worker，C.H仅路由新产物，生产函数不换。bindings/source_snapshot/01预登记、plan、history_evidence、source_guards和active_freeze保护输入/源码/计时/预算；8纯门槛首轮、0准备修复。控制原final/纯门槛按hash引用，未重跑旧verify。

逐入口outputs保留唯一原生/直达原文、原/直达全路径和虚拟信用见证、资源/几何独立收据及计时/查询账。OFF原生细查询null不可观测；入口、主/post/独立分别记。20秒post为迟到标记，18秒软候选限额4096，父150秒兜底，原生20秒不提高。

正式648指标CSV、同seed配对/状态等权/预定分层、自然完成与及时子集/排除、异常和负例表保留分母。旧ON与本OFF逐入口来源输出比较含原路线/post/终止及完整去时钟可用决策，一旦未解释自然差异则停止。旧ON时间追加限定说明另存，不覆盖原文；新旧非同轮随机受控，不全归因profile、不套用六状态倍率。

最终verify只读绑定与已有独立回执，新核心/后处理/几何0。manifest可核全部产物。独立审核每入口已实际完成、记账；报告绘图不追加算法。当前配置全量开发参照已封存停止，不自动追加批，不称创新或实机验证。
''',encoding='utf-8')
    print(json.dumps({'exported':True,'full':full,'P2_budget':timing['C']['budget'],'credit':credit,'ON_OFF':comp_summary},ensure_ascii=False))
    if not seal:return
    for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest,name
    for name,digest in read(H/'source_guards.json').items():assert sha(name)==digest,name
    root=R/'当前进度与下一步.md';current=root.read_text(encoding='utf-8-sig');(H/'root_pre_finalize.md').write_text(current,encoding='utf-8')
    header=f'''# 最新完成：关闭核心详细profile全54状态开发比较封存（2026-10-22）

中心区OFF全量质量时间开发比较_v0.1_20261022 已完成8纯门槛首轮（准备修复0）、324正式新入口（PPCPP/P2各162），真实技术/热身0，648视图均独立通过并完成可检任务返航，失败/未运行0。先读00_通俗全量开发比较报告.md、summary、review_packet及final_receipt。到上限停止，旧72受控和旧324 ON不混正式。

直接复用控制包已验OFF原worker/轻量唯一入口，仅C.H路由新产物；核心/信用/直达/预算保护不改。完整原54输入字节、原3seed/方法轮换和共同外部H证据保留，当前显式采集幂等、不扩大H；9基础地图，不称54独立实地图或连续事件收益。主计时包含必要包装/返回后来源校验/虚拟执行编码，flush实测扣除，冷导入/开始前hash/独立审核在外、墙钟另存。OFF原生细数null不可观测，非零开销或固有算法时间。原生20秒，post18软/4096/20仅迟到，父150秒。

A→B总距离省{pct(full['total_distance_A_B_saving'])}、状态等权省{pct(sv['A_B_saving'])}。B/C总距离差{pct(full['total_distance_B_C_extra'])}、状态等权多走{pct(sv['B_C_distance_extra'])}，平均少用{num(sv['B_C_saved_seconds'])}秒共同端到端，B更慢{full['B_slower_pairs']}配对保留；不以时间/距离百分比大小证明综合优越。P2触顶{timing['C']['budget']}/162，自然子集{natural['pairs']}/162配对、{natural['states']}/54状态，排除清单保存；有限自然完成不等于最优。

关键斜段不含格心首次信用：B {credit['B']['task_occurrences']}格次/{credit['B']['states']}状态，C {credit['C']['task_occurrences']}格次/{credit['C']['states']}状态；全历史未过格心A/B/C0/C分别{[credit[v]['never_center_occurrences'] for v in ('A','B','C0','C')]}。见证偏离格心不足，锚点未优化，零不追正例。完整转弯/阶段见证/触达事件口径、负例/新信用图、指标/分层/自然子集、所有返回/信用/资源独立证据封存。

旧ON逐入口对照：PPCPP原/直达相同{comp_summary['PPCPP']['raw_routes_equal']}/{comp_summary['PPCPP']['post_routes_equal']}（各162），P2为{comp_summary['P2_MULTI']['raw_routes_equal']}/{comp_summary['P2_MULTI']['post_routes_equal']}；旧ON触顶→OFF自然{comp_summary['P2_MULTI']['old_ON_budget_new_OFF_natural']}，双方自然确定性差异0。旧报告原文保留，时间/预算下质量限定说明另存。新旧非同轮随机受控，不精确全归因profile、不用六状态倍率校正；新数据仅当前OFF配置全量开发参照。

完整预登记/来源输入hash/attempt/异常账、原返回/post/虚拟信用与独立回执、入口/主/post/审核查询总账、只读verify已存。verify新增核心/后处理/几何0，旧文/原始记录不覆盖。封存更新后停止交负责人审核，无额外重复/预算/地图/seed/连续事件/机制/留出或推送。

---
'''
    root.write_text(header+'\n'+current,encoding='utf-8');(H/'root_after.md').write_bytes(root.read_bytes())
    files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','final_receipt.json')};dump(H/'manifest.json',{'files':files})
    dump(H/'final_receipt.json',{'status':'COMPLETE_OFF_FULL_DEVELOPMENT_COMPARISON_SEALED_STOP','passed':True,'formal_new_calls':324,'PPCPP':162,'P2':162,'technical':0,'warmup':0,'views':648,'pure_cases':8,'preparation_repairs':0,
        'failed':0,'unrun':0,'all_covered_and_returned':True,'P2_budget':timing['C']['budget'],'P2_all_finite_process_natural':timing['C']['budget']==0,
        'accepted_OFF_worker_directly_reused':True,'native_detail_unobservable_not_zero':True,'old_batches_unchanged':True,'ON_OFF_comparison':comp_summary,
        'verify_sha256':sha(H/'verify_receipt.json'),'manifest_sha256':sha(H/'manifest.json'),'sealed_files':len(files),'stopped_for_owner_review':True,'no_further_batches_started':True,'seal_new_core_or_geometry_calls':0})
    for name,digest in files.items():assert sha(H/name)==digest,name
    print({'sealed':True,'files':len(files)})

if __name__=='__main__':
    import sys
    main('--seal' in sys.argv)
