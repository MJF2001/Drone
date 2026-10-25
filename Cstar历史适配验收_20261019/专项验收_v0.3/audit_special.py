"""Read-only independent saved-evidence checks. Imports no runtime planner."""
import json,hashlib
from pathlib import Path
from collections import Counter
from audit_micro import audit,points,adjacent
ROOT=Path(__file__).resolve().parent
def represented(snapshot,current,pending):
    nodes={tuple(n[:2]) for n in snapshot['nodes']};edges={p:set() for p in nodes}
    for a,b in snapshot['edges']:a,b=tuple(a),tuple(b);edges[a].add(b);edges[b].add(a)
    seen={current} if current in nodes else set();stack=list(seen)
    while stack:
        a=stack.pop()
        for b in edges[a]-seen:seen.add(b);stack.append(b)
    represented=set(nodes);reachable=set(seen)
    for a in nodes:
        for b in edges[a]:
            if a[0]==b[0]:
                cells={(a[0],y) for y in range(min(a[1],b[1]),max(a[1],b[1])+1)}
                represented|=cells
                if a in seen:reachable|=cells
    return represented&pending,reachable&pending
def prune_checks(r,require_all):
    completed=interrupted=0
    for rec in r['prune_audits']:
        pending=points(rec['pending']);cur=tuple(rec['current'])
        before,reachable_before=represented(rec['before'],cur,pending)
        after,reachable_after=represented(rec['after'],cur,pending)
        if rec['status']=='completed':
            completed+=1;assert before<=after and reachable_before<=reachable_after
            if require_all:assert before==after==reachable_before==reachable_after==pending
        else:interrupted+=1
    return completed,interrupted
def ledger(c,r):
    f=points(c['free']);t=points(c['targets']);h=points(c['covered']);s=tuple(c['current'])
    path=list(map(tuple,r['diagnostic_route']));assert path[0]==s and set(path)<=f
    assert all(adjacent(a,b) for a,b in zip(path,path[1:]))
    pending=t-h-{s};last=0
    for e in r['task_events']:
        a,b=e['start_index'],e['end_index'];assert a==last and a<=b<len(path)
        credit=pending&set(path[a+1:b+1]);assert credit==points(e['credited'])
        pending-=credit;assert pending==points(e['pending_after']);last=b
    assert pending==points(r['pending'])
    assert not r['completion_tsp']
def hole_checks(c,r):
    verified=[];known=points(c['free'])|points(c.get('known_blocked',[]))|points(c.get('published_targets',c['targets']))|points(c['covered'])
    for it in r['iterations']:
        event=it.get('tsp')
        if not event:continue
        snap=event['graph_before_tour'];state={tuple(n[:2]):n[2] for n in snap['nodes']};edges={p:set() for p in state}
        for a,b in snap['edges']:a,b=tuple(a),tuple(b);edges[a].add(b);edges[b].add(a)
        dense=points(event['dense_nodes']);start=tuple(event['start']);goal=tuple(event['goal'])
        def outside(p):return any(state[q]=='Op' and q not in dense for q in edges[p])
        unknown=any((goal[0]+dx,goal[1]+dy) not in known for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
        expected=1 if outside(goal) or unknown else 2 if outside(start) else 3
        assert event['case']==expected
        order=list(map(tuple,event['order']));assert order[0]==start and dense<=set(order)
        if expected in (1,2):assert tuple(event['end'])==(goal if expected==1 else start)==order[-1]
        else:assert event['end'] is None
        path=list(map(tuple,r['diagnostic_route']));assert path[event['step']]==start
        assert path[event['step']+event['moved_steps']]==order[-1]
        verified.append(expected)
    return verified
def main():
    folder=ROOT/'evidence';manifest=json.loads((folder/'pre_run_manifest.json').read_text(encoding='utf8'))
    for path,sha in manifest['files'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    rows=json.loads((folder/'results.json').read_text(encoding='utf8'));counts=Counter();records=[];prunes=interrupted=0;partial_after_move=0
    old=ROOT.parent/'修正版_v0.2';references={}
    for sub in ('micro_evidence','regression_evidence'):
        for row in json.loads((old/sub/'results.json').read_text(encoding='utf8')):
            if row.get('seed',7)==7:references[row['name']]=row['result']
    for row in rows:
        c=row['input'];r=row['result'];ledger(c,r)
        good=r['status']=='task_complete';p,i=prune_checks(r,good);prunes+=p;interrupted+=i
        if row['kind']=='functional':
            audit(c,r);holes=hole_checks(c,r)
            if 'expected_hole_case' in c:assert c['expected_hole_case'] in holes
            else:
                ref=references[c['name']]
                for key in ('status','route','diagnostic_route','pending','task_filters','graph_counts','termination_trigger'):assert ref[key]==r[key],(c['name'],key)
            records.append(dict(name=c['name'],status=r['status'],hole_cases=holes,prune_passes=p));counts['functional_'+r['status']]+=1
        else:
            assert row['hits'],row['phase']
            if row['relation']=='before':
                assert good and r['route'] and r['seconds']<2
                audit(c,r);counts['boundary_before_success']+=1
            else:
                assert not r['route'] and r['status'] in ('wall_clock_cap','deadline') and r['seconds']>=2
                counts['boundary_rejected']+=1
                if row['phase']=='move_after':
                    assert len(r['diagnostic_route'])==2 and r['pending']==[[2,0]]
                    assert r['task_events'][-1]['interrupted'];partial_after_move+=1
    assert len(rows)==86 and counts['functional_task_complete']==26
    assert counts['boundary_before_success']==19 and counts['boundary_rejected']==38
    print(json.dumps(dict(gate='PASS_BOUNDED_SPECIAL',rows=len(rows),counts=counts,completed_prune_records_checked=prunes,interrupted_prune_records_retained=interrupted,partial_movement_ledger_cases=partial_after_move,original_26_semantic_outputs_unchanged=True,records=records),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
