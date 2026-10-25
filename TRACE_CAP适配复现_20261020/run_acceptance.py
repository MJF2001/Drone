"""Seal before serial calls. No tuning, no holdout and no performance ranking."""
import json,sys,hashlib,subprocess,time
from pathlib import Path
from collections import Counter
from audit import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def prepare(kind):
    out=HERE/(kind+'_evidence');assert not out.exists(),'Never overwrite a previous batch'
    out.mkdir();cases=[]
    if kind=='micro':
        for folder in ('micro_evidence','regression_evidence'):
            src=ROOT/'Cstar历史适配验收_20261019'/'修正版_v0.2'/folder/'inputs.json'
            for c in json.loads(src.read_text(encoding='utf-8')):
                name=folder+'__'+c['name'];p=out/'inputs'/(name+'.json');save(p,c);cases.append((name,p,sha(src)))
        budget=5
    else:
        base=ROOT/'Cstar道路正确性验收_20261019';old=json.loads((base/'protocol.json').read_text(encoding='utf-8'))
        for c in old['cases']:
            p=base/c['input'];assert sha(p)==c['input_sha256'];cases.append((c['name'],p,sha(p)))
        budget=20
    jobs=[]
    for name,p,source_hash in cases:
        for method in ('TRACE','CAP'):
            for seed in (20261018,20261019):
                jobs.append(dict(run_id=f'{name}__{method}__{seed}',case=name,input=str(p),input_sha256=sha(p),source_hash=source_hash,method=method,seed=seed,budget=budget))
    frozen={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('runtime/*.py'))}
    frozen.update({n:sha(HERE/n) for n in ('audit.py','worker.py','run_acceptance.py','test_core.py')})
    save(out/'protocol.json',dict(version='v0.1_20261020',kind=kind,scope='correctness only; deterministic seeds are repeats, not independent route diversity',budget_seconds=budget,watchdog_seconds=35,stop='two consecutive worker exceptions/watchdogs; preserve all outputs',sources=frozen,jobs=jobs))
    return out
def run(out):
    protocol=json.loads((out/'protocol.json').read_text(encoding='utf-8'))
    for p,h in protocol['sources'].items():assert sha(HERE/p)==h
    results=[];bad=0
    for job in protocol['jobs']:
        assert sha(Path(job['input']))==job['input_sha256']
        jp=out/'jobs'/(job['run_id']+'.json');rp=out/'results'/(job['run_id']+'.json')
        assert not rp.exists();save(jp,job);rp.parent.mkdir(exist_ok=True)
        begin=time.perf_counter()
        try:
            proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(jp),str(rp)],capture_output=True,text=True,timeout=35)
            if proc.returncode:raise RuntimeError(proc.stderr)
            r=json.loads(rp.read_text(encoding='utf-8'));c=json.loads(Path(job['input']).read_text(encoding='utf-8'));record=audit(c,r);bad=0
            if r['status']=='complete':assert r['seconds']<job['budget']
        except Exception as exc:
            record=dict(audit='FAIL',status='worker_or_audit_error',error=repr(exc));bad+=1
        record.update(run_id=job['run_id'],method=job['method'],case=job['case'],seed=job['seed'],worker_wall=time.perf_counter()-begin,result_sha256=sha(rp) if rp.exists() else None)
        results.append(record);save(out/'checks.json',results);print(job['run_id'],record['status'],record['audit'],flush=True)
        if bad>=2:break
    save(out/'summary.json',dict(scheduled=len(protocol['jobs']),executed=len(results),not_run=len(protocol['jobs'])-len(results),counts=dict(Counter(x['status'] for x in results)),audits=dict(Counter(x['audit'] for x in results))))
if __name__=='__main__':
    kind=sys.argv[1];assert kind in ('micro','road');out=prepare(kind);run(out)
