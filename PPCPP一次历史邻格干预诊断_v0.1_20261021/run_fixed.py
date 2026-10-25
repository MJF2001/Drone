"""Fixed sequential execution, 90s watchdog, no retry, max24 entries."""
from probe_common import *
import os,sys,subprocess,time
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
phase=sys.argv[1];assert phase in ('gate','formal');assert read(H/'stub_results.json')['passed']
if phase=='formal':assert len(read(H/'gate_analysis.json')['equivalence'])==6
actual=H/'actual_order.jsonl'
for j in [j for j in read(H/'fixed_order.json') if j['phase']==phase]:
    n=len(actual.read_text().splitlines()) if actual.exists() else 0;assert n<24
    out=H/'outputs'/f'{j["id"]}.json';assert not out.exists();log=H/'logs'/f'{j["id"]}.txt';assert not log.exists()
    event=dict(id=j['id'],phase=phase,sequence=n+1,started_utc=time.time(),core_calls_max=1)
    with actual.open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
    try:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,timeout=90,capture_output=True)
        with log.open('xb') as f:f.write(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(('worker failure',j['id'],p.returncode))
        x=read(out);assert len(x['actual_core_calls'])==1 and x['result']['eligible'] and x['result']['entry_seconds']<20
        both(read(H/j['input']),x['result']['raw']['route'])
        old=read(S/'outputs'/f'{j["case"]}__{SEEDS.index(j["seed"])}__PPCPP.json')['result']
        if j['mode'] in ('FROZEN','OFF'):assert comparable(x['result'])==comparable(old),'equivalence drift'
        else:assert x['result']['raw']['branches']['P0']['intervention']['trigger_count']==1
        save(H/'logs'/f'{j["id"]}.receipt.json',dict(id=j['id'],exit_code=0,one_core=True,eligible=True,output_sha256=sha(out),completed_utc=time.time()))
    except BaseException as ex:
        save(H/'STOP.json',dict(id=j['id'],reason=repr(ex),attempted_entries=n+1,remaining=[z['id'] for z in read(H/'fixed_order.json') if not (H/'outputs'/f'{z["id"]}.json').exists()],no_retry=True));raise
    print(phase,n+1,'/24',j['id'],flush=True)
