"""Explicit new-process rerun; separate from read-only evidence audit."""
import json,hashlib
from pathlib import Path
from special_suite import solve,execute_boundary
from audit_special import ledger,prune_checks,hole_checks
ROOT=Path(__file__).resolve().parent
def main():
    folder=ROOT/'evidence';protocol=json.loads((folder/'protocol.json').read_text(encoding='utf8'))
    manifest=json.loads((folder/'pre_run_manifest.json').read_text(encoding='utf8'))
    for path,sha in manifest['files'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    saved=json.loads((folder/'results.json').read_text(encoding='utf8'));current=[]
    for c in protocol['base_inputs']+protocol['hole_inputs']:
        current.append(solve(c,2,7))
    for spec in protocol['boundary_specs']:current.append(execute_boundary(spec)['result'])
    records=[]
    for row,r in zip(saved,current):
        r=json.loads(json.dumps(r));prior=row['result']
        assert {k:v for k,v in r.items() if k!='seconds'}=={k:v for k,v in prior.items() if k!='seconds'}
        ledger(row['input'],r);prune_checks(r,r['status']=='task_complete')
        if row['kind']=='functional':hole_checks(row['input'],r)
        records.append(dict(kind=row['kind'],name=row['input']['name'],phase=row.get('phase'),relation=row.get('relation'),status=r['status'],same_except_seconds=True))
    assert len(records)==86
    print(json.dumps(dict(replay_calls=86,real_clock_functional_calls=29,controlled_clock_calls=57,records=records),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
