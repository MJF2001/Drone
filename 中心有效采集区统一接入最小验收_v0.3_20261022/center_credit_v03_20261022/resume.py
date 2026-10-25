"""Finite observer repair, saved first-plan reuse, and at most 11 new entries."""
from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
from copy import deepcopy
import sys,json,subprocess,traceback,difflib,ast,importlib
from .utils import HERE,ROOT,read,dump,sha,now
OLD=ROOT/'中心有效采集区统一接入最小验收_v0.1_20261022'
PKG=HERE/'center_credit_v03_20261022'

def files():
    return {str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()
            and (p.suffix=='.py' or p.name in ('registration.json','namespace_expected.json','external_source_guards.json','changes.json','复用35纯案例hash.json'))}

def prepare():
    assert not (HERE/'changes.json').exists()
    changes=[];diffs=[]
    allowed={'observe.py','audit/_audit.py','worker.py'}
    for p in (OLD/'center_credit_v01_20261022').rglob('*.py'):
        name=str(p.relative_to(OLD/'center_credit_v01_20261022')).replace('\\','/')
        target=PKG/name
        before=p.read_text(encoding='utf-8').replace('center_credit_v01_20261022','center_credit_v03_20261022')
        after=target.read_text(encoding='utf-8')
        if before!=after:
            assert name in allowed,('unauthorized_change',name)
            changes.append(name)
            diffs.append(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(p),tofile=str(target))))
    dump(HERE/'changes.json',{'allowed_changes':changes,'unchanged_semantic_files':['service.py','executor.py','pipeline.py','connector.py','detector.py','post/engine.py','post/geometry.py','audit/region.py'],
        'scope':'observer ownership, conserved accounting assertions, actual independent-count finally persistence, saved continuation wrapper only'})
    (HERE/'修复.diff').write_text('\n'.join(diffs),encoding='utf-8')
    dump(HERE/'复用35纯案例hash.json',{str(p):sha(p) for p in (OLD/'technical_rounds/round_1').glob('*.json')})
    assert read(OLD/'technical_rounds/round_1/receipt.json')['passed']
    for p in HERE.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    dump(HERE/'namespace_expected.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')})
    dump(HERE/'precheck_registration.json',{'tests':['engine_only','wrapper_only','sequential','variable_counts','nested_exception_cleanup','serialization_identity'],
        'paired_old_new_branches':12,'new_core_cap':0,'post_search_cap':0,'round_cap':2})
    print({'prepared':True,'changed':changes,'reused_pure_cases':35,'core_calls':0})

