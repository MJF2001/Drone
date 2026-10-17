"""Materialize design tables only; no snapshots, solvers or native dependencies.

Use the bundled Python or any Python 3.12. Refuse to overwrite an existing output.
The geometry contract is document 45; this script is NOT the map generator.
"""
from pathlib import Path
from collections import Counter
import argparse
import csv
import hashlib
import json

MASTER = 'residual-scale-design-20261014-v0.1'
EVENTS = ('no_change', 'straight', 'corner', 'obstacle',
          'straight_obstacle', 'corner_obstacle')
# Each pair is development / holdout; no solver results inform these values.
DIMENSIONS = {
    'small': (((20, 3), (17, 4)), ((12, 5), (14, 5)),
              ((16, 3), (19, 4)), ((18, 3), (20, 4))),
    'medium': (((56, 5), (49, 6)), ((32, 9), (38, 8)),
               ((40, 6), (47, 7)), ((44, 6), (51, 8))),
    'large': (((128, 8), (113, 9)), ((80, 14), (93, 12)),
              ((96, 10), (109, 11)), ((104, 10), (121, 12))),
}


def seed_for(*parts):
    raw = '|'.join((MASTER, *map(str, parts))).encode('utf-8')
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], 'big') & 0x7fffffff


def tables():
    maps, states = [], []
    for scale, strata in DIMENSIONS.items():
        for k, pair in enumerate(strata):
            for j, (length, width) in enumerate(pair):
                split = ('development', 'holdout')[j]
                mid = f'{scale}_g{k+1}_{split}'
                ordinal = len(maps)
                arm = ((length + 1) // 2 if j == 0 else (3*length + 4)//5) if k == 2 else 0
                extra = max(1, width//3) if k == 3 else 0
                maps.append(dict(map_id=mid, ordinal=ordinal, split=split, scale=scale,
                    stratum=k+1, length=length, width=width, arm=arm, extra_width=extra,
                    widen_start=length//3 if extra else 0,
                    widen_stop=(2*length+2)//3 if extra else 0,
                    domain_kind='open' if k in (0, 2) else 'corridor',
                    reflect_y=bool(j), base_side='west' if j == 0 else 'east',
                    geometry_seed=seed_for(mid, 'geometry')))
                for h, history in enumerate(('H', 'V')):
                    for p, progress in enumerate((25, 50, 75)):
                        # Six histories/map: three assignments of each level per factor.
                        ratio = (20, 40)[(ordinal+h+p) % 2]
                        shape = ('block', 'barrier')[(ordinal+h+p) % 2]
                        distance = ('near', 'far')[(ordinal+h+p+(p//2)) % 2]
                        turn = ('left', 'right')[(ordinal+h+p) % 2]
                        for event in EVENTS:
                            sid = f'{mid}_{history}_p{progress}_{event}'
                            ext = event in ('straight', 'corner', 'straight_obstacle', 'corner_obstacle')
                            obs = 'obstacle' in event
                            states.append(dict(state_id=sid, map_id=mid, split=split,
                                scale=scale, stratum=k+1, history=history, progress_percent=progress,
                                event=event, extension_percent=ratio if ext else None,
                                turn=turn if event in ('corner', 'corner_obstacle') else None,
                                obstacle_shape=shape if obs else None,
                                obstacle_distance=distance if obs else None,
                                # Shared obstacle per history; independent of expansion variant.
                                obstacle_seed=seed_for(mid, history, progress, 'obstacle') if obs else None,
                                repeat_seed_0=seed_for(sid, 0), repeat_seed_1=seed_for(sid, 1)))
    return maps, states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    maps, states = tables()
    assert len(maps) == 24 and len(states) == 864
    assert len({s['state_id'] for s in states}) == 864
    assert Counter(s['split'] for s in states) == {'development': 432, 'holdout': 432}
    assert Counter(s['event'] for s in states) == dict.fromkeys(EVENTS, 144)
    assert Counter(s['scale'] for s in states) == dict.fromkeys(DIMENSIONS, 288)
    for m in maps:
        # Check six unique history assignments, not correlated event copies.
        ss = [s for s in states if s['map_id'] == m['map_id'] and s['event'] == 'corner_obstacle']
        for key in ('extension_percent', 'turn', 'obstacle_shape', 'obstacle_distance'):
            assert sorted(Counter(s[key] for s in ss).values()) == [3, 3], (m['map_id'], key)
    args.out.mkdir(parents=True, exist_ok=False)
    for filename, rows in [('base_maps.csv', maps), ('state_schedule.csv', states)]:
        with (args.out/filename).open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    protocol = dict(version='scale_design_v0.1_20261014', status='draft_not_frozen',
        master_seed=MASTER, methods=['P2_MULTI','OARP_CORE2','TREE_MST'],
        baseline_version='v2_20261012', budget_seconds=[1,5,20], repeats=2,
        map_count=24, state_count=864, geometry_generated=False, solver_called=False,
        holdout_solver_outputs_seen=False, native_environment_verified=False,
        scope='parameter manifest only; no geometric feasibility or algorithm validation')
    (args.out/'design.json').write_text(json.dumps(protocol, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    files = [args.out/n for n in ('base_maps.csv','state_schedule.csv','design.json')]
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.out/'sha256.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(protocol, ensure_ascii=False))


if __name__ == '__main__':
    main()
