"""PPCPP-centred analysis of this batch only; never invokes algorithms."""
import csv,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def summarize(rs):
    return dict(n=len(rs),shorter=sum(r['ppcpp_steps']<r['other_steps'] for r in rs),equal=sum(r['ppcpp_steps']==r['other_steps'] for r in rs),longer=sum(r['ppcpp_steps']>r['other_steps'] for r in rs),mean_relative=statistics.mean(r['relative'] for r in rs) if rs else None,ppcpp_sum=sum(r['ppcpp_steps'] for r in rs),other_sum=sum(r['other_steps'] for r in rs))
def main():
    assert not (HERE/'PPCPP中心统计.json').exists()
    p=read(HERE/'protocol.json');rows=read(HERE/'execution/checks.json');assert len(rows)==280
    by={(r['case_id'],r['seed'],r['method']):r for r in rows};details=[];summaries=[]
    for m in p['methods']:
        if m=='PPCPP':continue
        paired=[];missing=[]
        for c in p['cases']:
            for seed in p['seeds']:
                a=by[c['case_id'],seed,'PPCPP'];b=by[c['case_id'],seed,m]
                if a['timely'] and b['timely']:
                    r=dict(method=m,case_id=c['case_id'],seed=seed,name=c['original_name'],scale=c['scale'],state=c['state'],ppcpp_steps=a['steps'],other_steps=b['steps'],relative=a['steps']/b['steps']-1)
                    paired.append(r);details.append(r)
                else:missing.append(dict(case_id=c['case_id'],seed=seed,PPCPP_timely=a['timely'],other_timely=b['timely']))
        summaries.append(dict(method=m,**summarize(paired),unpaired=len(missing),missing=missing,by_state={s:summarize([r for r in paired if r['state']==s]) for s in ('control','event')},by_scale={s:summarize([r for r in paired if r['scale']==s]) for s in ('small','medium','large')}))
    out=dict(versions=p['versions'],new_solves=0,formal_calls=280,comparisons=summaries,paired_rows=len(details),scope='PPCPP as numerator, same-state/seed timely pairs; developer only; no pooling old results')
    (HERE/'PPCPP中心统计.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    with (HERE/'PPCPP及时配对明细.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(details)
    def table(rs,field=None):
        lines=['|对照|及时配对|未配对|PPCPP更短/相同/更长|PPCPP平均相对路程差|','|---|---:|---:|---|---:|']
        for x in rs:
            r=x if field is None else x['by_state'][field]
            rel='—' if r['mean_relative'] is None else f"{r['mean_relative']:+.2%}"
            lines.append(f"|{x['method']}|{r['n']}|{x['unpaired'] if field is None else 20-r['n']}|{r['shorter']}/{r['equal']}/{r['longer']}|{rel}|")
        return lines
    methods=read(HERE/'analysis.json')['methods'];a=next(r for r in methods if r['method']=='PPCPP')
    lines=['# PPCPP与其他算法新版共同预算分析','', '日期：2026-10-20。本批v0.3使用CSTAR_EQUIVALENT_v0.7，整批重新执行280次；不复用旧成绩。20个既有开发状态×两种子，每次20秒；两种子不是独立地图。','',
        '## 先看可用性和时间','',f"PPCPP完整合法{a['valid']}/40、及时{a['timely']}/40，平均入口{a['entry_mean']:.4f}秒、最大{a['entry_max']:.4f}秒。全部方法的失败、迟到、自报与入口时间见七算法共同预算比较报告及method_summary.csv。",'',
        '## 以PPCPP为主体的配对路程','', '相对差逐项按(PPCPP−对照)/对照计算；负值表示PPCPP更短，不把反方向百分比均值取负。只在双方均及时的同输入/种子配对，未配对保留；不能跨不同成功子集直接排名。','']+table(summaries)
    lines+=['','## 事件后状态单独看','', '下表每种对照最多20个状态—种子组合，避免由无变化控制状态替事件重规划作结论。','']+table(summaries,'event')
    lines+=['','## 无变化控制状态','']+table(summaries,'control')
    lines+=['','## 规模分组','', '|对照|规模|配对数|PPCPP更短/同/更长|平均相对差|','|---|---|---:|---|---:|']
    for x in summaries:
        for s,r in x['by_scale'].items():
            rel='—' if r['mean_relative'] is None else f"{r['mean_relative']:+.2%}"
            lines.append(f"|{x['method']}|{s}|{r['n']}|{r['shorter']}/{r['equal']}/{r['longer']}|{rel}|")
    lines+=['','## 解释边界','',
        '- 本轮没有挑选对PPCPP有利的新地图，未用留出；C*的语义修正与等价效率验收已先完成。修正前PPCPP相对C*的较大优势不能继续当作原论文机制差异。',
        '- 三种工程基线保留原冻结保底，独立四算法不引入该保底。OARP是模型2工程适配，不是完整OARP-Replan；TREE_MST不是TRACE/C*。比较的是明确版本，不是原论文名义上的直接优劣。',
        '- 共同提供真实历史、当前地图、当前位置、基地、资源及旧后缀。独立API不把旧后缀列为候选，未读取未来或覆盖见证。计时含入口内转换、检查与保留的观测，不含导入和独立外审；不等同原论文的运动覆盖完成时间。',
        '- 主表完整入口≤20.010秒及时，严格20秒另存；不能只看最终合法路线删去迟到。软截止不是硬实时保证。',
        '- 个例、分组和均值均须并列解释；不能凭平均路程差确认主算法、创新或普遍优势。更快不等于路线总是更短。',
        '- 原v0.2的280次、C*各中间版失败和旧PPCPP稿保留。本稿只使用v0.3新批次；未推送GitHub。','',
        '## 证据','', '`protocol.json`、`execution/`、`analysis.json`、`PPCPP中心统计.json`与`PPCPP及时配对明细.csv`；运行`verify.py`作只读核验，不增加求解。','']
    (HERE/'PPCPP与其他算法新版分析稿_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
