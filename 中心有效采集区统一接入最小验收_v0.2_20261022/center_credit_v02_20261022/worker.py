"""One real session once. Truth never enters the public planning request."""
from collections import Counter
import sys,json,traceback,time
from .utils import HERE,read,dump,sha,now,evidence
from .pipeline import run
from .executor import Executor
from .context import prepare_context,stable_context

def main(job_id):
    reg=read(HERE/'registration.json')
    job=next(j for j in reg['jobs'] if j['id']==job_id)
    final=HERE/'sessions'/(job_id+'.json')
    log=HERE/'logs'/(job_id+'_actions.jsonl')
    assert not final.exists() and not log.exists(),'no real reattempt'
    result={'job':job,'started_utc':now(),'passed':False,'plans':[],'native_counts':{}}
    ex=None
    observer=None
    aggregate=Counter()
    try:
        for name,digest in read(HERE/'real_freeze.json')['files'].items():
            assert sha(HERE/name)==digest,('package_conflict',name)
        for name,digest in read(HERE/'external_source_guards.json').items():
            assert sha(name)==digest,('external_conflict',name)
        h1,p2,engine,binding,cold,loaded,identity=prepare_context()
        result.update(cold=cold,loaded_sources=loaded,auditor_identity_before=identity)
        public=read(HERE/'worlds_public'/(job['world']+'.json'))
        private=read(HERE/'worlds_private'/(job['world']+'.json'))
        def writer(record):
            with log.open('a',encoding='utf-8') as f:
                f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
                f.flush()
        ex=Executor(public,private,writer)
        result.update(public_initial=public,private_truth_file='worlds_private/'+job['world']+'.json',initial=ex.initial)
        if job_id!='W1_H1':
            assert ex.action('collect_here')['status']=='committed'
        plans={}
        from .observe import Recorder
        if job_id=='W1_H1':
            old=read(HERE/'reuse_session_seed.json')
            ex.s['H']=set(map(tuple,old['final']['H']))
            ex.records=old['records'];ex.tail=ex.records[-1]['record_hash']
            ex.counts.clear()
            log.write_text(''.join(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n' for v in ex.records),encoding='utf-8')
            saved=read(HERE/'outputs/W1_H1_plan_1.json')
            result['plans'].append({'id':'W1_H1_plan_1','file':'outputs/W1_H1_plan_1.json','input':'calls/W1_H1_plan_1_public_input.json','provenance':'reused_saved_reaudited'})
            plans['W1_H1_plan_1']=saved
            ex.wait_plan('W1_H1_plan_1',saved['full_route'],sha(HERE/'outputs/W1_H1_plan_1.json'))
            status=ex.execute(saved['full_route'])
            assert status in ('detected','completed_route')
            start=1 if status=='detected' else 2
        else:
            start=0
        for index in range(start,2):
            ident=job_id+'_plan_'+str(index+1)
            plan_file=HERE/'outputs'/(ident+'.json')
            input_file=HERE/'calls'/(ident+'_public_input.json')
            dump(input_file,ex.public_case(ident))
            plan={'id':ident,'passed':False,'native_counts':{}}
            result['plans'].append({'id':ident,'file':str(plan_file.relative_to(HERE)),'input':str(input_file.relative_to(HERE))})
            observer=Recorder(h1,p2,engine,HERE/'logs'/(ident+'_markers.jsonl'))
            def core(payload,method,budget,seed):
                response=h1.run_payload(payload,'PPCPP',budget,seed) if method=='H1' else p2.run_payload(payload,budget,seed)
                dump(HERE/'calls'/(ident+'_native_return.json'),{'request_utf8':payload.decode(),'response':response,
                     'native_counts_at_return':dict(observer.counts)})
                return response
            def post(payload,**kwargs):
                encoded,envelope=engine.process(payload,**kwargs)
                dump(HERE/'calls'/(ident+'_post_return.json'),{'request_utf8':payload.decode(),
                     'response_utf8':encoded,'envelope':envelope})
                return encoded,envelope
            observer.mark('warm_pipeline_about_to_start',method=job['method'])
            counts=Counter()
            try:
                sys.settrace(observer.trace)
                try:
                    run(input_file.read_bytes(),job['method'],job['seed'],core,post,plan,observer)
                finally:
                    sys.settrace(None)
                plan['native_counts']=dict(observer.counts)
                dump(plan_file,evidence(plan))
                assert observer.counts['core_started']==observer.counts['core_returned']==observer.counts['core_complete']==1
                assert observer.counts['post_entry_calls']==1
                plan['auditor_identity_after_main']=stable_context(binding,identity)
                plan['independent']=binding.audit_one(plan,binding.post_auditor,counts)
                cap=reg['per_pipeline_caps']
                for key in ('independent_geometry','independent_distance'):
                    assert counts[key]<=cap[key],(key,counts[key])
                assert counts['independent_service_intersections']<=cap['independent_service']
                plan['auditor_identity_after_independent']=stable_context(binding,identity)
                plan['passed']=True
            except BaseException as error:
                plan.update(passed=False,failure={'reason':repr(error),'traceback':traceback.format_exc()})
                raise
            finally:
                plan['independent_counts_actual_even_on_exception']=dict(counts)
                plan['native_counts']=dict(observer.counts)
                aggregate.update(observer.counts)
                observer=None
                dump(plan_file,evidence(plan))
            plans[ident]=read(plan_file)
            ex.wait_plan(ident,plan['full_route'],sha(plan_file))
            status=ex.execute(plan['full_route'])
            if status=='detected':
                assert index==0,'second_discovery_or_replanning_cap'
                continue
            assert status=='completed_route',status
            break
        assert ex.completed(),'not_completed_and_returned_after_two_plans'
        replay=binding.package.audit_execution(public,private,ex.initial,ex.records,ex.snapshot(),plans)
        assert replay['completed']
        result['independent_execution']=replay
        for row in ex.records:
            if row['kind']=='plan_wait':
                assert sha(HERE/'outputs'/(row['plan_id']+'.json'))==row['plan_output_sha256']
        cap=reg['per_execution_caps']
        c=ex.counts; ic=replay['counts']
        assert c['execution_action_calls']<=cap['actions']
        assert c['detector_box_queries']+c['safety_box_queries']<=cap['main_boxes']
        assert ic.get('independent_detector_box_queries',0)+ic.get('independent_safety_box_queries',0)<=cap['independent_boxes']
        assert c['execution_truth_geometry']<=cap['main_truth_geometry']
        assert ic.get('independent_geometry',0)<=cap['independent_truth_geometry']
        assert c['execution_service_intersections']<=cap['main_service']
        assert ic.get('independent_service_intersections',0)<=cap['independent_service']
        result['auditor_identity_after']=stable_context(binding,identity)
        result['passed']=True
    except BaseException as error:
        sys.settrace(None)
        result['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
    if observer is not None:
        aggregate.update(observer.counts)
    result['native_counts']=dict(aggregate)
    if ex is not None:
        result.update(final=ex.snapshot(),records=ex.records,main_execution_counts=dict(ex.counts),completed=ex.completed())
    result['finished_utc']=now()
    dump(final,evidence(result))
    print(json.dumps({'id':job_id,'passed':result['passed'],'completed':result.get('completed'),
         'plans':len(result['plans']),'core_calls':aggregate['core_started'],'failure':result.get('failure')},ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main(sys.argv[1])
