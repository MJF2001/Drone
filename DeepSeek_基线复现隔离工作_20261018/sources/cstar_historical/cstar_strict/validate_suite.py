"""Deterministic cross-radius reproduction checks; no ground-truth planner input."""
import argparse
import hashlib
import json
from pathlib import Path
from geometry import World, coverage_audit, segment_free
from planner import CStar
from run import scenarios


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',type=int,default=15)
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'results'/'validation.json')
    args=parser.parse_args()
    rows=[]
    for radius in (1,2,3,5):
        for seed in range(args.seeds):
            for name,free,start,_,_ in scenarios(seed):
                if seed and name!='clutter':
                    continue
                for holes in (False,True):
                    p=CStar(start,World(free,radius).observe,seed=seed,holes=holes).run()
                    audit=coverage_audit(free,p.path,rc=.75,subdivisions=4)
                    audit.pop('missing_sample_points')
                    known=set(); temporal_ok=len(p.path)==len(p.observations)
                    for i,obs in enumerate(p.observations):
                        if i and not segment_free(p.path[i-1],p.path[i],known):
                            temporal_ok=False
                        known.update((x,y) for x,y,v in obs if v)
                    ok=(p.status=='graph_exhausted' and temporal_ok and
                        audit['collisions']==0 and audit['certified_area_lower_bound']==1.)
                    rows.append(dict(map=name,seed=seed,radius=radius,holes=holes,
                                     status=p.status,temporal_ok=temporal_ok,passed=ok,
                                     error=getattr(p,'error',None),**audit))
                    if not ok:
                        print('FAIL',name,seed,radius,holes,p.status,audit,flush=True)
        print('Completed radius',radius,flush=True)
    root=Path(__file__).parent
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ('planner.py','rcg.py','geometry.py','run.py','validate_suite.py','test_strict.py')}
    result=dict(config=dict(seeds=args.seeds,radii=[1,2,3,5],rc=.75,w=1,subdivisions=4),
                source_sha256=hashes,total=len(rows),passed=sum(r['passed'] for r in rows),runs=rows)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(f"Passed {result['passed']}/{result['total']}",flush=True)
    if result['passed']!=result['total']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
