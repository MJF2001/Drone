"""Frozen split-rank order: full service versus progress-aware visit skipping.

No rank or order optimisation. Matching GTSP cache warmup isolates path ties.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from model import Geometry
from audit import audit
from scenarios import deserialize
import oarp_replan
from oarp_replan.tour import gtsp_instance
from run_experiments import write_json

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'results/run_17_frozen_partition_ablation'
OUT = ROOT/'results/run_18_frozen_service_skip'


def replay(s, blocks, order, skip):
    g = Geometry(s)
    states,sets,matrix,start,end,penalty = gtsp_instance(g,blocks)
    assert order[0]==start and order[-1]==end
    visits = [p for node in order[1:-1] for p in states[node]]
    assert len(visits)==len(set(visits))
    assert set(visits)==s.targets-s.covered
    begin = time.perf_counter()
    route = [s.current]
    seen = set(s.covered)|{s.current}
    skipped = []
    for index,p in enumerate(visits):
        if skip and p in seen:
            skipped.append({'index':index,'point':p,'at_current_pose':p==route[-1]})
            continue
        extension = g.path(route[-1],p)
        route.extend(extension[1:])
        seen.update(extension)
    route.extend(g.path(route[-1],s.base)[1:])
    return {'route':tuple(route),'length':len(route)-1,'skipped':skipped,
        'replay_seconds_excluding_matrix':time.perf_counter()-begin,'visit_order':visits}


def main():
    OUT.mkdir(exist_ok=False)
    names = ('results.json','input_results.json','input_snapshots.json','manifest.json')
    for n in names:
        (OUT/('input_'+n)).write_bytes((SOURCE/n).read_bytes())
    sources = [Path(__file__),ROOT/'model.py',ROOT/'audit.py',ROOT/'scenarios.py',ROOT/'oarp_replan/tour.py']
    hashes = {}
    for f in sources:
        rel = f.relative_to(ROOT)
        dest = OUT/'source_snapshot'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(f.read_bytes())
        hashes[str(rel)] = hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'protocol':'frozen split ranks, orientations and order; skip only already-covered target visits',
        'source_sha256':hashes,'input_sha256':{n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in names},
        'cache_policy':'fresh Geometry per arm, identical GTSP matrix construction warmup',
        'rank_optimisation':False,'tour_optimisation':False,'held_out':False,'repetitions':1,
        'timing_scope':'postprocessing only, not full planner timing',
        'limits':'unit-step single-cell snapshots, not physical energy or new algorithm'})
    load = lambda n:json.loads((SOURCE/n).read_text(encoding='utf-8'))
    snapshots = {d['name']:deserialize(d) for d in load('input_snapshots.json')}
    original = {(r['case'],r['algorithm']):r for r in load('input_results.json')}
    rows = []
    for frozen in load('results.json'):
        s = snapshots[frozen['case']]
        old = original[frozen['case'],frozen['algorithm']]
        blocks = [{'kind':'rank','path':tuple(map(tuple,r['cells']))} for r in old['detail']['ranks']]
        row = {k:frozen[k] for k in ('case','algorithm','family','p2_length','common_fallback_length')}
        for mode in ('full','skip'):
            result = replay(s,blocks,frozen['split']['order'],mode=='skip')
            result['audit'] = audit(s,result['route'])
            assert result['audit']['valid'],result['audit']
            row[mode] = result
        row['full_matches_saved_route'] = list(map(list,row['full']['route']))==frozen['split']['route']
        assert row['full_matches_saved_route'],'cache or decoding mismatch'
        assert row['skip']['length']<=row['full']['length'],'skipping violated triangle bound'
        assert row['skip']['visit_order']==row['full']['visit_order']
        row['final_before'] = min(row['full']['length'],row['common_fallback_length'])
        row['final_after'] = min(row['skip']['length'],row['common_fallback_length'])
        rows.append(row)
    write_json(OUT/'results.json',rows)
    summary = {}
    for alg in ('OARP_CORE_1','OARP_CORE_2'):
        q = [r for r in rows if r['algorithm']==alg]
        summary[alg] = {
            'cases':len(q),'pure_improved':sum(r['skip']['length']<r['full']['length'] for r in q),
            'pure_equal':sum(r['skip']['length']==r['full']['length'] for r in q),
            'pure_worse':sum(r['skip']['length']>r['full']['length'] for r in q),
            'pure_full_total':sum(r['full']['length'] for r in q),'pure_skip_total':sum(r['skip']['length'] for r in q),
            'final_improved':sum(r['final_after']<r['final_before'] for r in q),
            'final_before_total':sum(r['final_before'] for r in q),'final_after_total':sum(r['final_after'] for r in q),
            'final_vs_p2':dict(Counter('skip_shorter' if r['final_after']<r['p2_length'] else 'equal' if r['final_after']==r['p2_length'] else 'p2_shorter' for r in q)),
            'p2_total':sum(r['p2_length'] for r in q),
            'skip_cases':sum(bool(r['skip']['skipped']) for r in q),
            'skipped_noncurrent_visits':sum(sum(not p['at_current_pose'] for p in r['skip']['skipped']) for r in q),
            'saved_full_route_mismatches':sum(not r['full_matches_saved_route'] for r in q)}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