def precheck():
    from .context import prepare_context,stable_context
    from .observe import Recorder
    from . import pipeline
    from .exact import Expr
    assert not (HERE/'precheck.json').exists()
    before=set(HERE.rglob('*'))
    h1,p2,engine,binding,cold,loaded,identity=prepare_context()
    assert before==set(HERE.rglob('*'))
    sys.path.insert(0,str(OLD))
    Old=importlib.import_module('center_credit_v01_20261022.observe').Recorder
    tests=[]
    forbidden={code for code,kind in Recorder(h1,p2,engine,HERE/'logs/unused').codes.items()
               if kind in ('h1_core','p2_core','post_entry','context','astar','distance','path')}
    def guard(frame,event,arg):
        if event=='call' and frame.f_code in forbidden:raise AssertionError('pure entry violation')
    def state(missing=False):
        return {'S':(Q(0),Q(0)),'h':None,'base':(Q(0),Q(0)),
                'F':{(Q(x),Q(y)) for x in (0,1) for y in (0,1)},'P':{(Q(1),Q(1 if missing else 0))},
                'H':set(),'D':set(),'E':Expr.number(100),'M':Expr()}
    for index,name in enumerate(read(HERE/'precheck_registration.json')['tests']):
        row={'id':name,'passed':False}
        try:
            branches=[]
            for cls in (Old,Recorder):
                obs=cls(h1,p2,engine,HERE/'logs'/('pure_'+name+'.jsonl'))
                counts=Counter();wc=Counter();errors=0
                sys.setprofile(guard);sys.settrace(obs.trace)
                try:
                    repeats=3 if name=='variable_counts' else 1
                    for _ in range(repeats):
                        if name!='wrapper_only':engine.credits([(0,0),(1,0),(0,0)],{(1,0)},counts)
                        if name!='engine_only':
                            try:pipeline.main_audit(state(name=='nested_exception_cleanup'),[(Q(0),Q(0)),(Q(1),Q(0)),(Q(0),Q(0))],wc,'post')
                            except pipeline.PipelineStop:
                                assert name=='nested_exception_cleanup';errors+=1
                    if name=='nested_exception_cleanup':
                        engine.credits([(0,0),(1,0)],{(1,0)},counts)
                finally:
                    sys.settrace(None);sys.setprofile(None)
                assert not any(obs.counts.get(k,0) for k in ('core_started','post_entry_calls','Astar_started'))
                if cls is Recorder:
                    assert obs.counts['post_service_intersections']==counts['service_intersections']
                    assert obs.counts['scope_wrapper_post_region_queries']==wc['post_service_intersections']
                    assert obs.counts['shared_region_queries_total']==sum(v for k,v in obs.counts.items() if k.startswith('scope_') and k.endswith('_region_queries'))
                    assert obs.counts['post_service_queries_total_protected']==counts['service_intersections']+wc['post_service_intersections']
                else:assert obs.counts['post_service_intersections']==counts['service_intersections']+wc['post_service_intersections']
                branches.append({'observer':'old' if cls is Old else 'new','counts':dict(obs.counts),'engine':dict(counts),'wrapper':dict(wc),'caught_expected_errors':errors})
            assert json.loads(json.dumps(branches))==branches
            row.update(passed=True,branches=branches,old_conflation_exposed=name not in ('engine_only',))
        except BaseException as e:
            row['failure']={'reason':repr(e),'traceback':traceback.format_exc()}
        tests.append(row)
        if not row['passed']:break
    result={'passed':len(tests)==6 and all(t['passed'] for t in tests),'tests':tests,'cold':cold,'new_core_calls':0,'post_search_calls':0,'graph_search_calls':0,
            'identity_after':stable_context(binding,identity),'new_queries':{'region':sum(sum(v['engine'].get('service_intersections',0)+v['wrapper'].get('post_service_intersections',0) for v in t.get('branches',[])) for t in tests)}}
    dump(HERE/'precheck.json',result)
    print({'precheck':result['passed'],'tests':len(tests),'core_calls':0,'region_queries':result['new_queries']})
    assert result['passed'],tests[-1]

def reuse():
    from .context import bind_saved
    assert read(HERE/'precheck.json')['passed'] and not (HERE/'reuse_receipt.json').exists()
    original=read(OLD/'outputs/W1_H1_plan_1.json');seed=read(OLD/'sessions/W1_H1.json')
    assert not original['passed'] and not seed['passed']
    assert original['snapshot']==read(OLD/'calls/W1_H1_plan_1_public_input.json')
    assert original['actual_before']==original['actual_after']
    public=read(HERE/'worlds_public/W1.json');oldpublic=seed['public_initial']
    assert public==oldpublic and seed['final']['M']['exact']['terms']==[] and seed['final']['h'] is None
    assert seed['final']['H']==[[0,0]] and len(seed['records'])==1
    p=deepcopy(original);nc=p['native_counts'];old_nc=deepcopy(nc)
    engine=p['post']['counts']['service_intersections']
    scope={'engine':engine}
    for phase in ('prediction','native','post','full'):scope['wrapper_'+phase]=p['wrapper_counts'].get(phase+'_service_intersections',0)
    assert old_nc['post_service_intersections']==engine+scope['wrapper_post']
    nc['post_service_intersections']=engine
    nc['shared_region_queries_total']=sum(scope.values())
    nc['post_service_queries_total_protected']=engine+scope['wrapper_post']
    assert nc['post_service_queries_total_protected']<=1200
    for key,val in scope.items():nc['scope_'+key+'_region_queries']=val
    p['provenance']={'status':'reused_saved_reaudited','old_plan':str(OLD/'outputs/W1_H1_plan_1.json'),
        'old_sha256':sha(OLD/'outputs/W1_H1_plan_1.json'),'old_observer_counts_unmodified':old_nc,
        'derived_scope_counts_not_original_trace':scope,'basis':'saved engine query counter and wrapper phase counters; full independent audit; no subtraction constant'}
    binding=bind_saved();c=Counter()
    try:p['independent']=binding.audit_one(p,binding.post_auditor,c)
    finally:dump(HERE/'reuse_audit_actual_counts.json',dict(c))
    p['passed']=True;p['reuse_status']='reused_saved_reaudited'
    dump(HERE/'outputs/W1_H1_plan_1.json',p)
    dump(HERE/'calls/W1_H1_plan_1_public_input.json',original['snapshot'])
    dump(HERE/'reuse_session_seed.json',seed)
    dump(HERE/'reuse_receipt.json',{'passed':True,'scope_derived':scope,'counts':dict(c),'new_core_calls':0,'new_post_calls':0,
        'old_failed_retained':not read(OLD/'outputs/W1_H1_plan_1.json')['passed'],'input_config_initial_equal':True})
    print({'saved_reuse':True,'new_core_calls':0,'counts':dict(c)})

