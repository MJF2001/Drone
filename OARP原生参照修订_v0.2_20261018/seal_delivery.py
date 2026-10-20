"""Seal only a fully verified delivery. --check never writes or runs solvers."""
import hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def ledger_gate(data):
    rows=[json.loads(s) for s in data.decode('utf-8').splitlines()];starts={};ends={}
    for e in rows:
        table=starts if e['event']=='start' else ends
        assert e['attempt_id'] not in table;table[e['attempt_id']]=e
        assert 'error' not in e
    assert starts.keys()==ends.keys()
    return len(starts)
def prefix_gate(data,seal):
    assert len(data)>=seal['bytes'] and digest(data[:seal['bytes']])==seal['sha256_of_prefix']
    assert len(data[:seal['bytes']].splitlines())==seal['lines']
def dependencies():
    lock=read('dependency_lock_after_execution.json')
    for p,h in lock['files'].items():assert digest(Path(p).read_bytes())==h
    return len(lock['files'])
def main():
    check='--check' in sys.argv
    load('verify_delivery').main()
    # Invoke the independent checker only in its read-only mode.
    prior=sys.argv[:]
    try:sys.argv=['supplement.py','--check'];load('supplement').main()
    finally:sys.argv=prior
    data=(ROOT/'calls.jsonl').read_bytes();calls=ledger_gate(data)
    rows=[json.loads(s) for s in data.decode('utf-8').splitlines()]
    # Missing end / duplicate attempt / error must all refuse sealing.
    for bad in (rows[:-1],rows+[rows[0]],[dict(rows[0],error='injected')]+rows[1:]):
        try:ledger_gate(('\n'.join(json.dumps(r) for r in bad)+'\n').encode())
        except AssertionError:pass
        else:raise AssertionError('broken ledger passed seal gate')
    depcount=dependencies()
    seal={'bytes':len(data),'lines':len(data.splitlines()),'sha256_of_prefix':digest(data),'starts_and_ends_paired':calls}
    prefix_gate(data,seal);prefix_gate(data+b'future_append_not_part_of_seal\n',seal)
    for bad in (data[:-1],bytes([data[0]^1])+data[1:]):
        try:prefix_gate(bad,seal)
        except AssertionError:pass
        else:raise AssertionError('corrupt prefix passed')
    if check:
        prefix_gate(data,read('ledger_seal.json'))
        manifest=read('manifest.json');assert all(digest((ROOT/p).read_bytes())==h for p,h in manifest.items())
        assert {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='manifest.json'}==set(manifest)
    else:
        assert not (ROOT/'manifest.json').exists(),'delivery already sealed'
        save('ledger_seal.json',seal)
        save('manifest.json',{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps({'package':'PASS','read_only':check,'ledger_call_pairs':calls,'dependency_files_checked':depcount,
        'manifest_files':len(read('manifest.json')),'broken_ledger_seal_negative_tests':3,'prefix_negative_tests':2,'new_solver_calls':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
