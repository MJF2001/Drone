"""Read saved evidence only; no planner imports/calls, no experiment writes."""
from pathlib import Path
import hashlib
import itertools
import json

ROOT = Path(__file__).resolve().parent
D = ROOT / '研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/continuous_history_diagnostics/fixed_scope_true_history_v0.1_20261017'
GROUPS = ('large_g4_development', 'small_g4_development', 'large_g1_development')
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    protocol = read(D / 'protocol.json')
    evidence = {'planner_calls': 0, 'protocol_sha256': sha(D / 'protocol.json'), 'states': {}, 'runs': []}
    for j in protocol['jobs']:
        if j['map_id'] not in GROUPS or j['method'] == 'P2_MULTI':
            continue
        path = D / 'formal' / (j['run_id'] + '.json')
        x = read(path); r = x['raw']; d = r['detail']; e = d.get('engine', {})
        cpath = Path(j['case']); c = read(cpath)
        assert sha(cpath) == j['case_sha256']
        plan = d['range_plan']; cfg = plan['plans'][j['method'].replace('RANGE_', 'R_')]
        initial = set(map(tuple, c['metadata']['initial_targets']))
        targets = set(map(tuple, c['targets'])); covered = set(map(tuple, c['covered']))
        free = set(map(tuple, c['free'])); req = set(map(tuple, cfg['required']))
        route = list(map(tuple, r['route'])); seen = covered | {tuple(c['current'])}; service = []
        assert route[0] == tuple(c['current']) and route[-1] == tuple(c['base'])
        assert set(route) <= free and targets - covered <= set(route)
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:]))
        for cell in route[1:]:
            if cell in targets and cell not in seen:
                service.append('old' if cell in initial else 'new'); seen.add(cell)
        evidence['states'][j['map_id']] = {
            'event': c['metadata']['event'], 'case_path': str(cpath), 'case_sha256': sha(cpath),
            'old_collision_indices': plan['old_collision_indices'],
            'new_components': [{'cells': len(z['cells']), 'anchor_index': z['anchor_index']} for z in plan['new_components']],
        }
        row = dict(run_id=j['run_id'], map_id=j['map_id'], budget=j['budget'], repeat=j['repeat'], method=j['method'],
                   raw_path=str(path), raw_sha256=sha(path), steps=len(route)-1, source=r['source'],
                   engine_status=e.get('status'), engine_stage=e.get('active_stage'),
                   patch_steps=len(r['core_patch'])-1, outside_steps=cfg['prefix_steps']+cfg['suffix_steps'],
                   scope={k:cfg[k] for k in ('left','right','start','join','required_count','pending_count','prefix_steps','suffix_steps')},
                   required_old=len(req & initial), required_new=len(req-initial),
                   acceptances=d['acceptances'], engine_events=e.get('events',[]),
                   service_runs=[(k,len(list(v))) for k,v in itertools.groupby(service)])
        if j['map_id']=='small_g4_development' and j['method']=='RANGE_PLUS1':
            a,b=cfg['start'],cfg['join']; lower=abs(a[0]-b[0])+abs(a[1]-b[1])+row['outside_steps']
            assert cfg['required_count']==0 and lower==46 and row['steps']==46
            assert r['core_route']==c['old_route'] and r['route']==c['old_route']
            row['fixed_scope_manhattan_lower_bound']=lower
        evidence['runs'].append(row)
    assert len(evidence['runs'])==48
    evidence['seed_feasible_under_plus1'] = []
    for b, rep in itertools.product((1,20),(0,1)):
        records = [z for z in evidence['runs'] if z['map_id']=='large_g4_development' and z['budget']==b and z['repeat']==rep]
        seed = next(z for z in records if z['method']=='RANGE_SEED')
        plus = next(z for z in records if z['method']=='RANGE_PLUS1')
        s = read(Path(seed['raw_path']))['raw']; p = read(Path(plus['raw_path']))['raw']
        cfg = p['detail']['range_plan']['plans']['R_PLUS1']
        c = read(Path(evidence['states']['large_g4_development']['case_path']))
        route = s['route']; prefix = c['old_route'][:cfg['left']+1]; suffix = c['old_route'][cfg['right']:]
        patch = route[cfg['left']:len(route)-cfg['suffix_steps']]
        assert route[:len(prefix)]==prefix and route[-len(suffix):]==suffix
        assert patch[0]==cfg['start'] and patch[-1]==cfg['join']
        assert set(map(tuple,cfg['required']))<=set(map(tuple,patch))
        assert len(route)-1<=c['distance_budget']
        evidence['seed_feasible_under_plus1'].append(dict(budget=b,repeat=rep,steps=len(route)-1,valid=True))
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
