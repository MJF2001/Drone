"""Freeze new snapshots before evaluating three equal-budget prototypes."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import statistics
from scenarios_structure import cases
from scenarios import serialize,deserialize
from structure_candidates import solve_candidate
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_20_new_structure_comparison'
ALGORITHMS=('P2_SHARED','STRIP_HV','TREE_MST')


def main():
    OUT.mkdir(exist_ok=False)
    raw=[serialize(s,m) for s,m in cases()]
    assert len(raw)==24
    write_json(OUT/'snapshots.json',raw)
    sources=[Path(__file__),*[ROOT/n for n in ('structure_candidates.py','scenarios_structure.py',
        'test_structure_candidates.py','model.py','audit.py','scenarios.py','scenarios_v2.py','planners.py')],
        ROOT/'oarp_replan/ranks.py',ROOT/'oarp_replan/tour.py']
    hashes={}
    for f in sources:
        rel=f.relative_to(ROOT)
        dest=OUT/'source_snapshot'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(f.read_bytes())
        hashes[str(rel)]=hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'protocol':'24 new-parameter road snapshots frozen before first result, equal total soft budget',
        'source_sha256':hashes,'snapshots_sha256':hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest(),
        'algorithms':ALGORITHMS,'seconds_per_solve':5,'seed':'3000+case_index',
        'execution_order':'cyclic rotation per case','repetitions':1,
        'common_fallback':'same old suffix and GD adapter; included in 5 seconds for every algorithm',
        'tree':'metric MST of pending cells plus current pose, BFS edge costs, two DFS preorders then bounded 2opt; NOT TRACE/STC',
        'strip':'H/V maximal pending ranks, GLNS default, split remaining total time across both; NOT OARP full core',
        'P2':'original rebuild search plus shared GD adapter; differs from historical P2',
        'scope':'new parameters/seeds in familiar template family, not OOD, not real field, not final paper test',
        'deadline':'soft cooperative; GLNS may overrun; recorded; final independent audit excluded from solve timing',
        'no_original_core_comparison':'no CORE LP/old-rank budget in this experiment'})
    records=[]
    for index,d in enumerate(raw):
        s=deserialize(d)
        order=ALGORITHMS[index%3:]+ALGORITHMS[:index%3]
        for algorithm in order:
            result=solve_candidate(s,algorithm,5,3000+index)
            result.update({'case':s.name,'family':d['metadata']['family']})
            records.append(result)
            write_json(OUT/'results.json',records)
            print(s.name+' '+algorithm+' '+str(result['audit']['length'] if result['audit'] else result['status'])+' '+str(round(result['seconds'],3)),flush=True)
    summary={}
    valid={a:{r['case']:r for r in records if r['algorithm']==a and r['audit'] and r['audit']['valid']} for a in ALGORITHMS}
    for a in ALGORITHMS:
        q=[r for r in records if r['algorithm']==a]
        summary[a]={'statuses':dict(Counter(r['status'] for r in q)),'sources':dict(Counter(r['source'] for r in q)),
            'valid':len(valid[a]),'steps_total':sum(r['audit']['length'] for r in valid[a].values()),
            'seconds_median':statistics.median(r['seconds'] for r in q),'seconds_max':max(r['seconds'] for r in q),
            'overruns_gt_10ms':sum(r['overrun_gt_10ms'] for r in q),
            'improved_over_common_fallback':sum(r['audit']['length']<r['detail']['common_length'] for r in q if r['audit'])}
    for a,b in (('TREE_MST','P2_SHARED'),('STRIP_HV','P2_SHARED'),('TREE_MST','STRIP_HV')):
        common=valid[a].keys()&valid[b].keys()
        summary[a+'_vs_'+b]={'paired':len(common),'wins':dict(Counter('a_shorter' if valid[a][c]['audit']['length']<valid[b][c]['audit']['length'] else 'equal' if valid[a][c]['audit']['length']==valid[b][c]['audit']['length'] else 'b_shorter' for c in common)),
            'a_total':sum(valid[a][c]['audit']['length'] for c in common),'b_total':sum(valid[b][c]['audit']['length'] for c in common)}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
