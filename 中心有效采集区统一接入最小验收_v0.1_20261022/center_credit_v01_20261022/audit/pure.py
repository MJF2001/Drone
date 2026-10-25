"""Independent pure entry prediction and tamper checks; no selector import."""
from copy import deepcopy
from . import _geometry as A
from . import region as Z
from ._audit import public_state,check_state

def audit_entry(saved,c):
    s=public_state(saved['input']['input'],c)
    assert saved['actual_before']==saved['actual_after']
    check_state(saved['actual_before'],s)
    q=A.pos(saved['q'],True)
    chosen=None;keys=[]
    for row,p in zip(saved['candidates'],sorted(s['F'])):
        assert A.pos(row['q'],True)==p
        legal=A.legal(s['F'],s['S'],p,c)
        length,square=A.metric(s['S'],p,c)
        affordable=A.sign(A.add(s['E'],length,-1))>=0
        dot=sum((p[j]-s['S'][j])*s['h'][j] for j in (0,1))
        assert row['legal']==legal and row['affordable']==affordable
        assert A.number(row['squared'])==square and A.number(row['dot'])==dot
        if legal and affordable:
            key=(square,-dot,p);keys.append(key)
            if p==q:
                chosen=key
    assert chosen is not None and all(chosen<=key for key in keys)
    f=deepcopy(s)
    events=Z.collect(f,c)+Z.service(f,s['S'],q,c)
    length,_=A.metric(s['S'],q,c)
    f['h']=(q[0]-s['S'][0],q[1]-s['S'][1]) if q!=s['S'] else s['h']
    f['S'],f['E'],f['M']=q,A.add(s['E'],length,-1),A.add(s['M'],length)
    assert events==saved['events']
    check_state(saved['prediction'],f)
    return {'passed':True,'predicted_H':sorted([list(map(int,p)) for p in f['H']])}

def audit_forecast(initial,saved,c):
    raw={k:initial[k] for k in ('S','h','F','P','H','D','base')}
    raw.update(E=initial['E']['exact'],M=initial['M']['exact'],heading_status='KNOWN')
    s=public_state(raw,c)
    path=[A.pos(p) for p in saved['route']]
    assert path[0]==s['S']
    events=Z.collect(s,c)
    for a,b in zip(path,path[1:]):
        assert A.legal(s['F'],a,b,c)
        events+=Z.service(s,a,b,c)
    assert events==saved['events'] and sorted([list(map(int,p)) for p in s['H']])==saved['H']
    return {'passed':True,'prediction_only':True}
