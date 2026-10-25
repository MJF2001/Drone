"""Read saved evidence only. No planner, post selection, or geometry invocations."""
from run_check import H,R,OLD,read,dump,sha,canonical
from collections import Counter
from pathlib import Path
import json,math,statistics,csv,importlib.util

def stats(vals):
    vals=sorted(vals)
    return {'N':len(vals),'median':statistics.median(vals) if vals else None,'min':min(vals) if vals else None,'max':max(vals) if vals else None,'mean':statistics.mean(vals) if vals else None}

def textnum(v):return '—' if v is None else f'{v:.6f}'
def range_text(s):return '—' if not s['N'] else f"{s['median']:.6f} [{s['min']:.6f}, {s['max']:.6f}]"

def export_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        keys=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})

def figure(groups,path):
    # Only imports the existing static drawing helpers; its main is guarded.
    spec=importlib.util.spec_from_file_location('_saved_static_report',OLD/'report_bench_v02.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    c=m.Canvas(1550,1050);c.text((35,20),'六固定状态：原生入口ON/OFF三重复中位数与范围',28)
    c.text((35,66),'横轴为秒、对数刻度；橙ON、蓝OFF；触顶行不当作同工作量加速比。',21)
    c.text((35,105),'全部为字典序选出的large状态；点为三重复中位数，线为最小/最大。',20)
    def plotx(t):return 395+760*(math.log10(t)-math.log10(.002))/(math.log10(25)-math.log10(.002))
    for t in (.005,.02,.1,.5,2,10,20):c.line([(plotx(t),145),(plotx(t),945)],'#e0e5ec',1)
    for index,group in enumerate(groups):
        y=160+index*65;label=group['case'].replace('large_','')+' / '+group['method'].replace('_MULTI','')
        c.text((35,y),label,18)
        for config,offset,col in (('ON',0,'#bd7540'),('OFF',20,'#287ea5')):
            s=group['configurations'][config]['native_entry_seconds']
            if not s['N']:continue
            c.line([(plotx(s['min']),y+offset+8),(plotx(s['max']),y+offset+8)],col,3)
            c.circle((plotx(s['median']),y+offset+8),5,col,col)
            c.text((1200,y+offset-5),config+' '+textnum(s['median'])+' s',18)
    c.line([(395,965),(1180,965)],'#374458',2)
    for s in (.005,.02,.1,.5,2,10,20):
        x=plotx(s);c.line([(x,957),(x,973)],'#374458',2);c.text((x-10,980),str(s),18)
    c.save(path)

def main(seal=False):
    assert not (H/'final_receipt.json').exists()
    status=read(H/'status.json');verify=read(H/'verify_receipt.json');assert verify['passed']
    plan=read(H/'plan.json');selection=read(H/'selection.json');strata={x['id']:x['stratum'] for x in selection['selected']}
    eventrows=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
    starts=[x for x in eventrows if x['event']=='started'];ends={x['id']:x for x in eventrows if x['event']=='ended'}
    saved={};rows=[];main_counts={c:Counter() for c in ('ON','OFF')};independent={c:Counter() for c in ('ON','OFF')};service={c:Counter() for c in ('ON','OFF')};native_ON=Counter()
    for ident in status['completed']:
        x=read(H/'outputs'/(ident+'.json'));assert x['passed'] and x['independent']['passed'];j=x['job'];saved[ident]=x;t=x['timing'];cfg=j['config']
        v=x['views']['B' if j['method']=='PPCPP' else 'C'];rawv=x['views']['A' if j['method']=='PPCPP' else 'C0']
        row={**j,**t,'old_stratum':strata[j['case']],'worker_wall_seconds':x['worker_wall_seconds'],'parent_wall_seconds':ends[ident]['wall'],
             'cold_import_seconds':x['cold_import_seconds'],'independent_seconds':x['independent_wall_seconds'],'raw_length':rawv['metrics']['length'],
             'post_length':v['metrics']['length'],'post_diagonal_offcenter_first_credit_tasks':v['metrics']['diagonal_offcenter_first_credit_tasks'],
             'post_fallback':x['post_envelope']['fallback'],'new_credit':v['metrics']['new_credit'],'missing':v['metrics']['missing'],'returned':v['metrics']['return_success'],
             'native_detailed_observable':x['native_observation']['observable'],'native_detailed_counts':x['native_observation']['counts'],'entry_ledger':x['entry_ledger']}
        rows.append(row)
        for record in x['views'].values():main_counts[cfg].update(record['counts'])
        independent[cfg].update(x['independent']['counts']);service[cfg].update(x['query_scope_schema'])
        if cfg=='ON':native_ON.update(x['native_counts_actual'])
    export_csv(H/'全部受控入口阶段计时与结果.csv',rows)
    pairs=[]
    for p in status['pairs']:
        on=saved[p['ON']];off=saved[p['OFF']];ta=on['timing'];tb=off['timing'];eligible=p['same_recorded_work_eligible']
        def work(raw):
            events=raw.get('events',[])
            return {'status':raw['status'],'active_stage':raw.get('active_stage'),'core_finished':raw.get('core_finished'),
                    'event_count':len(events),'passes':sum(e.get('passes',0) for e in events),'swaps':sum(e.get('swaps',0) for e in events),
                    'stage_statuses':[{k:e[k] for k in ('stage','status','passes','swaps','termination') if k in e} for e in events],
                    'improvements_without_clocks':canonical(raw.get('improvements',[])),
                    'PPCPP_trace_length':len(raw.get('trace',[])),'source':raw.get('source',raw.get('selected'))}
        pairs.append({**p,'old_stratum':strata[p['case']],'ON_recorded_work':work(on['native']['raw']),'OFF_recorded_work':work(off['native']['raw']),
            'ON_native':ta['native_entry_seconds'],'OFF_native':tb['native_entry_seconds'],
            'ON_common':ta['combined_end_to_end'],'OFF_common':tb['combined_end_to_end'],
            'same_work_native_ON_OFF_ratio':ta['native_entry_seconds']/tb['native_entry_seconds'] if eligible else None,
            'same_work_native_extra_seconds':ta['native_entry_seconds']-tb['native_entry_seconds'] if eligible else None,
            'same_work_common_ON_OFF_ratio':ta['combined_end_to_end']/tb['combined_end_to_end'] if eligible else None,
            'ON_raw_steps':len(on['native']['raw']['route'])-1,'OFF_raw_steps':len(off['native']['raw']['route'])-1,
            'ON_post_length':on['views']['B' if p['method']=='PPCPP' else 'C']['metrics']['length'],
            'OFF_post_length':off['views']['B' if p['method']=='PPCPP' else 'C']['metrics']['length'],
            'ON_native_canonical_sha256':__import__('hashlib').sha256(json.dumps(canonical(on['native']['raw']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'OFF_native_canonical_sha256':__import__('hashlib').sha256(json.dumps(canonical(off['native']['raw']),sort_keys=True,separators=(',',':')).encode()).hexdigest()})
    dump(H/'同状态seed重复ON_OFF完整配对.json',pairs);export_csv(H/'ON_OFF配对表.csv',pairs)
    timekeys=('native_entry_seconds','raw_common_end_to_end','post_engine_seconds','post_increment','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds','combined_end_to_end','artifact_flush_excluded_seconds','independent_seconds','worker_wall_seconds','parent_wall_seconds','cold_import_seconds')
    groups=[]
    for case in sorted(strata):
        for method in ('PPCPP','P2_MULTI'):
            pp=[p for p in pairs if p['case']==case and p['method']==method];configurations={}
            for config in ('ON','OFF'):
                rr=[r for r in rows if r['case']==case and r['method']==method and r['config']==config]
                configurations[config]={'N':len(rr),**{k:stats([r[k] for r in rr]) for k in timekeys},'natural':sum(r['termination']=='natural' for r in rr),'budget':sum(r['termination']=='budget' for r in rr),
                    'native_late':sum(r['native_late'] for r in rr),'raw_stage_late':sum(r['raw_stage_late'] for r in rr),'post_late':sum(r['post_late'] for r in rr),'combined_late':sum(r['combined_late'] for r in rr),
                    'post_fallback':dict(Counter(str(r['post_fallback']) for r in rr)),'raw_length':stats([r['raw_length'] for r in rr]),'post_length':stats([r['post_length'] for r in rr])}
            groups.append({'case':case,'method':method,'old_stratum':strata[case],'configurations':configurations,'paired':len(pp),
                'same_work_pairs':sum(p['same_recorded_work_eligible'] for p in pp),'raw_routes_equal':sum(p['raw_route_equal'] for p in pp),'post_routes_equal':sum(p['post_vertices_equal'] for p in pp),
                'same_work_native_ratio':stats([p['same_work_native_ON_OFF_ratio'] for p in pp if p['same_recorded_work_eligible']]),
                'same_work_common_ratio':stats([p['same_work_common_ON_OFF_ratio'] for p in pp if p['same_recorded_work_eligible']])})
    dump(H/'三重复中位数范围与配置比较.json',groups)
    summaries={}
    for method in ('PPCPP','P2_MULTI'):
        pp=[p for p in pairs if p['method']==method];rr=[r for r in rows if r['method']==method];eligible=[p for p in pp if p['same_recorded_work_eligible']]
        summaries[method]={'pairs':len(pp),'same_recorded_work_pairs':len(eligible),'raw_route_equal':sum(p['raw_route_equal'] for p in pp),'post_route_equal':sum(p['post_vertices_equal'] for p in pp),
            'same_recorded_work_native_ratio':stats([p['same_work_native_ON_OFF_ratio'] for p in eligible]),
            'same_recorded_work_all_ON_slower':bool(eligible) and all(p['ON_native']>p['OFF_native'] for p in eligible),
            'ON_natural':sum(r['config']=='ON' and r['termination']=='natural' for r in rr),'OFF_natural':sum(r['config']=='OFF' and r['termination']=='natural' for r in rr),
            'ON_budget_OFF_natural':sum(p['ON_termination']=='budget' and p['OFF_termination']=='natural' for p in pp),
            'OFF_budget_ON_natural':sum(p['OFF_termination']=='budget' and p['ON_termination']=='natural' for p in pp),
            'both_budget':sum(p['ON_termination']==p['OFF_termination']=='budget' for p in pp),
            'classifications':dict(Counter(p['classification'] for p in pp))}
    exceptions=[r for r in rows if any(r[k] for k in ('native_late','raw_stage_late','post_late','combined_late')) or r['termination']=='budget']
    dump(H/'所有迟到触顶异常与未运行.json',{'failure':status['failure'],'not_run':status['not_run'],'budget_or_late_entries':exceptions,'unexpected_pairs':[p for p in pairs if p['unexpected_mechanism_difference']]})
    accounts={'attempts_consuming_slots':len(starts),'completed_entries':len(rows),'real_warmup_or_technical_entries':0,
        'entry_layer_dispatched':sum(x['entry_ledger']['started'] for x in saved.values()),'entry_layer_returned':sum(x['entry_ledger']['returned'] for x in saved.values()),
        'ON_native_detail_observed':dict(native_ON),'OFF_native_detail':{'status':'unobservable','counts':None,'entries':sum(r['config']=='OFF' for r in rows)},
        'main_virtual_execution':{k:dict(v) for k,v in main_counts.items()},'post_and_main_service_scopes':{k:dict(v) for k,v in service.items()},'independent_saved_receipts':{k:dict(v) for k,v in independent.items()},
        'pure_prechecks':read(H/'prechecks.json'),'final_read_only_verify_new_calls':{k:verify[k] for k in ('new_core_calls','new_post_calls','new_geometry_queries')},
        'parent_wall_total':sum(x['wall'] for x in ends.values()),'worker_wall_total':sum(r['worker_wall_seconds'] for r in rows),'failure_retained':status['failure']}
    dump(H/'入口与查询总账.json',accounts)
    result={'attempted':len(starts),'completed':len(rows),'planned':len(plan['jobs']),'failure':status['failure'],'unrun':len(status['not_run']),'pairs':len(pairs),'summary_by_core':summaries,
        'same_recorded_work_definition':plan['same_work'],'old_batch_unchanged':True,'new_full54_batch_started':False,'holdout_used':False,'all_successful_outputs_covered_and_returned':all(r['missing']==0 and r['returned'] for r in rows)}
    result['worth_discussing_clean_full_batch']=summaries['P2_MULTI']['ON_budget_OFF_natural']>0
    result['report_export_revision']='v0.2; first report and linear-scale figure retained in report_export_v0.1; log axis and saved work summaries added without new experiments'
    assert result['summary_by_core']==read(H/'report_export_v0.1/summary.json')['summary_by_core']
    dump(H/'summary.json',result)
    figdir=H/'figures';figdir.mkdir(exist_ok=True);figure(groups,figdir/'六状态ON_OFF原生时间')
    lines=[]
    for g in groups:
        a,b=g['configurations']['ON'],g['configurations']['OFF'];lines.append('|'+ '|'.join([g['case'],g['method'],range_text(a['native_entry_seconds']),range_text(b['native_entry_seconds']),f"{a['natural']}/{a['N']}；{b['natural']}/{b['N']}",str(g['same_work_pairs'])+'/'+str(g['paired']),range_text(g['same_work_native_ratio'])])+'|')
    pp=summaries['PPCPP'];p2=summaries['P2_MULTI'];iscomplete=status['failure'] is None and len(rows)==len(plan['jobs'])
    report=f'''# 计时插桩影响受控核查

本轮{'完成' if iscomplete else '中止并保留'} {len(rows)}/{len(plan['jobs'])}次受控入口，消耗槽位{len(starts)}，真实技术/热身0；8纯案例首轮通过、准备修复0。每入口同时保留原返回和同版直达，成功返回均独立审核、覆盖当前可检责任并返航。旧324批和全部历史文件未修改。失败：{status['failure']}；未运行{len(status['not_run'])}。完成后停止，不自动扩大批次。

## 三个问题的回答

**详细观察是否明显扰动时间？** 同状态/原seed/重复中，两边自然完成、去除时钟后完整原生返回及可用决策记录相同的PPCPP配对{pp['same_recorded_work_pairs']}组，ON/OFF原生耗时比中位数/范围为{range_text(pp['same_recorded_work_native_ratio'])}，全部ON更慢={pp['same_recorded_work_all_ON_slower']}。P2相应配对{p2['same_recorded_work_pairs']}组，比值为{range_text(p2['same_recorded_work_native_ratio'])}，全部ON更慢={p2['same_recorded_work_all_ON_slower']}。这是本机这些固定配置和可用记录支持的观测开销证据；OFF逐函数/图查询数没有观测，不能宣称这些细节也被实测为相等。各状态三重复中位数与完整范围见下表，不挑最快值。

本轮答案是：**详细profile在这六固定状态上明显扰动了原生耗时**。合格配对的完整记录相同，原生比值范围分别约3.99–8.22和17.10–19.27，且全部ON更慢；这里的比值仅属于合格配对，不把9组预算行为变化的20秒比值混入。

**P2截止结果是否改变？** P2共{p2['pairs']}组配对，ON自然完成{p2['ON_natural']}，OFF自然完成{p2['OFF_natural']}；ON触顶/OFF自然完成{p2['ON_budget_OFF_natural']}组，OFF触顶/ON自然完成{p2['OFF_budget_ON_natural']}组，双触顶{p2['both_budget']}组。预算状态不同的耗时比被留空，不能解释成同工作量加速。原路径相同{p2['raw_route_equal']}/{p2['pairs']}，直达路径相同{p2['post_route_equal']}/{p2['pairs']}；差异按原截止/自然状态、阶段/passes/swaps/source/改进记录逐项保存，不把OFF路线变化当算法改进。两边自然完成而决策不一致或相同原路径无post时间截断却产生不同post路线会立即停批；本轮实质异常见原始failure及所有迟到触顶异常与未运行.json。

**旧报告哪些时间结论需限定、是否值得另议干净计时全批？** 上批仍是含详细profile的配置测量，原距离/合法性/信用证据保留；时间倍率、平均节省秒数、P2触顶率及相应预算下的距离质量只能按该配置解释，不能当无插桩算法固有耗时或用来给全54状态校正。**值得负责人另议干净计时全批协议**：本轮同时看到稳定同记录工作量开销和9组P2截止状态变化；本轮不启动该全批、不改旧表。关闭详细观察不构成新覆盖算法，不据此宣称创新。

本轮全部36组配对原路径及直达路径都相同，未观察到路线缩短。P2的9组ON触顶/OFF自然完成依然不能算同工作量：即使best路线相同，ON阶段/迭代记录已被截止截断，OFF走完既定有限流程；逐组ON_recorded_work/OFF_recorded_work保存stage/status/passes/swaps和改进记录，不以路径相同代替工作量相同。

## 受控表（秒，比值行无单位）

每格为三重复中位数 [最小, 最大]；同记录工作量比值只基于两边自然完成且完整规范化raw一致的配对。全部六状态由字典序规则选出，恰好都为large；不是跨尺寸代表样本。

|状态|核心|ON原生秒|OFF原生秒|自然完成ON；OFF|同记录工作量配对|合格配对原生ON/OFF比|
|---|---|---:|---:|---|---:|---:|
{chr(10).join(lines)}

![六状态ON/OFF时间]({(figdir/'六状态ON_OFF原生时间.png').as_posix()})

## 公平性、计时和结论边界

ON直接调用上批NativeObserver原类/profile原函数；OFF仅关闭核心详细profile。原核心合同、20秒截止、几何/候选审核、PPCPP分支及P2有限多初值/2-opt搜索不变，中心区service和直达engine/审核同一对象同hash。源码阶段A证明原生内部不调用中心区服务，实际中心区评估在原生返回后。不能用旧包与新包耗时相减预设插桩或中心区因果；本轮ON/OFF共用全部包装，构成有限受控差异。

原观察器附带的一次核心调用断言在OFF由两配置共同的轻量独占入口令牌替代，拒绝重复分派并在异常后移除profile，不重写原生/直达时钟。ON内部细计数保留，OFF明确null/不可观测，只有入口层账可直接计数；主执行、后处理、独立信用审核查询仍分别保存。冷导入的无任务profile监视两配置都保留在主时间外，因此OFF不是关闭所有保护或所有观察器。

主时间包含原生（含ON profile和两边相同分派）、返回后实际加载源码hash、必要原路径/新折线虚拟信用和编码、直达；开始前hash/冷导入在外。原证据两次实测flush从主时扣除，独立审核、完整落盘、进程创建在外但另记墙钟。直达18秒软截止/4096候选；原total20秒只标记迟到，不是强制中断，父进程150秒兜底。没有提高原生20秒或放松审核。原生、post engine、post增量、raw/post必要包装、共同端到端、审核、flush、worker/父墙钟的逐入口与三重复完整统计均已保存；必要包装是现有边界的可复核差值，不把hash等费用凭空删除。

线程口径的只读补充见03_阶段A线程口径只读补充.md：旧格心质量时间run只显式设OMP/OPENBLAS/MKL三项1，NUMEXPR继承未明；阶段A“相同原则”不表示四项逐字一致。本轮ON/OFF四项均明确为1，没有该组间差异。

同工作量判据是同完整有限流程自然完成且规范化raw全部相同；删除的只有预登记时钟字段，passes/swaps/阶段终止/路线/奖励trace等全部保留。OFF没有细查询观察，摘要一致不能替代无限粒度的执行证明。预算截断返回可能在时间检查边界产生路线或已完成工作量差异，必须结合预算状态解释；双触顶不能估完整成本。重复只描述本机波动，有限六状态不能外推全54、更不能将旧时间除平均倍率；系统后台负载未保证清零。

## 证据入口

01_阶段A源码与计时边界审查.md、02_保护等价与完整预登记.md、selection/plan/environment/source_guards和worker_diff.patch保存真实前协议。prechecks/active_freeze/attempts/status、outputs的原返回/post/完整虚拟信用事件/独立回执逐入口保存。全部受控入口阶段计时与结果.csv、ON_OFF配对表.csv、同状态seed重复ON_OFF完整配对.json、三重复中位数范围与配置比较.json保持分母。入口与查询总账.json分别记ON细查询、OFF不可观测、实际主/post/独立查询及纯门槛；所有异常/迟到/未运行保留。

最终verify只核绑定、保存输出及已有独立回执，新增核心/后处理/几何0。报告生成只读保存数据，不再求解/求交。阶段A和纯门槛不混作真实实验，受控重复不混入旧正式324批；留出、地图、seed、机制均未扩充。封存更新根进度后停止交负责人审核。

报告导出v0.2只改展示与解释：首版线性轴使PPCPP短时间范围难辨，改为明确标注的对数轴，并从已有返回补充工作量摘要及本轮明确判断。首版全部导出和脚本保留report_export_v0.1；未改任何实验源码/返回/计时/审核，新增核心/后处理/区域查询0。
'''
    (H/'00_通俗计时核查报告.md').write_text(report,encoding='utf-8')
    (H/'review_packet.md').write_text('''# 计时核查 review packet

先读00_通俗计时核查报告.md、summary.json及final_receipt.json。本轮是6固定状态×2核心×ON/OFF×3重复的最多72入口，不是旧54全批重跑。先看阶段A实际profile覆盖及20秒post只标记迟到的边界，再看保护等价预登记、selection/plan/worker_diff和freeze。

ON用旧原类原profile，OFF细查询null，不伪造0；两配置同一次轻量入口分派、同原生和post保护、同源相同服务/独立审核。所有attempt占槽，失败不补跑。outputs保存所有原返回、可用决策、完整直达/虚拟执行及独立收据。配对表中预算状态变化没有同工作量倍率；只有两边自然完成且去时钟raw一致才给合格倍率。OFF逐函数查询仍不可观测。

三重复表含所有阶段中位数/范围；异常表保留触顶、迟到、实质失败与未运行。查询总账把ON详细、OFF缺观察、共同主/post/独立和纯桩分开。verify_receipt只读绑定已有回执，新算法/后处理/几何0；manifest可复核全部文件。不校正旧54表，不据关闭计数后的路线变化称算法改进。旧合法性和距离证据保留，旧时间及预算结果限定在含profile配置。停止交审，未启动干净计时全批或留出。

当前报告导出v0.2用对数轴呈现三重复范围，并补可用工作摘要；初次线性图/报告保留report_export_v0.1。仅从原保存结果生成，未再做算法或区域审核。
''',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    if not seal:return
    for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest,name
    for name,digest in read(H/'source_guards.json').items():assert sha(name)==digest,name
    root=R/'当前进度与下一步.md';current=root.read_text(encoding='utf-8-sig');(H/'root_pre_finalize.md').write_text(current,encoding='utf-8')
    header=f'''# 最新完成：中心区详细计时插桩受控核查封存（2026-10-22）

中心区计时插桩影响核查_v0.1_20261022 已{'完成' if iscomplete else '中止'}{len(rows)}/{len(plan['jobs'])}真实入口，attempt消耗{len(starts)}，技术/热身0，8纯门槛首轮通过、准备修复0。先看00_通俗计时核查报告.md、阶段A源码/实际时间边界、保护等价预登记、summary/review_packet/final_receipt。旧324批和历史原样保留。

按旧P2状态字典序选3曾触顶/3三seed自然完成状态，最小原seed20261020；规则得到的六状态均large，不能当跨尺度代表。PPCPP/P2×ON/OFF×3重复，先后固定交替，新进程/四线程变量1。ON复用原profile；OFF只停详细profile、细查询null不可观测，原预算/合同/合法性/直达/独立审核保持，轻量一次入口保护两配置相同。原post20秒只有迟到标志，非强制中断，已披露。

PPCPP合格同记录工作量{pp['same_recorded_work_pairs']}配对，原生ON/OFF比中位/范围{range_text(pp['same_recorded_work_native_ratio'])}；P2合格{p2['same_recorded_work_pairs']}配对，比{range_text(p2['same_recorded_work_native_ratio'])}。P2自然完成ON{p2['ON_natural']}/OFF{p2['OFF_natural']}，ON触顶OFF自然{p2['ON_budget_OFF_natural']}配对；预算行为变化不算同工作量加速。原路径相同{p2['raw_route_equal']}/{p2['pairs']}，直达相同{p2['post_route_equal']}/{p2['pairs']}，完整工作/阶段/路线、异常和三重复范围保存。failure={status['failure']}，未运行{len(status['not_run'])}。

旧合法性/距离证据保留；旧时间与截止及预算下质量仅代表含profile配置，不是无插桩固有耗时。返回后来源hash仍在共同包装，flush按实测扣除，独立审核在外、全墙钟另列。有限六状态不能校正54，不将旧表除平均倍率；是否另议干净全批交负责人审核，本轮未自动启动。完整来源hash/差异/预登记/attempt/raw/post/执行信用/独立回执/查询总账与只读verify封存；verify新增核心/后处理/几何0。更新后停止，无留出、新地图/seed/机制或推送。

本轮27组合格配对均ON更慢，证实详细profile在这些状态上明显扰动原生耗时；9组P2从触顶转自然完成，但全部36组原/直达路线相同，没有路线改进。值得另议干净全批，仍须负责人另定协议；本轮不做全54倍率校正。报告导出v0.2仅改对数轴/补已有工作摘要，首版完整保留。

---
'''
    root.write_text(header+'\n'+current,encoding='utf-8');(H/'root_after.md').write_bytes(root.read_bytes())
    files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','final_receipt.json')};dump(H/'manifest.json',{'files':files})
    dump(H/'final_receipt.json',{'status':'COMPLETE_CONTROLLED_PROFILE_CHECK_SEALED_STOP' if iscomplete else 'ABORTED_CONTROLLED_PROFILE_CHECK_SEALED_STOP','passed':iscomplete,'attempted_slots':len(starts),'completed_entries':len(rows),'planned':len(plan['jobs']),'core_cap':72,
        'technical_or_warmup_entries':0,'pure_cases':8,'preparation_repairs':0,'failure_retained':status['failure'],'unrun':len(status['not_run']),'native_OFF_detail_unobservable_not_zero':True,
        'ON_original_profile_unchanged':True,'production_sources_unchanged':True,'old_batch_unchanged':True,'all_successful_routes_covered_returned':result['all_successful_outputs_covered_and_returned'],
        'verify_sha256':sha(H/'verify_receipt.json'),'manifest_sha256':sha(H/'manifest.json'),'sealed_files':len(files),'no_full_batch_started':True,'stopped_for_owner_review':True,'seal_new_core_or_geometry_calls':0,
        'report_export_revision':'v0.2; first export preserved','same_recorded_work_pairs':sum(s['same_recorded_work_pairs'] for s in summaries.values()),
        'P2_ON_budget_OFF_natural_pairs':p2['ON_budget_OFF_natural'],'all_paired_raw_and_post_routes_equal':all(p['raw_route_equal'] and p['post_vertices_equal'] for p in pairs),
        'worth_discussing_clean_full_batch':result['worth_discussing_clean_full_batch']})
    for name,digest in files.items():assert sha(H/name)==digest,name
    print({'sealed':True,'files':len(files)})

if __name__=='__main__':
    import sys
    main('--seal' in sys.argv)
