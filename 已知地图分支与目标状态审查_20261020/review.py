"""Read-only current TRACE/CAP known-map and tau-source review. No solves."""
import json,hashlib,sys
from collections import Counter,deque
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'TRACE_CAP适配复现_20261020'))
from audit import audit,distance
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def pts(x):return set(map(tuple,x))
def neighbours(p):x,y=p;return [(x-1,y),(x,y+1),(x,y-1),(x+1,y)]
def parts(cells):
    left=set(cells);out=[]
    while left:
        s=min(left);left.remove(s);todo=[s];part={s}
        while todo:
            for q in neighbours(todo.pop()):
                if q in left:left.remove(q);part.add(q);todo.append(q)
        out.append(part)
    return out
def center(r):
    n=len(r);sx=sum(p[0] for p in r);sy=sum(p[1] for p in r)
    return min(r,key=lambda p:((n*p[0]-sx)**2+(n*p[1]-sy)**2,p))
def prepare():
    assert not (HERE/'protocol.json').exists()
    batch=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';p=read(batch/'protocol.json')
    jobs=[j for j in p['jobs'] if j['method'] in ('TRACE','CAP')]
    files=[Path(j['input']) for j in jobs]+[batch/'execution/results'/(j['run_id']+'.json') for j in jobs]
    for folder in ('TRACE_CAP适配复现_20261020/runtime','CAP单源查询修正_v0.2_20261020/runtime'):files+=list((ROOT/folder).glob('*.py'))
    files += [ROOT/'TRACE_CAP适配复现_20261020/sources'/f for f in ('TRACE_2609.21777v1.txt','CAP_2503.00647v1.txt')]+[Path(__file__).resolve()]
    save(HERE/'protocol.json',dict(solver_calls=0,jobs=jobs,files={str(f):sha(f) for f in files},scope='TRACE known-region tree/order/local/transition; CAP local tau provenance/lifetime and global/end distinction; no unknown sensing or route reoptimization'))
def run():
    p=read(HERE/'protocol.json')
    for f,h in p['files'].items():assert sha(Path(f))==h
    batch=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';rows=[];counts=Counter()
    for j in p['jobs']:
        c=read(Path(j['input']));r=read(batch/'execution/results'/(j['run_id']+'.json'))['raw'];audit(c,r)
        f=pts(c['free']);t=pts(c['targets']);h=pts(c['covered']);path=list(map(tuple,r['diagnostic_route']))
        for k,plan in enumerate(r['plans']):
            start=tuple(plan['start']);pending=t-h-set(path[:plan['path_start']+1]);required=pts(plan['required']);s=plan['structure_before'];nodes={n['id']:n for n in s['nodes']};node=nodes[plan['region_id']]
            assert s['order'][0]==plan['region_id'] and required==pts(node['R']) and node['state']=='E'
            assert required<=pending and pts(plan['order'])-required-{start}<=({tuple(plan['end'])} if plan['end'] is not None else set())
            nonadjacent=start not in required and not any(q in required for q in neighbours(start))
            row=dict(run_id=j['run_id'],method=j['method'],plan=k,region=plan['region_id'],size=len(required),nonadjacent=nonadjacent,end_source=plan['end_source'],required_components=len(parts(required)))
            counts[j['method']+'_plans']+=1;counts[j['method']+'_nonadjacent']+=nonadjacent
            for n in nodes.values():
                if not n.get('children'):
                    assert pts(n['R'])==pts(n['A'])&pending
                    if n['R'] and len(parts(pts(n['R'])))>1:counts[j['method']+'_disconnected_leaf_snapshots']+=1
            if j['method']=='TRACE':
                for n in nodes.values():
                    if not n.get('children') and n['R']:assert tuple(n['center'])==center(pts(n['R']))
                    if n.get('children'):
                        expected={frozenset(x) for x in parts(pts(n['R']))};actual={frozenset(pts(nodes[i]['A'])) for i in n['children']};assert expected==actual
                next_id=s['order'][1] if len(s['order'])>1 else None;assert next_id==plan['next_id']
                expected=nodes[next_id]['center'] if next_id is not None else None;assert expected==plan['end']
                executed=plan['executed_order'];assert executed==(plan['order'][:-1] if expected is not None else plan['order'])
                realized=plan['path_end']-plan['path_start']
                omitted=distance(f,tuple(executed[-1]),tuple(expected)) if expected is not None else 0
                assert realized+omitted==plan['tsp']['final_cost']
                counts['TRACE_virtual_end']+=expected is not None;counts['TRACE_free_end']+=expected is None
            else:
                end=tuple(plan['end']);assert end in required
                expected=next((q for q in neighbours(start) if q in required),None)
                if expected is not None:assert plan['end_source']=='restart_direction_target'
                else:
                    expected=min(required,key=lambda q:(distance(f,start,q),q));assert plan['end_source']=='restart_nearest_entry_target'
                assert expected==end
                counts['CAP_'+plan['end_source']]+=1
                global_candidate=next((q for q in neighbours(start) if q in pending),None)
                row.update(tau=end,global_greedy_candidate=global_candidate,tau_differs_from_fresh_global_greedy=global_candidate is not None and global_candidate!=end)
                counts['CAP_fresh_global_greedy_disagrees']+=row['tau_differs_from_fresh_global_greedy']
                if k:counts['CAP_reinitialized_after_first_region']+=1
            rows.append(row)
        if j['method']=='TRACE':
            initialized=False
            for e in r['structure_events']:
                if e['type']=='split':counts['TRACE_runtime_splits' if initialized else 'TRACE_initial_splits']+=1
                if e['type']=='update':
                    initialized=True;old=e['old_order'];new=e['new_order'];same=set(old)&set(new);assert [i for i in old if i in same]==[i for i in new if i in same]
        else:
            replans=[e for e in r['structure_events'] if e['type']=='global_replan']
            assert all(not e['exploring'] and e['end'] is None for e in replans)
            counts['CAP_global_free_end_plans']+=len(replans)
    save(HERE/'checks.json',dict(calls=0,saved_outputs=len(p['jobs']),plans=len(rows),counts=dict(counts),records=rows,all_checks_pass=True))
    for f,h in p['files'].items():assert sha(Path(f))==h
    print(json.dumps(dict(calls=0,saved_outputs=len(p['jobs']),plans=len(rows),counts=dict(counts),all_checks_pass=True),ensure_ascii=False))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
