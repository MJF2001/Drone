"""Exactly one planned native entry per process; preserve before downstream audit."""
from collections import Counter
from pathlib import Path
import sys, json, time, traceback
from common import HERE, ROOT, read, dump, sha, now, evidence
from pipeline import run

def main(job_id):
    reg = read(HERE/'registration.json')
    job = next(j for j in reg['jobs'] if j['id'] == job_id)
    final = HERE/'outputs'/(job_id+'.json')
    marker = HERE/'logs'/(job_id+'_markers.jsonl')
    assert not final.exists() and not marker.exists(), 'no reattempt of real slot'
    freeze = read(HERE/'real_freeze.json')
    for name, digest in freeze['files'].items():
        assert sha(HERE/name) == digest, ('package_conflict', name)
    for name, digest in read(HERE/'external_source_guards.json').items():
        assert sha(name) == digest, ('external_source_conflict', name)
    from native_loader import modules, loaded_hashes
    h1, p2, engine, cold = modules()
    loaded = loaded_hashes()
    guards = read(HERE/'external_source_guards.json')
    for name, digest in loaded.items():
        if not Path(name).is_relative_to(HERE):
            assert name in guards and guards[name] == digest, ('unbound_loaded_source', name)
    from observe import Recorder
    observer = Recorder(h1, p2, engine, marker)
    result = {'job': job, 'started_utc': now(), 'cold': cold, 'loaded_sources': loaded,
              'passed': False, 'input_sha256': sha(HERE/job['input'])}
    def core(payload, method, budget, seed):
        response = h1.run_payload(payload, 'PPCPP', budget, seed) if method == 'H1' else p2.run_payload(payload, budget, seed)
        dump(HERE/'outputs'/(job_id+'_native_return.json'), {'request_utf8': payload.decode(),
               'response': response, 'native_counts_at_return': dict(observer.counts)})
        return response
    def post(payload, **kwargs):
        encoded, envelope = engine.process(payload, **kwargs)
        dump(HERE/'outputs'/(job_id+'_post_return.json'), {'request_utf8': payload.decode(),
               'response_utf8': encoded, 'envelope': envelope})
        return encoded, envelope
    try:
        observer.mark('warm_pipeline_about_to_start', method=job['method'])
        sys.settrace(observer.trace)
        try:
            run((HERE/job['input']).read_bytes(), job['method'], job['seed'], core, post, result, observer)
        finally:
            sys.settrace(None)
        result['native_counts'] = dict(observer.counts)
        # Persist all main/native/post data before external auditing.
        dump(final, evidence(result))
        assert observer.counts['core_started'] == observer.counts['core_returned'] == observer.counts['core_complete'] == 1
        assert observer.counts['post_entry_calls'] == 1
        from audit import load_auditor, audit_one
        counts = Counter()
        result['independent'] = audit_one(result, load_auditor(), counts)
        limits = reg['limits_per_real_slot']
        assert counts['independent_geometry'] <= limits['independent_geometry']
        assert counts['independent_distance'] <= limits['independent_distance']
        assert counts['independent_service_intersections'] <= limits['independent_service_intersections']
        result['passed'] = True
    except BaseException as error:
        sys.settrace(None)
        result.update(failure={'reason': repr(error), 'traceback': traceback.format_exc()}, passed=False)
    result['native_counts'] = dict(observer.counts)
    result['loaded_sources'] = loaded_hashes()
    result['finished_utc'] = now()
    dump(final, evidence(result))
    print(json.dumps({'id': job_id, 'passed': result['passed'], 'stage': result.get('stage'),
                      'failure': result.get('failure'), 'native_counts': result['native_counts']}, ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main(sys.argv[1])
