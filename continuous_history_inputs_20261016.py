"""Prepare pre-event-only planner inputs and replay genuine route prefixes."""
import math,copy
from run_outer_connector_diagnostic_20261016 import ROOT,ALGO,SOURCE,BASE,read,write,sha,manifest,route_check
DEST=ALGO/'continuous_history_diagnostics/preflight_v0.1_20261016'
def initial_input(control):
    old=control['metadata']['prefix']+control['old_route'][1:]
    c=dict(name=control['metadata']['map_id']+'_initial',free=copy.deepcopy(control['free']),
        targets=copy.deepcopy(control['metadata']['initial_targets']),covered=[],current=list(control['base']),base=list(control['base']),
        old_route=copy.deepcopy(old),radius=0,distance_budget=8*len(control['free']),
        metadata=dict(map_id=control['metadata']['map_id'],split='development',stage='pre_event',initial_policy='raw_H_canonical'))
    assert route_check(c,old)['valid'];return c
def checkpoint(c,route,percent=50):
    if not 0<percent<100:raise ValueError('progress outside open interval')
    if not route_check(c,route)['valid']:raise ValueError('invalid full initial route')
    targets=set(map(tuple,c['targets']));threshold=math.ceil(len(targets)*percent/100);seen=set()
    for i,p in enumerate(route):
        seen|={tuple(p)}&targets
        if len(seen)>=threshold:
            return dict(index=i,executed_route=copy.deepcopy(route[:i+1]),current=list(p),covered=[list(z) for z in sorted(seen)],
                old_route=copy.deepcopy(route[i:]),executed_steps=i,remaining_budget=c['distance_budget']-i,actual_progress=len(seen)/len(targets))
    raise ValueError('threshold unreachable')
def publish(initial,history,event):
    free=set(map(tuple,event['free']));current=tuple(history['current']);base=tuple(initial['base'])
    if current not in free:return dict(status='unsupported_current_blocked',case=None)
    if base not in free:return dict(status='unsupported_base_blocked',case=None)
    published=set(map(tuple,event['metadata']['published_targets']));covered=set(map(tuple,history['covered']))
    deferred=published-free-covered;active=published&free
    c=dict(name=initial['name']+'_continuous_'+event['metadata']['event'],free=copy.deepcopy(event['free']),
        targets=[list(z) for z in sorted(active)],covered=copy.deepcopy(history['covered']),current=list(history['current']),
        base=list(initial['base']),old_route=copy.deepcopy(history['old_route']),radius=0,distance_budget=history['remaining_budget'],
        metadata=dict(map_id=initial['metadata']['map_id'],split='development',initial_targets=copy.deepcopy(initial['targets']),
            event=event['metadata']['event'],deferred_targets=[list(z) for z in sorted(deferred)],
            published_targets=[list(z) for z in sorted(published)],actual_progress=history['actual_progress']))
    # Historical collection remains true even when later obstructed; unfinished hidden cells deferred.
    assert deferred.isdisjoint(covered) and active<=free
    return dict(status='published',case=c)
def main():
    manifest(SOURCE);DEST.mkdir(parents=True,exist_ok=False);(DEST/'initial_cases').mkdir();records=[]
    for f in read(SOURCE/'families.json'):
        if f['anchor']==f['control']:continue
        control_path=SOURCE/'cases'/(f['control']+'.json');control=read(control_path);c=initial_input(control)
        p=DEST/'initial_cases'/(f['map_id']+'.json');write(p,c)
        # RAW replay is untimed ledger verification, not the forthcoming optimized-history experiment.
        h=checkpoint(c,c['old_route']);e=read(SOURCE/'cases'/(f['anchor']+'.json'));published=publish(c,h,e)
        assert h['covered']==sorted(control['covered']) and h['current']==control['current'] and h['old_route']==control['old_route']
        records.append(dict(map_id=f['map_id'],initial_case=str(p),initial_case_sha256=sha(p),control_sha256=sha(control_path),event_source=str(SOURCE/'cases'/(f['anchor']+'.json')),
            event_source_sha256=sha(SOURCE/'cases'/(f['anchor']+'.json')),paired_seed=f['seed'],raw_replay=h,raw_event_status=published['status']))
    assert len(records)==10;write(DEST/'records.json',records)
    write(DEST/'completion.json',dict(initial_inputs=10,raw_history_replays=10,new_solver_calls=0,optimized_history_generated=False,holdout_used=False,source_sha256=sha(ROOT/'continuous_history_inputs_20261016.py')))
    write(DEST/'sha256.json',{str(p.relative_to(DEST)):sha(p) for p in DEST.rglob('*') if p.is_file()});print('10 pre-event inputs and RAW prefix replays passed; solve calls=0')
if __name__=='__main__':main()
