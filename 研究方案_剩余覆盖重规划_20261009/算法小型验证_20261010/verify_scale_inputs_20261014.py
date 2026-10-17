"""Read saved development input artifacts; no generator or solver imports.

Independent DFS + route-set checks for every record; also call the frozen
historical auditor on one geometric witness per base map. Does not benchmark.
"""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import argparse
import hashlib
import importlib.util
import json


def points(raw): return set(map(tuple,raw))


def sha_object(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),
                                    ensure_ascii=False).encode('utf-8')).hexdigest()


def connected(free,start):
    seen = {start}; todo = [start]
    while todo:
        x,y=todo.pop()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in free and p not in seen:seen.add(p);todo.append(p)
    return seen


def check_walk(route,free,start,end):
    assert route and route[0]==start and route[-1]==end
    assert set(route)<=free
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();src=args.input;out=args.out
    out.mkdir(parents=True,exist_ok=False)
    hashes=json.loads((src/'sha256.json').read_text())
    for name,value in hashes['artifacts'].items():
        assert hashlib.sha256((src/name).read_bytes()).hexdigest()==value,(name,'hash_mismatch')
    code=Path(__file__).parent
    for name,value in hashes['sources'].items():
        assert hashlib.sha256((code/name).read_bytes()).hexdigest()==value,(name,'source_changed')
    audit_path=code/'frozen_baselines/v2_20261012/source/audit.py'
    spec=importlib.util.spec_from_file_location('_independent_frozen_audit',audit_path)
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    maps={}
    for file in src.glob('*_development.json'):
        record=json.loads(file.read_text());maps[record['parameters']['map_id']]=record
    ledger=json.loads((src/'generation_ledger.json').read_text())
    ledger_by_id={r['state_id']:r for r in ledger}
    witnesses={r['state_id']:r['route'] for r in map(json.loads,(src/'witnesses.jsonl').open())}
    verified=[];reference_maps=set();obstacle_groups={};extension_groups={};history_groups={}
    clips=[];ranges=[]
    with (src/'snapshots.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            s=json.loads(line);sid=s['name'];meta=s['metadata'];mid=meta['map_id'];mp=maps[mid]
            assert meta['split']=='development' and mp['parameters']['split']=='development'
            assert sha_object(s)==ledger_by_id[sid]['snapshot_sha256']
            free,targets,covered=map(points,(s['free'],s['targets'],s['covered']))
            old,published,blocked,deferred=map(points,(meta['initial_targets'],meta['published_targets'],meta['obstacles'],meta['deferred_targets']))
            domain=points(mp['domain']);start=tuple(s['current']);base=tuple(s['base'])
            assert old==points(mp['initial_targets']) and base==tuple(mp['base'])
            assert free==domain-blocked and targets==published-blocked and targets<=free
            assert old<=published and covered<=old and deferred==(published-covered)&blocked
            assert not deferred & covered and s['radius']==0
            prefix=tuple(map(tuple,meta['prefix']));suffix=tuple(map(tuple,s['old_route']))
            full=tuple(map(tuple,mp['routes'][meta['history']]))
            check_walk(full,domain,base,base);check_walk(prefix,domain,base,start)
            assert prefix+suffix[1:]==full and suffix[0]==start
            assert covered==old & set(prefix)
            percent=meta['progress_percent']
            assert 100*len(covered)>=percent*len(old)
            assert 100*len(old & set(prefix[:-1]))<percent*len(old)
            assert start in free and base in free
            seen=connected(free,start)
            assert base in seen and targets-covered<=seen
            route=tuple(map(tuple,witnesses[sid]));check_walk(route,free,start,base)
            assert targets-covered<=set(route)
            assert s['distance_budget']==max(1,2*(len(route)-1))
            assert sha_object(route)==meta['witness_sha256']==ledger_by_id[sid]['witness_sha256']
            hk=(mid,meta['history'],percent)
            current_history=(start,tuple(sorted(covered)),prefix,suffix)
            assert history_groups.setdefault(hk,current_history)==current_history
            if 'obstacle' in meta['event']:
                assert blocked and blocked & (old-covered) and blocked & set(suffix)
                assert not blocked & {base,start}
                assert obstacle_groups.setdefault(hk,blocked)==blocked
                assert len(meta['placement']['attempts'])<=64
            else:assert not blocked
            ext=meta['event'].replace('_obstacle','')
            if ext in ('straight','corner'):
                extra=published-old
                assert extra and extra<=domain
                assert extension_groups.setdefault((hk,ext),extra)==extra
                assert meta['extension']['actual_fraction']==len(extra)/len(old)
                if meta['extension']['minimum_corner_size_clipped']:clips.append(sid)
            else:assert published==old
            if mid not in reference_maps:
                audit_snapshot=SimpleNamespace(free=free,targets=targets,covered=covered,
                    current=start,base=base,radius=0,distance_budget=s['distance_budget'])
                checked=reference.audit(audit_snapshot,route)
                assert checked['valid'],(sid,checked)
                reference_maps.add(mid)
            ranges.append(dict(state_id=sid,scale=meta['scale'],event=meta['event'],**meta['counts']))
            verified.append(sid)
    assert len(set(verified))==len(verified)==len(witnesses)
    generated=[r['state_id'] for r in ledger if r['status']=='generated']
    assert set(generated)==set(verified)
    assert len(ledger)==json.loads((src/'protocol.json').read_text())['expected_states']
    # Verify reproducibility from a clean in-memory reconstruction of every
    # generated record without calling any of the three planning algorithms.
    summary=dict(status='verified_development_geometry_not_benchmark',
        verified_states=len(verified),base_maps=len(maps),
        frozen_audit_witness_checks=len(reference_maps),generation_failures=len(ledger)-len(verified),
        clipped_corner_states=len(clips),hashes_verified=True,holdout_generated=False,
        solver_called=False,counts_by_scale=dict(Counter(r['scale'] for r in ranges)),
        counts_by_event=dict(Counter(r['event'] for r in ranges)),
        frozen_audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    for name,obj in [('summary.json',summary),('per_state_counts.json',ranges),('clipped_corner_states.json',clips)]:
        with (out/name).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
