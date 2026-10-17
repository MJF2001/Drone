"""All 96 predeclared cases, exact reference and unchanged candidates."""
from pathlib import Path
from collections import Counter
import hashlib,json
from scenarios_stress import cases
from scenarios import serialize,deserialize
from exact_grid_coverage import exact_coverage
from structure_candidates import solve_candidate
from audit import audit
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_22_structural_stress'
ALGORITHMS=('P2_SHARED','STRIP_HV','TREE_MST')


def main():
    OUT.mkdir(exist_ok=False)
    raw=[serialize(s,m) for s,m in cases()]
    assert len(raw)==96
    write_json(OUT/'snapshots.json',raw)
    names=('run_structural_stress.py','scenarios_stress.py','exact_grid_coverage.py',
        'structure_candidates.py','model.py','audit.py','scenarios.py','scenarios_v2.py','planners.py',
        'oarp_replan/ranks.py','oarp_replan/tour.py')
    hashes={}
    for name in names:
        f=ROOT/name;dest=OUT/'source_snapshot'/name
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes())
        hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'date':'2026-10-11','protocol':'96 structural snapshots frozen before first algorithm result',
        'source_sha256':hashes,'snapshots_sha256':hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest(),
        'factorial':'3 shapes x 2 domains x 2 initial scan orientations x 2 progress levels x 4 events',
        'no_outcome_filtering':True,'history_groups':24,'heuristic_seconds':5,'exact_seconds':30,'max_pending':12,
        'seed':'5000+case_index for GLNS; 20261011+history_group for obstacle placement',
        'repetitions':1,'algorithms':'unchanged run20 engineering candidates; common fallback, cyclic order',
        'scope':'purposeful small structural stress, not real occurrence frequencies or large-map validation'})
    records=[]
    for index,d in enumerate(raw):
        s=deserialize(d)
        if d['metadata']['environment_reason']:
            records.append({'case':s.name,'algorithm':'EXACT_GRID','status':'environment_infeasible',
                'route':(),'audit':None,'reason':d['metadata']['environment_reason']})
        else:
            exact=exact_coverage(s)
            exact.update({'case':s.name,'algorithm':'EXACT_GRID','audit':audit(s,exact['route']) if exact['route'] else None})
            records.append(exact)
        for alg in ALGORITHMS[index%3:]+ALGORITHMS[:index%3]:
            result=solve_candidate(s,alg,5,5000+index)
            result.update({'case':s.name})
            reference=next(r for r in reversed(records) if r['case']==s.name and r['algorithm']=='EXACT_GRID')
            if reference['status']=='optimal' and result['audit']:
                result['gap']=result['audit']['length']-reference['length']
                assert result['gap']>=0
            records.append(result)
        write_json(OUT/'results.json',records)
        print(s.name+': '+str([(r['algorithm'],r['audit']['length'] if r['audit'] else r['status'],r.get('gap')) for r in records[-4:]]),flush=True)
    summary={'snapshots':96,'history_groups':24,'exact_statuses':dict(Counter(r['status'] for r in records if r['algorithm']=='EXACT_GRID')),'algorithms':{}}
    for alg in ALGORITHMS:
        q=[r for r in records if r['algorithm']==alg];gaps=[r['gap'] for r in q if 'gap' in r]
        summary['algorithms'][alg]={'statuses':dict(Counter(r['status'] for r in q)),
            'matched_exact':len(gaps),'optimal_cases':sum(g==0 for g in gaps),'gap_total':sum(gaps),
            'gap_max':max(gaps,default=None),'steps_total':sum(r['audit']['length'] for r in q if r['audit']),
            'overruns_gt_10ms':sum(r.get('overrun_gt_10ms',False) for r in q)}
    exacts={r['case']:r for r in records if r['algorithm']=='EXACT_GRID'}
    summary['exact_steps_total']=sum(r['length'] for r in exacts.values() if r['status']=='optimal')
    meta={d['name']:d['metadata'] for d in raw}
    for factor in ('shape','family','orientation','requested_progress','domain_kind'):
        summary['P2_by_'+factor]={}
        for value in sorted({m[factor] for m in meta.values()}):
            q=[r for r in records if r['algorithm']=='P2_SHARED' and meta[r['case']][factor]==value]
            summary['P2_by_'+factor][str(value)]={'cases':len(q),'optimal':sum(r.get('gap')==0 for r in q),
                'gap_total':sum(r.get('gap',0) for r in q)}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
