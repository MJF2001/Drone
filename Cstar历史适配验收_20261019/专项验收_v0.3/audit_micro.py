"""Read-only independent replay. No imports of any planner or connector."""
import json,hashlib
from pathlib import Path
from collections import deque,Counter
ROOT=Path(__file__).resolve().parent
def points(xs):return set(map(tuple,xs))
def adjacent(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])==1
def exact_witness(c):
    f=points(c['free']);t=points(c['targets'])-points(c['covered']);s=tuple(c['current']);base=tuple(c['base'])
    ids={p:1<<i for i,p in enumerate(sorted(t))};full=(1<<len(t))-1
    initial=(s,ids.get(s,0));q=deque([(initial,0)]);seen={initial};parent={initial:None}
    while q:
        (p,mask),d=q.popleft()
        if p==base and mask==full:
            state=(p,mask);route=[]
            while state is not None:route.append(state[0]);state=parent[state]
            return d,list(reversed(route))
        for v in ((p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)):
            state=(v,mask|ids.get(v,0))
            if v in f and state not in seen:seen.add(state);parent[state]=(p,mask);q.append((state,d+1))
    return None,None
def audit(c,r):
    assert r['status']!='exception',r
    f=points(c['free']);t=points(c['targets']);h=points(c['covered']);s=tuple(c['current']);base=tuple(c['base'])
    path=list(map(tuple,r['diagnostic_route']));route=list(map(tuple,r['route']))
    assert path and path[0]==s and set(path)<=f
    assert all(adjacent(a,b) for a,b in zip(path,path[1:]))
    pending=t-h-{s};last=0
    for event in r['task_events']:
        a,b=event['start_index'],event['end_index'];assert a==last and a<=b<len(path)
        credit=pending & set(path[a+1:b+1]);assert credit==points(event['credited'])
        pending-=credit;assert pending==points(event['pending_after']);last=b
    assert pending==points(r['pending'])
    for it in r['iterations']:
        if 'nodes' not in it:continue
        nodes={tuple(n[:2]) for n in it['nodes']};assert nodes<=f
        # Independently evaluate closed-square supercover for axis/diagonal RCG edges.
        for edge in it['edges']:
            a,b=map(tuple,edge);assert a in nodes and b in nodes
            dx=b[0]-a[0];dy=b[1]-a[1]
            if dx==0:cells={(a[0],y) for y in range(min(a[1],b[1]),max(a[1],b[1])+1)}
            else:
                assert abs(dx)==1 and abs(dy)<=1
                cells={(x,y) for x in range(min(a[0],b[0]),max(a[0],b[0])+1) for y in range(min(a[1],b[1]),max(a[1],b[1])+1)}
            assert cells<=f
    decisions=[it for it in r['iterations'] if 'nodes' in it]
    assert len(decisions)==len(r['task_filters'])
    for it,fil in zip(decisions,r['task_filters']):
        p=tuple(fil['current']);assert p==path[it['step']]
        states={tuple(n[:2]):n[2] for n in it['nodes']};edges={v:set() for v in states}
        for a,b in it['edges']:a,b=tuple(a),tuple(b);edges[a].add(b);edges[b].add(a)
        opened={v for v in edges[p] if states[v]=='Op'};assert opened==points(fil['original'])
        remaining=points(fil['pending']);eligible=set()
        for v in opened:
            lap=set()
            for q in edges[v]:
                if q[0]==v[0]:lap|={(v[0],y) for y in range(min(v[1],q[1]),max(v[1],q[1])+1)}
            if v in remaining or lap&remaining:eligible.add(v)
        assert eligible==points(fil['eligible'])
        groups=[('left',{q for q in eligible if q[0]<p[0]}),('up',{q for q in eligible if q[0]==p[0] and q[1]>p[1]}),('down',{q for q in eligible if q[0]==p[0] and q[1]<p[1]}),('right',{q for q in eligible if q[0]>p[0]})]
        if not remaining:assert it['why']['group']=='task_complete'
        elif eligible:
            name,options=next((n,vs) for n,vs in groups if vs)
            assert it['why']['group']==name and tuple(it['goal']) in options
        elif it['why']['group']=='task_transit':
            why=it['why'];full=list(map(tuple,why['rcg_service_route']));a,b=map(tuple,why['service_edge'])
            assert full[0]==p and len(full)>1 and tuple(it['goal'])==full[1]
            assert all(v in edges[u] for u,v in zip(full,full[1:]))
            if why['service_kind']=='node':assert a==b and a in remaining and full[-1]==a
            else:
                assert a[0]==b[0] and full[-2:]==[a,b]
                assert {(a[0],y) for y in range(min(a[1],b[1]),max(a[1],b[1])+1)}&remaining
    assert r['completion_tsp'] is False
    if route:
        assert r['status']=='task_complete' and not pending
        assert route==path and route[-1]==base and t<=h|set(route)
        assert len(route)-1<=c['distance_budget'] and r['seconds']<2
    else:assert r['status']!='task_complete'
    exact_steps,witness=exact_witness(c)
    return dict(status=r['status'],steps=len(route)-1 if route else None,remaining=len(pending),
                exact_feasible_steps=exact_steps,exact_witness=witness,iterations=len(r['iterations']),
                retreat_iterations=sum(bool(i['retreat_used']) for i in r['iterations']),
                task_transit_iterations=sum(i['why']['group']=='task_transit' for i in r['iterations']),
                tsp_iterations=sum(bool(i.get('tsp')) for i in r['iterations']),
                link_insertions=sum(len(i.get('state_update',{}).get('link_inserted',[])) for i in r['iterations']))
def main():
    import sys
    folder=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'micro_evidence');cases={c['name']:c for c in json.loads((folder/'inputs.json').read_text(encoding='utf8'))}
    manifest=json.loads((folder/'pre_run_manifest.json').read_text(encoding='utf8'))
    normalized_input_hashes=[]
    for path,sha in manifest['files'].items():
        actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if actual!=sha and path.endswith('/inputs.json'):
            # The regression writer hashed the JSON serialization before Windows
            # newline conversion. Preserve that pre-run manifest; verify both
            # its exact normalized content and record the actual byte digest.
            assert hashlib.sha256((ROOT/path).read_text(encoding='utf8').encode()).hexdigest()==sha,path
            normalized_input_hashes.append(dict(path=path,actual_byte_sha256=actual,normalized_text_sha256=sha))
        else:assert actual==sha,path
    results=json.loads((folder/'results.json').read_text(encoding='utf8'));records=[];first={}
    for row in results:
        name=row['name'];r=row['result'];a=audit(cases[name],r);records.append(dict(name=name,replay=row.get('replay'),seed=row.get('seed',7),**a))
        deterministic={k:v for k,v in r.items() if k!='seconds'}
        key=(name,row.get('seed',7))
        if key in first:assert deterministic==first[key],name
        else:first[key]=deterministic
    summary=dict(records=records,status_counts=dict(Counter(r['status'] for r in records)),same_seed_duplicates_compared=len(results)-len(first),source_hashes_unchanged=True,normalized_input_hashes=normalized_input_hashes)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
