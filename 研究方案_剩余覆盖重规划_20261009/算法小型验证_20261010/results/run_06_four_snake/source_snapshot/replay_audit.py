"""Replay independent checks on saved actual paths, without invoking planners."""
from pathlib import Path
import argparse
import json
from audit import audit, environment_check
from scenarios import deserialize


def replay(folder):
    cases = {s['name']: deserialize(s) for s in json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))}
    records = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    errors = []
    for r in records:
        s = cases[r['case']]
        reason = environment_check(s)
        if r['route']:
            check = audit(s, tuple(map(tuple, r['route'])))
            if check != r['audit'] or not check['valid']:
                errors.append([r['case'], r['algorithm'], r['repeat'], 'audit_mismatch'])
        elif reason != r['reason'] or r['status'] != 'environment_infeasible':
            errors.append([r['case'], r['algorithm'], r['repeat'], 'infeasible_mismatch'])
    print(json.dumps({'checked': len(records), 'errors': errors}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', nargs='?', default='results/run_01')
    replay(Path(parser.parse_args().folder))
