"""Freeze -> bounded equivalence gates -> new 40-call batch. Old data immutable."""
import sys,json,hashlib,subprocess,time,os,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
OLD=ROOT/'Cstar道路正确性验收_20261019'
SPECIAL=ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,z):
    Path(p).parent.mkdir(exist_ok=True,parents=True)
    with Path(p).open('xb') as f:f.write(json.dumps(z,ensure_ascii=False,indent=2).encode())
def verify():
    frozen=read(HERE/'pre_run_manifest.json')
    for key in ('local','external'):
        for path,digest in frozen[key].items():assert sha(ROOT/path)==digest,path
    sys.path.insert(0,str(OLD));from run import verify as verify_old
    verify_old()
def core():
    sys.path.insert(0,str(HERE/'runtime'));import history_adapter
    assert Path(history_adapter.__file__).resolve()==(HERE/'runtime/history_adapter.py').resolve()
    return history_adapter.solve
def auditors():
    sys.path.insert(0,str(OLD));from audit_outputs import audit
    from audit_special import ledger,prune_checks
    return audit,ledger,prune_checks
def semantic(r):return {k:v for k,v in r.items() if k not in ('seconds','adaptation','protection_cache')}
def gates(protocol):
    solve=core();audit,ledger,prunes=auditors();results=[];summaries=[]
    prior=read(SPECIAL/'evidence/results.json');specs=read(SPECIAL/'evidence/protocol.json')['boundary_specs'];boundary_i=0
    for row in prior:
        c=row['input']
        if row['kind']=='functional':
            r=json.loads(json.dumps(solve(c,2,7)));assert semantic(r)==semantic(row['result']),c['name']
            audit(c,r,2);label=c['name']
        else:
            spec=specs[boundary_i];boundary_i+=1;value=[0.0];hits=[];armed=[False]
            def hook(stage):
                if stage=='return_before':armed[0]=True
                if stage==spec['phase'] or (spec['phase']=='return_bfs' and stage=='bfs_expand' and armed[0]):value[0]=spec['instant'];hits.append(stage)
            r=json.loads(json.dumps(solve(c,2,7,clock=lambda:value[0],checkpoint_hook=hook)))
            assert hits
            if spec['relation']=='before':assert r['status']=='task_complete';audit(c,r,2)
            else:assert r['status'] in ('wall_clock_cap','deadline') and not r['route']
            ledger(c,r);prunes(r,r['status']=='task_complete');label=spec['phase']+'_'+spec['relation']
        results.append(dict(kind=row['kind'],label=label,result=r));summaries.append(dict(label=label,status=r['status'],passed=True))
    for kind in ('control','event'):
        j=next(j for j in protocol['jobs'] if j['name']=='large_g1_development__'+kind and j['seed']==20261018)
        c=read(OLD/j['input']);r=json.loads(json.dumps(solve({k:c[k] for k in protocol['whitelist']},20,j['seed'],max_iterations=10)))
        reference=read(ROOT/'Cstar超时归因诊断_20261019'/(kind+'_result.json'))
        assert semantic(r)==semantic(reference),kind
        audit(c,r,20);results.append(dict(kind='prefix',label=kind,result=r));summaries.append(dict(label='prefix_'+kind,status=r['status'],passed=True,cache=r['protection_cache']))
    assert len(results)==88
    write(HERE/'gates/results.json',results);write(HERE/'gates/verification.json',dict(gate='PASS',calls=88,micro_and_boundary=86,prefix=2,records=summaries))
def worker(jobpath,dest):
    job=read(jobpath);p=read(HERE/'protocol.json');c=read(OLD/job['input']);solve=core()
    try:
        result=solve({k:c[k] for k in p['whitelist']},job['budget_seconds'],job['seed'],max_iterations=job['max_iterations'])
        write(dest,dict(worker_status='returned',job=job,input_sha256=sha(OLD/job['input']),result=result));return 0
    except BaseException:write(dest,dict(worker_status='exception',job=job,traceback=traceback.format_exc()));return 1
