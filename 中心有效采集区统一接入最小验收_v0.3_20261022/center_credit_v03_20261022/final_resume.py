"""Final finite continuation; old complete sessions are evidence only."""
from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
import sys,json,subprocess,traceback,ast,difflib
from copy import deepcopy
from .utils import HERE,ROOT,read,dump,sha,now
OLD=ROOT/'中心有效采集区统一接入最小验收_v0.2_20261022'
PKG=HERE/'center_credit_v03_20261022'

def prepare():
    assert not (HERE/'changes.json').exists()
    changes=[];diffs=[]
    for p in (OLD/'center_credit_v02_20261022').rglob('*.py'):
        name=str(p.relative_to(OLD/'center_credit_v02_20261022')).replace('\\','/')
        before=p.read_text(encoding='utf-8').replace('center_credit_v02_20261022','center_credit_v03_20261022');after=(PKG/name).read_text(encoding='utf-8')
        if before!=after:
            assert name in ('observe.py','worker.py','audit/_audit.py'),name
            changes.append(name);diffs.append(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(p),tofile=name)))
    dump(HERE/'changes.json',{'changed_existing':changes,'new_schema':'schema.py','new_continuation':'final_resume.py',
        'unchanged':['service.py','executor.py','pipeline.py','connector.py','detector.py','post/engine.py','audit/region.py'],
        'old_tests_hash_only':{'35_pure_hash_record':sha(OLD/'复用35纯案例hash.json'),'6_combo':sha(OLD/'precheck.json')}})
    (HERE/'schema修复.diff').write_text('\n'.join(diffs),encoding='utf-8')
    from .schema import REQUIRED,SCOPES
    dump(HERE/'计数契约.json',{'required_nonnegative_integer_fields':REQUIRED,'allowed_scopes':SCOPES,
        'producer':'observe.Recorder.__init__/start/finish/add/trace','serialization':'worker native_counts=dict(observer.counts), finally; plan independent Counter finally',
        'consumer':'schema.validate and audit._audit.audit_one exact equalities','other_ledgers':{'wrapper':'pipeline GuardedCounter','execution':'executor Counter','independent':'audit local Counter persisted even on exception'},
        'legacy_compat':'only derived after complete stage evidence and empty responsibility proof for omitted query zeros',
        'not_started_or_aborted':'never accepted as normal zero','budget':'original post overall 1200 retained'})
    dump(HERE/'precheck_registration.json',{'tests':['all_zero','one_scope','multiple_scopes','empty_task_return','zero_path','serialization','aborted_unstarted_unknown','missing_and_conservation_negative'],
        'cases_cap':16,'cases_registered':8,'round_cap':2,'core_cap':0,'post_search_cap':0})
    for p in HERE.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    dump(HERE/'namespace_expected.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')})
    print({'prepared':True,'changes':changes,'new_core_cap':6})

