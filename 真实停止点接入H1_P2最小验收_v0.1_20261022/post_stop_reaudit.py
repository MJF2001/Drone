"""One read-only audit of the already returned failed slot. No native/post imports.
Explicit module identity is used here only; frozen worker/verify sources are untouched.
This receipt cannot change the original failed status or authorize any further slots.
"""
from pathlib import Path
from collections import Counter
import importlib.util
from common import HERE, read, dump, sha, now

def main():
    target = HERE/'post_stop_saved_reaudit.json'
    assert not target.exists(), 'one saved re-audit only'
    status = read(HERE/'batch_status.json')
    assert status['failed'] == 1 and status['not_run'] == 11 and status['attempted'] == ['01_H1']
    source = HERE/'outputs/01_H1.json'
    data = read(source)
    assert data['passed'] is False and data['main_passed'] is True
    spec = importlib.util.spec_from_file_location('_explicit_saved_connector_audit', HERE/'audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counts = Counter()
    receipt = module.audit_one(data, module.load_auditor(), counts)
    assert counts['independent_geometry'] <= 327 and counts['independent_distance'] <= 227
    assert counts['independent_service_intersections'] <= 3624
    dump(target, {'utc': now(), 'kind': 'POST_STOP_SAVED_ONLY_REAUDIT_NOT_A_REAL_RETRY',
                 'source': 'outputs/01_H1.json', 'source_sha256': sha(source), 'original_status': 'failed',
                 'original_failed_status_unchanged': True, 'new_core_calls': 0, 'new_selector_calls': 0,
                 'new_postprocess_calls': 0, 'new_graph_search': 0, 'receipt': receipt,
                 'next_11_slots_not_authorized_to_resume': True})
    print({'saved_reaudit_passed': receipt['passed'], 'counts': dict(counts),
           'original_slot_still_failed': True, 'new_native_calls': 0})

if __name__ == '__main__':
    main()
