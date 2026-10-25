"""Independent four-neighbour residual partition audit; no runtime imports."""
def parts(points):
    todo=set(map(tuple,points)); out=[]
    while todo:
        p=min(todo); todo.remove(p); component={p}; stack=[p]
        while stack:
            x,y=stack.pop()
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if q in todo: todo.remove(q); component.add(q); stack.append(q)
        out.append(component)
    return out

def audit(before,after,pending):
    pending=set(map(tuple,pending)); actual=[]; seen=set()
    for node in after['nodes']:
        r=set(map(tuple,node['R']))
        assert r<=set(map(tuple,node['A']))
        assert not seen&r; seen|=r
        assert node['state']==('E' if r else 'C')
        if r:
            assert len(parts(r))==1; actual.append(frozenset(r))
    expected=[]
    for n in before['nodes']:
        expected.extend(frozenset(p) for p in parts(set(map(tuple,n['R']))&pending))
    assert set(expected)==set(actual) and seen==pending
    active={n['id'] for n in after['nodes'] if n['R']}
    assert len(after['order'])==len(active) and set(after['order'])==active
    return dict(valid=True,remaining=len(seen),active_nodes=len(active))
