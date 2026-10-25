"""Read saved outputs, paired comparisons; never invokes an algorithm."""
import json,csv,statistics,itertools,hashlib
from pathlib import Path
from common_audit import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvout(p,rows):
    if not rows:return
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def stats(xs):return dict(mean=statistics.mean(xs),median=statistics.median(xs),min=min(xs),max=max(xs)) if xs else None
def main():
    p=read(HERE/'protocol.json');rows=read(HERE/'execution/checks.json');completion=read(HERE/'execution/completion.json')
    assert len(rows)==len(p['jobs'])==280 and completion['not_run']==0
    cases={c['case_id']:c for c in p['cases']};by={(r['case_id'],r['seed'],r['method']):r for r in rows};assert len(by)==280
    for j,r in zip(p['jobs'],rows):
        assert j['run_id']==r['run_id'];c=read(Path(j['input']));assert hashlib.sha256(Path(j['input']).read_bytes()).hexdigest()==j['input_sha256']
        if not r['technical_failure']:
            fp=HERE/'execution/results'/(j['run_id']+'.json');assert hashlib.sha256(fp.read_bytes()).hexdigest()==r['result_sha256'];z=read(fp)
            assert z['job']==j;checked=audit(c,z);assert checked['valid']==r['valid'] and checked['steps']==r['steps']
            assert r['timely']==(r['valid'] and z['entry_seconds']<=20.010)
            assert r['strict_timely']==(r['valid'] and z['entry_seconds']<=20)
    summaries=[]
    for m in p['methods']:
        rr=[r for r in rows if r['method']==m];tt=[r for r in rr if r['timely']]
        summaries.append(dict(method=m,calls=len(rr),valid=sum(r['valid'] for r in rr),timely=len(tt),strict_timely=sum(r['strict_timely'] for r in rr),late_valid=sum(r['valid'] and not r['timely'] for r in rr),no_route=sum(not r['valid'] and not r['technical_failure'] for r in rr),technical_failure=sum(r['technical_failure'] for r in rr),fallback_selected=sum(r.get('fallback_selected',False) for r in rr),entry_mean=statistics.mean(r['entry_seconds'] for r in rr if 'entry_seconds' in r),entry_max=max(r.get('entry_seconds',0) for r in rr),bootstrap_max=max(r.get('bootstrap_seconds',0) for r in rr),steps_timely_mean=statistics.mean(r['steps'] for r in tt) if tt else None))
        summaries[-1].update(native_reported_timely=sum(r['valid'] and r.get('reported_seconds',float('inf'))<=20.010 for r in rr),entry_minus_reported_max=max(r.get('entry_seconds',0)-r.get('reported_seconds',0) for r in rr))
    pairwise=[];detail=[]
    for a,b in itertools.combinations(p['methods'],2):
        subset=[];missing=[]
        for case in p['cases']:
            for seed in p['seeds']:
                x=by[case['case_id'],seed,a];y=by[case['case_id'],seed,b]
                if x['timely'] and y['timely']:
                    rel=(x['steps']-y['steps'])/y['steps'] if y['steps'] else 0
                    item=dict(case_id=case['case_id'],name=case['original_name'],scale=case['scale'],state=case['state'],event=case['event'],seed=seed,a=a,b=b,a_steps=x['steps'],b_steps=y['steps'],difference=x['steps']-y['steps'],relative=rel)
                    subset.append(item);detail.append(item)
                else:missing.append(dict(case_id=case['case_id'],seed=seed,a_timely=x['timely'],b_timely=y['timely']))
        pairwise.append(dict(a=a,b=b,paired=len(subset),unpaired=len(missing),a_shorter=sum(x['difference']<0 for x in subset),equal=sum(x['difference']==0 for x in subset),a_longer=sum(x['difference']>0 for x in subset),mean_a_relative_b=statistics.mean(x['relative'] for x in subset) if subset else None,missing=missing))
    ref=[]
    for m in p['methods'][1:]:
        vals=[];missing=[]
        for case in p['cases']:
            for seed in p['seeds']:
                a=by[case['case_id'],seed,m];b=by[case['case_id'],seed,'P2_MULTI']
                if a['timely'] and b['timely']:vals.append(dict(case_id=case['case_id'],seed=seed,state=case['state'],scale=case['scale'],delta=a['steps']-b['steps'],relative=a['steps']/b['steps']-1))
                else:missing.append(dict(case_id=case['case_id'],seed=seed,method_timely=a['timely'],P2_timely=b['timely']))
        ref.append(dict(method=m,paired=len(vals),unpaired=len(missing),shorter=sum(v['delta']<0 for v in vals),equal=sum(v['delta']==0 for v in vals),longer=sum(v['delta']>0 for v in vals),mean_relative=statistics.mean(v['relative'] for v in vals) if vals else None,by_state={s:dict(n=sum(v['state']==s for v in vals),mean_relative=statistics.mean(v['relative'] for v in vals if v['state']==s)) for s in ('control','event') if any(v['state']==s for v in vals)},missing=missing))
    cohort=[]
    for case in p['cases']:
        for seed in p['seeds']:
            rr=[by[case['case_id'],seed,m] for m in p['methods']]
            cohort.append(dict(case_id=case['case_id'],name=case['original_name'],seed=seed,all_timely=all(r['timely'] for r in rr),**{m:(by[case['case_id'],seed,m]['steps'] if by[case['case_id'],seed,m]['timely'] else None) for m in p['methods']}))
    common=[x for x in cohort if x['all_timely']]
    common_quality=[dict(method=m,paired=len(common),sum_steps=sum(x[m] for x in common),mean_steps=statistics.mean(x[m] for x in common) if common else None,mean_relative_P2=statistics.mean(x[m]/x['P2_MULTI']-1 for x in common) if common else None) for m in p['methods']]
    scale_counts={m:{s:dict(calls=sum(r['method']==m and cases[r['case_id']]['scale']==s for r in rows),timely=sum(r['timely'] for r in rows if r['method']==m and cases[r['case_id']]['scale']==s)) for s in ('small','medium','large')} for m in p['methods']}
    complete_pairs=[x for x in pairwise if x['paired']==40]
    core_evidence={}
    for m in ('P2_MULTI','OARP_CORE2','TREE_MST'):
        rr=[r for r in rows if r['method']==m];raws=[read(HERE/'execution/results'/(r['run_id']+'.json'))['raw'] for r in rr if not r['technical_failure']]
        core_evidence[m]=dict(sources={s:sum(r.get('source')==s for r in raws) for s in sorted({r.get('source') for r in raws if r.get('source') is not None})},oarp_tour_recorded=sum('tour' in r.get('detail',{}) for r in raws) if m=='OARP_CORE2' else None)
    output=dict(completion=completion,methods=summaries,versus_P2=ref,pairwise=pairwise,all_method_common_timely=len(common),common_cohort_quality=common_quality,engineering_core_evidence=core_evidence,scope='developer states, not holdout; deterministic repeats not independent maps')
    output.update(timely_by_scale=scale_counts,complete_40_pairs=complete_pairs,common_cohort_scales={s:sum(cases[x['case_id']]['scale']==s for x in common) for s in ('small','medium','large')})
    save(HERE/'analysis.json',output);csvout(HERE/'method_summary.csv',summaries);csvout(HERE/'paired_details.csv',detail);csvout(HERE/'case_seed_steps.csv',cohort)
    flat=[]
    for r in rows:
        c=cases[r['case_id']];flat.append({k:r.get(k) for k in ('run_id','method','case_id','seed','valid','timely','strict_timely','steps','status','entry_seconds','reported_seconds','source','fallback_selected','technical_failure')}|dict(name=c['original_name'],scale=c['scale'],state=c['state'],event=c['event']))
    csvout(HERE/'all_runs.csv',flat)
    lines=['# 七算法共同预算开发比较结果','', '日期：2026-10-20。每次20秒软预算，主表以完整入口≤20.010秒为及时；另保留严格20秒统计。20个既有开发状态、两种子，280次正式执行；不是留出主实验。','', '## 完成及计时','', '|方法|合法/40|及时/40|严格20秒内|合法但迟到|无完整路线|技术失败|保底选中|平均入口秒|最大入口秒|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:lines.append(f"|{r['method']}|{r['valid']}|{r['timely']}|{r['strict_timely']}|{r['late_valid']}|{r['no_route']}|{r['technical_failure']}|{r['fallback_selected']}|{r['entry_mean']:.4f}|{r['entry_max']:.4f}|")
    lines+=['','### 自报时间与统一入口时间的差异','', '以下只作计时诊断，不替代预先固定的主表。原冻结框架在自报计时结束后仍执行其内部外置审核；统一入口将返回前的这部分也计入。迟到不能自动等同路线错误或核心搜索失败。','', '|方法|按自报秒≤20.010且路线合法|按完整入口及时|入口减自报最大秒|','|---|---:|---:|---:|']
    for r in summaries:lines.append(f"|{r['method']}|{r['native_reported_timely']}|{r['timely']}|{r['entry_minus_reported_max']:.6f}|")
    lines+=['','工程基线最终来源与OARP核心巡游记录数另见 analysis.json/engineering_core_evidence。保底选中不等于核心未运行；相同长度时可能保留先得到的保底。']
    lines+=['','## 相对P2的成对路程','', '只在双方均及时的同状态/同种子上比较；正数表示比P2更长。未配对次数必须同时读取，不能用成功子集的均值直接宣布总体优胜。','', '|方法|成对数|未配对|更短/相同/更长|平均相对路程差|','|---|---:|---:|---|---:|']
    for r in ref:lines.append(f"|{r['method']}|{r['paired']}|{r['unpaired']}|{r['shorter']}/{r['equal']}/{r['longer']}|{r['mean_relative']:+.2%}|" if r['mean_relative'] is not None else f"|{r['method']}|0|40|—|—|")
    lines+=['',f"七方法共同及时的状态—种子组合为 {len(common)}/40。全部21对方法的成对计数、失败组合及分组明细在 analysis.json 和 paired_details.csv 中。",'', '## 七方法同一成功子集的路线质量','', '下表使用完全相同的七方及时交集，仅作条件性质量比较；不能用这个子集隐去上一表的失败。各方法不同成功集合的路程总量不直接比较。','', '|方法|共同组合数|路程合计|平均步数|相对P2平均差|','|---|---:|---:|---:|---:|']
    for x in common_quality:
        if common:lines.append(f"|{x['method']}|{x['paired']}|{x['sum_steps']}|{x['mean_steps']:.2f}|{x['mean_relative_P2']:+.2%}|")
    lines+=['','共同及时子集的规模构成：'+str(output['common_cohort_scales'])+'。尤其不能用小、中图子集推断大图路线排序。','', '## 不删状态的40组全量及时对照','', '列出所有双方都40/40及时的方法组合，不只挑某个有利对照。相对差=(A-B)/B，负数表示A更短，计数亦以A为主。','', '|A|B|配对数|A更短/相同/更长|平均相对差|','|---|---|---:|---|---:|']
    for x in complete_pairs:lines.append(f"|{x['a']}|{x['b']}|40|{x['a_shorter']}/{x['equal']}/{x['a_longer']}|{x['mean_a_relative_b']:+.2%}|")
    lines+=['','## 及时率按规模分组','', '|方法|小图及时/12|中图及时/12|大图及时/16|','|---|---:|---:|---:|']
    for m in p['methods']:lines.append(f"|{m}|{scale_counts[m]['small']['timely']}|{scale_counts[m]['medium']['timely']}|{scale_counts[m]['large']['timely']}|")
    failed=[r for r in rows if not r['valid']]
    lines+=['','## 失败与迟到保留','']
    for r in failed:lines.append(f"- {r['run_id']}：{cases[r['case_id']]['original_name']}，状态{r.get('status','technical_failure')}。不拿诊断前缀当完整路线，没有重试或增加预算。")
    lines+=['','P2/MST的合法但迟到路线仍保留在 all_runs.csv；迟到不是路线非法。本批自报秒与入口秒的及时计数相同，因此不能把本批全部迟到都解释为统一入口新增包含了外审。具体超时来源尚未做剖析，不在性能比较期间改动。']
    lines+=['', '## 解释边界','', '- 这是各自声明适配版本的表现，不是未经修改的原论文算法排名。C*包含任务保护，CAP包含重启终点约定，TRACE采用虚拟段解释。','- 所有方法都得到相同当前地图、覆盖、位置、基地、资源及真实历史资料。三种工程基线使用真实旧后缀；其余独立算法的固定API不把旧后缀当候选。保底来源已单列，不把它包装为核心搜索胜利。','- OARP是冻结v2的OARP_CORE2，保留真实旧后缀及模型2，不是后来RANK0独立FULL版，也不是完整OARP-Replan控制器。','- 原生连接器不完全相同；均为四邻接最短连接，实际同长路径的附带采集可能不同。未在比较时改源码强行统一，否则需要另立版本。','- 主计时为完成入口墙钟：预载之后、输入对象构造开始到返回，含实现内部保留的审核/观测；不含落盘与独立外审。自报秒、导入秒、进程墙钟都保存。不比较自报核心秒与另一个方法端到端秒。','- 原生协作式截止/anytime规则保留。合法但超过20.010秒单列，不作为及时路线；严格20秒结果另列。10毫秒容差在看正式结果前已固定，不按结果扩大。','- 七方法固定顺序轮转、种子顺序反转，串行且限制常用数值线程；没有并行竞争试跑。两个种子不是独立地图样本，不计算将40项视作独立地图的显著性。','- 这里只测试20秒，不把它外推成1秒或120秒总量优势；总路程只在同一完整配对集合有意义。没有增加预算重跑失败、调阈值、删慢例或使用留出。','', '## 预检失败与版本','', '首个比较运行器v0.1省略旧后缀，P2预检一次成功后OARP预检因old route omitted original pending targets异常。正式0次；旧目录与两次预检保留，不混入本表。v0.2将真实历史后缀共同提供，各算法源码未改，重新完成7次五格接口预检和6项公共审核检查后才启动280次。','', '## 证据','', '- protocol.json：正式前封存输入、源码/关键依赖哈希、固定280工作项、计时/容差/停止规则。','- preflight/：7次独立预检；execution/：280次原始输出、日志、逐项哈希、入口/自报/导入/进程时间和共同及算法专项审核。','- method_summary.csv、all_runs.csv、case_seed_steps.csv：成功率、计时与全部状态路线步数；迟到和失败没有被删除。','- analysis.json、paired_details.csv：21对方法的成对结果和缺失配对。','- 结果只读再审不计为新增求解；不覆盖既有算法实验。','']
    (HERE/'七算法共同预算比较报告_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
