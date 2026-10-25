"""One independent import-context process, at most one saved-output audit."""
from pathlib import Path
from collections import Counter
import sys, traceback
from v02_utils import HERE, ROOT, read, dump, sha, now
from audit_binding import bind, baseline_identity, helpers_identity

def main(round_id, ident):
    reg = read(HERE/'registration.json')
    spec = next(x for x in reg['v02']['planned_checks'] if x['id']==ident)
    target = HERE/'prechecks'/f'round_{round_id}'/(ident+'.json')
    assert not target.exists(), 'precheck cannot be silently rerun'
    result = {'utc':now(),'id':ident,'mode':spec['mode'],'passed':False,'saved_audit_calls':0}
    forbidden = []
    def guard(frame,event,arg):
        if event=='call':
            source = Path(frame.f_code.co_filename).resolve()
            name=frame.f_code.co_name
            task=name in ('solve','run_payload','process','core_route')
            selection=name=='select' and source==(HERE/'connector.py').resolve()
            graph=name in ('path','distance','precheck') and source.name in ('model.py','unified_geometry.py','bfs_metric_geometry.py')
            if source.is_relative_to(ROOT) and (task or selection or graph):
                forbidden.append({'file':str(source),'function':frame.f_code.co_name})
                raise AssertionError('precheck_attempted_true_algorithm')
        return None
    try:
        sys.settrace(guard)
        mode = spec['mode']
        if mode=='auditor_first':
            assert baseline_identity(required=False) is None
            binding = bind()
            audit_before = binding.assert_stable()
            assert baseline_identity(required=False) is None
            from native_loader import modules
            _,_,_,cold = modules()
            assert binding.assert_stable()==audit_before
        elif mode=='worker_context':
            # Import the same worker top-level (pipeline/helpers) then call its actual precore prelude.
            import worker
            _,_,_,binding,cold,loaded,identity = worker.prepare_context()
            result['worker_exact_context'] = identity
        elif mode=='verify_context':
            import verify
            binding = verify.saved_auditor_binding()
            before = binding.assert_stable()
            from native_loader import modules
            _,_,_,cold = modules()
            assert binding.assert_stable()==before
        else:
            from native_loader import modules
            h1,p2,engine,cold = modules()
            frozen = baseline_identity()
            binding = bind()
            assert baseline_identity()==frozen
            if mode=='baseline_symbols':
                import audit as frozen_audit
                assert frozen_audit.audit.__module__=='audit'
                assert not hasattr(frozen_audit,'load_auditor')
                result['native_api_files']={'H1':h1.run_payload.__code__.co_filename,'P2':p2.run_payload.__code__.co_filename}
            if mode=='helper_stability':
                import pipeline
                generic = helpers_identity()
                private = binding.identity()['modules']
                assert private['._common']['file'] != generic['common']['file']
                assert private['._geometry']['file'] != generic['geometry']['file']
                result['generic_helpers'] = generic
        result['cold'] = cold
        before = {'auditor':binding.assert_stable(),'baseline_audit':baseline_identity(),'helpers':helpers_identity()}
        source = read(HERE/'reuse_source.json')
        data_path = ROOT/source['main_source']
        assert sha(data_path)==source['files'][source['main_source']]
        data = read(data_path)
        assert data['passed'] is False and data['main_passed'] is True
        counts = Counter()
        result['saved_audit_calls'] += 1
        result['saved_reaudit'] = binding.audit_one(data,binding.post_auditor,counts)
        assert counts['independent_geometry']<=327 and counts['independent_distance']<=227
        assert counts['independent_service_intersections']<=3624
        after = {'auditor':binding.assert_stable(),'baseline_audit':baseline_identity(),'helpers':helpers_identity()}
        assert before==after
        result.update(module_identity_before=before,module_identity_after=after,source_sha256=sha(data_path),
                      original_status='failed',reuse_status='reused_saved_reaudited',passed=True)
    except BaseException as error:
        result['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
    finally:
        sys.settrace(None)
    result.update(forbidden_calls=forbidden,native_core_calls=0,postprocess_calls=0,selector_calls=0,
                  graph_search_calls=0,stub_calls=0)
    dump(target,result)
    print({'id':ident,'passed':result['passed'],'failure':result.get('failure'),'saved_audit_calls':result['saved_audit_calls']})
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main(int(sys.argv[1]),sys.argv[2])
