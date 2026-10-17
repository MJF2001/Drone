"""Independent saved-route and skip-reason verification; no planner calls."""
import hashlib
import json
from pathlib import Path
from audit import audit
from scenarios import deserialize

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results/run_18_frozen_service_skip'


def main():
    load = lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    manifest = load('manifest.json')
    errors = []
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    for name,digest in manifest['input_sha256'].items():
        if hashlib.sha256((OUT/('input_'+name)).read_bytes()).hexdigest()!=digest:
            errors.append('input hash '+name)
    snapshots = {d['name']:(deserialize(d),d['metadata']) for d in load('input_input_snapshots.json')}
    prior = {(r['case'],r['algorithm']):r for r in load('input_results.json')}
    ranks = {(r['case'],r['algorithm']):r['detail']['ranks'] for r in load('input_input_results.json')}
    seen_ids = set()
    skipped_checks = 0
    rows = load('results.json')
    for r in rows:
        key = r['case'],r['algorithm']
        if key in seen_ids:
            errors.append('duplicate '+str(key))
        seen_ids.add(key)
        s,meta = snapshots[r['case']]
        if s.radius!=0:
            errors.append('not single-cell')
        frozen = prior[key]
        states = [p for b in ranks[key] for p in (b['cells'],list(reversed(b['cells'])))]
        visits = [p for index in frozen['split']['order'][1:-1] for p in states[index]]
        if len(visits)!=len(set(map(tuple,visits))) or set(map(tuple,visits))!=s.targets-s.covered:
            errors.append('partition '+str(key))
        for mode in ('full','skip'):
            a = r[mode]
            route = tuple(map(tuple,a['route']))
            result = audit(s,route)
            if not result['valid'] or result!=a['audit'] or a['length']!=len(route)-1:
                errors.append('route '+str(key)+mode)
            if set(route)&set(map(tuple,meta['deferred_targets'])):
                errors.append('deferred flown '+str(key))
            if a['visit_order']!=visits:
                errors.append('changed service order '+str(key))
        if r['full']['route']!=frozen['split']['route']:
            errors.append('changed reference '+str(key))
        # Walk saved actual path and original visits. A skipped visit must have
        # appeared before the CURRENT route pointer, not merely later on route.
        path = list(map(tuple,r['skip']['route']))
        seen = set(s.covered)|{path[0]}
        cursor = 0
        skipped = {e['index']:e for e in r['skip']['skipped']}
        if len(skipped)!=len(r['skip']['skipped']):
            errors.append('duplicate skip index '+str(key))
        for index,raw in enumerate(visits):
            p = tuple(raw)
            if index in skipped:
                event = skipped[index]
                if p not in seen or tuple(event['point'])!=p or event['at_current_pose']!=(p==path[cursor]):
                    errors.append('unjustified skip '+str(key)+str(index))
                skipped_checks+=1
                continue
            if p in seen:
                errors.append('skip policy mismatch '+str(key)+str(index))
            while cursor<len(path)-1 and path[cursor]!=p:
                cursor+=1
                seen.add(path[cursor])
            if path[cursor]!=p:
                errors.append('missing ordered visit '+str(key)+str(index))
        if r['skip']['length']>r['full']['length']:
            errors.append('worse route '+str(key))
        if r['final_after']!=min(r['skip']['length'],r['common_fallback_length']) or r['final_before']!=frozen['split']['with_common_fallback']:
            errors.append('candidate accounting '+str(key))
    if len(seen_ids)!=128:
        errors.append('expected 128 pairs')
    result = {'paired_orders':len(rows),'routes_checked':2*len(rows),'skip_reasons_checked':skipped_checks,
        'errors':errors,'scope':'independent audit, frozen visits and reference route, prior-coverage justification for every skipped visit, ledger and archived hashes; no optimisation optimality claim'}
    (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors


if __name__=='__main__':
    main()
