"""Tiny exact route-splicing mechanism probe, not a timed candidate algorithm."""
from pathlib import Path
from collections import deque
import hashlib,itertools,json,sys,time,traceback

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
OUT=ALGO/'development_range_probes/v0.1_20261015'
sys.path.insert(0,str(ALGO))
from scale_scene_generator_20261014 import path

def adjacent(p):
    x,y=p;return ((x-1,y),(x,y-1),(x,y+1),(x+1,y))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def pointset(c,key):return set(map(tuple,c[key]))

def fixtures():
    result=[]
    free={(x,y) for x in range(13) for y in (0,-2)}|{(0,-1),(12,-1)}|{(x,1) for x in range(3)}
    current=(0,0);base=(12,-2)
    blocks=[dict(label=l,service=[(x,0),(x+1,0)]) for l,x in zip('ABCD',(2,4,6,8))]
    old=[(x,0) for x in range(13)]+[(12,-1),base]
    result.append(build('loop_AB_sufficient',free,current,base,blocks,old,{(1,0)},set(),
        [(12,-2)]+[(x,-2) for x in range(11,-1,-1)]+[(0,-1),current]))
    free={(x,y) for x in range(11) for y in range(-2,3)};current=(0,0);base=(10,-2)
    blocks=[dict(label=l,service=[(x,0),(x,1)]) for l,x in zip('ABCD',(2,4,6,8))]
    old=[current]
    for b in blocks:
        old.extend(path(free,old[-1],b['service'][0])[1:]);old.extend(b['service'][1:])
    old.extend(path(free,old[-1],base)[1:])
    history=[base]+[(x,-2) for x in range(9,-1,-1)]+[(0,-1),current]
    for name,blocked,extra in (
        ('open_boundary_tradeoff',{(1,0)},set()),
        ('return_tail_broken',{(1,0),(8,-1)},set()),
        ('obscured_target',{(1,0),(4,1)},set()),
        ('new_targets_fixed_domain',set(),{(3,2),(4,2)})):
        result.append(build(name,free,current,base,blocks,old,blocked,extra,history))
    return result

def build(name,free,current,base,blocks,old,blocked,extra,history):
    initial={current}|{p for b in blocks for p in b['service']};covered=initial&set(history)
    assert covered=={current} and not blocked&{current,base}
    for b in blocks:
        b['entry_index']=old.index(b['service'][0]);b['exit_index']=old.index(b['service'][-1])
    published=initial|extra
    return dict(name=name,free=sorted(free-blocked),targets=sorted(published-blocked),covered=sorted(covered),
        current=current,base=base,old_route=old,radius=0,distance_budget=200,blocks=blocks,
        metadata=dict(split='constructed_development_fixture',initial_targets=sorted(initial),
            published_targets=sorted(published),obstacles=sorted(blocked),deferred_targets=sorted((published-covered)&blocked),
            historical_prefix=history,initial_free=sorted(free),future_events_available=False))

def cuts(c,scope):
    # Start-prefix only for this primitive: do not pretend interior/multi-window exists.
    if scope not in ('AB','ABC','ALL'):raise ValueError('unknown_scope')
    right=(c['blocks'][2]['entry_index'] if scope=='AB' else
           c['blocks'][3]['entry_index'] if scope=='ABC' else len(c['old_route'])-1)
    return 0,right

def contract(c):
    free=pointset(c,'free');targets=pointset(c,'targets');covered=pointset(c,'covered');m=c['metadata']
    if c['radius']!=0:raise ValueError('radius_not_zero')
    if not targets<=free:raise ValueError('targets_not_free')
    if tuple(c['current']) not in free or tuple(c['base']) not in free:raise ValueError('endpoint_not_free')
    if len(targets-covered)>12 or len(free)>200:raise ValueError('tiny_probe_cap')
    initial=pointset(m,'initial_targets');published=pointset(m,'published_targets');blocked=pointset(m,'obstacles')
    if targets!=published-blocked:raise ValueError('target_ledger')
    if pointset(m,'deferred_targets')!=(published-covered)&blocked:raise ValueError('deferred_ledger')
    old=tuple(map(tuple,c['old_route']))
    if old[0]!=tuple(c['current']) or old[-1]!=tuple(c['base']):raise ValueError('old_endpoints')
    if any(sum(abs(a[i]-b[i]) for i in (0,1))!=1 for a,b in zip(old,old[1:])):raise ValueError('old_step')

