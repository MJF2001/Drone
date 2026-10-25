import sys,json,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
from audit_branch import audit as branch_audit,bfs
spec=importlib.util.spec_from_file_location('frozen_independent_audit',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py');pa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)

def norm(x):return json.loads(json.dumps(x))

def audit(c,r):
    if 'branches' not in r:
        if r['route']:pa.audit(c,r)
        return
    k=2 if r['version']=='PPCPP_SECOND_RECOVERY_ROLLOUT_v0.1' else 1
    assert r['version'] in ('PPCPP_SECOND_RECOVERY_ROLLOUT_v0.1','PPCPP_FIRST_RECOVERY_ROLLOUT_v0.1')
    if k==2:assert r['override_recovery']==2
    bs=r['branches'];state=r['branch_state'];goals=[]
    if state:
        f=set(map(tuple,c['free']));pending=set(map(tuple,state['pending']));cur=tuple(state['path'][-1]);d=bfs(f,cur)
        assert pending==set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(map(tuple,state['path']))
        nearest=min(pending,key=lambda q:(d[q],q));assert nearest==tuple(state['nearest'])
        if k==2:assert state['recovery_index']==2
        goals=[nearest]
        if r['mode']=='three':
            db=bfs(f,tuple(c['base']))
            for g in (min(pending,key=lambda q:(db[q],q)),min(pending,key=lambda q:(-db[q],q))):
                if g not in goals:goals.append(g)
    for i,b in enumerate(bs):
        assert b.get('override_recovery',1)==k
        if state:
            assert tuple(b['forced_goal'])==goals[i] and norm(b['diagnostic_route'][:len(state['path'])])==norm(state['path'])
            if b['status']=='core_complete':
                es=[e for e in b['trace'] if e['kind']=='recovery'];assert es[k-1]['index']==len(state['path'])-1
        else:assert b['forced_goal'] is None
        if b['status']=='core_complete':branch_audit(c,b)
    if r['status']=='core_complete':
        valid=[i for i,b in enumerate(bs) if b['status']=='core_complete'];chosen=min(valid,key=lambda i:(len(bs[i]['route']),i))
        assert r['selected_branch']==chosen and norm(r['route'])==norm(bs[chosen]['route']) and norm(r['trace'])==norm(bs[chosen]['trace'])
        if state:assert len(bs)==len(goals)
        else:assert len(bs)==1 and sum(e['kind']=='recovery' for e in r['trace'])<k
    else:assert not r['route']
