"""Bounded ON/OFF observation experiment; production algorithms imported unchanged."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import sys,os,json,time,hashlib,subprocess,traceback,platform,inspect,ast,difflib
H=Path(__file__).resolve().parent;R=H.parent
OLD=R/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'
sys.path.insert(0,str(OLD))
from center_bench_v01_20261022 import bench as B
from center_bench_v01_20261022.metrics import evaluate
from center_bench_v01_20261022.post import engine
read=B.read;dump=B.dump;sha=B.sha;ps=B.ps
PRECHECKS=['zero_observer_and_entry_ledger','fixed_return_ON_OFF_equality_and_limits','original_deadline_checks_survive','original_legality_checks_survive','OFF_unobservable_not_zero','serialization','independent_audit_identity','single_entry_and_exception_cleanup']

def detail(obs):
    return {'observable':obs is not None,'status':'observed' if obs is not None else 'not_observed_profile_OFF',
            'counts':dict(obs.c) if obs is not None else None}

def invoke_once(fn,ledger,obs):
    assert ledger=={'started':0,'returned':0,'exceptions':0},'entry must have one exclusive owner'
    ledger['started']+=1
    assert sys.getprofile() is None
    sys.setprofile(obs.profile if obs is not None else None)
    try:
        out=fn();ledger['returned']+=1;return out
    except BaseException:
        ledger['exceptions']+=1;raise
    finally:sys.setprofile(None)

def canonical(raw):
    """Remove documented clock fields, retaining all routes and available decisions."""
    excluded={'seconds','accepted_seconds','budget','overrun_gt_10ms','start','end'}
    if isinstance(raw,dict):return {k:canonical(v) for k,v in raw.items() if k not in excluded}
    if isinstance(raw,list):return [canonical(v) for v in raw]
    if isinstance(raw,tuple):return [canonical(v) for v in raw]
    return raw

def pair_check(a,b):
    assert a['job']['config']!=b['job']['config']
    on,off=(a,b) if a['job']['config']=='ON' else (b,a)
    ja,jb=on['job'],off['job'];assert all(ja[k]==jb[k] for k in ('case','seed','method','repeat'))
    natural=on['timing']['termination']==off['timing']['termination']=='natural'
    route_same=on['native']['raw']['route']==off['native']['raw']['route']
    decisions_same=canonical(on['native']['raw'])==canonical(off['native']['raw'])
    post_same=on['post']['vertices']==off['post']['vertices']
    post_budget=any(x['post_envelope']['fallback'] in ('soft_deadline',) or x['post_envelope']['late'] for x in (on,off))
    unexpected=(natural and not decisions_same) or (route_same and not post_same and not post_budget)
    return {'case':ja['case'],'method':ja['method'],'seed':ja['seed'],'repeat':ja['repeat'],'ON':ja['id'],'OFF':jb['id'],
            'ON_termination':on['timing']['termination'],'OFF_termination':off['timing']['termination'],
            'both_natural':natural,'raw_route_equal':route_same,'available_decisions_equal':decisions_same,'post_vertices_equal':post_same,
            'same_recorded_work_eligible':natural and decisions_same,
            'classification':'unexpected_natural_or_post_difference_STOP' if unexpected else 'both_natural_same_recorded_work' if natural else 'budget_behavior_difference' if on['timing']['termination']!=off['timing']['termination'] else 'both_budget_work_unresolved',
            'unexpected_mechanism_difference':unexpected,
            'OFF_detail':off['native_observation']}

def setup():
    assert not (H/'plan.json').exists()
    for d in ('inputs','outputs','logs','source_snapshot'):(H/d).mkdir(exist_ok=True)
    (H/'root_before.md').write_bytes((R/'当前进度与下一步.md').read_bytes())
    (H/'source_snapshot/执行稿.md').write_bytes((R/'中心区计时插桩影响受控核查执行稿_给sol_20261022.md').read_bytes())
    oldplan=read(OLD/'plan.json');bycase={};guards=read(OLD/'old_source_guards.json')
    for j in oldplan['formal']:
        if j['method']!='P2_MULTI':continue
        file=OLD/'outputs'/(j['id']+'.json');x=read(file);assert x['passed']
        bycase.setdefault(j['case'],[]).append({'job':j,'termination':x['timing']['termination'],'sha256':sha(file),'file':str(file)})
        guards[str(file)]=sha(file)
    budget=sorted(k for k,v in bycase.items() if any(x['termination']=='budget' for x in v))[:3]
    natural=sorted(k for k,v in bycase.items() if len(v)==3 and all(x['termination']=='natural' for x in v))[:3]
    assert not set(budget)&set(natural)
    selection=[{'id':case,'stratum':stratum,'seed':min(x['job']['seed'] for x in bycase[case]),'old_P2_evidence':bycase[case]} for stratum,cases in [('old_P2_any_budget',budget),('old_P2_all_three_natural',natural)] for case in cases]
    selection.sort(key=lambda x:x['id']);jobs=[];pairnum=0
    for repeat in (1,2,3):
        for ci,c in enumerate(selection):
            methods=('PPCPP','P2_MULTI') if (repeat+ci)%2 else ('P2_MULTI','PPCPP')
            for method in methods:
                configs=('ON','OFF') if pairnum%2==0 else ('OFF','ON');pairnum+=1
                for config in configs:
                    jobs.append({'id':f"controlled__{c['id']}__{method}__r{repeat}__{config}",'case':c['id'],'method':method,'config':config,'seed':c['seed'],'repeat':repeat,'input':'inputs/'+c['id']+'.json'})
    for c in selection:(H/'inputs'/(c['id']+'.json')).write_bytes((OLD/'inputs'/(c['id']+'.json')).read_bytes())
    for name,digest in read(OLD/'active_freeze.json').items():assert sha(OLD/name)==digest;guards[str(OLD/name)]=digest
    for name in ('final_receipt.json','manifest.json','01_完整预登记与计时口径.md','review_packet.md','00_通俗开发比较报告.md','old_source_guards.json'):
        guards[str(OLD/name)]=sha(OLD/name)
    older=R/'PPCPP直达质量时间开发比较_v0.1_20261022'
    for name in ('run.py','01_终止语义与预登记.md','source_seal.json'):guards[str(older/name)]=sha(older/name)
    dump(H/'source_guards.json',guards)
    dump(H/'selection.json',{'rule':'lexicographic first 3 states with any old formal P2 deadline; first 3 with all three old seeds natural; minimum original seed per state; no selection by new results','selected':selection,'available_budget_states':sum(any(x['termination']=='budget' for x in v) for v in bycase.values()),'available_all_natural_states':sum(len(v)==3 and all(x['termination']=='natural' for x in v) for v in bycase.values()),'missing_slots':6-len(selection),'new_core_calls':0})
    dump(H/'plan.json',{'jobs':jobs,'cap':72,'planned':len(jobs),'no_technical_or_warmup_entries':True,'prechecks':PRECHECKS,'precheck_cap':8,'preparation_repair_cap':2,
        'budget':{'native':20,'post_total':20,'post_soft':18,'post_candidate':4096,'parent_worker_timeout':150},
        'thread_env':oldplan['thread_env'],'repeats':3,'order':'adjacent paired configurations; ON-first/OFF-first strictly alternating across core pairs; method order alternates by case/repeat',
        'ON':'exact previous NativeObserver class and profile method, only around same native entry',
        'OFF':'no detailed profiler, counts null/unobservable; original native clocks, contract, geometry deadlines/audits and post controls unchanged',
        'lightweight_guard':'exclusive single native-entry dispatch token for both configs; no per-function hook or safety clock replacement',
        'timing':'same old common boundaries, pre-start freeze/cold outside, post-return loaded-core hashes inside common wrapper; subtract two actual evidence flushes; independent audit outside; worker and parent walls separate',
        'same_work':'both natural and canonical complete raw output equal, removing only seconds/accepted_seconds/budget/overrun_gt_10ms/start/end; keep stages/status/passes/swaps/improvements/source/route/PPCPP decisions; this is recorded-work equivalence, OFF detailed query counts unobservable',
        'stop':'any substantive failure or unexplained natural decision/post-route difference; preserve all attempts, no fixes or replacement after start; budget-state differences alone allowed',
        'statistics':'paired same state/seed/repeat; each state/core/config all 3 times median and min/max; same-recorded-work pairs separately, no full-54 correction'})
    dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'CPU':os.environ.get('PROCESSOR_IDENTIFIER'),'thread_rule':oldplan['thread_env'],'cache':'serial fresh process per entry; no across-entry cache','source_profile':inspect.getsourcefile(B.NativeObserver),'profile_source_sha256':sha(inspect.getsourcefile(B.NativeObserver))})
    (H/'source_snapshot/NativeObserver.py.txt').write_text(inspect.getsource(B.NativeObserver),encoding='utf-8')
    (H/'source_snapshot/previous_worker.py.txt').write_text(inspect.getsource(B.worker),encoding='utf-8')
    (H/'worker_diff.patch').write_text(''.join(difflib.unified_diff(inspect.getsource(B.worker).splitlines(True),inspect.getsource(worker).splitlines(True),fromfile='previous_instrumented_worker',tofile='controlled_worker')),encoding='utf-8')
    print({'selected':[c['id'] for c in selection],'new_calls':0,'planned':len(jobs)})

def precheck():
    assert not (H/'prechecks.json').exists()
    runtime,p2=B.load_native();records=[]
    for name in PRECHECKS:
        obs=B.NativeObserver(runtime,p2);ledger={'started':0,'returned':0,'exceptions':0};counts=Counter();passed=False
        try:
            if name=='zero_observer_and_entry_ledger':
                assert all(type(v) is int and v==0 for v in obs.c.values()) and ledger=={'started':0,'returned':0,'exceptions':0}
            elif name=='fixed_return_ON_OFF_equality_and_limits':
                values=[]
                for enabled in (True,False):
                    token={'started':0,'returned':0,'exceptions':0}
                    def fixed():
                        assert bool(sys.getprofile())==enabled
                        return {'raw':{'route':[[0,0]],'status':'finished'},'limits':{'native':20,'post_total':20,'post_soft':18,'post_candidate':4096}}
                    values.append(invoke_once(fixed,token,obs if enabled else None));assert token=={'started':1,'returned':1,'exceptions':0}
                assert values[0]==values[1] and sys.getprofile() is None
                assert read(H/'plan.json')['budget']==dict(values[0]['limits'],parent_worker_timeout=150)
            elif name=='original_deadline_checks_survive':
                import model
                for enabled in (True,False):
                    g=object.__new__(model.Geometry);g.deadline=-1;token={'started':0,'returned':0,'exceptions':0}
                    try:invoke_once(lambda:g.check_time(),token,obs if enabled else None);raise AssertionError('deadline disabled')
                    except model.DeadlineExceeded:assert token['exceptions']==1
                assert sys.getprofile() is None
            elif name=='original_legality_checks_survive':
                from model import Snapshot
                from unified_geometry import single_cell_audit
                s=Snapshot('fixed_audit',frozenset({(0,0),(1,0)}),frozenset({(1,0)}),frozenset(),(0,0),(0,0),(),0,4)
                for enabled in (True,False):
                    def fixed():
                        assert single_cell_audit(s,((0,0),(1,0),(0,0)))['valid']
                        assert not single_cell_audit(s,((0,0),(2,0),(0,0)))['valid']
                        assert not single_cell_audit(s,((0,0),))['valid']
                    invoke_once(fixed,{'started':0,'returned':0,'exceptions':0},obs if enabled else None)
            elif name=='OFF_unobservable_not_zero':
                x=detail(None);assert not x['observable'] and x['counts'] is None and x['status']=='not_observed_profile_OFF'
            elif name=='serialization':
                v={'observation':detail(None),'entry':ledger,'native':{'raw':{'route':[[0,0]],'events':[{'stage':'fixed','passes':3,'start':.1,'end':.2}],'seconds':.3}}}
                assert read_json(json.dumps(v,ensure_ascii=False,allow_nan=False))==v
                w=deepcopy(v['native']);w['raw']['events'][0].update(start=10,end=20);w['raw']['seconds']=30
                assert canonical(v['native']['raw'])==canonical(w['raw'])
                w['raw']['events'][0]['passes']=4;assert canonical(v['native']['raw'])!=canonical(w['raw'])
            elif name=='independent_audit_identity':
                ids=B.identity();assert ids['primary']['module']!=ids['independent']['module'] and ids['primary']['sha256']!=ids['independent']['sha256']
            elif name=='single_entry_and_exception_cleanup':
                invoke_once(lambda:{'fixed':True},ledger,obs)
                try:invoke_once(lambda:None,ledger,None);raise RuntimeError('duplicate accepted')
                except AssertionError:pass
                def fail():raise ValueError('fixed failure')
                token={'started':0,'returned':0,'exceptions':0}
                try:invoke_once(fail,token,obs);raise RuntimeError('exception swallowed')
                except ValueError:assert token=={'started':1,'returned':0,'exceptions':1}
                assert sys.getprofile() is None
            passed=True
        except BaseException as exc:
            records.append({'id':name,'passed':False,'reason':repr(exc),'traceback':traceback.format_exc(),'native_observer':dict(obs.c)});break
        records.append({'id':name,'passed':passed,'native_observer':dict(obs.c),'real_core_calls':0,'post_search_calls':0})
    result={'passed':len(records)==8 and all(x['passed'] for x in records),'cases':records,'real_core_calls':0,'post_search_calls':0,'identity':B.identity(),'preparation_repairs':0}
    dump(H/'prechecks.json',result);print({'passed':result['passed'],'cases':len(records),'new_core_calls':0});assert result['passed']

def read_json(s):return json.loads(s)

def worker(job):
    dest=H/'outputs'/(job['id']+'.json');assert not dest.exists()
    result={'job':job,'passed':False,'views':{},'started_utc':time.time(),'configuration':job['config']};obs=None;ledger={'started':0,'returned':0,'exceptions':0}
    wall=time.perf_counter()
    try:
        for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest,name
        guards=read(H/'source_guards.json')
        for name,digest in guards.items():assert sha(name)==digest,name
        cold=time.perf_counter();runtime,p2=B.load_native();result['cold_import_seconds']=time.perf_counter()-cold
        for module in (runtime,p2,runtime.native):
            path=str(Path(module.__file__).resolve());assert path in guards and sha(path)==guards[path]
        payload=(H/job['input']).read_bytes();c=json.loads(payload);original=deepcopy(c);result['input']=c
        assert tuple(c['current']) in ps(c['covered']);result['initial_collect_here']={'new_H':[],'reason':'same supplied H, explicit idempotent collection'}
        result['identity_before']=B.identity()
        if job['config']=='ON':obs=B.NativeObserver(runtime,p2)
        else:assert job['config']=='OFF'
        start=time.perf_counter();corestart=time.perf_counter()
        native=invoke_once(lambda:runtime.run_payload(payload,'PPCPP',20,job['seed']) if job['method']=='PPCPP' else p2.run_payload(payload,20,job['seed']),ledger,obs)
        coreend=time.perf_counter();result['native']=native;result['loaded_core_sources']={}
        for key in ('runtime','p2_adapter','candidate','model','p2_search_audit','unified_geometry','bfs_metric_geometry'):
            module=sys.modules.get(key)
            if module is not None:
                path=str(Path(module.__file__).resolve());assert path in guards and sha(path)==guards[path],('unbound core',path)
                result['loaded_core_sources'][path]=sha(path)
        flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_native_raw.json'),native);native_flush=time.perf_counter()-flush
        assert native['raw'].get('route'),'no complete original output'
        assert native['raw']['status'] in ('core_complete','finished','deadline')
        corewire=json.dumps(native,ensure_ascii=False,separators=(',',':'));route=json.loads(corewire)['raw']['route']
        rawname='A' if job['method']=='PPCPP' else 'C0';postname='B' if rawname=='A' else 'C'
        result['views'][rawname]=evaluate(c,route,grid=True)
        json.dumps(result['views'][rawname],ensure_ascii=False,separators=(',',':'));rawend=time.perf_counter()
        request={'id':job['id'],'input':c,'raw':json.loads(corewire)['raw']};wire=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()
        postwire,envelope=engine.process(wire,limit=4096,soft=18,total=20)
        result.update(post_request_utf8=wire.decode(),post_response_utf8=postwire,post_envelope=envelope)
        flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_post_raw.json'),{'request':request,'response_utf8':postwire,'envelope':envelope});post_flush=time.perf_counter()-flush
        post=json.loads(postwire);result['post']=post;result['views'][postname]=evaluate(c,post['vertices'])
        json.dumps(result,ensure_ascii=False,separators=(',',':'));end=time.perf_counter()
        assert c==original and ledger=={'started':1,'returned':1,'exceptions':0}
        if obs:assert obs.c['core_started']==obs.c['core_returned']==1
        counts={'engine':post['counts']['service_intersections'],'raw_execution':result['views'][rawname]['counts'].get('execute_service_intersections',0),'post_execution':result['views'][postname]['counts'].get('execute_service_intersections',0)}
        counts['total']=sum(counts.values());assert all(type(v) is int and v>=0 for v in counts.values())
        n=len(route)-1;u=len(ps(c['targets'])-ps(c['covered']));assert counts['engine']<=n*u;result['query_scope_schema']=counts
        result['timing']={'native_entry_seconds':coreend-corestart,'raw_common_end_to_end':rawend-start-native_flush,'post_increment':end-rawend-post_flush,'combined_end_to_end':end-start-native_flush-post_flush,'artifact_flush_excluded_seconds':native_flush+post_flush,
            'native_late':coreend-corestart>=20,'raw_stage_late':rawend-start-native_flush>20,'combined_late':end-start-native_flush-post_flush>40,'post_late':end-rawend-post_flush>20 or envelope['late'],
            'native_status':native['raw'].get('status'),'termination':'budget' if native['raw'].get('status')=='deadline' else 'natural',
            'raw_necessary_wrapper_seconds':rawend-start-native_flush-(coreend-corestart),'post_engine_seconds':envelope['entry_seconds'],
            'post_necessary_wrapper_seconds':end-rawend-post_flush-envelope['entry_seconds'],
            'main_measured_includes':'same raw/post virtual execution and encoding, post-return actual-source hashes, common single-entry dispatch, ON original profile only',
            'outside_main':'pre-start frozen-source hashes, cold import, two actual evidence flushes, independent audit, process creation'}
        result['main_passed']=True;dump(dest,result)
        independent_start=time.perf_counter();result['independent']=B.audit_result(result);result['independent_wall_seconds']=time.perf_counter()-independent_start
        result['identity_after']=B.identity();assert result['identity_before']==result['identity_after'];result['passed']=True
    except BaseException as exc:
        sys.setprofile(None);result['failure']={'reason':repr(exc),'traceback':traceback.format_exc()}
    finally:
        result['entry_ledger']=ledger;result['native_observation']=detail(obs);result['native_counts_actual']=dict(obs.c) if obs is not None else None
        result['worker_wall_seconds']=time.perf_counter()-wall;dump(dest,result)
    print(json.dumps({'id':job['id'],'passed':result['passed'],'failure':result.get('failure'),'seconds':result['worker_wall_seconds']},ensure_ascii=False))
    if not result['passed']:raise SystemExit(1)

def freeze():
    return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.suffix=='.py' or p.is_relative_to(H/'inputs') or p.name in ('plan.json','source_guards.json','selection.json','prechecks.json','environment.json','01_阶段A源码与计时边界审查.md','02_保护等价与完整预登记.md'))}

def run():
    assert read(H/'prechecks.json')['passed'] and not (H/'attempts.jsonl').exists()
    plan=read(H/'plan.json');assert len(plan['jobs'])<=72;dump(H/'active_freeze.json',freeze());env=dict(os.environ,**plan['thread_env'],PYTHONDONTWRITEBYTECODE='1')
    status={'completed':[],'failure':None,'not_run':[],'pairs':[]};jobs=plan['jobs'];pair_cache={}
    for i,j in enumerate(jobs):
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':j['id'],'event':'started','time':time.time()})+'\n')
        before=time.perf_counter();jobfile=H/'current_job.json';dump(jobfile,j)
        try:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jobfile)],env=env,capture_output=True,timeout=150)
            (H/'logs'/(j['id']+'.log')).write_bytes(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError('worker nonzero; saved output retained')
            x=read(H/'outputs'/(j['id']+'.json'));status['completed'].append(j['id'])
            key=(j['case'],j['method'],j['repeat'])
            if key in pair_cache:
                check=pair_check(pair_cache.pop(key),x);status['pairs'].append(check)
                if check['unexpected_mechanism_difference']:raise RuntimeError('unexplained mechanism difference; stop without retry')
            else:pair_cache[key]=x
        except BaseException as exc:status['failure']={'id':j['id'],'reason':repr(exc),'traceback':traceback.format_exc()};status['not_run']=[v['id'] for v in jobs[i+1:]]
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':j['id'],'event':'ended','wall':time.perf_counter()-before,'success':not bool(status['failure'])})+'\n')
        dump(H/'status.json',status)
        print('COMPLETE' if not status['failure'] else 'STOP',i+1,'/'+str(len(jobs)),j['id'],flush=True)
        if status['failure']:return
    print('FINITE CONTROLLED BATCH COMPLETE; STOP',flush=True)

def verify():
    assert not (H/'verify_receipt.json').exists()
    for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest,name
    for name,digest in read(H/'source_guards.json').items():assert sha(name)==digest,name
    status=read(H/'status.json');receipts=[]
    for ident in status['completed']:
        file=H/'outputs'/(ident+'.json');x=read(file);assert x['passed'] and x['independent']['passed']
        assert x['input']==read(H/x['job']['input']) and read(H/'outputs'/(ident+'_native_raw.json'))==x['native']
        assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0}
        if x['job']['config']=='OFF':assert x['native_counts_actual'] is None and x['native_observation']['counts'] is None
        else:assert x['native_counts_actual']['core_started']==x['native_counts_actual']['core_returned']==1
        for v in x['views'].values():assert v['metrics']['missing']==0 and v['metrics']['return_success']
        receipts.append({'id':ident,'sha256':sha(file),'independent_saved_counts':x['independent']['counts']})
    dump(H/'verify_receipt.json',{'passed':True,'completed':len(receipts),'receipts':receipts,'failure_retained':status['failure'],'scope':'read-only source/input/output bindings and saved independent receipts','new_core_calls':0,'new_post_calls':0,'new_geometry_queries':0})
    print({'verified':len(receipts),'new_core_calls':0,'new_geometry_queries':0,'failure':status['failure']})

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='worker':worker(read(sys.argv[2]))
    else:{'setup':setup,'precheck':precheck,'run':run,'verify':verify}[mode]()
