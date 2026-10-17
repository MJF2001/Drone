"""Frozen-partition diagnostic. No rank optimisation or outcome-based selection."""
import hashlib
import json
from collections import Counter, deque
from pathlib import Path
import time
import oarp_replan
from oarp_replan.tour import tour_replan
from model import Geometry
from scenarios import deserialize
from audit import audit
from run_experiments import write_json

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'results/run_16_oarp_default_v3'
OUT = ROOT/'results/run_17_frozen_partition_ablation'


def exact_independent(s, blocks):
    """Independent BFS distances and forward subset DP, no planner matrix reuse."""
    if len(blocks) > 12:
        return None
    paths = [tuple(map(tuple,b['path'])) for b in blocks]
    states = [p for path in paths for p in (path,tuple(reversed(path)))]
    cache = {}
    def distance(a,b):
        if a not in cache:
            ds = {a:0}
            q = deque([a])
            while q:
                x,y = q.popleft()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in s.free and p not in ds:
                        ds[p] = ds[x,y]+1
                        q.append(p)
            cache[a] = ds
        return cache[a][b]
    if not states:
        return distance(s.current,s.base)
    dp = {(1<<(j//2),j):distance(s.current,p[0])+len(p)-1 for j,p in enumerate(states)}
    for mask in range(1,1<<len(paths)):
        for j,p in enumerate(states):
            value = dp.get((mask,j))
            if value is None:
                continue
            for k,t in enumerate(states):
                if not mask>>(k//2)&1:
                    key = mask|1<<(k//2),k
                    cost = value+distance(p[-1],t[0])+len(t)-1
                    dp[key] = min(dp.get(key,float('inf')),cost)
    full = (1<<len(paths))-1
    return min(dp[full,j]+distance(p[-1],s.base) for j,p in enumerate(states))


def main():
    OUT.mkdir(exist_ok=False)
    raw = json.loads((SOURCE/'snapshots.json').read_text(encoding='utf-8'))
    previous = json.loads((SOURCE/'results.json').read_text(encoding='utf-8'))
    base = json.loads((SOURCE/'baseline_results.json').read_text(encoding='utf-8'))
    snapshots = {d['name']:deserialize(d) for d in raw}
    indexes = {d['name']:i for i,d in enumerate(raw)}
    p2 = {r['case']:r['audit']['length'] for r in base if r['algorithm']=='P2'}
    files = [Path(__file__),ROOT/'model.py',ROOT/'audit.py',ROOT/'scenarios.py',ROOT/'oarp_replan/tour.py']
    hashes = {}
    for f in files:
        rel = f.relative_to(ROOT)
        dest = OUT/'source_snapshot'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(f.read_bytes())
        hashes[str(rel)] = hashlib.sha256(f.read_bytes()).hexdigest()
    for name in ('snapshots.json','results.json','baseline_results.json'):
        (OUT/('input_'+name)).write_bytes((SOURCE/name).read_bytes())
    write_json(OUT/'manifest.json',{'protocol':'frozen rank partition, retained packets vs independent ranks',
        'source_sha256':hashes,'input_sha256':{n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in ('snapshots.json','results.json','baseline_results.json')},
        'seconds_per_tour':5,'seed':'1000+snapshot_index','mode':'author GLNS default',
        'rank_optimisation_rerun':False,'held_out':False,'repetitions':1,
        'scope':'diagnostic, not new algorithm or original end-to-end reproduction',
        'timing':'tour only; excludes rank optimisation, fallback generation, exact verification',
        'fallback':'same old suffix and scene GD adapter for both modes',
        'exact_limit':12,'exact_scope':'fixed blocks and rigid full-block service only'})
    rows = []
    for prev in previous:
        s = snapshots[prev['case']]
        ranks = prev['detail']['ranks']
        packed = prev['detail']['blocks']
        split = [{'kind':'rank','rank_keys':[(r['axis'],r['cells'][0],r['cells'][-1])], 'path':r['cells']} for r in ranks]
        cells = [tuple(p) for r in ranks for p in r['cells']]
        assert len(cells)==len(set(cells)) and set(cells)==s.targets-s.covered
        assert sum(len(b['rank_keys']) for b in packed)==len(ranks)
        # Same common fallback candidates in both arms; audit before acceptance.
        g = Geometry(s)
        left = set(s.targets-s.covered)
        visits = []
        for p in s.old_route:
            if p in left and p in s.free:
                visits.append(p)
                left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        fallback = [('GD_adapter_fallback',g.expand(visits)),('unchanged_old_suffix',s.old_route)]
        fallback = [(name,route) for name,route in fallback if audit(s,route)['valid']]
        common_name,common_route = min(fallback,key=lambda x:len(x[1]))
        row = {'case':s.name,'algorithm':prev['algorithm'],'family':prev['family'],
            'ranks':len(ranks),'packed_blocks':len(packed),'split_blocks':len(split),
            'common_fallback_length':len(common_route)-1,'common_fallback_source':common_name,'p2_length':p2[s.name]}
        arms = [('packed',packed),('split',split)]
        if indexes[s.name]%2:
            arms.reverse()
        for mode,blocks in arms:
            begin = time.perf_counter()
            gg = Geometry(s,begin+5)
            result = tour_replan(gg,blocks,seconds=5,seed=1000+indexes[s.name])
            elapsed = time.perf_counter()-begin
            check = audit(s,result['route'])
            assert check['valid'],check
            exact = exact_independent(s,blocks)
            assert exact is None or result['length']>=exact
            row[mode] = {'length':result['length'],'route':result['route'],'order':result['order'],
                'audit':check,'seconds':elapsed,'overrun_gt_10ms':elapsed>5.01,
                'solver':result['solver'],'exact':exact,
                'gap':None if exact is None else result['length']-exact,
                'with_common_fallback':min(result['length'],len(common_route)-1)}
        row['packed_matches_previous'] = row['packed']['length']==prev['detail']['tour']['length']
        row['original_final_matches_candidates'] = min(row['packed']['length'],len(common_route)-1)==prev['audit']['length']
        if row['packed']['exact'] is not None and row['split']['exact'] is not None:
            assert row['split']['exact']<=row['packed']['exact'],'nested feasible-set violation'
        rows.append(row)
        write_json(OUT/'results.json',rows)
        print(f"{s.name} {prev['algorithm']}: packed={row['packed']['length']} split={row['split']['length']}",flush=True)
    summary = {}
    for alg in ('OARP_CORE_1','OARP_CORE_2'):
        subset = [r for r in rows if r['algorithm']==alg]
        def compare(field):
            a = [r['packed'][field] for r in subset]
            b = [r['split'][field] for r in subset]
            return {'split_shorter':sum(y<x for x,y in zip(a,b)),'equal':sum(y==x for x,y in zip(a,b)),
                'packed_shorter':sum(y>x for x,y in zip(a,b)),'packed_total':sum(a),'split_total':sum(b)}
        summary[alg] = {'pure_tour':compare('length'),'with_common_fallback':compare('with_common_fallback'),
            'split_final_vs_p2':dict(Counter('split_shorter' if r['split']['with_common_fallback']<r['p2_length'] else 'equal' if r['split']['with_common_fallback']==r['p2_length'] else 'p2_shorter' for r in subset)),
            'p2_total':sum(r['p2_length'] for r in subset),
            'both_exact':sum(r['packed']['exact'] is not None and r['split']['exact'] is not None for r in subset),
            'exact_checks':sum(r[m]['exact'] is not None for r in subset for m in ('packed','split')),
            'positive_heuristic_gaps':sum((r[m]['gap'] or 0)>0 for r in subset for m in ('packed','split')),
            'packed_rerun_differences':sum(not r['packed_matches_previous'] for r in subset),
            'old_final_candidate_differences':sum(not r['original_final_matches_candidates'] for r in subset),
            'overruns':sum(r[m]['overrun_gt_10ms'] for r in subset for m in ('packed','split'))}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
