"""Read saved evidence only. No selector, native loader, core or engine imports."""
from collections import Counter
from pathlib import Path
from common import HERE, ROOT, read, dump, sha, now
from audit import load_auditor, audit_one

def main():
    manifest = read(HERE/'completion_manifest.json')
    for name, digest in manifest['files'].items():
        assert sha(HERE/name) == digest, ('package_hash', name)
    for row in read(HERE/'old_files.json'):
        assert sha(ROOT/row['path']) == row['sha256'], ('old_file_hash', row['path'])
    for name, digest in read(HERE/'external_source_guards.json').items():
        assert sha(name) == digest, ('external_source_hash', name)
    for binding in read(HERE/'bindings.json'):
        assert sha(HERE/binding['copy']) == sha(ROOT/binding['source']) == binding['sha256']
    assert sha(HERE/'root_before.md') == manifest['root_before']
    assert sha(HERE/'root_after.md') == manifest['root_after']
    reg = read(HERE/'registration.json')
    status = read(HERE/'batch_status.json')
    assert len(status['attempted']) <= 12 and len(set(status['attempted'])) == len(status['attempted'])
    assert status['attempted'] == [j['id'] for j in reg['jobs'][:len(status['attempted'])]]
    assert status['not_run'] == 12-len(status['attempted'])
    assert len(status['completed'])+status['failed'] == len(status['attempted'])
    counts, audits, completed = Counter(), [], {}
    auditor = load_auditor()
    for ident in status['attempted']:
        path = HERE/'outputs'/(ident+'.json')
        if not path.exists():
            assert status['failure'] and status['failure']['job']['id'] == ident
            continue
        data = read(path)
        assert data['job']['id'] == ident
        assert sha(HERE/data['job']['input']) == data['input_sha256']
        assert data.get('snapshot') == read(HERE/data['job']['input'])
        for name, digest in data.get('loaded_sources', {}).items():
            assert sha(name) == digest
        if data['passed']:
            slot = Counter()
            receipt = audit_one(data, auditor, slot)
            assert slot['independent_geometry'] <= reg['limits_per_real_slot']['independent_geometry']
            assert slot['independent_distance'] <= reg['limits_per_real_slot']['independent_distance']
            assert slot['independent_service_intersections'] <= reg['limits_per_real_slot']['independent_service_intersections']
            counts.update(slot)
            audits.append({'id': ident, 'receipt': receipt})
            completed[ident] = data
        else:
            assert data.get('failure') and status['failure']['job']['id'] == ident
    pairs = []
    for case in reg['cases']:
        h, p = completed.get(case['id']+'_H1'), completed.get(case['id']+'_P2')
        if h and p:
            for name in ('gamma', 'gamma_length', 'h_entry', 'predicted_entry', 'actual_before', 'actual_after', 'core_request'):
                assert h[name] == p[name], ('paired_physical_state', case['id'], name)
            pairs.append(case['id'])
    directory = HERE/'verify_receipts'
    directory.mkdir(exist_ok=True)
    index = len(list(directory.glob('verify_*.json')))+1
    report = {'utc': now(), 'status': 'VERIFIED_SAVED_ONLY', 'main_batch_status': manifest['status'],
              'saved_successful_pipelines_checked': len(audits), 'paired_physical_inputs_equal': pairs,
              'failed_preserved': status['failed'], 'not_run': status['not_run'],
              'new_core_calls': 0, 'new_selector_calls': 0, 'new_postprocess_calls': 0, 'new_graph_search': 0,
              'saved_geometry_and_decision_rechecks': dict(counts), 'files_checked': len(manifest['files']),
              'old_files_checked': len(read(HERE/'old_files.json')), 'audits': audits}
    dump(directory/f'verify_{index:03d}.json', report)
    print({k: v for k, v in report.items() if k != 'audits'})

if __name__ == '__main__':
    main()