def exact_patch(free,required,start,join):
    points=sorted(required);bits={p:1<<i for i,p in enumerate(points)};goal=(1<<len(points))-1
    initial=(start,bits.get(start,0));queue=deque([initial]);parents={initial:None};final=None
    while queue:
        state=queue.popleft();p,mask=state
        if p==join and mask==goal:final=state;break
        for q in adjacent(p):
            child=(q,mask|bits.get(q,0))
            if q in free and child not in parents:parents[child]=state;queue.append(child)
    if final is None:return None,dict(visited_states=len(parents))
    route=[]
    while final is not None:route.append(final[0]);final=parents[final]
    return tuple(reversed(route)),dict(visited_states=len(parents))

def inspect_scope(c,scope):
    contract(c);left,right=cuts(c,scope);old=tuple(map(tuple,c['old_route']));free=pointset(c,'free')
    prefix=old[:left+1];suffix=old[right:];targets=pointset(c,'targets');covered=pointset(c,'covered')
    outside=set(prefix)|set(suffix)
    # Window tasks must be serviced before rejoining; do not credit future suffix coverage early.
    required=((targets-covered)&set(old[left:right])) | (targets-covered-outside)
    required-=set(prefix)
    invalid=[i for i,p in enumerate(old[right:],right) if p not in free]
    affected=[i for i,p in enumerate(old) if p not in free]
    return dict(scope=scope,left=left,right=right,join=old[right],required=sorted(required),
        prefix=prefix,suffix=suffix,invalid_preserved_indices=invalid,all_old_collision_indices=affected,
        local_pending_count=len(required),total_pending_count=len(targets-covered),
        local_pending_fraction=len(required)/len(targets-covered) if targets-covered else 0)

def solve_scope(c,scope):
    begin=time.perf_counter();info=inspect_scope(c,scope)
    if info['invalid_preserved_indices']:
        return dict(status='scope_rejected_preserved_collision',route=None,scope_info=info,
            seconds=time.perf_counter()-begin,not_a_global_infeasibility_claim=True)
    patch,stats=exact_patch(pointset(c,'free'),set(map(tuple,info['required'])),tuple(c['current']),tuple(info['join']))
    if patch is None:
        return dict(status='scope_unreachable',route=None,scope_info=info,search=stats,seconds=time.perf_counter()-begin)
    route=patch+tuple(map(tuple,info['suffix']))[1:]
    return dict(status='exact_scope_route',route=route,patch=patch,scope_info=info,search=stats,
        steps=len(route)-1,patch_steps=len(patch)-1,preserved_tail_steps=len(info['suffix'])-1,
        seconds=time.perf_counter()-begin,resource_satisfied=len(route)-1<=c['distance_budget'])

def main(out):
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir()
    cases=fixtures();protected={str(p):sha(p) for p in (Path(__file__),
        ROOT/'verify_range_interface_probe_20261015.py',ROOT/'test_range_interface_probe_20261015.py',
        ALGO/'scale_scene_generator_20261014.py',ALGO/'prepare_scale_design_20261014.py')}
    bm=json.loads((ALGO/'frozen_baselines/v2_20261012/manifest.json').read_text(encoding='utf-8'))
    protected.update({str(ALGO/'frozen_baselines/v2_20261012/source'/n):h for n,h in bm['source_sha256'].items()})
    assert all(sha(Path(p))==h for p,h in protected.items())
    write(out/'protocol.json',dict(version='range_interface_tiny_v0.1_20261015',cases=[c['name'] for c in cases],
        scopes=['AB','ABC','ALL'],expected_runs=15,holdout_used=False,baseline_solve_called=False,
        objective='Exact tiny constrained splice routes, no soft-budget performance ranking.',
        candidate_selection='All five hand-constructed fixtures saved; not a representative map sample.',
        limitations=['Only start-prefix windows; no interior or multi-window selector.',
            'Fixed literal tail, not a region-visiting flexible policy.',
            'Exact BFS tiny caps, no online range selection or 1/20s comparison.'],
        protected_hashes=protected))
    results=[]
    try:
        for c in cases:
            write(out/'cases'/(c['name']+'.json'),c)
            for scope in ('AB','ABC','ALL'):results.append(dict(case=c['name'],scope=scope,result=solve_scope(c,scope)))
        write(out/'results.json',results)
        assert all(sha(Path(p))==h for p,h in protected.items())
        write(out/'completion.json',dict(status='tiny_primitive_finished_pending_independent_verification',runs=len(results),
            routes=sum(r['result']['route'] is not None for r in results),holdout_used=False,protected_unchanged=True))
        write(out/'sha256.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
        print(json.dumps([dict(case=r['case'],scope=r['scope'],status=r['result']['status'],steps=r['result'].get('steps')) for r in results]))
    except BaseException:
        write(out/'aborted.json',dict(completed=len(results),traceback=traceback.format_exc()));raise

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
