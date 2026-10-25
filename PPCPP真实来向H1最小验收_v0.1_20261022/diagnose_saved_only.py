"""One saved-result audit after fail-stop. No repair, planner or rerun."""
from pathlib import Path
import json,hashlib,traceback
from independent_audit import audit_output

HERE=Path(__file__).resolve().parent

def main():
    target=HERE/'失败只读归因与保存路线审计.json';assert not target.exists(),'no repeated diagnostic audit'
    p=HERE/'outputs/legacy__large_I_corner_p30__ORIGINAL.json'
    x=json.loads(p.read_text(encoding='utf8'));c=x['input'];raw=x['entry']['raw']['branches']['P0']
    assert not x['passed'] and x['failure'] and 'independent_audit.py' in x['failure']['traceback']
    previous=c['previous'];first=raw['trace'][0]
    finding=dict(failed_slot=1,original_attempt_remains_failed=True,
        failure_location='independent_audit.py:80, direct tuple/list equality',
        producer_evidence='Frozen runtime.py converts previous with tuple(c[previous]); native ppcpp.py writes that tuple into event.previous. Worker input c remains JSON list.',
        in_memory_representation_check=dict(tuple_equals_list=tuple(previous)==previous,same_coordinates=tuple(previous)==tuple(first['previous'])),
        serialization_note='Saved JSON converts tuples to arrays; a saved-output-only check does not reproduce the in-memory container mismatch.',
        input_sha256=x['source_input_sha256'],output_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        added_calls=dict(real_entries=0,cores=0,graph_searches=0,LOS_queries=0,new_routes=0,independent_saved_route_audit_attempts=1),
        frozen_source_modified=False,retry=False)
    try:
        finding['saved_route_audit']=audit_output(c,x['job']['heading'],raw,False)
        finding['saved_route_audit_completed']=True
    except BaseException as ex:
        finding.update(saved_route_audit_completed=False,diagnostic_exception=dict(reason=repr(ex),traceback=traceback.format_exc()))
    finding['limitation']='Diagnoses review harness failure only. Not a successful formal slot, not a legacy/H1 pair, not H1 real-entry acceptance.'
    target.write_text(json.dumps(finding,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(failure='audit tuple/list mismatch',saved_route_valid=finding['saved_route_audit_completed'],formal_slot_passed=False,extra_real_entries=0),ensure_ascii=False))

if __name__=='__main__':main()
