"""Read-only geometry checks, not implementations or rankings of literature methods."""
import csv
import json
from pathlib import Path


def check(raw):
    rows = []
    for d in raw:
        target = set(map(tuple, d['targets']))
        free = set(map(tuple, d['free']))
        covered = set(map(tuple, d['covered']))
        pending = target - covered
        meta = d['metadata']
        rows.append({
            'case': d['name'],
            'family': meta['family'],
            'target_cells': len(target),
            'flight_cells': len(free),
            'target_outside_legal_poses': len(target-free),
            'pending_outside_legal_poses': len(pending-free),
            'legal_poses_outside_targets': len(free-target),
            'new_target_count': meta['new_target_count'],
            'obstacle_cells': len(meta['obstacles']),
            'footprint_radius': d['radius'],
        })
    summary = {'snapshots_checked': len(rows),
        'cases_with_targets_outside_legal_poses': sum(r['target_outside_legal_poses'] > 0 for r in rows),
        'cases_with_pending_outside_legal_poses': sum(r['pending_outside_legal_poses'] > 0 for r in rows),
        'cases_with_legal_transit_outside_targets': sum(r['legal_poses_outside_targets'] > 0 for r in rows),
        'cases_with_expansion': sum(r['new_target_count'] > 0 for r in rows),
        'cases_with_obstacles': sum(r['obstacle_cells'] > 0 for r in rows),
        'cases_with_nonzero_footprint_radius': sum(r['footprint_radius'] > 0 for r in rows),
        'interpretation': 'Model differences only; no literature performance or universal incompatibility claim.'}
    return rows, summary


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    source = root/'results/run_11_fixed_domain_v2/snapshots.json'
    rows, summary = check(json.loads(source.read_text(encoding='utf-8')))
    out = root/'results/literature_fit_audit'
    out.mkdir(exist_ok=True)
    with (out/'cases.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