def precheck():
    from .context import prepare_context,stable_context
    from .observe import Recorder
    from .schema import validate,REQUIRED
    from . import pipeline
    from .exact import Expr
    assert not (HERE/'precheck.json').exists()
    before=set(HERE.rglob('*'));h1,p2,engine,binding,cold,loaded,identity=prepare_context();assert before==set(HERE.rglob('*'))
    tests=[]
    def state(empty=True,away=False):return {'S':(Q(int(away)),Q(0)),'h':(Q(1),Q(0)),'base':(Q(0),Q(0)),
        'F':{(Q(0),Q(0)),(Q(1),Q(0))},'P':set() if empty else {(Q(1),Q(0))},'H':set(),'D':set(),'E':Expr.number(100),'M':Expr()}
    forbidden={code for code,kind in Recorder(h1,p2,engine,HERE/'logs/unused').codes.items() if kind in ('h1_core','p2_core','post_entry','context','astar','distance','path')}
    def guard(frame,event,arg):
        if event=='call' and frame.f_code in forbidden:raise AssertionError('pure forbidden algorithm')
    for name in read(HERE/'precheck_registration.json')['tests']:
        obs=Recorder(h1,p2,engine,HERE/'logs'/name);c=Counter();row={'id':name,'passed':False};neg=0
        try:
            obs.start();sys.setprofile(guard);sys.settrace(obs.trace)
            try:
                if name in ('one_scope','multiple_scopes','serialization','missing_and_conservation_negative'):
                    engine.credits([(0,0),(1,0)],{(1,0)},c)
                if name=='multiple_scopes':pipeline.main_audit(state(False),[(Q(0),Q(0)),(Q(1),Q(0)),(Q(0),Q(0))],c,'post')
                if name=='empty_task_return':pipeline.main_audit(state(True,True),[(Q(1),Q(0)),(Q(0),Q(0))],c,'post')
                if name in ('zero_path','all_zero'):pipeline.main_audit(state(True),[(Q(0),Q(0))],c,'post')
                if name=='aborted_unstarted_unknown':
                    try:raise RuntimeError('fixed injected wrapper exception')
                    except RuntimeError:obs.finish(False)
                else:obs.finish(True)
            finally:sys.settrace(None);sys.setprofile(None)
            data=json.loads(json.dumps(dict(obs.counts)))
            if name=='aborted_unstarted_unknown':
                for counts in (data,dict(Recorder(h1,p2,engine,HERE/'logs/unused').counts)):
                    rejected=False
                    try:validate(counts)
                    except AssertionError:rejected=True
                    assert rejected;neg+=1
                try:obs.add('scope_unrecognized_region_queries')
                except pipeline.PipelineStop:neg+=1
                assert neg==3
            else:
                validate(data)
                if name=='missing_and_conservation_negative':
                    for kind in ('missing','total','bool','negative'):
                        bad=dict(data)
                        if kind=='missing':del bad[REQUIRED[0]]
                        elif kind=='total':bad[REQUIRED[0]]+=1
                        elif kind=='bool':bad[REQUIRED[0]]=True
                        else:bad[REQUIRED[0]]=-1
                        rejected=False
                        try:validate(bad)
                        except AssertionError:rejected=True
                        assert rejected;neg+=1
            row.update(passed=True,counts=dict(obs.counts),wrapper_or_engine_counts=dict(c),expected_rejections=neg)
        except BaseException as e:row['failure']={'reason':repr(e),'traceback':traceback.format_exc()}
        tests.append(row)
        if not row['passed']:break
    out={'passed':len(tests)==8 and all(t['passed'] for t in tests),'tests':tests,'core_calls':0,'post_search_calls':0,
         'cold':cold,'identity_after':stable_context(binding,identity)}
    dump(HERE/'precheck.json',out);print({'precheck':out['passed'],'cases':len(tests),'core_calls':0});assert out['passed'],tests[-1]

def reuse():
    from .schema import compatible
    from .context import bind_saved
    assert read(HERE/'precheck.json')['passed'] and not (HERE/'reuse_receipt.json').exists()
    file=OLD/'outputs/W2_P2_plan_2.json';p=read(file);seed=read(OLD/'sessions/W2_P2.json')
    assert not p['passed'] and not seed['passed']
    assert seed['final']['S']==[{'n':2,'d':1},{'n':21,'d':8}] and len(seed['final']['H'])==5 and seed['final']['D']==[]
    assert seed['final']['M']['exact']=={'terms':[{'r':1,'c':{'n':59,'d':8}}]}
    assert p['snapshot']==read(OLD/'calls/W2_P2_plan_2_public_input.json')
    for key in ('S','h','F','P','H','D','base','E','M'):assert seed['final'][key]==p['actual_before'][key]
    q=compatible(p,sha(file));b=bind_saved();c=Counter()
    try:q['independent']=b.audit_one(q,b.post_auditor,c)
    finally:dump(HERE/'reuse_audit_actual_counts.json',dict(c))
    q.update(passed=True,reuse_status='reused_saved_reaudited');dump(HERE/'outputs/W2_P2_plan_2.json',q)
    dump(HERE/'calls/W2_P2_plan_2_public_input.json',p['snapshot']);dump(HERE/'resume_seed.json',seed)
    dump(HERE/'resume_plan_rows.json',[{'id':'W2_P2_plan_1','file':str(OLD/'outputs/W2_P2_plan_1.json'),'provenance':'old_accepted_saved'},
        {'id':'W2_P2_plan_2','file':'outputs/W2_P2_plan_2.json','provenance':'reused_saved_reaudited'}])
    dump(HERE/'reuse_receipt.json',{'passed':True,'source_sha256':sha(file),'source':str(file),'old_failed_retained':not read(file)['passed'],
        'derived_schema':q['counter_schema_compatibility'],'counts':dict(c),'new_core_calls':0,'new_post_calls':0})
    print({'reuse':True,'counts':dict(c),'new_core_calls':0})

