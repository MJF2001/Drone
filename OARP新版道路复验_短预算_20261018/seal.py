"""Verify and seal short-budget outcomes, including empty/late failures."""
import hashlib,json,sys
from pathlib import Path
import verify
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    check='--check' in sys.argv;v=verify.main()
    assert sha(ROOT/'kernel.py')==sha(ROOT.parent/'OARP新版道路复验_汇报用_20261018/kernel.py')
    rows=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    budget_summary={}
    for b in (1,20):
        rs=[verify.read('results/'+j['plan_id']+'.json') for j in verify.read('protocol.json')['planned'] if j['budget']==b]
        assert len(rs)==20
        budget_summary[str(b)]={'n':20,'legal':sum(r['flags']['route_valid'] for r in rs),
            'timely_legal':sum(r['flags']['within_budget'] for r in rs),'core_complete':sum(r['core_complete'] for r in rs),
            'empty_results':sum(not r['route'] for r in rs),'total_seconds':sum(r['public_seconds'] for r in rs)}
    for e in rows:
        if e['event']=='end' and e['kind']=='SCIP' and e['has_incumbent']:
            assert e['objective'] is not None and e['dual_bound']<=e['objective']+1e-6
    data=(ROOT/'calls.jsonl').read_bytes();prefix={'bytes':len(data),'lines':len(data.splitlines()),'sha256_of_prefix':hashlib.sha256(data).hexdigest()}
    if check:
        assert verify.read('ledger_seal.json')==prefix
        assert all(sha(ROOT/p)==h for p,h in verify.read('manifest.json').items())
    else:
        assert not (ROOT/'manifest.json').exists()
        save('verification_summary.json',dict(v,by_budget=budget_summary,core_identical_to_120s=True))
        save('ledger_seal.json',prefix)
        save('manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps({'package':'PASS','read_only':check,'by_budget':budget_summary,
        'manifest_files':len(verify.read('manifest.json')),'new_solver_calls':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
