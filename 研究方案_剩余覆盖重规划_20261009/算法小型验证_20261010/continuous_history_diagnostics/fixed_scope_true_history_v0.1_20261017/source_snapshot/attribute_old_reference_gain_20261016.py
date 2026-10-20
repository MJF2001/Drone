"""Saved-result attribution only; no solve calls, no new benchmark timings."""
from collections import Counter
import heapq,statistics
from run_outer_connector_diagnostic_20261016 import *
from verify_outer_connector_diagnostic_20261016 import VERIFY
DEST=BASE/'attribution_v0.1_20261016'
def independent_fallback(c):
    free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']));old=list(map(tuple,c['old_route']))
    current=tuple(c['current']);base=tuple(c['base']);left=targets-covered;visits=[]
    for p in old:
        if p in left and p in free:visits.append(p);left.remove(p)
    visits+=sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0]))
    def path(a,b):
        lo,hi=sorted((a,b));cost={lo:0};parent={};q=[(abs(lo[0]-hi[0])+abs(lo[1]-hi[1]),0,lo)]
        while q:
            _,n,p=heapq.heappop(q)
            if n!=cost[p]:continue
            if p==hi:
                r=[hi]
                while r[-1]!=lo:r.append(parent[r[-1]])
                r.reverse();return r if a==lo else list(reversed(r))
            x,y=p
            for z in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
                if z in free and n+1<cost.get(z,float('inf')):
                    cost[z]=n+1;parent[z]=p;heapq.heappush(q,(n+1+abs(z[0]-hi[0])+abs(z[1]-hi[1]),n+1,z))
        raise AssertionError('unreachable')
    route=[current];covered|={current}&targets
    for p in visits:
        if p in covered:continue
        extension=path(route[-1],p);route+=extension[1:];covered|=set(extension)&targets
    route+=path(route[-1],base)[1:];return route
def main():
    manifest(OUT);manifest(INPUT);manifest(VERIFY)
    assert all(sha(Path(p))==h for p,h in read(OUT/'protocol.json')['protected_hashes'].items())
    import portable_frozen
    from prepare_road_range_diagnostic_20261015 import snapshot
    from unified_geometry import UnifiedGeometry
    from road_range_candidate_20261015 import digest
    records=read(INPUT/'records.json');fallback={};checks=[]
    for e in records:
        c=read(Path(e['case']));r=independent_fallback(c);assert route_check(c,r)['valid']
        s=snapshot(c);g=UnifiedGeometry(s,float('inf'));left=set(s.targets-s.covered);visits=[]
        for p in s.old_route:
            if p in left and p in s.free:visits.append(p);left.remove(p)
        visits+=sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0]))
        assert tuple(r)==g.expand(visits);fallback[e['case']]=r
        checks.append(dict(case=e['case'],steps=len(r)-1,sha256=digest(r),independent_matches_shared=True))
    jobs=read(OUT/'protocol.json')['jobs'];lookup={}
    for j in jobs:
        raw=read(OUT/'runs'/(j['run_id']+'.json'))['raw'];lookup[j['case'],j['budget'],j['method']]=raw
        entries=raw['improvements'] if j['method']=='P2_MULTI' else raw['detail']['acceptances']
        for v in entries:
            label=v.get('source',v.get('label'))
            if label=='common_fallback':assert v['steps']==len(fallback[j['case']])-1
    pairs=[]
    for e in records:
        for b in (1,20):
            l=lookup[e['case'],b,'LITERAL'];p=lookup[e['case'],b,'P2_MULTI'];f=len(fallback[e['case']])-1
            ll=len(l['route'])-1;pp=len(p['route'])-1
            assert ll<=f and pp<=f
            gap=ll-pp;lg=f-ll;pg=f-pp;assert gap==pg-lg
            pairs.append(dict(map_id=e['map_id'],reference=e['reference'],budget=b,fallback_steps=f,local_steps=ll,P2_steps=pp,
                local_gain_over_fallback=lg,P2_gain_over_fallback=pg,gap=gap,
                strict_local_gain=lg>0,local_final_source=l['source'],local_wins=gap<0,
                winning_local_better_than_fallback=gap<0 and lg>0))
    summary=[]
    for ref in ('RAW','P2_REF'):
        for b in (1,20):
            r=[p for p in pairs if p['reference']==ref and p['budget']==b]
            summary.append(dict(reference=ref,budget=b,states=len(r),fallback_sum=sum(v['fallback_steps'] for v in r),local_gain=sum(v['local_gain_over_fallback'] for v in r),P2_gain=sum(v['P2_gain_over_fallback'] for v in r),local_improves_fallback=sum(v['strict_local_gain'] for v in r),local_wins=sum(v['local_wins'] for v in r),winning_local_better_than_fallback=sum(v['winning_local_better_than_fallback'] for v in r)))
    DEST.mkdir(exist_ok=False)
    for name,obj in [('fallback_checks',checks),('paired_decomposition',pairs),('summary',summary)]:write(DEST/(name+'.json'),obj)
    write(DEST/'record.json',dict(new_optimizer_calls=0,offline_reconstructions=20,comparison_pairs=40,original_results_unchanged=True,source_sha256=sha(Path(__file__)),holdout_used=False,limitation='Within-reference arithmetic attribution, not a randomized causal effect or across-reference equal-budget comparison.'))
    write(DEST/'sha256.json',{str(p.relative_to(DEST)):sha(p) for p in DEST.rglob('*') if p.is_file()});print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
