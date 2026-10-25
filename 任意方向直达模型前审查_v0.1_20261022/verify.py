"""Independent saved-route index and arithmetic verification, no geometry query."""
from pathlib import Path
import json,hashlib,collections
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def ps(x):return set(map(tuple,x))
def main():
    for p,v in read(H/'来源hash.json').items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==v,p
    rows=read(H/'60份字段与原路线段账.json');assert len(rows)==60
    for r in rows:
        c=read(r['input']);o=read(r['output']);raw=o['result']['raw'] if 'result' in o else o['entry']['native_return']['raw'];walk=raw['route'];required=ps(c['targets'])-ps(c['covered']);indices={p:min(i for i,q in enumerate(walk) if tuple(q)==p) for p in required};order=sorted(indices.items(),key=lambda z:z[1]);assert r['first_services']==[dict(point=list(p),index=i) for p,i in order]
        n=len(walk)-1;assert n==r['L4']==r['original_euclidean_length'];assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(walk,walk[1:]));owners=[];totals=collections.Counter();cross=collections.Counter();trace=raw['trace']
        for k in range(n):
            if not order:owner='empty_task_to_base'
            elif k<order[0][1]:owner='start_to_first'
            elif k>=order[-1][1]:owner='last_to_base'
            else:owner='between_first_services'
            owners.append(owner);totals[owner]+=1;j=max(i for i,t in enumerate(trace) if t['index']<=k);cross[owner+' x '+trace[j]['kind']]+=1
        assert all(r['service_totals'][k]==totals[k] for k in r['service_totals']) and r['service_trace_cross']==dict(cross)
        edgeids=[]
        for s in r['service_segments']:assert s['saved_moves']==s['right']-s['left']==s['saved_euclidean_length'] and s['start']==walk[s['left']] and s['end']==walk[s['right']];edgeids+=list(range(s['left'],s['right']))
        assert edgeids==list(range(n));p=r['physical'];assert ps(p['U'])==ps(c['targets'])-ps(c['covered']) and ps(p['D'])==ps(c['published_targets'])-ps(c['free'])-ps(c['covered'])
        for ref in r['P2_pairings']:
            if 'input' in ref:q=read(ref['input'])
            else:q=read(ref['output_session'])['sessions']['P2_MULTI']['requests'][ref['request_index']]['input']
            expected=dict(F=ps(q['free']),P=ps(q['published_targets']),H=ps(q['covered']),U=ps(q['targets'])-ps(q['covered']),D=ps(q['deferred_targets']),current=q['current'],previous=q['previous'],base=q['base'],E=q['distance_budget']);flags={k:(ps(p[k])==v if isinstance(v,set) else p[k]==v) for k,v in expected.items()};assert ref['fields']==flags and ref['physical_equal']==all(flags.values())
        assert all(r[k] is None for k in ('shortcut_length','geometry_gain','fixed_order_optimum','free_order_optimum'))
    if (H/'completion_manifest.json').exists():
        for p,v in read(H/'completion_manifest.json')['files'].items():assert hashlib.sha256((H/p).read_bytes()).hexdigest()==v,p
    print(json.dumps(dict(passed=True,records=60,all_saved_edges_partitioned_once=True,source_hashes=len(read(H/'来源hash.json')),new_planner_core_search_visibility_shortcut_routes=0),ensure_ascii=False))
if __name__=='__main__':main()