def real():
    assert read(HERE/'reuse_receipt.json')['passed'] and not (HERE/'real_started.json').exists()
    dump(HERE/'real_freeze.json',{'utc':now(),'files':files()})
    dump(HERE/'real_started.json',{'utc':now(),'new_core_cap':11,'cross_version_cap':12})
    batch={'attempted':[],'not_run':[],'stopped_on_exception':False,'core_calls':0}
    jobs=read(HERE/'registration.json')['jobs']
    for i,j in enumerate(jobs):
        try:
            done=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'run_center.py'),'worker',j['id']],capture_output=True,text=True,encoding='utf-8',timeout=105)
            (HERE/'logs'/(j['id']+'_stdout.log')).write_text(done.stdout,encoding='utf-8')
            (HERE/'logs'/(j['id']+'_stderr.log')).write_text(done.stderr,encoding='utf-8')
            s=read(HERE/'sessions'/(j['id']+'.json'));batch['core_calls']+=s['native_counts'].get('core_started',0)
            batch['attempted'].append({'id':j['id'],'passed':s['passed']})
            print(batch['attempted'][-1],flush=True)
            assert batch['core_calls']<=11
            if done.returncode or not s['passed']:raise RuntimeError(s.get('failure'))
        except BaseException as e:
            batch.update(stopped_on_exception=True,reason=repr(e),not_run=[x['id'] for x in jobs[i+1:]])
            break
        finally:dump(HERE/'batch_receipt.json',batch)
    assert not batch['stopped_on_exception'],batch

def verify():
    from .context import bind_saved
    directory=HERE/'verification_runs';directory.mkdir(exist_ok=True)
    path=directory/('verify_'+str(1+len(list(directory.glob('verify_*.json'))))+'.json')
    for name,digest in read(HERE/'real_freeze.json')['files'].items():assert sha(HERE/name)==digest
    for name,digest in read(HERE/'external_source_guards.json').items():assert sha(name)==digest
    if (HERE/'manifest.json').exists():
        for name,digest in read(HERE/'manifest.json')['files'].items():assert sha(HERE/name)==digest
    binding=bind_saved();c=Counter();checks=[]
    def guard(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','process','core_route','select','run'):raise AssertionError('saved verify entry')
    sys.setprofile(guard)
    try:
        for entry in read(HERE/'batch_receipt.json')['attempted']:
            s=read(HERE/'sessions'/(entry['id']+'.json'));plans={}
            for row in s['plans']:
                p=read(HERE/row['file'])
                if p['passed']:binding.audit_one(p,binding.post_auditor,c);plans[row['id']]=p
            public=read(HERE/'worlds_public'/(s['job']['world']+'.json'));private=read(HERE/s['private_truth_file'])
            records=[json.loads(l) for l in (HERE/'logs'/(entry['id']+'_actions.jsonl')).read_text(encoding='utf-8').splitlines()]
            assert records==s['records']
            for row in records:
                if row['kind']=='plan_wait':assert sha(HERE/'outputs'/(row['plan_id']+'.json'))==row['plan_output_sha256']
            receipt=binding.package.audit_execution(public,private,s['initial'],records,s['final'],plans,counts=c)
            assert receipt['completed']==s['completed']
            checks.append({'id':entry['id'],'passed':s['passed'],'execution':receipt})
    finally:sys.setprofile(None)
    out={'passed':True,'checks':checks,'counts':dict(c),'new_core_calls':0,'new_selector_calls':0,'new_post_calls':0,'new_graph_search_calls':0}
    dump(path,out);print({'saved_verify':True,'counts':dict(c)})

def main(args):
    mode=args[0]
    if mode=='worker':
        from .worker import main as worker
        worker(args[1])
    else:{'prepare':prepare,'precheck':precheck,'reuse':reuse,'real':real,'verify':verify}[mode]()