def real():
    assert read(HERE/'reuse_receipt.json')['passed'] and not (HERE/'real_started.json').exists()
    freeze={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and (p.suffix=='.py' or p.name in ('registration.json','namespace_expected.json','changes.json','external_source_guards.json','计数契约.json'))}
    dump(HERE/'real_freeze.json',{'files':freeze,'utc':now()});dump(HERE/'real_started.json',{'new_core_cap':6,'cross_version_cap':12,'utc':now()})
    batch={'attempted':[],'not_run':[],'core_calls':0,'stopped_on_exception':False}
    jobs=['W2_P2','W2_H1','W3_H1','W3_P2']
    for i,ident in enumerate(jobs):
        try:
            done=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'run_center.py'),'worker',ident],capture_output=True,text=True,encoding='utf-8',timeout=105)
            (HERE/'logs'/(ident+'_stdout.log')).write_text(done.stdout,encoding='utf-8');(HERE/'logs'/(ident+'_stderr.log')).write_text(done.stderr,encoding='utf-8')
            s=read(HERE/'sessions'/(ident+'.json'));batch['core_calls']+=s['native_counts'].get('core_started',0)
            batch['attempted'].append({'id':ident,'passed':s['passed']});print(batch['attempted'][-1],flush=True)
            assert batch['core_calls']<=6
            if not s['passed'] or done.returncode:raise RuntimeError(s.get('failure'))
        except BaseException as e:batch.update(stopped_on_exception=True,reason=repr(e),not_run=jobs[i+1:]);break
        finally:dump(HERE/'batch_receipt.json',batch)
    assert not batch['stopped_on_exception'],batch

def verify():
    from .schema import compatible
    from .context import bind_saved
    for name,digest in read(HERE/'real_freeze.json')['files'].items():assert sha(HERE/name)==digest
    for name,digest in read(HERE/'external_source_guards.json').items():assert sha(name)==digest
    if (HERE/'manifest.json').exists():
        for name,digest in read(HERE/'manifest.json')['files'].items():assert sha(HERE/name)==digest
    b=bind_saved();c=Counter();checks=[]
    files=[OLD/'sessions/W1_H1.json',OLD/'sessions/W1_P2.json']+[HERE/'sessions'/(j['id']+'.json') for j in read(HERE/'batch_receipt.json')['attempted']]
    def guard(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','process','core_route','select','run'):raise AssertionError('saved only')
    sys.setprofile(guard)
    try:
        for file in files:
            s=read(file);plans={};origin=file.parent.parent
            for row in s['plans']:
                pfile=origin/row['file'];p=read(pfile)
                if not p['passed']:continue
                compatible_p=p if 'observer_started' in p['native_counts'] else compatible(p,sha(pfile))
                b.audit_one(compatible_p,b.post_auditor,c);plans[row['id']]=p
            records=[json.loads(l) for l in (origin/'logs'/(s['job']['id']+'_actions.jsonl')).read_text(encoding='utf-8').splitlines()]
            assert records==s['records']
            for row in records:
                if row['kind']=='plan_wait':
                    pfile=origin/next(p['file'] for p in s['plans'] if p['id']==row['plan_id']);assert sha(pfile)==row['plan_output_sha256']
            receipt=b.package.audit_execution(read(origin/'worlds_public'/(s['job']['world']+'.json')),read(origin/s['private_truth_file']),s['initial'],records,s['final'],plans,counts=c)
            assert receipt['completed']==s['completed'];checks.append({'id':s['job']['id'],'source':str(file),'original_passed':s['passed'],'execution':receipt})
    finally:sys.setprofile(None)
    directory=HERE/'verification_runs';directory.mkdir(exist_ok=True);path=directory/('verify_'+str(1+len(list(directory.glob('verify_*.json'))))+'.json')
    dump(path,{'passed':True,'checks':checks,'counts':dict(c),'new_core_calls':0,'new_selector_calls':0,'new_post_calls':0,'new_graph_search_calls':0})
    print({'saved_verify':True,'sessions':len(checks),'counts':dict(c)})

def main(args):
    if args[0]=='worker':
        from .worker import main as worker
        worker(args[1])
    else:{'prepare':prepare,'precheck':precheck,'reuse':reuse,'real':real,'verify':verify}[args[0]]()
