"""Independent replay and published-state gates; no optimization."""
from collections import deque
from prepare_continuous_history_runs_20261016 import *
from continuous_history_inputs_20261016 import checkpoint,publish
CHECK=ALGO/'continuous_history_diagnostics/preparation_verification_v0.1_20261016'
def main():
    manifest(PREP);manifest(PREF);protocol=read(PREP/'protocol.json')
    assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    from verify_road_range_diagnostic_20261015 import independent_plan
    import portable_frozen
    from prepare_road_range_diagnostic_20261015 import snapshot
    from road_range_candidate_20261015 import range_plan
    from attribute_old_reference_gain_20261016 import independent_fallback
    from audit import audit
    rows=[json.loads(v) for v in (PREP/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==len(protocol['jobs'])==10
    records=read(PREF/'records.json');checks=[];cases={}
    for j,row,e in zip(protocol['jobs'],rows,records):
        assert all(row[k]==v for k,v in j.items());c=read(Path(j['case']));dest=PREP/'runs'/(j['run_id']+'.json')
        if not row['valid']:checks.append(dict(map_id=j['map_id'],status='preparation_failed'));continue
        p=read(dest);raw=p['raw'];route=raw['route'];assert p['case_sha256']==sha(Path(j['case'])) and p['seed']==raw['seed']==j['seed']
        assert route_check(c,route)['valid'] and audit(snapshot(c),tuple(map(tuple,route)))==raw['independent_audit']
        targets=set(map(tuple,c['targets']));seen=set();threshold=(len(targets)+1)//2;index=None
        for i,point in enumerate(route):
            seen.update({tuple(point)}&targets)
            if len(seen)>=threshold:index=i;break
        h=checkpoint(c,route);assert h['index']==index and set(map(tuple,h['covered']))==seen
        assert h['old_route']==route[index:] and h['executed_route']==route[:index+1] and h['remaining_budget']==c['distance_budget']-index
        event=read(Path(e['event_source']));out=publish(c,h,event);entry=dict(map_id=j['map_id'],initial_run=j['run_id'],initial_steps=len(route)-1,
            preparation_seconds=raw['seconds'],history=h,status=out['status'],seed0=event['metadata']['repeat_seed_0'],seed1=event['metadata']['repeat_seed_1'])
        if out['case']:
            state=out['case'];free=set(map(tuple,event['free']));published=set(map(tuple,event['metadata']['published_targets']))
            assert set(map(tuple,state['targets']))==published&free and set(map(tuple,state['covered']))==seen
            assert set(map(tuple,state['metadata']['deferred_targets']))==published-free-seen
            reachable={tuple(state['current'])};q=deque(reachable)
            while q:
                x,y=q.popleft()
                for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if z in free and z not in reachable:reachable.add(z);q.append(z)
            needs=(published&free)-seen|{tuple(state['base'])}
            if not needs<=reachable:entry['status']='environment_disconnected'
            else:
                witness=independent_fallback(state);entry['witness_steps']=len(witness)-1
                if not route_check(state,witness)['valid']:entry['status']='resource_witness_failed_not_proof_infeasible'
                else:
                    plan=independent_plan(state);assert plan==json.loads(json.dumps(range_plan(snapshot(state),targets)))
                    entry['status']='gates_passed';entry['range_plan']=plan;cases[j['map_id']]=state
        checks.append(entry)
    CHECK.mkdir(exist_ok=False);(CHECK/'cases').mkdir()
    for mid,c in cases.items():write(CHECK/'cases'/(mid+'.json'),c)
    write(CHECK/'checks.json',checks)
    write(CHECK/'summary.json',dict(preparation_calls=10,valid_preparation=sum(r['valid'] for r in rows),event_status_counts={s:sum(e['status']==s for e in checks) for s in {e['status'] for e in checks}},
        preparation_seconds=sum(r['seconds'] or 0 for r in rows),overruns=sum(r['overrun_gt_10ms'] for r in rows),max_overrun_seconds=max(r['seconds']-20 for r in rows if r['seconds'] is not None),comparison_calls=0,holdout_used=False))
    write(CHECK/'sha256.json',{str(p.relative_to(CHECK)):sha(p) for p in CHECK.rglob('*') if p.is_file()});print(json.dumps(read(CHECK/'summary.json'),ensure_ascii=False))
if __name__=='__main__':main()
