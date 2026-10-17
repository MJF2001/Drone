"""Verify serialized diagnostics independently of the search invocation."""
from pathlib import Path
import argparse
import json
from dataclasses import replace
from collections import Counter
from audit import audit, environment_check
from scenarios import deserialize
from mechanisms import admissible
from run_experiments import write_json


def verify(folder):
    originals = {d['name']: deserialize(d) for d in json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))}
    variants = {d['name']: deserialize(d) for d in json.loads((folder/'sensitivity_snapshots.json').read_text(encoding='utf-8'))}
    mechanisms = json.loads((folder/'mechanism_results.json').read_text(encoding='utf-8'))
    sensitivities = json.loads((folder/'sensitivity_results.json').read_text(encoding='utf-8'))
    errors, checked, baseline_matches = [], 0, 0
    pools = {}
    for r in mechanisms:
        s = originals[r['case']]
        if r['route']:
            for route_key, check_key in [('route', 'audit'), ('skipped_route', 'skipped_audit')]:
                check = audit(s, tuple(map(tuple, r[route_key])))
                checked += 1
                if check != r[check_key] or not check['valid']:
                    errors.append((s.name, r['algorithm'], route_key))
            order = r['order']
            if sorted(order) != list(range(len(r['points']))):
                errors.append((s.name, r['algorithm'], 'not_permutation'))
            mode = ('group' if r['algorithm'].startswith('G') else 'packet') if r['algorithm'].endswith('locked') else 'free'
            if not admissible(order, r['labels'], mode):
                errors.append((s.name, r['algorithm'], 'constraint'))
            key = (s.name, r['algorithm'][0])
            value = (r['points'], r['labels'])
            if key in pools and pools[key] != value:
                errors.append((s.name, 'pool_mismatch'))
            pools[key] = value
        elif r['status'] != 'environment_infeasible' or environment_check(s) != r['reason']:
            errors.append((s.name, r['algorithm'], 'infeasibility'))
    for r in sensitivities:
        s = variants[r['case']]
        if r['radius'] == 1 and r['margin'] == 2:
            original = originals[r['source_case']]
            if replace(s, name=original.name) != original:
                errors.append((s.name, 'baseline_model_changed'))
            else:
                baseline_matches += 1
        if r['route']:
            check = audit(s, tuple(map(tuple, r['route'])))
            checked += 1
            if check != r['audit'] or not check['valid']:
                errors.append((s.name, 'sensitivity_route'))
        elif r['status'] == 'environment_infeasible':
            if environment_check(s) != r['reason']:
                errors.append((s.name, 'infeasibility'))
        elif r['status'] != 'incompatible_current' or s.current in s.free:
            errors.append((s.name, 'unhandled_failure'))
    summary = {'mechanism_records': len(mechanisms), 'sensitivity_records': len(sensitivities),
               'actual_routes_checked': checked, 'unchanged_baseline_snapshots': baseline_matches,
               'errors': errors}
    write_json(folder/'saved_file_verification.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder')
    verify(Path(parser.parse_args().folder))
