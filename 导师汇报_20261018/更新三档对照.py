"""Combine all three budgets and per-state step/time results in one table."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
DEV=WORK/'DeepSeek_底层算法开发比较_20261018'
LONG=WORK/'OARP新版道路复验_汇报用_20261018';SHORT=WORK/'OARP新版道路复验_短预算_20261018'
INDEPENDENT=WORK/'OARP独立基线复测_v0.1_20261018'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    records=[];hashes={}
    independent=(INDEPENDENT/'manifest.json').exists()
    omethod='OARP_FULL_INDEPENDENT_SCENE' if independent else 'OARP_FULL_SCENE'
    def track(p):hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return load(p)
    for budget,batch in ((1,'BUDGET1'),(20,'BUDGET20'),(120,'LONG120')):
        for p in sorted((DEV/'runs'/batch/'results').glob('*.json')):
            d=track(p)
            if d['method_id'] not in ('P2_MULTI','TREE_MST','PPCPP_CORE4'):continue
            records.append({'budget':budget,'method':d['method_id'],'case':d['case_id'],'seed':d['seed'],
                'steps':d['route_steps'],'seconds':d['call_total_seconds'],
                'legal':bool(d['audit']['valid'] and d['resource_check']['ok']),
                'timely':bool(d['within_budget'] and d['audit']['valid'] and d['resource_check']['ok']),
                'source':d['final_source']})
    for root in ((INDEPENDENT,) if independent else (LONG,SHORT)):
        protocol=track(root/'protocol.json')
        for j in protocol['planned']:
            d=track(root/'results'/f"{j['plan_id']}.json")
            records.append({'budget':j.get('budget',120),'method':omethod,'case':j['case'],'seed':j['seed'],
                'steps':len(d['route'])-1 if d['route'] else None,'seconds':d['public_seconds'],
                'legal':bool(d['flags']['route_valid']),'timely':bool(d['flags']['within_budget']),
                'core_complete':d['core_complete'],'source':d['source']})
    assert len(records)==240
    assert len({(d['budget'],d['case'],d['seed'],d['method']) for d in records})==240
    methods=('P2_MULTI','TREE_MST','PPCPP_CORE4',omethod)
    summaries={}
    for budget in (1,20,120):
        summaries[str(budget)]={}
        for method in methods:
            rs=[d for d in records if d['budget']==budget and d['method']==method];assert len(rs)==20
            valid=sum(d['legal'] for d in rs)
            summaries[str(budget)][method]={'n':20,'legal':valid,'timely':sum(d['timely'] for d in rs),
                'total_steps':sum(d['steps'] for d in rs) if valid==20 else None,
                'saved_legal_steps':sum(d['steps'] for d in rs if d['legal']),
                'total_seconds':sum(d['seconds'] for d in rs),
                'core_complete':sum(d.get('core_complete',False) for d in rs) if method==omethod else None}
    cases=sorted({d['case'] for d in records},key=lambda c:({'small':0,'medium':1,'large':2}[c.split('_')[0]],c))
    lines=['| 预算 | 状态 | P2：步数／耗时 | TREE：步数／耗时 | PPCPP：步数／耗时 | 新OARP：步数／耗时 |',
           '|---|---|---:|---:|---:|---:|']
    if independent:lines[0]=lines[0].replace('新OARP','OARP独立运行')
    def cell(rs,total=False):
        legal=sum(d['legal'] for d in rs);seconds=sum(d['seconds'] for d in rs)
        steps=str(sum(d['steps'] for d in rs)) if legal==len(rs) else '—'
        text=f'{steps} / {seconds:.3f}'
        if legal<len(rs):text+=f'（合法{legal}/{len(rs)}）'
        if total:text+=f'；及时{sum(d["timely"] for d in rs)}/{len(rs)}'
        elif any(not d['timely'] for d in rs):text+='†'
        return text
    for budget in (1,20,120):
        for case in cases:
            values=[cell([d for d in records if d['budget']==budget and d['case']==case and d['method']==m]) for m in methods]
            lines.append(f'| {budget}秒 | {case.removesuffix("_development")} | '+' | '.join(values)+' |')
        values=[cell([d for d in records if d['budget']==budget and d['method']==m],True) for m in methods]
        lines.append(f'| **{budget}秒** | **20次合计** | '+' | '.join('**'+v+'**' for v in values)+' |')
    heading='## 三、基线算法的步数与时间比较'
    intro='''同样10个状态，每种方法在1秒、20秒、120秒预算下各运行两个种子。表内每个状态都是**两次运行的合计步数／合计规划耗时（秒）**，每档末行汇总20次，步数均包含完整剩余覆盖和返航。

†表示至少一次未在预算内返回合法完整路线；—表示该组没有全部返回合法路线，不以不完整步数参与排名。合计行的“及时”是预算内合法返回次数。超预算但最终合法的路线保留作质量诊断。
'''
    o1=summaries['1'][omethod];o20=summaries['20'][omethod];o120=summaries['120'][omethod]
    summary=f'''新版OARP在1秒、20秒、120秒下，预算内合法返回分别为{o1['timely']}/20、{o20['timely']}/20、{o120['timely']}/20。120秒档总步数为{o120['total_steps']}、总耗时为{o120['total_seconds']:.3f}秒；短预算的失败和超时保留在表中。

P2、TREE和PPCPP采用已有同状态数据；OARP采用本轮新版FULL配置的三档结果。时间均计完整规划入口，依赖预加载另计。

**C*已完成核心复现和微图测试，但已覆盖历史尚未进入核心决策。目前版本可作为重启诊断，尚未纳入本表的剩余覆盖基线；历史适配完成后再补充同条件比较。**
'''
    if independent:
        summary=f'''OARP独立运行在1秒、20秒、120秒下，预算内合法返回分别为{o1['timely']}/20、{o20['timely']}/20、{o120['timely']}/20。20秒和120秒档总步数均为{o120['total_steps']}，合计规划耗时分别为{o20['total_seconds']:.3f}秒和{o120['total_seconds']:.3f}秒。1秒档的两个失败均为large_g3，其连接距离计算尚未完成。

OARP仅采用自身条带划分与访问顺序求解产出的路线，不使用额外贪心或旧路线候选。P2、TREE和PPCPP沿用已有同状态、同预算数据，结果包含各自原框架的候选与保底机制。时间均计完整规划入口，包含几何计算和最终审核；依赖预加载另计。三档均按各自终止配置运行，不把120秒上限当作求解到全局最优。

**C*已完成核心复现和微图测试，但已覆盖历史尚未进入核心决策。目前版本可作为重启诊断，尚未纳入本表的剩余覆盖基线；历史适配完成后再补充同条件比较。**
'''
    target=ROOT/'导师汇报稿_汇报版_20261018.md';text=target.read_text(encoding='utf-8')
    assert heading in text and '## 四、' in text
    oldsection=text[text.index(heading):text.index('## 四、')]
    (ROOT/'存档_上一版第三节_仅120秒.md').write_text(oldsection,encoding='utf-8') if not (ROOT/'存档_上一版第三节_仅120秒.md').exists() else None
    section=heading+'\n\n'+intro+'\n'+'\n'.join(lines)+'\n\n'+summary+'\n'
    text=text[:text.index(heading)]+section+text[text.index('## 四、'):]
    if independent:text=text.replace('新版OARP整体条带适配版（FULL）','OARP整体条带适配版（FULL，独立运行）')
    text=text.replace('ε*修正版尚无本批可比数据，C*与TRACE暂未纳入本表的数值排名。',
                      'ε*修正版尚无本批可比数据；C*的历史适配尚未完成；TRACE暂未纳入数值比较。')
    text=text.replace('第一步，改进底层路径规划。以新版整体条带配置为参照，',
                      '第一步，改进底层路径规划。先提高短预算下及时返回合法完整路线的能力，再以新版整体条带配置为参照，')
    direction=ROOT/'第四节_底层算法研究方向.md'
    if direction.exists():text=text[:text.index('## 四、')]+direction.read_text(encoding='utf-8')
    next_plan=ROOT/'第五节_下一步规划.md'
    if next_plan.exists():text+='\n'+next_plan.read_text(encoding='utf-8')
    target.write_text(text,encoding='utf-8')
    (ROOT/'汇报版三档数据依据.json').write_text(json.dumps({'summary':summaries,'records':records,'input_sha256':hashes,
        'Cstar':'restart diagnostic, core history not integrated; no performance call added'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False,indent=2));print('ONE combined table,33 data/total rows')
if __name__=='__main__':main()
