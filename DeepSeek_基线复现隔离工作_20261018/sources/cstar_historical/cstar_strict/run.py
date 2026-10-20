"""Repeatable unknown-world experiments, independently audited after planning."""
from pathlib import Path
import argparse
import json
import math
import random
import time
from geometry import World,connected,coverage_audit,dist
from planner import CStar

def scenarios(seed):
    w,h=20,16
    base={(x,y) for x in range(w) for y in range(h)}
    start=(w-2,1)
    yield 'empty',base,start,w,h
    blocks=base-{(x,y) for a,b,c,d in [(4,4,7,11),(11,2,14,6),(12,10,17,13)] for x in range(a,c) for y in range(b,d)}
    yield 'blocks',blocks,start,w,h
    rooms=base-{(9,y) for y in range(h) if y not in (3,4,12)}
    rooms-={(x,8) for x in range(w) if x not in (3,4,15,16)}
    yield 'rooms',rooms,start,w,h
    rng=random.Random(seed)
    clutter=set(base)
    for _ in range(12):
        x,y=rng.randrange(2,w-3),rng.randrange(2,h-3)
        clutter-={(x+a,y+b) for a in range(rng.randrange(1,4)) for b in range(rng.randrange(1,4))}
    yield 'clutter',connected(clutter,start),start,w,h

def main():
    args=argparse.ArgumentParser()
    args.add_argument('--seeds',type=int,default=3)
    args.add_argument('--radius',type=float,default=5)
    args.add_argument('--rc',type=float,default=.75)
    args.add_argument('--subdivisions',type=int,default=4)
    args.add_argument('--out',type=Path,default=Path(__file__).parent/'results')
    args.add_argument('--ablation',action='store_true')
    args.add_argument('--require-full-coverage',action='store_true',
                      help='Fail unless the conservative continuous-area certificate is 100%%')
    args=args.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    rows=[];traces=[]
    for seed in range(args.seeds):
        for name,free,start,w,h in scenarios(seed):
            if seed and name!='clutter':
                continue
            for holes in ((True,False) if args.ablation else (True,)):
                began=time.perf_counter()
                p=CStar(start,World(free,args.radius).observe,seed=seed,holes=holes).run()
                seconds=time.perf_counter()-began
                audit=coverage_audit(free,p.path,args.rc,args.subdivisions)
                missing=audit.pop('missing_sample_points')
                turns=0;last=None;angle_total=0.
                for a,b in zip(p.path,p.path[1:]):
                    angle=round(math.atan2(b[1]-a[1],b[0]-a[0]),8)
                    if last is not None:
                        change=abs(angle-last)%(2*math.pi)
                        angle_total+=min(change,2*math.pi-change)
                    turns+=int(last is not None and angle!=last);last=angle
                row=dict(map=name,seed=seed,holes=holes,status=p.status,error=getattr(p,'error',None),
                         length=round(sum(dist(a,b) for a,b in zip(p.path,p.path[1:])),4),turns=turns,
                         paper_turns=int(math.floor(angle_total/(math.pi/2)+1e-6)),
                         seconds=round(seconds,4),iterations=len(p.history),links=p.graph.link_count,
                         keep_open=p.keep_open_count,tsp_events=sum(e['type']=='tsp' for e in p.events),
                         retreats=p.retreat_count,added=p.graph.total_added,pruned=p.graph.total_pruned,
                         peak_nodes=max(len(s['nodes']) for s in p.history) if p.history else 0,**audit)
                rows.append(row);print(json.dumps(row),flush=True)
                if seed==0 and holes:
                    traces.append(dict(name=name,width=w,height=h,free=sorted(free),path=p.path,modes=p.modes,
                                       observations=p.observations,history=p.history,events=p.events,metrics=row,
                                       missing=missing,rc=args.rc))
    (args.out/'metrics.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    (args.out/'traces.json').write_text(json.dumps(traces),encoding='utf8')
    (args.out/'config.json').write_text(json.dumps(dict(seeds=args.seeds,radius=args.radius,rc=args.rc,
                    subdivisions=args.subdivisions,ablation=args.ablation,
                    require_full_coverage=args.require_full_coverage,w=1,paper='2505.13782v3'),indent=2),encoding='utf8')
    if any(r['status']!='graph_exhausted' or r['collisions'] or
           r['uncovered_interior_samples'] or
           (args.require_full_coverage and r['certified_area_lower_bound']<1.) for r in rows):
        raise SystemExit(1)

if __name__=='__main__':
    main()
