"""Finite, original-version, independent-history event experiment for the report."""
from pathlib import Path
import collections, hashlib, json, math, os, subprocess, sys, time

H = Path(__file__).resolve().parent
ROOT = H.parent
OUT = H / '七算法从零起飞事件演示_v0.1'
OLD = ROOT / '七算法共同预算比较_v0.3_Cstar07_20261020'
METHODS = ['PPCPP', 'P2_MULTI', 'OARP_CORE2', 'TREE_MST', 'CSTAR', 'TRACE', 'CAP']
SEED = 20261018

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, d): p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def points(x): return set(map(tuple, x))

def audit(s, r):
    route = list(map(tuple, r))
    assert route and route[0] == tuple(s['current']) and route[-1] == tuple(s['base'])
    assert set(route) <= points(s['free'])
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:]))
    assert points(s['targets']) <= points(s['covered']) | set(route)
    assert len(route)-1 <= s['distance_budget']
    return len(route)-1

def turns(route):
    vec = [(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
    ninety = sum(a[0]*b[0]+a[1]*b[1] == 0 for a,b in zip(vec,vec[1:]))
    reverse = sum(a[0]*b[0]+a[1]*b[1] == -1 for a,b in zip(vec,vec[1:]))
    return dict(turn90=ninety, turn180=reverse)

def check_sources(protocol):
    for name, sha in protocol['sources'].items(): assert digest(ROOT/name) == sha, name

def main():
    assert not OUT.exists(), 'Existing experiment is never overwritten or rerun.'
    protocol = read(OLD/'protocol.json')
    check_sources(protocol)
    OUT.mkdir()
    for name in ['inputs','jobs','results','logs']: (OUT/name).mkdir()
    worlds=[]
    for index, event in [(0,'straight'),(2,'corner'),(4,'obstacle')]:
        control=read(OLD/'inputs'/f'case{index:02d}.json')
        after=read(OLD/'inputs'/f'case{index+1:02d}.json')
        map_id=protocol['cases'][index]['original_name'].removesuffix('__control')
        original=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/continuous_history_diagnostics/preflight_v0.1_20261016/initial_cases'/f'{map_id}.json'
        initial=read(original)
        assert points(initial['free'])==points(control['free'])
        assert points(initial['targets'])==points(control['published_targets'])
        worlds.append(dict(id=map_id,event=event,initial=dict(free=initial['free'],published=initial['targets'],base=initial['base'],distance_budget=initial['distance_budget']),
                           after=dict(free=after['free'],published=after['published_targets']),predator=control['predator'],
                           source_initial=str(original),source_initial_sha256=digest(original),source_after=str(OLD/'inputs'/f'case{index+1:02d}.json'),source_after_sha256=digest(OLD/'inputs'/f'case{index+1:02d}.json')))
    write(OUT/'protocol.json',dict(worlds=worlds,methods=METHODS,seed=SEED,versions=protocol['versions'],trigger='first cell-center arrival covering at least 50% of INITIAL published tasks; each method has its own history',
          initial_old_route=[],initial_history=[],budget_seconds_per_entry=20,timely_tolerance=.010,watchdog_seconds=90,max_entries=42,
          resource='original initial resource minus actual executed prefix',event='fixed original event coordinates; do not move obstacles based on routes',
          occupied_event='stop that session if fixed event blocks current/base',quality='compare distances only for complete sessions with identical final completed/deferred target sets; report others separately',
          execution='execute returned valid routes, retaining late labels; no flight waiting model',sources=protocol['sources'],worker=str(OLD/'worker.py'),worker_sha256=digest(OLD/'worker.py'),runner_sha256=digest(Path(__file__))))
    env=os.environ.copy()
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='1'
    ledger=[];sessions=[]
    def call(world,method,stage,snapshot):
        check_sources(protocol)
        ident=f'{world["id"]}__{method}__{stage}'
        ip=OUT/'inputs'/(ident+'.json');jp=OUT/'jobs'/(ident+'.json');dest=OUT/'results'/(ident+'.json')
        write(ip,snapshot)
        job=dict(run_id=ident,case_id=world['id'],input=str(ip),input_sha256=digest(ip),method=method,budget=20,seed=SEED)
        write(jp,job);entry=dict(id=ident,method=method,stage=stage,started=True)
        ledger.append(entry);write(OUT/'call_ledger.json',ledger)
        start=time.perf_counter()
        with (OUT/'logs'/(ident+'.log')).open('wb') as stream:
            run=subprocess.run([sys.executable,'-B','-X','utf8',str(OLD/'worker.py'),str(jp),str(dest)],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
        entry.update(wall_seconds=time.perf_counter()-start,returncode=run.returncode)
        assert run.returncode==0 and dest.is_file(), ident
        result=read(dest)
        entry.update(status=result['status'],seconds=result['entry_seconds'],timely=result['entry_seconds']<=20.010,has_route=bool(result['route']))
        if result['route']:entry['steps']=audit(snapshot,result['route'])
        write(OUT/'call_ledger.json',ledger)
        print(json.dumps(entry,ensure_ascii=False),flush=True)
        return result
    for wi,world in enumerate(worlds):
        order=METHODS[wi:]+METHODS[:wi]
        for method in order:
            ini=world['initial'];pub0=points(ini['published']);free0=points(ini['free']);base=ini['base']
            s=dict(free=ini['free'],targets=ini['published'],covered=[],current=base,base=base,published_targets=ini['published'],deferred_targets=[],distance_budget=ini['distance_budget'],
                   name=world['id']+'_'+method+'_initial',initial_targets=ini['published'],predator=world['predator'],previous=None,old_route=[])
            first=call(world,method,'initial',s)
            session=dict(world=world['id'],method=method,seed=SEED,initial_result=ledger[-1]['id'],status='initial_failed')
            if first['route']:
                covered=set();cut=None
                for i,p in enumerate(first['route']):
                    q=tuple(p)
                    if q in pub0:covered.add(q)
                    if len(covered)*2>=len(pub0):cut=i;break
                assert cut is not None
                prefix=first['route'][:cut+1];pub1=points(world['after']['published']);free1=points(world['after']['free'])
                deferred=pub1-free1-covered
                session.update(prefix=prefix,event_step=cut,event_covered=sorted(covered),event_initial_coverage=len(covered)/len(pub0),initial_plan=first['route'],initial_seconds=first['entry_seconds'],status='event_environment_stop')
                if tuple(prefix[-1]) in free1 and tuple(base) in free1:
                    post=dict(s,free=world['after']['free'],targets=sorted(pub1&free1),published_targets=sorted(pub1),covered=sorted(covered),current=prefix[-1],previous=prefix[-2] if cut else None,
                              deferred_targets=sorted(deferred),distance_budget=ini['distance_budget']-cut,name=world['id']+'_'+method+'_after',old_route=first['route'][cut:])
                    second=call(world,method,'after',post)
                    session.update(after_result=ledger[-1]['id'],after_seconds=second['entry_seconds'],after_plan=second['route'],status='after_failed',deferred=sorted(deferred))
                    if second['route']:
                        whole=prefix+second['route'][1:];completed=covered|(set(map(tuple,second['route']))&pub1)
                        assert pub1&free1<=completed and completed|deferred==pub1
                        session.update(status='complete',route=whole,steps=len(whole)-1,remaining_steps=len(second['route'])-1,total_seconds=first['entry_seconds']+second['entry_seconds'],
                                       timely=first['entry_seconds']<=20.010 and second['entry_seconds']<=20.010,completed=sorted(completed),**turns(whole))
            sessions.append(session);write(OUT/'sessions.json',sessions)
    check_sources(protocol)
    assert len(ledger)<=42
    write(OUT/'results.json',dict(worlds=worlds,sessions=sessions,calls=len(ledger),complete=sum(s['status']=='complete' for s in sessions),planned_sessions=21))
    print('COMPLETE',len(ledger),'entries',len(sessions),'sessions',flush=True)

if __name__=='__main__':main()
