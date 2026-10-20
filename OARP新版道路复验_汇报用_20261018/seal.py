"""Seal / read-only check, no solver imports or executions."""
import ast,hashlib,json,sys
from pathlib import Path
import verify
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):(ROOT/p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    check='--check' in sys.argv;v=verify.main()
    records=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    rawcount=0
    for job in verify.read('protocol.json')['planned']:
        r=verify.read('results/'+job['plan_id']+'.json');ends=[e for e in records if e.get('parent')==r['attempt_id'] and e['kind']=='SCIP' and e['event']=='end']
        assert len(ends)==1;e=ends[0];assert e['status']=='optimal' and e['has_incumbent'] and e['gap']<1e-6
        vals=e['values'];o={ast.literal_eval(k):vals[name] for k,name in e['mapping']['orientation'].items()}
        y={ast.literal_eval(k):vals[name] for k,name in e['mapping']['endpoint'].items()}
        assert not e['mapping']['auxiliary_beta_names']
        assert all(abs(x-round(x))<1e-6 and -1e-6<=x<=1+1e-6 for x in vals.values())
        rr=r['core_detail']['ranks'];assert abs(len(rr)-sum(y.values())/2)<1e-6
        assert {k for k,x in y.items() if x>.5}=={(s['axis'],side,tuple(s['cells'][i])) for s in rr for side,i in (('L',0),('R',-1))}
        for s in rr:
            for p in map(tuple,s['cells']):assert o[s['axis'],p]>.5 and abs(o['H',p]+o['V',p]-1)<1e-6
        assert abs(e['objective']-len(rr))<1e-6 and abs(e['dual_bound']-len(rr))<1e-6
        rawcount+=1
    data=(ROOT/'calls.jsonl').read_bytes();prefix={'bytes':len(data),'lines':len(data.splitlines()),'sha256_of_prefix':hashlib.sha256(data).hexdigest()}
    if check:
        old=verify.read('ledger_seal.json');assert prefix==old
        assert all(sha(ROOT/p)==h for p,h in verify.read('manifest.json').items())
    else:
        assert not (ROOT/'manifest.json').exists()
        save('verification_summary.json',dict(v,raw_SCIP_vectors_verified=rawcount))
        save('ledger_seal.json',prefix)
        save('manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps({'sealed_package':'PASS','read_only':check,'raw_vectors':rawcount,
        'manifest_files':len(verify.read('manifest.json')),'new_planner_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
