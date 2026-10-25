"""Full fixed OFF snapshot batch; reuse the accepted controlled worker unchanged."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import sys,os,json,time,hashlib,subprocess,traceback,platform,inspect,ast,importlib.util
H=Path(__file__).resolve().parent;R=H.parent
ON=R/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'
CONTROL=R/'中心区计时插桩影响核查_v0.1_20261022'
spec=importlib.util.spec_from_file_location('_accepted_controlled_OFF',CONTROL/'run_check.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
# Artifact routing only: no production callable, budget, clock or observation change.
C.H=H
read=C.read;dump=C.dump;sha=C.sha;ps=C.ps
PRECHECKS=['OFF_source_identity','single_entry_protection','explicit_zero_and_unobservable_record','all_inputs_and_history','serialization','reject_fabricated_unknown_counts','fixed_scale_bounds','read_only_verify_stub_and_source']

def strict_OFF(x):
    assert x['job']['config']=='OFF'
    assert x['native_observation']=={'observable':False,'status':'not_observed_profile_OFF','counts':None}
    assert x['native_counts_actual'] is None
    assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0}

def verify_one(x,inp,native,post):
    assert x['passed'] and x['independent']['passed'];strict_OFF(x)
    assert x['input']==inp and x['native']==native
    assert x['post_request_utf8']==json.dumps(post['request'],ensure_ascii=False,separators=(',',':'))
    assert x['post_response_utf8']==post['response_utf8'] and x['post_envelope']==post['envelope']
    for record in x['views'].values():assert record['metrics']['missing']==0 and record['metrics']['return_success']

def comparison(x,old):
    assert x['input']==old['input'] and all(x['job'][k]==old['job'][k] for k in ('case','seed','method'))
    natural=x['timing']['termination']==old['timing']['termination']=='natural'
    decisions=C.canonical(x['native']['raw'])==C.canonical(old['native']['raw'])
    rawsame=x['native']['raw']['route']==old['native']['raw']['route']
    postsame=x['post']['vertices']==old['post']['vertices']
    posttime=any(v['post_envelope']['late'] or v['post_envelope']['fallback']=='soft_deadline' for v in (x,old))
    bad=(natural and not decisions) or (rawsame and not postsame and not posttime)
    return {'id':x['job']['id'],'case':x['job']['case'],'seed':x['job']['seed'],'method':x['job']['method'],
        'old_ON_termination':old['timing']['termination'],'new_OFF_termination':x['timing']['termination'],
        'both_natural':natural,'raw_route_equal':rawsame,'post_route_equal':postsame,'canonical_decisions_equal':decisions,
        'classification':'unexplained_deterministic_difference_STOP' if bad else 'both_natural_records_equal' if natural else 'budget_behavior_changed' if x['timing']['termination']!=old['timing']['termination'] else 'both_budget_work_unresolved',
        'substantive_difference':bad,'old_ON_output_sha256':sha(ON/'outputs'/(x['job']['id']+'.json')),
        'cross_batch_not_randomized_control':True}

def setup():
    assert not (H/'plan.json').exists()
    for d in ('inputs','outputs','logs','source_snapshot'):(H/d).mkdir(exist_ok=True)
    (H/'root_before.md').write_bytes((R/'当前进度与下一步.md').read_bytes())
    (H/'source_snapshot/执行稿.md').write_bytes((R/'中心区关闭核心详细插桩全量开发比较执行稿_给sol_20261022.md').read_bytes())
    oldplan=read(ON/'plan.json');formal=[dict(j,config='OFF') for j in oldplan['formal']];assert len(formal)==324
    assert len({j['case'] for j in formal})==54 and set(j['seed'] for j in formal)=={20261020,20261021,20261022}
    for p in (ON/'inputs').glob('*.json'):(H/'inputs'/p.name).write_bytes(p.read_bytes())
    assert len(list((H/'inputs').glob('*.json')))==54
    (H/'history_evidence.json').write_bytes((ON/'history_evidence.json').read_bytes())
    guards=read(CONTROL/'source_guards.json')
    for name,digest in read(CONTROL/'active_freeze.json').items():assert sha(CONTROL/name)==digest;guards[str(CONTROL/name)]=digest
    for name in ('final_receipt.json','manifest.json','02_保护等价与完整预登记.md','03_阶段A线程口径只读补充.md','verify_receipt.json','review_packet.md'):
        guards[str(CONTROL/name)]=sha(CONTROL/name)
    for j in oldplan['formal']:
        p=ON/'outputs'/(j['id']+'.json');guards[str(p)]=sha(p)
    # Documents and render helpers are frozen source references, not new experiments.
    for p in (ON/'report_bench_v02.py',R/'研究主线澄清_直达条件与覆盖判定不是创新_20261022.md',R/'任务格与中心采集区设计及资料依据_20261022.md'):
        guards[str(p)]=sha(p)
    dump(H/'source_guards.json',guards)
    dump(H/'bindings.json',{'accepted_OFF_module':str(CONTROL/'run_check.py'),'module_sha256':sha(CONTROL/'run_check.py'),
        'worker_unchanged':True,'worker_source_sha256':hashlib.sha256(inspect.getsource(C.worker).encode()).hexdigest(),
        'entry_guard_source_sha256':hashlib.sha256(inspect.getsource(C.invoke_once).encode()).hexdigest(),
        'only_namespace_rebinding':'C.H set to new output package; worker source and all production callables unchanged',
        'accepted_detail_OFF':C.detail(None),'new_core_calls':0})
    dump(H/'plan.json',{'formal':formal,'technical':[],'formal_cap':324,'technical_cap':0,'real_warmup':0,'views':648,
        'thread_env':oldplan['thread_env'],'budget':{'native':20,'post_soft':18,'post_total_late_marker':20,'post_candidate':4096,'parent_timeout':150},
        'prechecks':PRECHECKS,'precheck_cap':8,'preparation_repair_cap':2,'configuration':'关闭核心详细profile配置; not zero-observation or pure algorithm timing',
        'order':'exact original formal order and seeds, methods alternate per state/seed; fresh serial process per entry',
        'history':'same externally supplied evidence-backed H, explicit idempotent collect_here, no broadened replay, no future events',
        'scale_bounds':oldplan['geometry_bounds'],'timing':'exact accepted OFF worker boundaries; loaded-core hash included after native, two actual evidence flushes excluded, cold/pre-hash/independent outside; worker/parent wall separate',
        'canonical_removed_clock_fields':['seconds','accepted_seconds','budget','overrun_gt_10ms','start','end'],
        'cross_batch_comparison':'same input/seed native/post/termination/canonical decisions; no precise causal time attribution; unexplained both-natural differences stop',
        'statistics':'same-state same-seed then three-seed state equal; total distance ratios separate; nearest-rank P95; full batch plus natural subset/excluded IDs',
        'stop':'first substantive failure; all attempts consume slots, no retry; no new maps/seeds/budgets/mechanisms'})
    dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'CPU':os.environ.get('PROCESSOR_IDENTIFIER'),'thread_env':oldplan['thread_env'],'serial':True,'cross_entry_cache':False})
    for name,fn in [('accepted_worker.py.txt',C.worker),('accepted_invoke_once.py.txt',C.invoke_once)]:
        (H/'source_snapshot'/name).write_text(inspect.getsource(fn),encoding='utf-8')
    print({'prepared':54,'formal':324,'technical':0,'new_core_calls':0,'OFF_worker_directly_reused':True})

def validate_scale(f,p):assert type(f) is int and type(p) is int and 0<=f<=10000 and 0<=p<=1500

def precheck():
    assert not (H/'prechecks.json').exists();records=[]
    for name in PRECHECKS:
        try:
            if name=='OFF_source_identity':
                binding=read(H/'bindings.json');assert sha(CONTROL/'run_check.py')==binding['module_sha256']
                assert hashlib.sha256(inspect.getsource(C.worker).encode()).hexdigest()==binding['worker_source_sha256']
                assert C.worker.__code__.co_filename==str(CONTROL/'run_check.py') and C.H==H and C.detail(None)['counts'] is None
                assert C.B.identity()['primary']['file']!=C.B.identity()['independent']['file']
            elif name=='single_entry_protection':
                token={'started':0,'returned':0,'exceptions':0};out=C.invoke_once(lambda:{'fixed':True},token,None)
                assert out=={'fixed':True} and token=={'started':1,'returned':1,'exceptions':0} and sys.getprofile() is None
                try:C.invoke_once(lambda:None,token,None);raise RuntimeError('duplicate accepted')
                except AssertionError:pass
            elif name=='explicit_zero_and_unobservable_record':
                x={'job':{'config':'OFF'},'native_observation':C.detail(None),'native_counts_actual':None,'entry_ledger':{'started':1,'returned':1,'exceptions':0}}
                strict_OFF(x);zero={'engine':0,'raw_execution':0,'post_execution':0,'total':0};assert sum(zero[k] for k in ('engine','raw_execution','post_execution'))==zero['total']
            elif name=='all_inputs_and_history':
                plan=read(H/'plan.json');history=read(H/'history_evidence.json');assert len(history)==54 and len(plan['formal'])==324
                counts=Counter((j['case'],j['seed'],j['method']) for j in plan['formal']);assert len(counts)==324 and set(counts.values())=={1}
                for h in history:
                    file=H/'inputs'/(h['id']+'.json');c=read(file);assert file.read_bytes()==(ON/'inputs'/file.name).read_bytes()
                    assert ps(c['covered'])=={tuple(e['cell']) for e in h['evidence']} and tuple(c['current']) in ps(c['covered'])
                    assert ps(c['deferred_targets'])==ps(c['published_targets'])-ps(c['free'])-ps(c['covered'])
                    witness_path=next(p for p in h['source_files'] if 'witnesses' in Path(p).parts);prefix=read(witness_path)['history']
                    before_path=next(p for p in h['source_files'] if 'prep' in Path(p).parts and 'inputs' in Path(p).parts);before=read(before_path)
                    for e in h['evidence']:
                        assert prefix[e['prefix_index']]==e['cell']==e['point'] and tuple(e['cell']) in ps(before['targets'])&ps(before['free'])
                        assert e['published_before_event'] and e['center_in_new_open_region']
                    for p,digest in h['source_files'].items():assert sha(p)==digest
            elif name=='serialization':
                x={'native_observation':C.detail(None),'entry_ledger':{'started':0,'returned':0,'exceptions':0},'input':read(next((H/'inputs').glob('*.json')))}
                assert json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))==x and x['native_observation']['counts'] is None
            elif name=='reject_fabricated_unknown_counts':
                base={'job':{'config':'OFF'},'native_observation':C.detail(None),'native_counts_actual':None,'entry_ledger':{'started':1,'returned':1,'exceptions':0}}
                for badvalue in ({},0,{'row_BFS_built':0}):
                    x=deepcopy(base);x['native_observation']['counts']=badvalue;rejected=False
                    try:strict_OFF(x)
                    except AssertionError:rejected=True
                    assert rejected
            elif name=='fixed_scale_bounds':
                for p in (H/'inputs').glob('*.json'):
                    c=read(p);validate_scale(len(c['free']),len(c['published_targets']))
                for f,p in ((10001,1),(1,1501)):
                    rejected=False
                    try:validate_scale(f,p)
                    except AssertionError:rejected=True
                    assert rejected
            elif name=='read_only_verify_stub_and_source':
                post={'request':{'id':'fixed'},'response_utf8':'fixed','envelope':{'late':False}}
                x={'job':{'config':'OFF'},'native_observation':C.detail(None),'native_counts_actual':None,'entry_ledger':{'started':1,'returned':1,'exceptions':0},'passed':True,'independent':{'passed':True},'input':{'fixed':True},'native':{'raw':'fixed'},'post_request_utf8':json.dumps(post['request'],ensure_ascii=False,separators=(',',':')),'post_response_utf8':'fixed','post_envelope':post['envelope'],'views':{'fixed':{'metrics':{'missing':0,'return_success':True}}}}
                verify_one(x,{'fixed':True},{'raw':'fixed'},post)
                code=ast.parse(inspect.getsource(verify)+inspect.getsource(verify_one))
                forbidden={'worker','invoke_once','run_payload','process','evaluate','audit_result','solve'}
                for node in ast.walk(code):
                    if isinstance(node,ast.Call):assert (node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else '') not in forbidden
            records.append({'id':name,'passed':True,'new_core_calls':0,'post_search_calls':0,'new_region_queries':0})
        except BaseException as exc:
            records.append({'id':name,'passed':False,'reason':repr(exc),'traceback':traceback.format_exc()});break
    passed=len(records)==8 and all(r['passed'] for r in records)
    dump(H/'prechecks.json',{'passed':passed,'cases':records,'new_core_calls':0,'post_search_calls':0,'new_region_queries':0,'preparation_repairs':0,
        'reused_evidence_not_rerun':{'controlled_prechecks_sha256':sha(CONTROL/'prechecks.json'),'controlled_final_sha256':sha(CONTROL/'final_receipt.json')}})
    print({'prechecks':passed,'cases':len(records),'new_core_calls':0});assert passed

def freeze():
    return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.suffix=='.py' or p.is_relative_to(H/'inputs') or p.name in ('plan.json','bindings.json','history_evidence.json','source_guards.json','environment.json','prechecks.json','01_完整预登记与计时口径.md'))}

def worker(job):
    assert job['config']=='OFF'
    C.worker(job)

def run():
    assert read(H/'prechecks.json')['passed'] and not (H/'attempts.jsonl').exists()
    plan=read(H/'plan.json');jobs=plan['formal'];assert len(jobs)==324 and not plan['technical'];dump(H/'active_freeze.json',freeze())
    env=dict(os.environ,**plan['thread_env'],PYTHONDONTWRITEBYTECODE='1');status={'formal_completed':[],'technical_completed':[],'failure':None,'not_run':[],'ON_OFF_comparisons':[]}
    for i,j in enumerate(jobs):
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':j['id'],'event':'started','time':time.time()})+'\n')
        before=time.perf_counter();jobfile=H/'current_job.json';dump(jobfile,j)
        try:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jobfile)],env=env,capture_output=True,timeout=150)
            (H/'logs'/(j['id']+'.log')).write_bytes(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError('worker nonzero; preserved output')
            x=read(H/'outputs'/(j['id']+'.json'));strict_OFF(x);status['formal_completed'].append(j['id'])
            check=comparison(x,read(ON/'outputs'/(j['id']+'.json')));status['ON_OFF_comparisons'].append(check)
            if check['substantive_difference']:raise RuntimeError('unexplained deterministic ON/OFF difference; stop')
        except BaseException as exc:status['failure']={'id':j['id'],'reason':repr(exc),'traceback':traceback.format_exc()};status['not_run']=[v['id'] for v in jobs[i+1:]]
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':j['id'],'event':'ended','wall':time.perf_counter()-before,'success':not bool(status['failure'])})+'\n')
        dump(H/'status.json',status)
        if status['failure']:print('STOP',i+1,j['id'],flush=True);return
        if (i+1)%12==0:print('COMPLETE',i+1,'/324',j['id'],flush=True)
    print('FINITE OFF FULL BATCH COMPLETE; STOP',flush=True)

def verify():
    assert not (H/'verify_receipt.json').exists()
    for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest,name
    for name,digest in read(H/'source_guards.json').items():assert sha(name)==digest,name
    status=read(H/'status.json');receipts=[]
    for ident in status['formal_completed']:
        file=H/'outputs'/(ident+'.json');x=read(file)
        verify_one(x,read(H/x['job']['input']),read(H/'outputs'/(ident+'_native_raw.json')),read(H/'outputs'/(ident+'_post_raw.json')))
        receipts.append({'id':ident,'sha256':sha(file),'independent_saved_counts':x['independent']['counts']})
    dump(H/'verify_receipt.json',{'passed':True,'completed_outputs':len(receipts),'receipts':receipts,'failure_retained':status['failure'],'scope':'bindings and saved independent receipts only','new_core_calls':0,'new_post_calls':0,'new_geometry_queries':0})
    print({'verified':len(receipts),'new_core_calls':0,'new_geometry_queries':0,'failure':status['failure']})

if __name__=='__main__':
    if sys.argv[1]=='worker':worker(read(sys.argv[2]))
    else:{'setup':setup,'precheck':precheck,'run':run,'verify':verify}[sys.argv[1]]()
