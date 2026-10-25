"""Serial fresh processes for original PPCPP and two independent exact engines."""
import os,sys,time,subprocess,json
from joint_common import H,R,S,read,save,sha,account,query
def sources():return {str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
from pathlib import Path
def seal(name,parent):
    original=read(parent);original=original.get('files',original)
    for p,h in original.items():assert sha(p)==h,p
    files=dict(original)
    for p in sources():
        if Path(p).is_relative_to(R):files[p]=sha(p)
    for p in H.rglob('*'):
        if p.is_file() and p.name!='actual_order.jsonl':files[str(p.resolve())]=sha(p)
    save(H/name,dict(created_utc=time.time(),stage=name,files=files,excluded_mutable=['actual_order.jsonl'],parent_seal_sha256=sha(parent),limitations='Relevant environment inherited from original pressure formal_seal; system DLLs are not a full machine image. Runtime jobs/input/code and loaded source hashes are recorded, not an independent argument receipt.'))
    print('SEALED',name,len(files),flush=True)
def worker(jp,out):
    j=read(jp);frozen=read(H/j['seal'])['files']
    if j['phase'] in ('prep','formal'):
        sys.path.insert(0,str(R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'));import runtime
        extras={str(Path(runtime.native.__file__).resolve()),str(Path(runtime.native.core.__file__).resolve())}
    else:
        engine=__import__('exact_bfs' if j['engine']=='BFS' else 'exact_dijkstra');extras=set()
    imports={}
    for p in sorted(sources()|extras):
        if Path(p).is_relative_to(R):assert p in frozen and sha(p)==frozen[p],p;imports[p]=sha(p)
    if j['phase'] in ('prep','formal'):
        inp=H/j['input'];assert sha(inp)==frozen[str(inp.resolve())];payload=inp.read_bytes();called=time.time();x=runtime.run_payload(payload,'PPCPP',20,20261021)
        save(out,dict(job=j,result=x,call_utc=called,imports=imports,input_sha256=sha(inp)))
    else:
        request=read(H/j['request']);called=time.time();begin=time.perf_counter();r=engine.solve(request,str(H/'certificates'/f'{j["id"]}.json.gz'));wire=json.dumps(r,allow_nan=False);elapsed=time.perf_counter()-begin
        if elapsed>=60:r.update(status='unresolved',reason='whole_query_wall_limit',length=None,route=[])
        save(out,dict(job=j,request=request,request_sha256=sha(H/j['request']),result=r,query_seconds=elapsed,call_utc=called,imports=imports,certificate='certificates/'+j['id']+'.json.gz'))
def exact_request(j):
    if j['phase']=='gate':
        gate=next(g for g in read(H/'gate_fixtures.json') if g['id']==j['fixture']);return gate['request']
    c=read(H/'inputs'/f'{j["case"]}.json');ref=read(H/'outputs'/f'{j["case"]}.json')['result'];assert ref['raw']['route']
    ep=account(c,ref['raw']['route'])['ep'];assert ep is not None
    return query(c,ep if j['problem']=='FIXED' else None)
def execute(phase):
    order=read(H/('prep_order.json' if phase=='prep' else 'formal_order.json' if phase=='formal' else 'gate_order.json' if phase=='gate' else 'exact_templates.json'))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');done=[]
    from joint_proof import audit
    for index,original in enumerate(order):
        j=dict(original)
        if phase=='exact':
            ref=read(H/'outputs'/f'{j["case"]}.json')['result']
            if not ref['raw'].get('route') or ref['entry_seconds']>=20:continue
        if phase in ('gate','exact'):
            j['request']='requests/'+j['id']+'.json';save(H/j['request'],exact_request(j))
        jp=H/'jobs'/f'{j["id"]}.json';save(jp,j)
        out=H/('prep_outputs' if phase=='prep' else 'outputs' if phase=='formal' else 'exact')/f'{j["id"]}.json';assert not out.exists();start=time.time()
        try:
            proc=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jp),str(out)],env=env,timeout=90,capture_output=True);code=proc.returncode;(H/'logs'/f'{j["id"]}.txt').write_bytes(proc.stdout+proc.stderr)
        except subprocess.TimeoutExpired as exc:
            code='watchdog';(H/'logs'/f'{j["id"]}.txt').write_text(str(exc),encoding='utf8')
            if phase in ('gate','exact'):save(out,dict(job=j,request=read(H/j['request']),result=dict(status='unresolved',reason='watchdog',length=None,route=[],discovered=None,expanded=None),query_seconds=90,certificate=None))
        with (H/'actual_order.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(id=j['id'],phase=phase,code=code,started_utc=start,finished_utc=time.time()))+'\n')
        if code!=0 and code!='watchdog':raise RuntimeError(('technical_stop',j['id'],code))
        if phase in ('prep','formal'):
            if code=='watchdog':raise RuntimeError(('PPCPP_watchdog_stop',j['id']))
            x=read(out)['result'];c=read(H/j['input'])
            if x['raw'].get('route'):account(c,x['raw']['route'])
            if phase=='prep':assert x['eligible'] and x['entry_seconds']<20,('prep_stop',j)
            if x['raw'].get('status')=='core_invalid':raise RuntimeError(('invalid_reference',j))
            print(phase,index+1,'/',len(order),j['id'],x['raw']['status'],flush=True)
        else:
            x=read(out);r=x['result']
            if x['certificate']:audit(x['request'],r,H/x['certificate'])
            if r['status']=='optimal':
                c=next(g['input'] for g in read(H/'gate_fixtures.json') if g['id']==j['fixture']) if phase=='gate' else read(H/'inputs'/f'{j["case"]}.json');account(c,r['route'],x['request']['last'])
            if phase=='gate':
                expected=next(g['expected'] for g in read(H/'gate_fixtures.json') if g['id']==j['fixture']);assert r['status']==('optimal' if expected is not None else 'infeasible') and r['length']==expected,('gate_stop',j,r)
            elif r['status']=='infeasible':raise RuntimeError(('legal_reference_conflict',j,r))
            if j['engine']=='DIJKSTRA':
                previous=read(H/'exact'/f'{j["id"].replace("DIJKSTRA","BFS")}.json')['result']
                if previous['status']!='unresolved' and r['status']!='unresolved':assert previous['status']==r['status'] and previous['length']==r['length'],('independent_disagreement',j)
            print(phase,index+1,'/',len(order),j['id'],r['status'],r['length'],flush=True)
    save(H/(phase+'_completion.json'),dict(phase=phase,finished=True))
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='worker':worker(sys.argv[2],sys.argv[3])
    elif mode=='seal_prep':seal('prep_seal.json',S/'formal_seal.json')
    elif mode=='seal_event':seal('event_seal.json',H/'prep_seal.json')
    else:execute(mode)
