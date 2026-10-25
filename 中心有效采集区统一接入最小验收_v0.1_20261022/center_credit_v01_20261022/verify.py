"""Saved-only replay. No selector, native solve, postprocessor or graph searches."""
from collections import Counter
from pathlib import Path
import sys,json,traceback,time
from .utils import HERE,ROOT,read,dump,sha,now,evidence
from .pipeline import grid
from .executor import Executor
from .context import bind_saved as bind
from .audit.pure import audit_entry,audit_forecast

def forbidden(frame,event,arg):
    if event=='call' and frame.f_code.co_name in ('solve','run_payload','process','core_route','select','known_select','run'):
        raise RuntimeError('saved_only_verifier_forbidden_algorithm_entry')
    return forbidden

def main():
    directory=HERE/'verification_runs'
    directory.mkdir(exist_ok=True)
    number=1+len(list(directory.glob('verify_*.json')))
    dest=directory/('verify_'+str(number)+'.json')
    assert not dest.exists()
    result={'utc':now(),'passed':False,'core_calls':0,'selector_calls':0,'post_calls':0,'graph_search_calls':0,
            'plans':[],'sessions':[],'technical':[],'source':str(HERE)}
    c=Counter()
    try:
        if (HERE/'manifest.json').exists():
            for relative,digest in read(HERE/'manifest.json')['files'].items():
                assert sha(HERE/relative)==digest,('sealed_file_changed',relative)
        for relative,digest in read(HERE/'real_freeze.json')['files'].items():
            assert sha(HERE/relative)==digest,('real_frozen_file_changed',relative)
        for path,digest in read(HERE/'external_source_guards.json').items():
            assert sha(path)==digest,('old_source_or_data_changed',path)
        for b in read(HERE/'source_bindings.json'):
            assert sha(b['source'])==b['source_sha256']
        binding=bind()
        identity=binding.assert_stable()
        sys.settrace(forbidden)
        reg=read(HERE/'registration.json')
        for file in sorted((HERE/'technical_rounds').glob('round_*/*.json')):
            if file.name in ('receipt.json','source_hashes.json','preparation.json'):
                continue
            saved=read(file)
            if not saved['passed']:
                result['technical'].append({'file':str(file.relative_to(HERE)),'retained_failure':True})
                continue
            case=saved['case']
            receipt=binding.package.audit_execution(case['public'],case['private'],saved['initial'],saved['records'],saved['final'],technical=True)
            c.update(receipt['counts'])
            if 'entry_prediction' in saved:
                audit_entry(saved['entry_prediction'],c)
            if 'fixed_forecast' in saved:
                audit_forecast(saved['initial'],saved['fixed_forecast'],c)
            if 'negative_controls' in saved:
                for mutation in saved['negative_controls']:
                    rejected=False
                    negative_counts=Counter()
                    try:
                        binding.package.audit_execution(case['public'],case['private'],saved['initial'],mutation['records'],mutation['final'],technical=True,counts=negative_counts)
                    except AssertionError:
                        rejected=True
                    assert rejected
                    c.update(negative_counts)
            result['technical'].append({'file':str(file.relative_to(HERE)),'passed':True,'receipt':receipt})
        batch=read(HERE/'batch_receipt.json')
        for entry in batch['attempted']:
            job=next(j for j in reg['jobs'] if j['id']==entry['id'])
            file=HERE/'sessions'/(job['id']+'.json')
            if not file.exists():
                result['sessions'].append({'id':job['id'],'controller_failure_without_final':True})
                continue
            saved=read(file)
            plans={}
            for row in saved['plans']:
                plan=read(HERE/row['file'])
                if plan['passed']:
                    pc=Counter()
                    receipt=binding.audit_one(plan,binding.post_auditor,pc)
                    c.update(pc)
                    result['plans'].append({'id':row['id'],'receipt':receipt,'output_sha256':sha(HERE/row['file'])})
                    plans[row['id']]=plan
                else:
                    result['plans'].append({'id':row['id'],'retained_failure':True})
            public=read(HERE/'worlds_public'/(job['world']+'.json'))
            private=read(HERE/'worlds_private'/(job['world']+'.json'))
            lines=[json.loads(line) for line in (HERE/'logs'/(job['id']+'_actions.jsonl')).read_text(encoding='utf-8').splitlines()]
            assert lines==saved['records']
            for row in lines:
                if row['kind']=='plan_wait':
                    assert sha(HERE/'outputs'/(row['plan_id']+'.json'))==row['plan_output_sha256']
            receipt=binding.package.audit_execution(public,private,saved['initial'],lines,saved['final'],plans)
            if saved['passed']:
                assert saved['completed'] and receipt['completed']
                assert saved['independent_execution']['actual_length_exact']==receipt['actual_length_exact']
            c.update(receipt['counts'])
            result['sessions'].append({'id':job['id'],'original_passed':saved['passed'],'replay':receipt})
        result['identity_after']=binding.assert_stable()
        assert identity==result['identity_after']
        if (HERE/'final_receipt.json').exists():
            final=read(HERE/'final_receipt.json')
            assert sha(HERE/'manifest.json')==final['manifest_sha256']
            assert sha(HERE/final['first_verify_file'])==final['first_verify_sha256']
        result.update(passed=True,batch_stopped=batch['stopped_on_exception'],unrun=batch['not_run'])
    except BaseException as error:
        result['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
    finally:
        sys.settrace(None)
    result['counts']=dict(c)
    dump(dest,evidence(result))
    print(json.dumps({'saved_only_verify':result['passed'],'file':str(dest),'plans':len(result['plans']),
          'sessions':len(result['sessions']),'counts':dict(c),'failure':result.get('failure')},ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
