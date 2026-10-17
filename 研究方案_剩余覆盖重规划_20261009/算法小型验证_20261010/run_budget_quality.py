"""Controlled budget sensitivity on existing medium snapshots; no new tuning."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,statistics
from scenarios import deserialize
from structure_candidates import solve_candidate
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_23_budget_quality'
INPUT=ROOT/'results/run_20_new_structure_comparison/snapshots.json'
ALGORITHMS=('P2_SHARED','STRIP_HV','TREE_MST')
BUDGETS=(.1,.5,2.,5.,20.)
REPEATS=2


def summarize(records):
    references={}
    long_references={}
    for r in records:
        if r['audit'] and r['audit']['valid']:
            c=r['case'];length=r['audit']['length']
            references[c]=min(references.get(c,float('inf')),length)
            if r['budget']==20:
                long_references[c]=min(long_references.get(c,float('inf')),length)
    groups=defaultdict(list)
    for r in records:
        groups[r['algorithm'],r['budget']].append(r)
    result={}
    for (algorithm,budget),rows in groups.items():
        valid=[r for r in rows if r['audit'] and r['audit']['valid']]
        lengths=[r['audit']['length'] for r in valid]
        result[algorithm+'@'+str(budget)]={
            'executions':len(rows),'valid_complete_routes':len(valid),
            'statuses':dict(Counter(r['status'] for r in rows)),
            'sources':dict(Counter(r.get('source') for r in rows)),
            'median_seconds':statistics.median(r['seconds'] for r in rows),
            'max_seconds':max(r['seconds'] for r in rows),
            'overruns_gt_10ms':sum(r.get('overrun_gt_10ms',False) for r in rows),
            'valid_step_total':sum(lengths),
            'matched_to_pooled_reference':len(valid),
            'pooled_reference_total_on_valid':sum(references[r['case']] for r in valid),
            'excess_steps_vs_pooled':sum(r['audit']['length']-references[r['case']] for r in valid),
            'equal_to_pooled':sum(r['audit']['length']==references[r['case']] for r in valid),
            'matched_to_20s_reference':sum(r['case'] in long_references for r in valid),
            'shorter_than_20s_reference':sum(r['audit']['length']<long_references[r['case']] for r in valid if r['case'] in long_references)}
    # Pair by the same case, method and repetition; preserve failures.
    by={(r['case'],r['algorithm'],r['repeat'],r['budget']):r for r in records}
    paired={}
    for algorithm in ALGORITHMS:
        for budget in BUDGETS[:-1]:
            counts=Counter();gap=0
            for key,r in by.items():
                if r['algorithm']!=algorithm or r['budget']!=budget:
                    continue
                ref=by.get((r['case'],algorithm,r['repeat'],20.))
                if ref is None:continue
                a=r['audit'];b=ref['audit']
                if not a or not a['valid']:
                    counts['short_no_valid_route']+=1;continue
                if not b or not b['valid']:
                    counts['long_no_valid_route']+=1;continue
                delta=a['length']-b['length'];gap+=delta
                counts['short_worse' if delta>0 else 'equal' if delta==0 else 'short_better']+=1
            paired[algorithm+'@'+str(budget)]={'counts':dict(counts),'paired_step_difference_short_minus_20s':gap}
    return {'groups':result,'same_method_same_seed_vs_20s':paired,
        'pooled_feasible_reference':references,'20s_feasible_reference':long_references,
        'reference_is_proven_optimal':False,'scope':'all methods/budgets/seeds pooled feasible upper bound; missing routes never treated as zero cost'}


def main():
    OUT.mkdir(exist_ok=False)
    raw=json.loads(INPUT.read_text(encoding='utf-8'))
    (OUT/'snapshots.json').write_bytes(INPUT.read_bytes())
    names=('run_budget_quality.py','structure_candidates.py','model.py','audit.py','scenarios.py',
        'planners.py','oarp_replan/ranks.py','oarp_replan/tour.py')
    hashes={}
    for name in names:
        f=ROOT/name;dest=OUT/'source_snapshot'/name
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes())
        hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'date':'2026-10-11','protocol':'budget response, fixed existing run20 snapshots, unchanged candidates',
        'input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'source_sha256':hashes,
        'snapshots':len(raw),'budgets_seconds':BUDGETS,'repetitions':REPEATS,'algorithms':ALGORITHMS,
        'seed':'6000+10*case_index+repeat, identical across budgets and methods',
        'order':'budget order rotated by case and reversed on second repetition; method order also rotated',
        'budget_includes':'geometry, reachability, common fallback generation, search and incumbent validation',
        'soft_limit':True,'not_a_real_UAV_deadline':True,'held_out':False,
        'offline_reference':'20s same unchanged methods, plus best feasible pooled all-run reference; not exact',
        'limitations':'two repeats only; budget affects search interruption and GLNS allocation; STRIP has fixed 50ms reservation',
        'no_algorithm_change':True})
    records=[]
    for index,d in enumerate(raw):
        s=deserialize(d)
        for repeat in range(REPEATS):
            shift=index%len(BUDGETS)
            budgets=BUDGETS[shift:]+BUDGETS[:shift]
            if repeat:budgets=tuple(reversed(budgets))
            for budget in budgets:
                shift=(index+repeat)%3
                methods=ALGORITHMS[shift:]+ALGORITHMS[:shift]
                for algorithm in methods:
                    r=solve_candidate(s,algorithm,budget,6000+10*index+repeat)
                    r.update({'case':s.name,'family':d['metadata']['family'],'budget':budget,'repeat':repeat})
                    records.append(r)
                write_json(OUT/'results.json',records)
        print(str(index+1)+'/'+str(len(raw))+' '+s.name+' finished',flush=True)
    summary=summarize(records)
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary['same_method_same_seed_vs_20s'],ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
