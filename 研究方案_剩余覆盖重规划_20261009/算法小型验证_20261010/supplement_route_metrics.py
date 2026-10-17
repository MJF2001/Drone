"""Postprocess immutable run_26 routes. No planner is called."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,statistics,math
from scenarios import deserialize
from audit import audit

D=Path(__file__).parent
SOURCE=D/'results'/'run_26_unified_new_maps'
OUT=D/'results'/'run_27_supplement_metrics_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'

def metrics(route,targets,covered):
    route=list(map(tuple,route));targets=set(targets);covered=set(covered)
    if not route:raise ValueError('empty route')
    initial_credit={route[0]}&targets-covered
    seen=covered|initial_credit
    counts=dict(fresh_target_steps=0,historical_target_steps=0,
                repeated_new_target_steps=0,non_target_steps=0)
    pending=targets-seen
    completion=0 if not pending else None
    for i,p in enumerate(route[1:],1):
        if p not in targets:counts['non_target_steps']+=1
        elif p in covered:counts['historical_target_steps']+=1
        elif p in seen:counts['repeated_new_target_steps']+=1
        else:counts['fresh_target_steps']+=1
        seen.add(p);pending.discard(p)
        if completion is None and not pending:completion=i
    moves=len(route)-1
    vectors=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
    assert all(abs(x)+abs(y)==1 for x,y in vectors)
    turns90=sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vectors,vectors[1:]))
    turns180=sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vectors,vectors[1:]))
    target_visits=moves-counts['non_target_steps']
    duplicate=counts['historical_target_steps']+counts['repeated_new_target_steps']
    assert sum(counts.values())==moves
    return dict(**counts,length=moves,target_arrivals=target_visits,
        duplicate_target_arrivals=duplicate,overlap_ratio=duplicate/target_visits if target_visits else None,
        turns90=turns90,turns180=turns180,direction_changes=turns90+turns180,
        initial_credit=len(initial_credit),missing_targets=len(targets-seen),
        completion_step=completion,return_tail_steps=moves-completion if completion is not None else None)

def checks():
    t={(x,y) for x in range(2) for y in range(3)}
    cycle=[(0,0),(0,1),(0,2),(1,2),(1,1),(1,0),(0,0)]
    snake=[(0,0),(1,0),(1,1),(0,1),(0,2),(1,2),(0,2),(0,1),(0,0)]
    a=metrics(cycle,t,{(0,0)});b=metrics(snake,t,{(0,0)})
    assert (a['length'],a['fresh_target_steps'],a['duplicate_target_arrivals'],a['return_tail_steps'])==(6,5,1,1)
    assert (b['length'],b['duplicate_target_arrivals'],b['return_tail_steps'])==(8,3,3)
    # End of mission is not joined back to its first direction: three turns.
    assert a['turns90']==3 and a['turns180']==0 and b['turns180']==1
    c=metrics([(0,0),(1,0),(2,0),(1,0),(0,0)],{(1,0)},set())
    assert c['non_target_steps']==2 and c['repeated_new_target_steps']==1 and c['turns180']==1
    z=metrics([(0,0)],{(0,0)},set())
    assert z['initial_credit']==1 and z['overlap_ratio'] is None and z['return_tail_steps']==0

def percentile(values,p):
    a=sorted(values);pos=(len(a)-1)*p;i=int(pos)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(pos-i)

def main():
    checks();OUT.mkdir(exist_ok=False,parents=True)
    inputs=['runs.json','references.json','snapshots.json','protocol.json']
    hashes={f:hashlib.sha256((SOURCE/f).read_bytes()).hexdigest() for f in inputs}
    read=lambda f:json.loads((SOURCE/f).read_text(encoding='utf-8'))
    snaps={r['snapshot']['name']:deserialize(r['snapshot']) for r in read('snapshots.json')}
    rows=[]
    for kind,records in [('comparison',read('runs.json')),('reference',read('references.json'))]:
        for r in records:
            s=snaps[r['case']];route=r['route']
            check=audit(s,list(map(tuple,route)))
            assert check==r['independent_audit'],(r['case'],check,r['independent_audit'])
            m=metrics(route,s.targets,s.covered)
            assert m['length']==check['length'] and m['direction_changes']==check['direction_changes']
            assert m['missing_targets']==check['uncovered']==0
            improvements=r['detail'].get('improvements',[])
            rows.append(dict(case=r['case'],algorithm=r['algorithm'],budget=r['budget'],
                repeat=r.get('repeat'),kind=kind,family=r['metadata']['family'],valid=check['valid'],
                seconds=r['seconds'],overrun_gt_10ms=r['overrun_gt_10ms'],
                first_logged_incumbent_seconds=improvements[0]['elapsed'] if improvements else None,**m))
    groups=defaultdict(list)
    for r in rows:groups[(r['kind'],r['budget'],r['algorithm'])].append(r)
    totals=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps',
        'non_target_steps','target_arrivals','duplicate_target_arrivals','turns90','turns180','return_tail_steps']
    summary=[]
    for (kind,budget,method),rs in sorted(groups.items()):
        sums={key:sum(r[key] for r in rs) for key in totals}
        ratios=[r['overlap_ratio'] for r in rs if r['overlap_ratio'] is not None]
        summary.append(dict(kind=kind,budget=budget,algorithm=method,n=len(rs),valid=sum(r['valid'] for r in rs),
            **sums,overlap_pooled=sums['duplicate_target_arrivals']/sums['target_arrivals'],
            overlap_mean=statistics.mean(ratios),seconds_mean=statistics.mean(r['seconds'] for r in rs),
            seconds_p95=percentile([r['seconds'] for r in rs],.95),
            overruns=sum(r['overrun_gt_10ms'] for r in rs)))
    protocol={'input_sha256':hashes,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'counts':{'comparison':432,'reference':24},'no_solver_called':True,
        'overlap':'arrival-based; excludes origin; historical plus within-route repeated target arrivals / all target arrivals',
        'zero_denominator':'null; excluded from arithmetic mean, never treated as zero',
        'length_partition':'fresh_target + historical_target + repeated_new_target + non_target = length',
        'return_tail':'suffix after final pending target first covered; overlaps spatial categories, do not add to partition',
        'first_time':'first logged incumbent only, not independently instrumented first feasible route timing'}
    for name,obj in [('per_run.json',rows),('summary.json',summary),('protocol.json',protocol)]:
        (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    assert hashes=={f:hashlib.sha256((SOURCE/f).read_bytes()).hexdigest() for f in inputs}
    lines=['# 路径质量指标补充统计（2026-10-12）','',
        '## 本轮工作','',
        '未调用规划器、未重新求解。读取run_26的432次对照和24次20秒P2参照，重新执行独立审计并补算指标；全部456条路线通过核验。原始文件SHA256在统计前后保持一致。','',
        '## 统计口径','',
        '一个格子代表一次有效采集范围，道路可以宽多个格子；相机仅检查正下方一格。','',
        '主表按每一步的落点统计，排除重规划起点（它不对应新增移动）。起点若为未完成目标，单独记initial_credit。飞行中经过目标即算检查，不模拟相机开关。','',
        '- 新覆盖：第一次到达本次尚未完成的目标格。','- 历史重复：到达重规划前已经检查过的目标格。',
        '- 本轮重复：再次到达本轮刚完成的目标格。','- 非目标转移：到达当前目标集合之外的合法位置。',
        '- 路径覆盖重叠率＝（历史重复＋本轮重复）／全部目标格到达次数。它是按访问次数计算的冗余比例，不是重复区域面积占比，也不涉及图像重叠。',
        '- 四项移动步数之和严格等于路线长度。返航仍包含在主统计中；另给出最后一个待检目标完成后的返航尾段，不能与四项分类再相加。',
        '- 90°与180°按相邻四邻接移动向量计算，不赋予时间或能耗权重。',
        '- 汇总重叠率同时保留按到达次数加权的总体比例及每条路线比例的算术平均；主表使用前者。','',
        '## 全部计算预算结果','',
        '每行48次运行，来自24状态×2次重复；重复不是独立地图。长度、转弯及转移量是总和，计算耗时为每次均值和P95。','',
        '|预算/秒|方法|步数|重叠率|90°转弯|180°折返|非目标转移步数|计算均值/秒|计算P95/秒|',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        if r['kind']!='comparison':continue
        lines.append(f'|{r["budget"]}|{r["algorithm"]}|{r["length"]}|{r["overlap_pooled"]:.2%}|{r["turns90"]}|{r["turns180"]}|{r["non_target_steps"]}|{r["seconds_mean"]:.4f}|{r["seconds_p95"]:.4f}|')
    lines+=['','## 5秒预算的路程组成','',
        '|方法|新覆盖|历史重复|本轮重复|非目标转移|返航尾段（另行观察）|','|---|---:|---:|---:|---:|---:|']
    for r in summary:
        if r['kind']=='comparison' and r['budget']==5:
            lines.append('|'+r['algorithm']+'|'+ '|'.join(str(r[k]) for k in totals[1:5]+['return_tail_steps'])+'|')
    lines+=['','## 解释与限制','',
        '重叠率与路径长度并非完全独立：在同一个状态中，新覆盖工作量固定，总长度差异来自重复覆盖和非目标转移。应分析组成，避免将相关指标宣传为多项独立优势。','',
        '首条有效路线时间目前仅有首个改进日志时间；日志可供参考，未纳入主表作为独立精确计时证据。本次没有重新测量计算时间，沿用原求解耗时。所有方法预算超过10ms的次数仍为0。','',
        '这是同批开发地图的事后补充评价，不能充当新的独立验证；不代表真实飞行能耗。原实现仍为P2、横纵条带工程候选和MST加2-opt，不能代表完整文献算法。','',
        '详细数据与输入哈希保存在算法小型验证_20261010/results/run_27_supplement_metrics_20261012/。']
    report=B/'37_路径质量指标补充统计_20261012.md'
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2));print(report)

if __name__=='__main__':main()
