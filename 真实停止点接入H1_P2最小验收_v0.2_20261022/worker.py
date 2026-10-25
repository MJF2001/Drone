"""Resume exactly one unused slot. Auditor identity is bound BEFORE any solving."""
from collections import Counter
from pathlib import Path
import sys, json, traceback
from v02_utils import HERE, read, dump, sha, now, evidence
from pipeline import run
from context import prepare_context, stable_context

def main(job_id):
    assert job_id!='01_H1','01_H1 is saved-only reuse; never a v0.2 worker entry'
    reg=read(HERE/'registration.json')
    assert job_id in {j['id'] for j in reg['resume_jobs']}
    job=next(j for j in reg['resume_jobs'] if j['id']==job_id)
    final=HERE/'outputs'/(job_id+'.json')
    marker=HERE/'logs'/(job_id+'_markers.jsonl')
    assert not final.exists() and not marker.exists(),'no real reattempt'
    result={'job':job,'started_utc':now(),'passed':False,'native_counts':{},'precore_ready':False}
    observer=None
    try:
        freeze=read(HERE/'real_freeze.json')
        for name,digest in freeze['files'].items():
            assert sha(HERE/name)==digest,('package_conflict',name)
        for name,digest in read(HERE/'external_source_guards.json').items():
            assert sha(name)==digest,('external_conflict',name)
        h1,p2,engine,binding,cold,loaded,identity=prepare_context()
        result.update(cold=cold,loaded_sources=loaded,auditor_identity_before=identity,precore_ready=True,
                      input_sha256=sha(HERE/job['input']))
        from observe import Recorder
        observer=Recorder(h1,p2,engine,marker)
        def core(payload,method,budget,seed):
            response=h1.run_payload(payload,'PPCPP',budget,seed) if method=='H1' else p2.run_payload(payload,budget,seed)
            dump(HERE/'outputs'/(job_id+'_native_return.json'),{'request_utf8':payload.decode(),'response':response,
                 'native_counts_at_return':dict(observer.counts)})
            return response
        def post(payload,**kwargs):
            encoded,envelope=engine.process(payload,**kwargs)
            dump(HERE/'outputs'/(job_id+'_post_return.json'),{'request_utf8':payload.decode(),
                 'response_utf8':encoded,'envelope':envelope})
            return encoded,envelope
        observer.mark('warm_pipeline_about_to_start',method=job['method'])
        sys.settrace(observer.trace)
        try:
            run((HERE/job['input']).read_bytes(),job['method'],job['seed'],core,post,result,observer)
        finally:
            sys.settrace(None)
        result['native_counts']=dict(observer.counts)
        dump(final,evidence(result))
        assert observer.counts['core_started']==observer.counts['core_returned']==observer.counts['core_complete']==1
        assert observer.counts['post_entry_calls']==1
        result['auditor_identity_after_main']=stable_context(binding,identity)
        counts=Counter()
        result['independent']=binding.audit_one(result,binding.post_auditor,counts)
        limits=reg['limits_per_real_slot']
        assert counts['independent_geometry']<=limits['independent_geometry']
        assert counts['independent_distance']<=limits['independent_distance']
        assert counts['independent_service_intersections']<=limits['independent_service_intersections']
        result['auditor_identity_after_independent']=stable_context(binding,identity)
        result['passed']=True
    except BaseException as error:
        sys.settrace(None)
        result.update(passed=False,failure={'reason':repr(error),'traceback':traceback.format_exc()})
    if observer is not None:
        result['native_counts']=dict(observer.counts)
    from native_loader import loaded_hashes
    result['loaded_sources']=loaded_hashes()
    result['finished_utc']=now()
    dump(final,evidence(result))
    print(json.dumps({'id':job_id,'passed':result['passed'],'failure':result.get('failure'),
                      'native_counts':result['native_counts']},ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main(sys.argv[1])
