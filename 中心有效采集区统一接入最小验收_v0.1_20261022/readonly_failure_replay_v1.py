"""Report-only replay of the frozen failed auditor; never a runtime repair."""
from collections import Counter
from pathlib import Path
import sys,json,traceback
from center_credit_v01_20261022.utils import HERE,read,dump,sha,now
from center_credit_v01_20261022.context import bind_saved

def guard(frame,event,arg):
    if event=='call' and frame.f_code.co_name in ('solve','run_payload','process','core_route','select','run'):
        raise RuntimeError('saved_failure_replay_forbids_algorithms')
    return guard

def main():
    output=HERE/'readonly_failure_replay_v1.json'
    assert not output.exists(),'one saved replay only'
    for name,digest in read(HERE/'real_freeze.json')['files'].items():
        assert sha(HERE/name)==digest
    plan=read(HERE/'outputs/W1_H1_plan_1.json')
    assert not plan['passed'] and plan['main_passed']
    binding=bind_saved();identity=binding.initial;c=Counter()
    receipt={'utc':now(),'scope':'reproduce_frozen_auditor_failure_from_saved_payload_only',
        'original_failed_unchanged':True,'new_core_calls':0,'new_selector_calls':0,'new_post_calls':0,'new_graph_search_calls':0,
        'plan_sha256':sha(HERE/'outputs/W1_H1_plan_1.json')}
    caught=None
    sys.settrace(guard)
    try:
        binding.audit_one(plan,binding.post_auditor,c)
    except AssertionError as error:
        caught=traceback.format_exc()
    finally:
        sys.settrace(None)
    assert caught and "nc.get('post_service_intersections',0)==post['counts']['service_intersections']" in caught
    receipt.update(reproduced_original_failure=True,traceback=caught,counts=dict(c),
        observed_counter=plan['native_counts']['post_service_intersections'],
        saved_engine_service_queries=plan['post']['counts']['service_intersections'],
        saved_wrapper_post_audit_queries=plan['wrapper_counts']['post_service_intersections'])
    assert receipt['observed_counter']==receipt['saved_engine_service_queries']+receipt['saved_wrapper_post_audit_queries']
    receipt['counter_conflation_identity_proved']=True
    receipt['identity_after']=binding.assert_stable();assert receipt['identity_after']==identity
    receipt['runtime_independent_counts_status']='not persisted on exception; deterministic frozen replay counts listed as new saved queries, not observed runtime counters'
    dump(output,receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('identity_after','traceback')},ensure_ascii=False))

if __name__=='__main__':
    main()
