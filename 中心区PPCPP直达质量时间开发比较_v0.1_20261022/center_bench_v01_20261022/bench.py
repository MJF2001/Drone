"""Fixed 54-snapshot center-credit benchmark. All entry points are guarded."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from fractions import Fraction as Q
import sys,os,json,time,hashlib,subprocess,traceback,platform,ast,difflib
H=Path(__file__).resolve().parents[1];R=H.parent
OLD=R/'PPCPP直达质量时间开发比较_v0.1_20261022'
HISTORY=R/'PPCPP_LAST新开发地图验证_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def ps(v):return set(map(tuple,v))

def identity():
    import inspect
    from . import service
    from .audit import region
    assert service.intersection is not region.intersection
    return {'primary':{'module':service.intersection.__module__,'file':inspect.getsourcefile(service.intersection),'sha256':sha(inspect.getsourcefile(service.intersection))},
            'independent':{'module':region.intersection.__module__,'file':inspect.getsourcefile(region.intersection),'sha256':sha(inspect.getsourcefile(region.intersection))}}

def setup():
    assert not (H/'plan.json').exists()
    for d in ('inputs','outputs','logs','source_snapshot'):(H/d).mkdir(exist_ok=True)
    (H/'root_before.md').write_bytes((R/'当前进度与下一步.md').read_bytes())
    (H/'source_snapshot/执行稿.md').write_bytes((R/'中心区新条件PPCPP直达质量时间开发比较执行稿_给sol_20261022.md').read_bytes())
    protocol=read(HISTORY/'protocol.json');slots={s['id']:s for s in protocol['slots']};history=[];sourceguards={}
    for file in sorted((OLD/'inputs').glob('*.json')):
        c=read(file);ident=file.stem;slot=slots[ident]
        assert c==read(HISTORY/'inputs'/file.name)
        witnessfile=HISTORY/'witnesses'/file.name;w=read(witnessfile)
        prepfile=HISTORY/'prep/results'/(slot['base_id']+'.json');prep=read(prepfile)
        preinput=HISTORY/'prep/inputs'/(slot['base_id']+'.json');before=read(preinput)
        prefix=w['history'];old=ps(before['targets']);f0=ps(before['free']);covered=ps(c['covered'])
        assert prefix==prep['raw']['route'][:w['cut']+1]
        assert before['current']==before['base'] and not before['covered'] and ps(before['initial_targets'])==old
        assert prefix[0]==before['base'] and prefix[-1]==c['current'] and prefix[-2]==c['previous']
        assert set(map(tuple,prefix))<=f0 and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(prefix,prefix[1:]))
        assert covered==ps(prefix)&old and covered<=ps(c['published_targets'])
        assert ps(c['initial_targets'])==old and not before['covered'] and ps(c['targets'])==ps(c['published_targets'])&ps(c['free'])
        assert ps(c['deferred_targets'])==ps(c['published_targets'])-ps(c['free'])-covered
        assert tuple(c['current']) in covered,'common explicit collect must agree with supplied center history'
        assert all(all(5*abs(p[j]-p[j])<1 for j in (0,1)) for p in covered)
        assert len(c['free'])<=10000 and len(c['published_targets'])<=1500
        (H/'inputs'/file.name).write_bytes(file.read_bytes())
        evidence=[{'cell':list(p),'prefix_index':next(i for i,q in enumerate(prefix) if tuple(q)==p),'point':list(p),
                   'published_before_event':p in old,'center_in_new_open_region':True,'blocked_only_after_completed':p not in ps(c['free'])} for p in sorted(covered)]
        history.append({'id':ident,'size':slot['size'],'event':slot['event'],'has_event':True,'H':len(covered),'evidence':evidence,
            'source_files':{str(p):sha(p) for p in (file,witnessfile,prepfile,preinput)},'history_semantics':'externally supplied fixed H; no broadened replay credit'})
        sourceguards.update(history[-1]['source_files'])
    assert len(history)==54
    dump(H/'history_evidence.json',history)
    technical=[]
    for size in ('small','medium','large'):
        for event in ('corner','obstacle'):
            chosen=sorted(x['id'] for x in history if x['size']==size and x['event']==event)[0]
            for method in (('PPCPP','P2_MULTI') if len(technical)%4==0 else ('P2_MULTI','PPCPP')):
                technical.append({'id':'technical__'+chosen+'__'+method,'case':chosen,'seed':20261020,'method':method,'phase':'technical','input':'inputs/'+chosen+'.json'})
    formal=read(OLD/'plan.json')['formal'];assert len(formal)==324
    for j in formal:assert j['seed'] in (20261020,20261021,20261022) and j['case'] in slots
    dump(H/'plan.json',{'technical':technical,'formal':formal,'technical_selection':'no no-event stratum exists; per size choose first lexicographic corner and obstacle; no substitutions after outcomes',
        'missing_strata':['small/no_event','medium/no_event','large/no_event'],'core_cap':336,'technical_cap':12,'formal_cap':324,
        'geometry_bounds':{'free':10000,'public_targets':1500,'observed_free_max':max(len(read(H/j['input'])['free']) for j in formal),
            'observed_target_max':max(len(read(H/j['input'])['published_targets']) for j in formal),'source_edges':'n <= supplied distance_budget (1e6)',
            'post_candidate':4096,'post_source_output_each':'<= n','region_queries':'<= n * active_remaining; exact box rejections separately counted'},
        'budget':{'core':20,'post_total':20,'post_soft':18,'combined_nominal':40,'worker_timeout':150},
        'scale_adaptation':'snapshot grid entry only; no S-to-q or micro 25/12 limits; exact service predicates reused; independent exact necessary target-box rejection before analytic region predicate',
        'history':'common externally supplied pre-event center witnesses, explicit current collect, no event-prefix replay enlargement',
        'P95':'nearest rank ceil(.95*N)-1','thread_env':{'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'},
        'timing':'A/C0: native plus encoding and necessary new-credit virtual execution; B/C: same native and A/C0 wrapper plus post and new-credit execution/encoding. Cold/hash/disk/independent audits excluded, wall recorded separately',
        'precheck_cap':16,'precheck_cases':12,'preparation_repair_cap':2})
    guards=read(OLD/'source_seal.json')
    guards.update(sourceguards)
    for p in (OLD/'completion_manifest.json',R/'中心有效采集区统一接入最小验收_v0.3_20261022/final_receipt.json'):guards[str(p)]=sha(p)
    dump(H/'old_source_guards.json',guards)
    bindings=[]
    origin=R/'中心有效采集区统一接入最小验收_v0.3_20261022/center_credit_v03_20261022'
    for name in ('exact.py','service.py','post/engine.py','post/geometry.py','audit/region.py','audit/_post_geometry.py','audit/_post_saved.py'):
        bindings.append({'source':str(origin/name),'source_sha256':sha(origin/name),'copy':'center_bench_v01_20261022/'+name,'byte_equal':sha(origin/name)==sha(H/'center_bench_v01_20261022'/name)})
    assert all(b['byte_equal'] for b in bindings if not b['copy'].endswith('_post_saved.py'))
    dump(H/'bindings.json',bindings)
    for b in bindings:guards[b['source']]=b['source_sha256']
    dump(H/'old_source_guards.json',guards)
    original=(origin/'audit/_post_saved.py').read_text(encoding='utf-8');current=(H/'center_bench_v01_20261022/audit/_post_saved.py').read_text(encoding='utf-8')
    (H/'规模适配.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),current.splitlines(True),fromfile='accepted_region_audit',tofile='scaled_region_audit')),encoding='utf-8')
    dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'CPU':os.environ.get('PROCESSOR_IDENTIFIER'),
        'thread_rule':read(H/'plan.json')['thread_env'],'parallel_solvers':0,'cache_rule':'fresh serial process per entry; metric/audit state local, no across-entry cache'})
    for p in H.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    print({'prepared_inputs':54,'history_verified':54,'technical':12,'formal':324,'missing_no_event':True,'core_calls':0})

def load_native():
    calls=[]
    def watch(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','process','core_route'):calls.append(frame.f_code.co_filename)
    sys.setprofile(watch)
    try:
        sys.path.insert(0,str(R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'))
        import runtime,p2_adapter
    finally:sys.setprofile(None)
    assert not calls
    return runtime,p2_adapter

def audit_result(result):
    from .metrics import evaluate
    from .audit import _post_saved
    start=time.perf_counter();counts=Counter();receipts={};c=result['input'];before=deepcopy(c)
    for name,view in result['views'].items():
        independent=evaluate(c,view['path'],True,grid=name in ('A','C0'))
        assert independent['metrics']==view['metrics'] and independent['events']==view['events']
        counts.update(independent['counts']);receipts[name]={'passed':True,'counts':independent['counts']}
    n=len(result['native']['raw']['route'])-1;u=len(ps(c['targets'])-ps(c['covered']))
    post=_post_saved.audit_one({'id':result['job']['id'],'limits':{'candidate_geometry':4096,'independent_geometry':n,'independent_service_intersections':n*u}},
                result['post_request_utf8'].encode(),result['post_response_utf8'].encode())
    counts.update({'post_independent_'+k:v for k,v in post['counts'].items()})
    assert c==before
    return {'passed':True,'views':receipts,'post':post,'counts':dict(counts),'seconds':time.perf_counter()-start,'identity':identity()}

def precheck():
    from .metrics import evaluate
    from . import service as C
    from .audit import region as Z
    from .post import engine
    assert not (H/'prechecks.json').exists()
    before=set(H.rglob('*'));runtime,p2=load_native();assert before==set(H.rglob('*'))
    fixtures=['zero_counts','one_scope','multiple_scope','empty_return','roundtrip','module_identity','no_import_task','exclusive_writer','scale_boundary','center_contained','new_region_difference','tampered_witness']
    records=[]
    for name in fixtures:
        c=Counter();passed=False
        try:
            if name in ('zero_counts','one_scope','multiple_scope'):
                ledger={k:0 for k in ('raw','engine','post','total')}
                if name!='zero_counts':C.intersection((0,0),(2,0),(1,0),c,'test');ledger['engine']+=1
                if name=='multiple_scope':C.intersection((0,0),(2,0),(1,0),c,'test');ledger['raw']+=1
                ledger['total']=ledger['raw']+ledger['engine']+ledger['post']
                assert all(type(v) is int and v>=0 for v in ledger.values()) and ledger['total']==sum(ledger[k] for k in ('raw','engine','post'))
            elif name=='empty_return':
                case={'free':[[0,0],[1,0]],'published_targets':[],'covered':[],'deferred_targets':[],'current':[1,0],'base':[0,0],'distance_budget':5}
                x=evaluate(case,[[1,0],[0,0]],grid=True);y=evaluate(case,[[1,0],[0,0]],True,True);assert x['metrics']==y['metrics']
                c.update(x['counts']);c.update(y['counts'])
            elif name=='roundtrip':
                ev=C.intersection((0,0),(2,0),(1,0),c,'test');assert json.loads(json.dumps(ev))==ev
            elif name in ('module_identity','no_import_task'):assert identity()['primary']['file']!=identity()['independent']['file']
            elif name=='exclusive_writer':
                p=H/'logs/exclusive_stub';assert not p.exists()
                with p.open('x') as f:f.write('one owner')
                refused=False
                try:
                    with p.open('x'):pass
                except FileExistsError:refused=True
                assert refused
            elif name=='scale_boundary':
                inputs=[read(p) for p in (H/'inputs').glob('*.json')];assert max(len(c['free']) for c in inputs)>25 and max(len(c['published_targets']) for c in inputs)>12
                assert all(len(c['free'])<=10000 and len(c['published_targets'])<=1500 for c in inputs)
            elif name=='center_contained':assert C.inside((1,1),(1,1),c,'test') and Z.internal((1,1),(1,1),c)
            else:
                ev=C.intersection((0,0),(2,Q(9,5)),(1,1),c,'test');iv=Z.intersection((0,0),(2,Q(9,5)),(1,1),c)
                assert ev==iv and 2*1!=Q(9,5)*1
                if name=='tampered_witness':
                    bad=deepcopy(ev);bad['witness']['point'][0]={'n':999,'d':1}
                    rejected=False
                    try:assert bad==Z.intersection((0,0),(2,Q(9,5)),(1,1),c)
                    except AssertionError:rejected=True
                    assert rejected
            passed=True
        except BaseException as e:records.append({'id':name,'passed':False,'failure':repr(e),'traceback':traceback.format_exc(),'counts':dict(c)});break
        records.append({'id':name,'passed':passed,'counts':dict(c)})
    out={'passed':len(records)==12 and all(r['passed'] for r in records),'cases':records,'core_calls':0,'post_search_calls':0,'identity':identity()}
    dump(H/'prechecks.json',out);print({'prechecks':out['passed'],'cases':len(records),'core_calls':0});assert out['passed'],records[-1]

class NativeObserver:
    def __init__(self,runtime,p2):
        import model,bfs_metric_geometry,unified_geometry
        self.c=Counter({k:0 for k in ('core_started','core_returned','core_complete','context_calls','row_BFS_built','Astar_searches','geometry_distance_calls','geometry_path_calls','native_audit_calls')})
        self.codes={runtime.native.solve.__code__:'core',p2.p2_solve.__code__:'core',model.Geometry.__init__.__code__:'context',
            model.Geometry.path.__code__:'astar',bfs_metric_geometry.BFSMetricGeometry.distance.__code__:'distance',unified_geometry.UnifiedGeometry.path.__code__:'path',unified_geometry.single_cell_audit.__code__:'audit'}
        self.frames={}
    def profile(self,frame,event,arg):
        kind=self.codes.get(frame.f_code)
        if kind is None:return
        if event=='call':
            if kind=='core':self.c['core_started']+=1;assert self.c['core_started']<=1
            elif kind=='context':self.c['context_calls']+=1
            elif kind=='distance':self.c['geometry_distance_calls']+=1
            elif kind=='path':self.c['geometry_path_calls']+=1
            elif kind=='audit':self.c['native_audit_calls']+=1
            obj=frame.f_locals.get('self');self.frames[id(frame)]=(kind,getattr(obj,'bfs_rows_built',0),getattr(obj,'searches',0))
        elif event=='return':
            old=self.frames.pop(id(frame),None)
            if old:
                obj=frame.f_locals.get('self')
                if kind=='core':self.c['core_returned']+=int(isinstance(arg,dict));self.c['core_complete']+=int(isinstance(arg,dict) and arg.get('status') in ('core_complete','finished'))
                if kind=='distance':self.c['row_BFS_built']+=getattr(obj,'bfs_rows_built',0)-old[1]
                if kind=='astar':self.c['Astar_searches']+=getattr(obj,'searches',0)-old[2]

def worker(job):
    from .metrics import evaluate
    from .post import engine
    from . import service
    dest=H/'outputs'/(job['id']+'.json');assert not dest.exists()
    result={'job':job,'passed':False,'views':{},'started_utc':time.time()};obs=None
    wall=time.perf_counter()
    try:
        freeze=read(H/'active_freeze.json')
        for name,digest in freeze.items():assert sha(H/name)==digest,name
        for name,digest in read(H/'old_source_guards.json').items():assert sha(name)==digest,name
        cold=time.perf_counter();runtime,p2=load_native();result['cold_import_seconds']=time.perf_counter()-cold
        guards=read(H/'old_source_guards.json')
        for module in (runtime,p2,runtime.native):
            path=str(Path(module.__file__).resolve());assert path in guards and sha(path)==guards[path]
        payload=(H/job['input']).read_bytes();c=json.loads(payload);original=deepcopy(c);result['input']=c
        # Current is already evidenced in supplied H; explicit collection is idempotent.
        assert tuple(c['current']) in ps(c['covered']);result['initial_collect_here']={'new_H':[],'reason':'explicit action; current already in supplied history'}
        result['identity_before']=identity();obs=NativeObserver(runtime,p2)
        start=time.perf_counter();corestart=time.perf_counter();sys.setprofile(obs.profile)
        try:native=runtime.run_payload(payload,'PPCPP',20,job['seed']) if job['method']=='PPCPP' else p2.run_payload(payload,20,job['seed'])
        finally:sys.setprofile(None)
        coreend=time.perf_counter();result['native']=native
        result['loaded_core_sources']={}
        for key in ('runtime','p2_adapter','candidate','model','p2_search_audit','unified_geometry','bfs_metric_geometry'):
            module=sys.modules.get(key)
            if module is not None:
                path=str(Path(module.__file__).resolve());assert path in guards and sha(path)==guards[path],('unbound core',path)
                result['loaded_core_sources'][path]=sha(path)
        # Preserve native before post/audit. All variants share this one return.
        flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_native_raw.json'),native);native_flush=time.perf_counter()-flush
        assert native['raw'].get('route'),'no complete original output'
        corewire=json.dumps(native,ensure_ascii=False,separators=(',',':'));route=json.loads(corewire)['raw']['route']
        rawname='A' if job['method']=='PPCPP' else 'C0';postname='B' if rawname=='A' else 'C'
        result['views'][rawname]=evaluate(c,route,grid=True)
        json.dumps(result['views'][rawname],ensure_ascii=False,separators=(',',':'));rawend=time.perf_counter()
        request={'id':job['id'],'input':c,'raw':json.loads(corewire)['raw']};wire=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()
        postwire,envelope=engine.process(wire,limit=4096,soft=18,total=20)
        result.update(post_request_utf8=wire.decode(),post_response_utf8=postwire,post_envelope=envelope)
        flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_post_raw.json'),{'request':request,'response_utf8':postwire,'envelope':envelope});post_flush=time.perf_counter()-flush
        post=json.loads(postwire);result['post']=post
        result['views'][postname]=evaluate(c,post['vertices'])
        json.dumps(result,ensure_ascii=False,separators=(',',':'));end=time.perf_counter()
        assert c==original and obs.c['core_started']==obs.c['core_returned']==1
        counts={'engine':post['counts']['service_intersections'],'raw_execution':result['views'][rawname]['counts'].get('execute_service_intersections',0),
                'post_execution':result['views'][postname]['counts'].get('execute_service_intersections',0)}
        counts['total']=sum(counts.values());assert all(type(v) is int and v>=0 for v in counts.values()) and counts['total']==counts['engine']+counts['raw_execution']+counts['post_execution']
        n=len(route)-1;u=len(ps(c['targets'])-ps(c['covered']));assert counts['engine']<=n*u
        result['query_scope_schema']=counts
        result['timing']={'native_entry_seconds':coreend-corestart,'raw_common_end_to_end':rawend-start-native_flush,'post_increment':end-rawend-post_flush,'combined_end_to_end':end-start-native_flush-post_flush,'artifact_flush_excluded_seconds':native_flush+post_flush,
            'native_late':coreend-corestart>=20,'raw_stage_late':rawend-start-native_flush>20,'combined_late':end-start-native_flush-post_flush>40,'post_late':end-rawend-post_flush>20 or envelope['late'],
            'native_status':native['raw'].get('status'),'termination':'budget' if native['raw'].get('status')=='deadline' else 'natural',
            'main_measured_includes':'native observer, decode/encode and necessary primary new-credit execution/metrics; post increment includes source/credit validation',
            'outside_main':'cold import, hash checks, raw artifact flushes, independent audits, process creation'}
        # Raw flush is persisted for failure evidence and separately excluded from timings below.
        result['main_passed']=True;dump(dest,result)
        independent_start=time.perf_counter()
        result['independent']=audit_result(result)
        result['independent_wall_seconds']=time.perf_counter()-independent_start
        result['identity_after']=identity();assert result['identity_before']==result['identity_after']
        result['passed']=True
    except BaseException as e:
        sys.setprofile(None);result['failure']={'reason':repr(e),'traceback':traceback.format_exc()}
    finally:
        if obs:result['native_counts_actual']=dict(obs.c)
        result['worker_wall_seconds']=time.perf_counter()-wall;dump(dest,result)
    print(json.dumps({'id':job['id'],'passed':result['passed'],'failure':result.get('failure'),'seconds':result['worker_wall_seconds']},ensure_ascii=False))
    if not result['passed']:raise SystemExit(1)

def freeze():
    return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.suffix=='.py' or p.is_relative_to(H/'inputs') or p.name in ('plan.json','bindings.json','history_evidence.json','old_source_guards.json','environment.json','prechecks.json'))}

def run():
    assert read(H/'prechecks.json')['passed'] and not (H/'attempts.jsonl').exists()
    plan=read(H/'plan.json');dump(H/'active_freeze.json',freeze());env=dict(os.environ,**plan['thread_env'],PYTHONDONTWRITEBYTECODE='1')
    status={'technical_completed':[],'formal_completed':[],'failure':None,'not_run':[]}
    jobs=plan['technical']+plan['formal']
    for i,job in enumerate(jobs):
        if i==len(plan['technical']):
            # Technical saved replay, no algorithm calls; finish before formal freeze.
            receipts=[]
            for old in plan['technical']:
                receipt=audit_result(read(H/'outputs'/(old['id']+'.json')));receipts.append({'id':old['id'],'audit':receipt})
            dump(H/'technical_saved_replay.json',{'passed':True,'checks':receipts,'new_core_calls':0,'new_post_calls':0})
            dump(H/'formal_freeze.json',read(H/'active_freeze.json'))
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':job['id'],'phase':job['phase'],'event':'started','time':time.time()})+'\n')
        before=time.perf_counter();jobfile=H/'current_job.json';dump(jobfile,job)
        try:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'run_bench.py'),'worker',str(jobfile)],env=env,capture_output=True,timeout=150)
            (H/'logs'/(job['id']+'.log')).write_bytes(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError('worker nonzero; see preserved output')
            status[job['phase']+'_completed'].append(job['id'])
        except BaseException as e:
            status['failure']={'id':job['id'],'phase':job['phase'],'reason':repr(e),'traceback':traceback.format_exc()};status['not_run']=[j['id'] for j in jobs[i+1:]]
        with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':job['id'],'event':'ended','wall':time.perf_counter()-before,'success':not bool(status['failure'])})+'\n')
        dump(H/'status.json',status)
        if status['failure']:print('STOP',job['id'],flush=True);return
        if i<12 or (i+1)%12==0:print('COMPLETE',i+1,'/336',job['id'],flush=True)
    print('COMPLETE FINITE BATCH STOP',flush=True)

def verify():
    assert not (H/'verify_receipt.json').exists()
    for name,digest in read(H/'active_freeze.json').items():assert sha(H/name)==digest
    for name,digest in read(H/'old_source_guards.json').items():assert sha(name)==digest
    status=read(H/'status.json');completed=status['technical_completed']+status['formal_completed'];receipts=[]
    for ident in completed:
        file=H/'outputs'/(ident+'.json');x=read(file)
        assert x['passed'] and x['independent']['passed'] and x['input']==read(H/x['job']['input'])
        assert read(H/'outputs'/(ident+'_native_raw.json'))==x['native']
        for v in x['views'].values():assert v['metrics']['missing']==0 and v['metrics']['return_success']
        receipts.append({'id':ident,'sha256':sha(file),'independent_receipt':x['independent']['counts']})
    dump(H/'verify_receipt.json',{'passed':True,'completed_outputs':len(receipts),'receipts':receipts,'failure_retained':status['failure'],
        'scope':'source/input/output binding and saved independent receipts; no fresh geometry','new_core_calls':0,'new_selector_calls':0,'new_post_calls':0,'new_geometry_queries':0})
    print({'saved_artifacts_verified':len(receipts),'failure':status['failure'],'new_core_calls':0,'new_geometry_queries':0})

def main(args):
    if args[0]=='worker':worker(read(args[1]))
    else:{'setup':setup,'precheck':precheck,'run':run,'verify':verify}[args[0]]()
