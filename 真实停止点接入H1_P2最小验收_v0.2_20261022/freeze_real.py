"""No algorithms: validate preparation and freeze original unused 11 jobs."""
from pathlib import Path
from collections import Counter
import difflib,ast
from v02_utils import HERE,ROOT,read,dump,sha,now

def main():
    assert not (HERE/'real_freeze.json').exists(),'already frozen'
    reg=read(HERE/'registration.json')
    checks=read(HERE/'prechecks/round_1/result.json')
    assert checks['all_six_passed'] and checks['processes_total']==checks['saved_audits_total']==6
    phase_a=Counter()
    for row in checks['rows']:
        data=read(HERE/row['source'])
        assert data['passed'] and data['saved_audit_calls']==1 and not data['forbidden_calls']
        assert data['module_identity_before']==data['module_identity_after']
        phase_a.update(data['saved_reaudit']['counts'])
    assert phase_a['independent_geometry']==90 and phase_a['independent_distance']==72
    assert phase_a['independent_service_intersections']==198
    dump(HERE/'phase_A_counts.json',{'process_checks':6,'saved_return_audits':6,'counts':dict(phase_a),
         'new_core':0,'new_selector':0,'new_postprocess':0,'new_graph_search':0,'new_stub':0})
    original=read(HERE/'original_registration.json')
    assert all(reg[name]==original[name] for name in original)
    assert reg['resume_jobs']==reg['jobs'][1:]
    old=ROOT/'真实停止点接入H1_P2最小验收_v0.1_20261022'
    inputs={}
    for file in sorted((HERE/'inputs').glob('*.json')):
        assert sha(file)==sha(old/'inputs'/file.name)
        inputs[str(file.relative_to(HERE))]=sha(file)
    dump(HERE/'input_byte_identity.json',inputs)
    for row in read(HERE/'bindings.json'):
        assert sha(HERE/row['copy'])==sha(ROOT/row['source'])==row['sha256']
    check=read(HERE/'prechecks/round_1/A04.json')
    source=read(HERE/'reuse_source.json')
    payload=read(ROOT/source['main_source'])
    assert payload['passed'] is False and payload['main_passed'] is True
    assert check['saved_reaudit']['passed'] and check['reuse_status']=='reused_saved_reaudited'
    assert check['source_sha256']==sha(ROOT/source['main_source'])
    dump(HERE/'reuse_ready.json',{'utc':now(),'id':'01_H1','status':'reused_saved_reaudited','original_status':'failed',
         'source':source['main_source'],'source_sha256':sha(ROOT/source['main_source']),
         'precheck':'prechecks/round_1/A04.json','precheck_sha256':sha(HERE/'prechecks/round_1/A04.json'),
         'new_core':0,'new_selector':0,'new_postprocess':0,'counts_in_phase_A_only':check['saved_reaudit']['counts']})
    mapping=[]
    for job in reg['jobs']:
        mapping.append({'job':job,'origin':'v0.1_saved_failed_return' if job['id']=='01_H1' else 'v0.2_new_once',
             'source':source['main_source'] if job['id']=='01_H1' else str((HERE/'outputs'/(job['id']+'.json')).relative_to(ROOT)),
             'expected_status':'reused_saved_reaudited' if job['id']=='01_H1' else 'passed',
             'old_failed_status_unchanged':job['id']=='01_H1'})
    dump(HERE/'12槽来源事前登记.json',mapping)
    diffs=[]
    for name in ('worker.py','run_real.py','verify.py'):
        diffs+=list(difflib.unified_diff((old/name).read_text(encoding='utf-8').splitlines(True),
                  (HERE/name).read_text(encoding='utf-8').splitlines(True),fromfile='v0.1/'+name,tofile='v0.2/'+name))
    for name in ('audit_binding.py','context.py'):
        diffs+=list(difflib.unified_diff([], (HERE/name).read_text(encoding='utf-8').splitlines(True),
                  fromfile='/dev/null',tofile='v0.2/'+name))
    (HERE/'模块绑定与接续包装.diff').write_text(''.join(diffs),encoding='utf-8')
    # No task calls at top-level in any new package/control; cold-load traces also passed.
    for file in HERE.rglob('*.py'):
        if 'prechecks' in file.parts:
            continue
        ast.parse(file.read_text(encoding='utf-8-sig'))
    names=[file for file in HERE.rglob('*.py') if 'prechecks' not in file.parts]
    names+=list((HERE/'inputs').glob('*.json'))
    names += [HERE/name for name in ('registration.json','original_registration.json','audit_expected_identity.json',
              'external_source_guards.json','bindings.json','old_files.json','reuse_ready.json','reuse_source.json',
              '12槽来源事前登记.json','phase_A_counts.json','01_v0.2修复与接续合同.md')]
    dump(HERE/'real_freeze.json',{'utc':now(),'files':{str(p.relative_to(HERE)):sha(p) for p in names},
         'new_core_cap':11,'H1_new_cap':5,'P2_new_cap':6,'cross_version_core_cap':12,
         'worker_01_H1_forbidden':True,'no_runtime_changes_after_start':True})
    print({'phase_A_passed':6,'phase_A_saved_geometry':90,'reuse_01_H1_no_reexecution':True,
           'new_core_slots':11,'freeze_files':len(names)})

if __name__=='__main__':
    main()