def equivalence(job,candidate):
    path=OLD/'execution'/(job['run_id']+'.result.json')
    expected=read(OLD/'execution_reaudit.json')['artifact_sha256']['execution\\'+job['run_id']+'.result.json']
    assert sha(path)==expected
    reference=read(path)['result']
    if reference['status']=='task_complete':
        assert semantic(candidate)==semantic(reference),job['run_id'];return 'full_output_equal'
    for key in ('diagnostic_route','task_filters','prune_audits'):
        assert reference[key]==candidate[key][:len(reference[key])],(job['run_id'],key)
    completed=reference['iterations'][:-1]
    assert completed==candidate['iterations'][:len(completed)]
    return 'old_incomplete_prefix_equal'
def roads(p):
    audit,_,_=auditors();out=HERE/'execution';out.mkdir(exist_ok=False);rows=[];consecutive=0
    for job in p['jobs']:
        verify();name=job['run_id'];jobpath=out/(name+'.job.json');dest=out/(name+'.result.json');write(jobpath,job)
        started=time.perf_counter();watchdog=False
        with (out/(name+'.log')).open('x',encoding='utf8') as log:
            try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',str(jobpath),str(dest)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=35,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')).returncode
            except subprocess.TimeoutExpired:code=None;watchdog=True
        row=dict(run_id=name,watchdog=watchdog,returncode=code,accepted=False,wall_seconds=time.perf_counter()-started)
        if code==0 and not watchdog:
            saved=read(dest);assert saved['job']==job and saved['input_sha256']==job['input_sha256']
            try:
                c=read(OLD/job['input']);r=saved['result'];checked=audit(c,r,20)
                same=equivalence(job,r)
                row.update(checked,independent_audit='passed',equivalence=same,cache=r['protection_cache'])
            except Exception:row.update(independent_audit='failed',error=traceback.format_exc())
        consecutive=consecutive+1 if watchdog or code!=0 else 0;rows.append(row)
        with (out/'ledger.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        print(name,row.get('status','technical_or_audit_failure'),row['accepted'],flush=True)
        if consecutive>=2:break
    verify();write(out/'completion.json',dict(started=len(rows),unstarted=40-len(rows),accepted=sum(r['accepted'] for r in rows),gate='PASS' if len(rows)==40 and all(r['accepted'] for r in rows) else 'NOT_PASSED',ranking=False,holdout=False))
def main():
    if len(sys.argv)>1:return worker(Path(sys.argv[2]),Path(sys.argv[3]))
    if (HERE/'protocol.json').exists():raise RuntimeError('Do not overwrite sealed run')
    old=read(OLD/'protocol.json')
    p=dict(version='cache_v0.4_correctness_20261019',jobs=old['jobs'],whitelist=old['core_input_whitelist'],budget=20,max_iterations=20000,watchdog=35,seeds=old['seeds'],gate_calls=88,road_calls=40,road_only_if_equivalence_gates_pass=True,no_retries=True,stop='same as old protocol; any feasible failure blocks gate; two consecutive worker exceptions/watchdogs stop',holdout=False,ranking=False,change='last exact-state task-protection cache only; no single-source replacement or audit removal')
    write(HERE/'protocol.json',p)
    local={str(q.relative_to(ROOT)):sha(q) for q in sorted(HERE.rglob('*')) if q.is_file() and q.suffix!='.log'}
    external={str(q.relative_to(ROOT)):sha(q) for q in (OLD/'freeze_manifest.json',OLD/'protocol.json',OLD/'execution_reaudit.json',OLD/'audit_outputs.py',SPECIAL/'audit_special.py',SPECIAL/'audit_micro.py')}
    write(HERE/'pre_run_manifest.json',dict(local=local,external=external))
    verify();gates(p);verify();roads(p);return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        if not (HERE/'abort.json').exists():write(HERE/'abort.json',dict(error=traceback.format_exc()))
        raise
