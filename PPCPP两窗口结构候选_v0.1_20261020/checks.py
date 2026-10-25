"""Independent DSU/BFS window audit, plus original reward and coverage audit."""
import json,importlib.util
from pathlib import Path
from audit_branch import audit as branch_audit,bfs
H=Path(__file__).resolve().parent;R=H.parent
spec=importlib.util.spec_from_file_location('frozen_independent_audit',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py');pa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)
def norm(x):return json.loads(json.dumps(x))
def partition(cells):
    p={q:q for q in cells}
    def root(q):
        while p[q]!=q:p[q]=p[p[q]];q=p[q]
        return q
    for x,y in cells:
        for z in ((x+1,y),(x,y+1)):
            if z in cells:p[root(z)]=root((x,y))
    groups={}
    for q in cells:groups.setdefault(root(q),set()).add(q)
    groups=sorted(groups.values(),key=min)
    return {q:i for i,g in enumerate(groups) for q in g},list(map(len,groups)),list(map(min,groups))
def audit(c,r):
    if 'branches' not in r:
        if r['route']:pa.audit(c,r)
        return
    structure=r['version']=='PPCPP_TWO_WINDOW_STRUCTURE_v0.1'
    assert structure or r['version']=='PPCPP_FIRST_RECOVERY_ROLLOUT_v0.1'
    bs=r['branches'];state=r['branch_state'];k=r['override_recovery'] if structure else 1;free=set(map(tuple,c['free']));expected=[]
    path=bs[0]['diagnostic_route'] if bs else r['diagnostic_prefix'];path=list(map(tuple,path))
    if structure:
        windows=r['structural_windows'];assert len(windows)<=2
        for i,w in enumerate(windows,1):
            assert w['recovery_index']==i and w['index']<len(path) and tuple(w['current'])==path[w['index']]
            cur=path[w['index']];pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(path[:w['index']+1]);assert pending
            assert not any(q in pending for q in ((cur[0]-1,cur[1]),(cur[0]+1,cur[1]),(cur[0],cur[1]-1),(cur[0],cur[1]+1)))
            d=bfs(free,cur);db=bfs(free,tuple(c['base']));goals=[]
            for q in (min(pending,key=lambda q:(d[q],q)),min(pending,key=lambda q:(db[q],q)),min(pending,key=lambda q:(-db[q],q))):
                if q not in goals:goals.append(q)
            lab,sizes,anchors=partition(pending);ids=[lab[q] for q in goals]
            assert norm(w['goals'])==norm(goals) and w['pending_count']==len(pending)
            assert w['component_count']==len(sizes) and w['component_sizes']==sizes and norm(w['component_anchors'])==norm(anchors)
            assert w['candidate_component_ids']==ids and w['eligible']==(len(set(ids))>=2)
            if w['eligible']:assert i==len(windows)
        if state is not None:
            assert k in (1,2) and len(windows)==k and windows[-1]['eligible']
            assert norm(state['goals'])==norm(windows[-1]['goals'])
        if r['status']=='core_complete':
            recs=[e for e in bs[0]['trace'] if e['kind']=='recovery']
            assert [w['index'] for w in windows]==[e['index'] for e in recs[:(k if k else 2)]]
            assert (k is not None)==any(w['eligible'] for w in windows)
    if state:
        pending=set(map(tuple,state['pending']));cur=tuple(state['path'][-1]);d=bfs(free,cur)
        assert pending==set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(map(tuple,state['path']))
        nearest=min(pending,key=lambda q:(d[q],q));assert nearest==tuple(state['nearest'])
        expected=[nearest]
        if r['mode']=='three':
            db=bfs(free,tuple(c['base']))
            for q in (min(pending,key=lambda q:(db[q],q)),min(pending,key=lambda q:(-db[q],q))):
                if q not in expected:expected.append(q)
        if structure:assert state['recovery_index']==k
    for i,b in enumerate(bs):
        assert b.get('override_recovery',1)==k
        if state:
            assert tuple(b['forced_goal'])==expected[i] and norm(b['diagnostic_route'][:len(state['path'])])==norm(state['path'])
            if b['status']=='core_complete':assert [e for e in b['trace'] if e['kind']=='recovery'][k-1]['index']==len(state['path'])-1
        else:assert b['forced_goal'] is None
        if b['status']=='core_complete':branch_audit(c,b)
    if r['status']=='core_complete':
        valid=[i for i,b in enumerate(bs) if b['status']=='core_complete'];chosen=min(valid,key=lambda i:(len(bs[i]['route']),i))
        assert r['selected_branch']==chosen and norm(r['route'])==norm(bs[chosen]['route']) and norm(r['trace'])==norm(bs[chosen]['trace'])
        assert len(bs)==(len(expected) if state else 1)
    else:assert not r['route']
