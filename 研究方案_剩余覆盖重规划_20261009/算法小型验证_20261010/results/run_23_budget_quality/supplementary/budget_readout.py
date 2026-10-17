"""Post-run descriptive readout; never selects or reruns algorithms."""
from pathlib import Path
import json
from collections import Counter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_23_budget_quality'


def main():
    load=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    summary=load('summary.json');rows=load('results.json');raw=load('snapshots.json')
    by={(r['case'],r['algorithm'],r['repeat'],r['budget']):r for r in rows}
    names=[d['name'] for d in raw]
    analysis={}
    for alg in ('P2_SHARED','STRIP_HV','TREE_MST'):
        analysis[alg]={}
        for budget in (.1,.5,2.,5.):
            values=[];deltas=[]
            for case in names:
                differences=[]
                for rep in range(2):
                    a=by[case,alg,rep,budget]['audit'];b=by[case,alg,rep,20.]['audit']
                    if a and b and a['valid'] and b['valid']:
                        differences.append(a['length']-b['length'])
                if len(differences)==2:
                    kind='both_worse' if min(differences)>0 else 'both_equal' if max(differences)==min(differences)==0 else 'both_better' if max(differences)<0 else 'mixed'
                    values.append(kind);deltas.append({'case':case,'repeat_differences':differences})
                else:values.append('incomplete_pair')
            analysis[alg][str(budget)]={'case_counts':dict(Counter(values)),'details':deltas}
    (OUT/'repeat_consistency.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 预算对照原始读数','',
        '每个档位、每种方法为24个快照×2次执行；总步数只汇总有效完整路线，必须同时看有效数量。参照是所有运行中的最好可行路线，不是已证最优。','',
        '| 方法 | 预算秒 | 有效完整路线/48 | 总步数 | 对可行参照超额步数 | 中位耗时秒 | 搜索限时保留路线次数 | 无路线次数 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for b in (.1,.5,2.,5.,20.):
        for alg in ('P2_SHARED','STRIP_HV','TREE_MST'):
            g=summary['groups'][alg+'@'+str(b)]
            lines.append(f"| {alg} | {b:g} | {g['valid_complete_routes']} | {g['valid_step_total']} | {g['excess_steps_vs_pooled']} | {g['median_seconds']:.4f} | {g['statuses'].get('planned_at_timeout',0)} | {g['executions']-g['valid_complete_routes']} |")
    lines.extend(['','## 同方法、同种子相对20秒结果','',
        '| 方法 | 较短预算秒 | 短预算更差/相同/更好 | 配对净增步数 |',
        '|---|---:|---|---:|'])
    for alg in ('P2_SHARED','STRIP_HV','TREE_MST'):
        for b in (.1,.5,2.,5.):
            p=summary['same_method_same_seed_vs_20s'][alg+'@'+str(b)];c=p['counts']
            lines.append(f"| {alg} | {b:g} | {c.get('short_worse',0)} / {c.get('equal',0)} / {c.get('short_better',0)} | {p['paired_step_difference_short_minus_20s']} |")
    (OUT/'预算对照表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({a:{b:v['case_counts'] for b,v in q.items()} for a,q in analysis.items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
