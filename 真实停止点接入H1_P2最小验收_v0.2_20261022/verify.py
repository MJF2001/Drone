"""Saved-only independent verification; imports no native loader/selector/engine."""
from pathlib import Path
from collections import Counter
from v02_utils import HERE, ROOT, read, dump, sha, now
from audit_binding import bind

def saved_auditor_binding():
    return bind()

def assert_saved_identity(data):
    before=data['auditor_identity_before']
    assert before==data['auditor_identity_after_main']==data['auditor_identity_after_independent']
    expected=read(HERE/'audit_expected_identity.json')
    for module in before['auditor']['modules'].values():
        assert sha(module['file'])==module['sha256']
        assert Path(module['origin']).resolve()==Path(module['file']).resolve()
        assert Path(module['file']).resolve().is_relative_to(HERE/expected['package'])
    assert Path(before['baseline_audit']['file']).resolve()==Path(expected['baseline_audit_path']).resolve()
    assert sha(before['baseline_audit']['file'])==before['baseline_audit']['sha256']
    for function in before['auditor']['functions'].values():
        assert sha(function['file'])==function['sha256']
        assert function['module'].startswith(expected['package']+'.')

def physical_pairs(data_by_id, cases):
    pairs=[]
    physical=('free','published_targets','targets','covered','deferred_targets','current','base',
              'old_route','initial_targets','distance_budget','predator')
    for case in cases:
        h,p=data_by_id.get(case['id']+'_H1'),data_by_id.get(case['id']+'_P2')
        if h is None or p is None:
            continue
        for name in ('gamma','gamma_length','h_entry','predicted_entry','actual_before','actual_after'):
            assert h[name]==p[name],('physical_pair',case['id'],name)
        for name in physical:
            assert h['core_request'][name]==p['core_request'][name],('core_physical_pair',case['id'],name)
        pairs.append({'case':case['id'],'physical_state_equal':True,
                      'H1_source':'reused_v0.1_failed_return_reaudited' if case['id']=='01' else 'new_v0.2',
                      'P2_source':'new_v0.2','same_round_timing_pair':case['id']!='01'})
    return pairs

def main():
    manifest=read(HERE/'completion_manifest.json')
    for name,digest in manifest['files'].items():
        assert sha(HERE/name)==digest,('package_hash',name)
    for row in read(HERE/'old_files.json'):
        assert sha(ROOT/row['path'])==row['sha256'],('old_changed',row['path'])
    for name,digest in read(HERE/'external_source_guards.json').items():
        assert sha(name)==digest
    assert sha(HERE/'root_before.md')==manifest['root_before']
    assert sha(HERE/'root_after.md')==manifest['root_after']
    for row in read(HERE/'bindings.json'):
        assert sha(ROOT/row['source'])==sha(HERE/row['copy'])==row['sha256']
    reg=read(HERE/'registration.json')
    oldreg=read(HERE/'original_registration.json')
    for name in ('cases','jobs','limits_per_real_slot','pipeline_seconds','connector_seconds','core_seconds_max','post_candidate_absolute_seconds'):
        assert reg[name]==oldreg[name]
    assert reg['resume_jobs']==oldreg['jobs'][1:]
    stage=read(HERE/'batch_status.json')
    assert len(stage['attempted'])<=11 and len(set(stage['attempted']))==len(stage['attempted'])
    assert stage['attempted']==[j['id'] for j in reg['resume_jobs'][:len(stage['attempted'])]]
    assert '01_H1' not in stage['attempted']
    binding=saved_auditor_binding()
    identity=binding.assert_stable()
    counts=Counter()
    checked=[]
    data_by_id={}
    source=read(HERE/'reuse_source.json')
    oldpath=ROOT/source['main_source']
    old=read(oldpath)
    assert old['passed'] is False and old['main_passed'] is True
    ready=read(HERE/'reuse_ready.json')
    assert ready['status']=='reused_saved_reaudited'
    assert sha(ROOT/ready['source'])==ready['source_sha256']
    slot=Counter()
    receipt=binding.audit_one(old,binding.post_auditor,slot)
    counts.update(slot)
    checked.append({'id':'01_H1','origin':'old_failed_return_reaudited','receipt':receipt})
    data_by_id['01_H1']=old
    for job in reg['resume_jobs']:
        path=HERE/'outputs'/(job['id']+'.json')
        if job['id'] not in stage['completed']:
            continue
        data=read(path)
        assert data['passed'] and data['job']==job
        assert data['input_sha256']==sha(HERE/job['input'])
        assert data['snapshot']==read(HERE/job['input'])
        assert_saved_identity(data)
        for name,digest in data['loaded_sources'].items():
            assert sha(name)==digest
        slot=Counter()
        receipt=binding.audit_one(data,binding.post_auditor,slot)
        limits=reg['limits_per_real_slot']
        assert slot['independent_geometry']<=limits['independent_geometry']
        assert slot['independent_distance']<=limits['independent_distance']
        assert slot['independent_service_intersections']<=limits['independent_service_intersections']
        counts.update(slot)
        checked.append({'id':job['id'],'origin':'new_v0.2','receipt':receipt})
        data_by_id[job['id']]=data
    pairs=physical_pairs(data_by_id,reg['cases'])
    gate_ok=len(stage['completed'])==11 and stage['failed']==0 and len(pairs)==6 and len(checked)==12
    assert gate_ok==manifest['real_acceptance_passed']
    assert binding.assert_stable()==identity
    directory=HERE/'verify_receipts'
    directory.mkdir(exist_ok=True)
    index=len(list(directory.glob('verify_*.json')))+1
    report={'utc':now(),'status':'VERIFIED_SAVED_ONLY','real_acceptance_passed':gate_ok,
        'new_slots_checked':len(stage['completed']),'old_saved_return_checked':1,'old_status_still_failed':True,
        'cross_version_distinct_native_entries':1+len(stage['attempted']),
        'new_selector':0,'new_core':0,'new_postprocess':0,'new_graph_search':0,
        'saved_rechecks':dict(counts),'physical_pairs':pairs,'auditor_identity':identity,
        'manifest_files_checked':len(manifest['files']),'old_guard_records_checked':len(read(HERE/'old_files.json')),
        'receipts':checked}
    dump(directory/f'verify_{index:03d}.json',report)
    print({k:v for k,v in report.items() if k not in ('receipts','auditor_identity')})

if __name__=='__main__':
    main()
