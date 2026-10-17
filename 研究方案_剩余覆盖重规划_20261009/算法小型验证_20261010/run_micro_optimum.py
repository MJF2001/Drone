"""Global grid optimum versus frozen engineering candidates on 48 tiny cases."""
from pathlib import Path
from collections import Counter
import hashlib,json,statistics
from scenarios_micro import cases
from scenarios import serialize,deserialize
from exact_grid_coverage import exact_coverage
from structure_candidates import solve_candidate
from audit import audit
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_21_micro_global_optimum'
ALGORITHMS=('P2_SHARED','STRIP_HV','TREE_MST')


def main():
    OUT.mkdir(exist_ok=False)
    raw=[serialize(s,m) for s,m in cases()]
    assert len(raw)==48
    write_json(OUT/'snapshots.json',raw)
    names=('run_micro_optimum.py','exact_grid_coverage.py','scenarios_micro.py','test_exact_grid_coverage.py',
        'structure_candidates.py','model.py','audit.py','scenarios.py','scenarios_v2.py','planners.py',
        'oarp_replan/ranks.py','oarp_replan/tour.py')
    hashes={}
    for name in names:
        f=ROOT/name
        dest=OUT/'source_snapshot'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(f.read_bytes())
        hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'protocol':'48 frozen micro event snapshots, true grid-coverage-return optimum',
        'source_sha256':hashes,'snapshots_sha256':hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest(),
        'exact_solver':'unit-edge BFS on (position, covered-pending-bitmask)',
        'exact_seconds':30,'max_pending_targets':12,'heuristic_seconds':5,
        'heuristics':'unchanged run20 candidates, equal common fallback, cyclic execution order',
        'seed':'4000+case_index','repetitions':1,'held_out_scope':'new small templates, no scalability/field inference',
        'original_paper_reproduction':False,'no_optimality_claim_for_heuristics':True})
    records=[]
    for index,d in enumerate(raw):
        s=deserialize(d)
        exact=exact_coverage(s)
        exact.update({'case':s.name,'algorithm':'EXACT_GRID','family':d['metadata']['family'],
            'audit':audit(s,exact['route']) if exact['route'] else None})
        records.append(exact)
        order=ALGORITHMS[index%3:]+ALGORITHMS[:index%3]
        for algorithm in order:
            r=solve_candidate(s,algorithm,5,4000+index)
            r.update({'case':s.name,'family':d['metadata']['family']})
            if exact['status']=='optimal' and r['audit']:
                r['gap']=r['audit']['length']-exact['length']
                assert r['gap']>=0
            records.append(r)
        write_json(OUT/'results.json',records)
        print(s.name+': '+str([(r['algorithm'],r.get('length',r['audit']['length'] if r['audit'] else r['status']),r.get('gap')) for r in records[-4:]]),flush=True)
    exacts=[r for r in records if r['algorithm']=='EXACT_GRID']
    summary={'snapshots':48,'exact_statuses':dict(Counter(r['status'] for r in exacts)),
        'exact_steps_total':sum(r['length'] for r in exacts if r['status']=='optimal'),
        'exact_seconds_max':max(r['seconds'] for r in exacts),'algorithms':{}}
    for alg in ALGORITHMS:
        q=[r for r in records if r['algorithm']==alg]
        gaps=[r['gap'] for r in q if 'gap' in r]
        summary['algorithms'][alg]={'statuses':dict(Counter(r['status'] for r in q)),
            'matched_exact':len(gaps),'optimal_cases':sum(g==0 for g in gaps),'nonoptimal_cases':sum(g>0 for g in gaps),
            'gap_total':sum(gaps),'gap_max':max(gaps,default=None),'gap_median':statistics.median(gaps) if gaps else None,
            'steps_total':sum(r['audit']['length'] for r in q if r['audit']),
            'sources':dict(Counter(r['source'] for r in q))}
    summary['P2_gap_by_family']={f:{'cases':len(q:=[r for r in records if r['algorithm']=='P2_SHARED' and r['family']==f]),
        'optimal_cases':sum(r.get('gap')==0 for r in q),'gap_total':sum(r.get('gap',0) for r in q)} for f in ('no_change','straight','obstacle','corner_obstacle')}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
