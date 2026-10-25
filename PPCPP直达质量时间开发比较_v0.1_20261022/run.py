from pathlib import Path
import sys,os,json,time,hashlib,subprocess,traceback,math
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def modules():
    begin=time.perf_counter();sys.path.insert(0,str(R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'));import runtime,p2_adapter
    sys.path.insert(0,str(H/'postsrc'));import engine,audit_saved
    return runtime,p2_adapter,engine,audit_saved,time.perf_counter()-begin
def pipeline(payload,method,seed,fn,engine):
    start=time.perf_counter();native=fn(payload,seed);original_end=time.perf_counter();assert native['raw'].get('route'),'no complete original output'
    c=json.loads(payload);original_wire=json.dumps(native,ensure_ascii=False,separators=(',',':'));a_end=time.perf_counter()
    n=len(native['raw']['route'])-1;u=len(set(map(tuple,c['targets']))-set(map(tuple,c['covered'])));limits={'candidate_geometry':4096,'source_geometry':n,'output_geometry':n,'independent_geometry':n,'main_service_intersections':n*u,'independent_service_intersections':n*u}
    request={'id':'pipeline','input':c,'raw':native['raw']};wire=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode('utf8');post,post_envelope=engine.process(wire)
    result={'native':native,'post':json.loads(post),'post_envelope':post_envelope,'audit_payload':request,'limits':limits};encoded=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode('utf8');end=time.perf_counter()
    times={'original_seconds':a_end-start,'adapter_return_seconds':original_end-start,'post_increment_seconds':end-a_end,'pipeline_seconds':end-start,'original_late':a_end-start>20,'post_late':end-a_end>20,'original_status':native['raw'].get('status'),'termination':'budget' if native['raw'].get('status')=='deadline' else 'natural','encoding_transfer_included':True}
    assert times['pipeline_seconds']>=times['original_seconds']>=0
    return result,times,wire,post.encode('utf8')
def worker(job):
    runtime,p2,engine,auditor,cold=modules()
    for p,v in read(H/'source_seal.json').items():assert sha(p)==v,p
    j=read(job);payload=(H/j['input']).read_bytes();assert sha(H/j['input'])==read(H/'input_hashes.json')[j['input']]
    fn=(lambda p,s:runtime.run_payload(p,'PPCPP',20,s)) if j['method']=='PPCPP' else (lambda p,s:p2.run_payload(p,20,s))
    result,times,wire,post=pipeline(payload,j['method'],j['seed'],fn,engine);c=result['audit_payload']['input'];route=result['native']['raw']['route'];F=set(map(tuple,c['free']));T=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));assert tuple(route[0])==tuple(c['current']) and tuple(route[-1])==tuple(c['base']);assert all(tuple(p) in F for p in route) and T<=set(map(tuple,route));assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]));assert len(route)-1<=c['distance_budget']
    audit=auditor.audit_one({'id':'pipeline','limits':result['limits']},wire,post)
    result.update(job=j,timing=times,cold_import_seconds=cold,audit=audit);dump(H/'outputs'/(j['id']+'.json'),result)
def setup():
    runtime,p2,engine,auditor,cold=modules();old=read(R/'PPCPP四方向共同预算正式比较_v0.1_20261020/seal.json');files={}
    for m in list(sys.modules.values()):
        p=getattr(m,'__file__',None)
        if p and Path(p).is_file() and Path(p).resolve().is_relative_to(R):
            p=str(Path(p).resolve())
            if not Path(p).is_relative_to(H):assert p in old and sha(p)==old[p],('frozen_source_conflict',p)
            files[p]=sha(p)
    B=R/'任意方向合法直达有限诊断_v0.1_20261022';mf=read(B/'frozen_manifest.json')['files']
    for oldname,newname in [('engine.py','engine.py'),('geometry.py','geometry.py'),('audit_geometry.py','audit_geometry.py'),('verify.py','audit_saved.py')]:assert sha(H/'postsrc'/newname)==mf[oldname]
    assert read(B/'gate_attempt_1.json')['passed'];files[str(B/'gate_attempt_1.json')]=sha(B/'gate_attempt_1.json');files[str(H/'run.py')]=sha(H/'run.py');dump(H/'source_seal.json',files);dump(H/'input_hashes.json',{'inputs/'+p.name:sha(p) for p in (H/'inputs').glob('*.json')});dump(H/'import_setup.json',{'cold_import_seconds':cold,'modules':len(files)})
def stubs():
    _,_,engine,_,_=modules();c={'free':[[0,0]],'targets':[],'covered':[],'published_targets':[],'deferred_targets':[],'current':[0,0],'base':[0,0],'distance_budget':0};payload=json.dumps(c).encode();records=[]
    for mode in ('empty','fault','missing_output','timing'):
        calls=[0]
        def fake(p,s):
            calls[0]+=1
            if mode=='fault':raise RuntimeError('handwritten fault')
            return {'raw':{'route':[] if mode=='missing_output' else [[0,0]],'trace':[],'status':'finished'}}
        try:
            r,t,_,_=pipeline(payload,'STUB',0,fake,engine);assert mode in ('empty','timing');assert t['pipeline_seconds']>=t['original_seconds'] and t['post_increment_seconds']>=0
            records.append({'mode':mode,'passed':True,'responses':calls[0],'timing':t})
        except (RuntimeError,AssertionError):
            assert mode in ('fault','missing_output');records.append({'mode':mode,'passed':True,'responses':calls[0],'failure_propagated':True})
    dump(H/'stub_results.json',records)
def run():
    plan=read(H/'plan.json');assert not (H/'attempts.jsonl').exists(),'no reruns';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');completed=[];failure=None
    for phase in ('technical','formal'):
        if phase=='formal':
            tech=[read(H/'outputs'/(j['id']+'.json')) for j in plan['technical']]
            for case in sorted({j['case'] for j in plan['technical']}):
                for method in ('PPCPP','P2_MULTI'):
                    a,b=[x for x in tech if x['job']['case']==case and x['job']['method']==method];assert a['native']['raw']['route']==b['native']['raw']['route'] and a['post']['vertices']==b['post']['vertices'],'technical deterministic repeat mismatch'
            dump(H/'technical_pass.json',{'passed':True,'real_entries':12,'stubs':4,'repeat_routes_equal':True})
        for j in plan[phase]:
            jp=H/'current_job.json';dump(jp,j);begin=time.perf_counter()
            with (H/'attempts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps({'id':j['id'],'phase':phase,'event':'started'})+'\n')
            try:
                p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jp)],env=env,capture_output=True,timeout=90);(H/'logs'/(j['id']+'.log')).write_bytes(p.stdout+p.stderr)
                if p.returncode:raise RuntimeError('worker exit '+str(p.returncode))
                completed.append(j['id'])
            except Exception as ex:failure={'job':j,'reason':repr(ex),'traceback':traceback.format_exc()}
            dump(H/'status.json',{'completed':completed,'failure':failure,'formal_planned':324,'technical_planned':12})
            if failure:print('STOP',j['id'],failure['reason'],flush=True);return
            if len(completed)%12==0:print('completed',len(completed),'/336',flush=True)
    print('COMPLETE STOP',flush=True)
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='setup':setup()
    elif mode=='stubs':stubs()
    elif mode=='worker':worker(sys.argv[2])
    else:run()
