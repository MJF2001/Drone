"""Uninstrumented paired implementation comparison, same coverage heuristic."""
from pathlib import Path
from collections import Counter
import hashlib,json,statistics
from model import Geometry
from bfs_metric_geometry import BFSMetricGeometry
from structure_candidates import solve_candidate
from scenarios import deserialize
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_25_optimized_p2_baseline'
INPUT=ROOT/'results/run_23_budget_quality/snapshots.json'
BUDGETS=(.1,.5,5.,20.)
METHODS=('P2_ASTAR','P2_BFS')


def main():
    OUT.mkdir(exist_ok=False)
    raw=json.loads(INPUT.read_text(encoding='utf-8'))
    (OUT/'snapshots.json').write_bytes(INPUT.read_bytes())
    prev=json.loads((ROOT/'results/run_23_budget_quality/results.json').read_text(encoding='utf-8'))
    references={r['case']:r for r in prev if r['algorithm']=='P2_SHARED' and r['budget']==20 and r['repeat']==0}
    write_json(OUT/'previous_20s_references.json',references)
    hashes={}
    for name in ('run_optimized_baseline.py','bfs_metric_geometry.py','structure_candidates.py','model.py',
        'planners.py','audit.py','scenarios.py','test_bfs_metric_geometry.py'):
        p=ROOT/name;dest=OUT/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(p.read_bytes());hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'date':'2026-10-11','purpose':'engineering baseline correction, not new coverage method',
        'input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'source_sha256':hashes,
        'budgets_seconds':BUDGETS,'repeats':2,'implementations':METHODS,
        'identical':'candidate order, NN/2opt rules, common fallback, exact metric, legacy path tie policy',
        'difference':'lazy per-source BFS distance rows instead of per-pair A* distance materialisation',
        'instrumentation':False,'order':'budget rotation/reversal, implementation order alternated',
        'held_out':False,'deadline':'same cooperative total soft limit','seed':'7000+10*case_index+repeat'})
    rows=[]
    for index,d in enumerate(raw):
        s=deserialize(d)
        for repeat in range(2):
            shift=index%4;budgets=BUDGETS[shift:]+BUDGETS[:shift]
            if repeat:budgets=tuple(reversed(budgets))
            for budget in budgets:
                methods=METHODS if (index+repeat)%2==0 else tuple(reversed(METHODS))
                for method in methods:
                    r=solve_candidate(s,'P2_SHARED',budget,7000+10*index+repeat,
                        geometry_class=Geometry if method=='P2_ASTAR' else BFSMetricGeometry)
                    r.update({'case':s.name,'algorithm':method,'budget':budget,'repeat':repeat})
                    if budget==20:
                        r['route_matches_previous_20s']=list(map(list,r['route']))==references[s.name]['route']
                        assert r['route_matches_previous_20s'],'unlimited behaviour changed'
                    rows.append(r)
                write_json(OUT/'results.json',rows)
        print(str(index+1)+'/24 '+s.name+' finished',flush=True)
    summary={}
    by={(r['case'],r['algorithm'],r['repeat'],r['budget']):r for r in rows}
    for budget in BUDGETS:
        group={}
        for method in METHODS:
            q=[r for r in rows if r['algorithm']==method and r['budget']==budget]
            group[method]={'statuses':dict(Counter(r['status'] for r in q)),
                'valid':sum(bool(r['audit'] and r['audit']['valid']) for r in q),
                'steps_total':sum(r['audit']['length'] for r in q if r['audit']),
                'seconds_median':statistics.median(r['seconds'] for r in q),
                'seconds_total':sum(r['seconds'] for r in q),
                'seconds_max':max(r['seconds'] for r in q),
                'overruns_gt_10ms':sum(r.get('overrun_gt_10ms',False) for r in q)}
        counts=Counter();deltas=[];persistent=Counter()
        for d in raw:
            outcomes=[]
            for repeat in range(2):
                old=by[d['name'],'P2_ASTAR',repeat,budget];new=by[d['name'],'P2_BFS',repeat,budget]
                if not old['audit'] or not new['audit']:
                    counts['unmatched_failure']+=1;continue
                delta=old['audit']['length']-new['audit']['length'];deltas.append(delta)
                outcome='BFS_shorter' if delta>0 else 'equal' if delta==0 else 'ASTAR_shorter'
                counts[outcome]+=1;outcomes.append(outcome)
            if len(outcomes)==2:
                persistent[outcomes[0] if outcomes[0]==outcomes[1] else 'mixed']+=1
        group['paired_counts']=dict(counts);group['BFS_steps_saved']=sum(deltas)
        group['case_repeat_consistency']=dict(persistent)
        summary[str(budget)]=group
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
