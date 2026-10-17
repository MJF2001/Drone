"""Verify serialized paths, incumbents and complete-pool coverage independently."""
import argparse
import json
from pathlib import Path
from audit import audit
from scenarios import deserialize
from run_experiments import write_json


def verify(folder):
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    source = Path(manifest['source'])
    source_manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    cases = {r['name']:deserialize(r) for r in json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))}
    records = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    previous = {r['case']:r['audit']['length'] for r in json.loads((source/'results.json').read_text(encoding='utf-8'))
                if r['algorithm']=='P2'}
    errors, pools_checked = [], 0
    for name in ('planners.py','model.py','audit.py'):
        if manifest['source_sha256'][name] != source_manifest['source_sha256'][name]:
            errors.append([name,'baseline_source_changed'])
    for r in records:
        s = cases[r['case']]
        check = audit(s,tuple(map(tuple,r['route'])))
        if check != r['audit'] or not check['valid']:
            errors.append([s.name,r['algorithm'],r['repeat'],'route_audit'])
        if r['algorithm']=='P2':
            if check['length'] != previous[s.name]:
                errors.append([s.name,'baseline_mismatch'])
            continue
        if r['baseline_stage_length'] != previous[s.name] or check['length'] > previous[s.name]:
            errors.append([s.name,r['algorithm'],'incumbent_not_preserved'])
        for log in r['logs']:
            if not log['completed']:
                continue
            pools_checked += 1
            points = set(map(tuple,log['points']))
            if not points <= s.free or len(points) != len(log['points']):
                errors.append([s.name,r['algorithm'],'illegal_or_duplicate_centres'])
            seen = set(s.covered)
            for x,y in s.targets-seen:
                if any(max(abs(x-p[0]),abs(y-p[1]))<=s.radius for p in points|{s.current}):
                    seen.add((x,y))
            if not s.targets <= seen:
                errors.append([s.name,r['algorithm'],'pool_coverage'])
            for candidate in log['candidates']:
                if set(map(tuple,candidate['visits'])) != points or len(candidate['visits'])!=len(points):
                    errors.append([s.name,r['algorithm'],'ordering_changed_point_pool'])
        origin = r['source']
        if origin.get('kind')=='old_suffix':
            if tuple(map(tuple,r['route'])) != s.old_route:
                errors.append([s.name,'old_suffix_source_mismatch'])
        else:
            matched = [c for log in r['logs'] if log['phase_index']==origin['phase_index']
                and log['direction']==origin['direction'] for c in log['candidates']
                if c['label']==origin['label']]
            if len(matched)!=1 or not matched[0]['valid'] or matched[0]['length']!=check['length']:
                errors.append([s.name,r['algorithm'],'winning_source_mismatch'])
    summary = {'output_routes_checked':len(records),'completed_pools_checked':pools_checked,
               'unchanged_baseline_source_files':3,'errors':errors}
    write_json(folder/'saved_file_verification.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('folder')
    verify(Path(p.parse_args().folder))
