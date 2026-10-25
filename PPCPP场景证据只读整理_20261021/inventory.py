"""Read saved JSON only; never import planners, generate routes or search graphs."""
import json, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sources = {}
def read(p):
    data = p.read_bytes()
    sources[str(p.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return json.loads(data.decode('utf-8-sig'))
def pts(v): return set(map(tuple, v))

folder = ROOT / 'PPCPP四方向共同预算正式比较_v0.1_20261020'
prior = ROOT / 'PPCPP_LAST新开发地图验证_v0.1_20261020'
rows = []
for p in sorted((folder / 'inputs').glob('*.json')):
    c = read(p)
    old = read(prior / 'inputs' / p.name)
    assert c == old, p.name
    runs = [read(folder / 'outputs' / f'{p.stem}__{i}__PPCPP.json')['result'] for i in range(3)]
    routes = [r['raw']['route'] for r in runs]
    assert routes[0] == routes[1] == routes[2]
    assert all(r['eligible'] and r['entry_seconds'] <= r['budget'] for r in runs)
    route = routes[0]
    assert route[0] == c['current'] and route[-1] == c['base']
    assert pts(route) <= pts(c['free'])
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:]))
    assert pts(c['targets']) <= pts(c['covered']) | pts(route)
    counts = collections.Counter(t['kind'] for t in runs[0]['raw']['trace'])
    added = pts(c['published_targets']) - pts(c['initial_targets'])
    h = pts(c['covered'])
    adjacent = sum(any((x+dx,y+dy) in h for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))) for x,y in added)
    rows.append(dict(case=p.stem, event=p.stem.split('_')[2], source_equal_LAST=True,
                     added_targets=len(added), added_cells_adjacent_to_history=adjacent,
                     current=c['current'], previous=c['previous'],
                     length=len(route)-1, trace_kinds=dict(counts),
                     mean_ms=sum(r['entry_seconds'] for r in runs)*1000/3))
summary={}
for event in ('straight','corner','obstacle'):
    rr=[r for r in rows if r['event']==event]
    summary[event]=dict(states=len(rr), summed_length=sum(r['length'] for r in rr),
                       mean_ms=sum(r['mean_ms'] for r in rr)/len(rr),
                       trace_kinds=dict(sum((collections.Counter(r['trace_kinds']) for r in rr), collections.Counter())),
                       states_added_adjacent_to_history=sum(r['added_cells_adjacent_to_history']>0 for r in rr))
result=dict(scope='54 saved states and 162 saved native-mode PPCPP outputs; no rerun',
            solver_calls=0, graph_searches=0, new_maps=0, states=rows, summary=summary, source_sha256=sources)
(HERE/'54状态读取核对.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
