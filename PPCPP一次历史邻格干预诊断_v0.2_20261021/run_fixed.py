"""Hash-bound stages, fixed serial slots, one core/entry, fail closed, no retries."""
from stage_control import *
from analyze import compute
import os,sys,subprocess,time
def execute(phase):
    require_preseal();require('stubs');assert phase in ('gate','formal')
    if phase=='formal':require('gate')
    actual=H/'actual_order.jsonl';done=[json.loads(line) for line in actual.read_text(encoding='utf8').splitlines()] if actual.exists() else []
    assert len(done)==(0 if phase=='gate' else 12),('no silent resume',phase,len(done));env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');phase_outputs=[]
    for j in [j for j in read(H/'fixed_order.json') if j['phase']==phase]:
        require_preseal();require('stubs');require('gate') if phase=='formal' else None
        n=len(done);assert n<24;out=H/'outputs'/f'{j["id"]}.json';log=H/'logs'/f'{j["id"]}.txt';assert not out.exists() and not log.exists()
        event=dict(id=j['id'],phase=phase,sequence=n+1,started_utc=time.time(),core_calls_max=1)
        with actual.open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
        done.append(event)
        try:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,timeout=90,capture_output=True)
            with log.open('xb') as f:f.write(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError(('worker failure',j['id'],p.returncode))
            x=read(out);assert len(x['actual_core_calls'])==1 and x['result']['eligible'] and x['result']['entry_seconds']<20;both(read(H/j['input']),x['result']['raw']['route'])
            old=read(S/'outputs'/f'{j["case"]}__{SEEDS.index(j["seed"])}__PPCPP.json')['result']
            if j['mode'] in ('FROZEN','OFF'):assert comparable(x['result'])==comparable(old),'equivalence drift'
            else:assert x['result']['raw']['branches']['P0']['intervention']['trigger_count']==1
            save(H/'logs'/f'{j["id"]}.receipt.json',dict(id=j['id'],exit_code=0,one_core=True,eligible=True,output_sha256=sha(out),completed_utc=time.time()));phase_outputs.append(out)
        except BaseException as ex:
            save(H/'STOP.json',dict(id=j['id'],reason=repr(ex),attempted_entries=n+1,remaining=[z['id'] for z in read(H/'fixed_order.json') if z['id'] not in {r['id'] for r in done}],no_retry=True));raise
        print(phase,n+1,'/24',j['id'],flush=True)
    try:
        a=compute('gate' if phase=='gate' else None)
        if phase=='gate':
            assert len(a['rows'])==12 and len(a['equivalence'])==6;save(H/'gate_analysis.json',a);paths=[H/'gate_analysis.json']
        else:
            assert len(a['rows'])==24 and len(a['pairs'])==6;save(H/'analysis.json',a);csvsave(H/'24调用完整指标.csv',a['rows']);csvsave(H/'6正式配对.csv',a['pairs']);csvsave(H/'2状态三种子原值均值范围.csv',a['states']);save(H/'all_decision_audits.json',a['audits']);paths=[H/'analysis.json',H/'all_decision_audits.json',H/'24调用完整指标.csv',H/'6正式配对.csv',H/'2状态三种子原值均值范围.csv']
        receipt(phase,paths+phase_outputs);print('PASS',phase,'audit; ordinary_BFS=',a['ordinary_BFS_total'],'verdict=',a['stop_verdict'],flush=True)
    except BaseException as ex:
        if not (H/'STOP.json').exists():save(H/'STOP.json',dict(phase=phase,reason=repr(ex),attempted_entries=len(done),no_retry=True))
        raise
if __name__=='__main__':execute(sys.argv[1])
