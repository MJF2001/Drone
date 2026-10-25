"""Read-only preparation replay; verifies witnesses, never runs solvers."""
import json
from pathlib import Path
from collections import Counter
from run import verify,read,ROOT,HERE
from audit_inputs import check_case,check_history
def main():
    p=verify();assert not p['holdout_used'] and p['new_initial_plans']==0
    assert p['core_input_whitelist']==['free','targets','covered','current','base','published_targets','distance_budget']
    sources=read(HERE/'provenance.json');hs=read(ROOT/sources[0]['history_source']);history={h['map_id']:h['history'] for h in hs}
    checks=[]
    for row in sources:check_history(read(ROOT/row['initial_source']),history[row['map_id']])
    for item in p['cases']:
        c=read(HERE/item['input']);w=read(HERE/'witnesses'/(item['name']+'.json'))['route']
        checks.append(dict(name=c['name'],**check_case(c,w)))
    assert len(checks)==20
    print(json.dumps(dict(read_only=True,status='SEALED_NOT_RUN' if not (HERE/'execution').exists() else 'EXECUTION_PRESENT',new_solver_calls=0,states=len(checks),jobs=len(p['jobs']),base_map_counts=dict(Counter(r['map_id'].split('_')[0] for r in sources)),state_counts=dict(Counter(c['scale'] for c in p['cases'])),event_counts=dict(Counter(c['event'] for c in p['cases'])),witness_checks=len(checks),history_checks=len(sources),protected_input_replay=True),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
