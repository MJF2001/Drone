"""Independent replay audit of saved files; no solver imports."""
from pathlib import Path
import hashlib,json,math

H=Path(__file__).resolve().parent
P=H/'七算法从零起飞事件演示_v0.3'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pts(x):return set(map(tuple,x))
data=read(P/'results.json');protocol=read(P/'protocol.json');ledger=read(P/'call_ledger.json')
checks=[]
for session in data['sessions']:
    if session['status']=='unsupported_initial_contract':
        assert session['method']=='OARP_CORE2'
        checks.append(dict(world=session['world'],method=session['method'],status='unsupported_initial_contract'))
        continue
    assert session['status']=='complete'
    world=next(w for w in data['worlds'] if w['id']==session['world'])
    a=read(P/'inputs'/(session['initial_result']+'.json'))
    b=read(P/'inputs'/(session['after_result']+'.json'))
    r0=read(P/'results'/(session['initial_result']+'.json'))
    r1=read(P/'results'/(session['after_result']+'.json'))
    assert a['covered']==[] and a['old_route']==[] and a['current']==a['base'] and a['previous'] is None
    assert pts(a['published_targets'])==pts(world['initial']['published'])
    assert pts(a['free'])==pts(world['initial']['free'])
    history=set();trigger=None;P0=pts(a['published_targets'])
    for i,q in enumerate(r0['route']):
        if tuple(q) in P0:history.add(tuple(q))
        if 2*len(history)>=len(P0):trigger=i;break
    assert trigger==session['event_step'] and r0['route'][:trigger+1]==session['prefix']
    assert pts(b['covered'])==history==pts(session['event_covered'])
    assert b['current']==session['prefix'][-1] and b['previous']==session['prefix'][-2]
    assert b['old_route']==r0['route'][trigger:]
    assert b['distance_budget']==a['distance_budget']-trigger
    assert pts(b['free'])==pts(world['after']['free']) and pts(b['published_targets'])==pts(world['after']['published'])
    P1=pts(b['published_targets']);F1=pts(b['free'])
    assert pts(b['targets'])==P1&F1
    assert pts(b['deferred_targets'])==P1-F1-history
    for request,result in [(a,r0),(b,r1)]:
        r=result['route'];F=pts(request['free'])
        assert r[0]==request['current'] and r[-1]==request['base'] and pts(r)<=F
        assert all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(r,r[1:]))
        assert pts(request['targets'])<=pts(request['covered'])|pts(r)
        assert len(r)-1<=request['distance_budget']
    full=session['prefix']+r1['route'][1:]
    assert full==session['route'] and len(full)-1==session['steps']
    done=history|(pts(r1['route'])&P1);deferred=P1-F1-history
    assert done==pts(session['completed']) and deferred==pts(session['deferred']) and done|deferred==P1 and not done&deferred
    turn90=turn180=0
    for a0,a1,a2 in zip(full,full[1:],full[2:]):
        v=(a1[0]-a0[0],a1[1]-a0[1]);u=(a2[0]-a1[0],a2[1]-a1[1]);dot=v[0]*u[0]+v[1]*u[1]
        turn90+=dot==0;turn180+=dot==-1
    assert (turn90,turn180)==(session['turn90'],session['turn180'])
    assert math.isclose(session['total_seconds'],r0['entry_seconds']+r1['entry_seconds'],abs_tol=1e-12)
    checks.append(dict(world=session['world'],method=session['method'],status='verified',trigger_step=trigger,
                       old_suffix_blocked=bool(pts(r0['route'][trigger:])-F1),final_completed=len(done),deferred=len(deferred)))
for name,sha in protocol['sources'].items():assert hashlib.sha256((H.parent/name).read_bytes()).hexdigest()==sha
assert len(checks)==21 and sum(c['status']=='verified' for c in checks)==18
assert len(ledger)==36 and sum(c.get('executed',False) for c in ledger)==32 and sum(c.get('reused',False) for c in ledger)==4
assert data['total_actual_entries']==37
receipt=dict(passed=True,checks=checks,independent_completed_sessions=18,unsupported_sessions=3,
             successful_original_version_entries=36,prior_failed_original_version_entries=1,actual_entries_across_versions=37,
             new_solver_calls_during_verification=0,
             results_sha256=hashlib.sha256((P/'results.json').read_bytes()).hexdigest(),
             limitations=['three small developer maps; one seed', 'OARP_CORE2 has no empty-old-route initialization in this frozen interface',
                          'obstacle-world final task responsibility differs between PPCPP and peers; do not rank their distances as equal work',
                          'v0.2 cache-identity comparison stopped on tuple/list representation; no new solver call; normalized in v0.3'])
(P/'independent_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='checks'},ensure_ascii=False,indent=2))
