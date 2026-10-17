"""Instrument unchanged P2 stages. Timing instrumentation is not a benchmark."""
from pathlib import Path
from collections import Counter
import hashlib,json,time
from model import Geometry
from scenarios import deserialize
from planners import candidates,nearest,two_opt
from audit import audit
from run_experiments import write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_24_p2_stage_profile'
INPUT=ROOT/'results/run_23_budget_quality/snapshots.json'


class ProfileGeometry(Geometry):
    def __init__(self,*args,**kwargs):
        self.counts=Counter()
        super().__init__(*args,**kwargs)
    def distance(self,a,b):
        self.counts['distance_calls']+=1
        return super().distance(a,b)
    def path(self,a,b):
        self.counts['path_calls']+=1
        self.counts['cached_path_calls' if (a,b) in self.cache else 'uncached_path_calls']+=1
        begin=time.perf_counter()
        result=super().path(a,b)
        self.counts['path_seconds_inclusive']+=time.perf_counter()-begin
        return result


def profile(s):
    begin=time.perf_counter();stages=[];events=[];best=None;source=None;g=None
    def stage(name,fn):
        before=Counter(g.counts) if g else Counter()
        start=time.perf_counter();value=fn();elapsed=time.perf_counter()-start
        counts=Counter(g.counts) if g else Counter()
        stages.append({'name':name,'seconds':elapsed,
            'counts':{k:counts[k]-before[k] for k in counts}})
        return value
    def offer(route,label):
        nonlocal best,source
        check=audit(s,route) if route else None
        improved=bool(check and check['valid'] and (best is None or len(route)<len(best)))
        if improved:best,source=tuple(route),label
        events.append({'time':time.perf_counter()-begin,'label':label,
            'valid':bool(check and check['valid']),'length':check['length'] if check else None,
            'improved':improved,'incumbent_length':len(best)-1 if best else None})
    start=time.perf_counter();g=ProfileGeometry(s,begin+60)
    stages.append({'name':'geometry','seconds':time.perf_counter()-start,'counts':{}})
    assert stage('precheck',g.precheck) is None
    stage('old_suffix_validate',lambda:offer(s.old_route,'common_old_suffix'))
    def fallback():
        left=set(s.targets-s.covered);visits=[]
        for p in s.old_route:
            if p in left and p in s.free:visits.append(p);left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        return g.expand(visits)
    route=stage('GD_expand',fallback)
    stage('GD_validate',lambda:offer(route,'common_GD_adapter'))
    demand=s.targets-s.covered-g.views[s.current]
    for direction in ('H','V'):
        points=stage(direction+'_candidates',lambda:candidates(g,demand,direction))
        route=stage(direction+'_snake_expand',lambda:g.expand(points))
        stage(direction+'_snake_validate',lambda:offer(route,'P2_search'))
        nn=stage(direction+'_nearest',lambda:nearest(g,points))
        route=stage(direction+'_NN_expand',lambda:g.expand(nn))
        stage(direction+'_NN_validate',lambda:offer(route,'P2_search'))
        for label,seed in (('snake',points),('NN',nn)):
            visits=stage(direction+'_'+label+'_2opt',lambda:two_opt(g,seed))
            route=stage(direction+'_'+label+'_2opt_expand',lambda:g.expand(visits))
            stage(direction+'_'+label+'_2opt_validate',lambda:offer(route,'P2_search'))
    return {'case':s.name,'route':best,'source':source,'audit':audit(s,best),
        'seconds':time.perf_counter()-begin,'stages':stages,'events':events,
        'counts':dict(g.counts),'Astar_searches':g.searches}


def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'snapshots.json').write_bytes(INPUT.read_bytes())
    raw=json.loads(INPUT.read_text(encoding='utf-8'))
    prev=json.loads((ROOT/'results/run_23_budget_quality/results.json').read_text(encoding='utf-8'))
    refs={r['case']:r for r in prev if r['algorithm']=='P2_SHARED' and r['budget']==20 and r['repeat']==0}
    hashes={}
    for name in ('profile_p2_stages.py','model.py','planners.py','audit.py','scenarios.py'):
        p=ROOT/name;dest=OUT/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(p.read_bytes());hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'purpose':'stage attribution and candidate timeline, not fair timing comparison',
        'input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'source_sha256':hashes,
        'budget':60,'repeats':1,'instrumentation_overhead':True,'algorithm_changes':False})
    rows=[]
    for d in raw:
        r=profile(deserialize(d));r['same_route_as_uninstrumented_20s']=list(map(list,r['route']))==refs[r['case']]['route']
        assert r['same_route_as_uninstrumented_20s']
        rows.append(r);write_json(OUT/'results.json',rows)
        print(r['case']+' '+str(round(r['seconds'],3)),flush=True)
    grouped=Counter()
    for r in rows:
        for stage in r['stages']:
            name=stage['name']
            category=('nearest' if name.endswith('_nearest') else '2opt' if name.endswith('_2opt') else
                'route_validation' if name.endswith('_validate') else 'route_expansion' if name.endswith('_expand') else
                'candidate_generation' if name.endswith('_candidates') else name)
            grouped[category]+=stage['seconds']
    total=sum(grouped.values())
    write_json(OUT/'summary.json',{'cases':len(rows),'same_saved_routes':sum(r['same_route_as_uninstrumented_20s'] for r in rows),
        'stage_seconds':dict(grouped),'stage_fraction':{k:v/total for k,v in grouped.items()},
        'counts':dict(sum((Counter(r['counts']) for r in rows),Counter())),
        'Astar_searches':sum(r['Astar_searches'] for r in rows),'instrumented_stage_total':total})


if __name__=='__main__':main()
