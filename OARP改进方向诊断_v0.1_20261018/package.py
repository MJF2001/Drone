"""--seal once, or --check read-only; all checks execute without any solver."""
import hashlib,json,sys
from pathlib import Path
import verify,verify_extra
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def write(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    sealing='--seal' in sys.argv
    assert sealing or '--check' in sys.argv
    verify.main();verify_extra.main()
    assert (ROOT/'analysis.json').exists() and (ROOT/'micro_analysis.json').exists()
    data=(ROOT/'calls.jsonl').read_bytes()
    seal={'bytes':len(data),'lines':len(data.splitlines()),'sha256_of_prefix':hashlib.sha256(data).hexdigest(),
          'complete_entry_calls':75,'nested_SCIP_calls':75,'nested_GLNS_calls':75}
    verify.prefix(data,seal);verify.prefix(data+b'future append outside sealed prefix\n',seal)
    for bad in (data[:-1],bytes([data[0]^1])+data[1:]):
        try:verify.prefix(bad,seal)
        except AssertionError:pass
        else:raise AssertionError('corrupt prefix accepted')
    if sealing:
        assert not (ROOT/'manifest.json').exists()
        write('ledger_seal.json',seal)
        write('manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    else:
        assert read('ledger_seal.json')==seal
        manifest=read('manifest.json');assert all(sha(ROOT/p)==h for p,h in manifest.items())
        verify.membership(list(manifest),[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='manifest.json'])
    print(json.dumps({'package':'PASS','read_only':not sealing,'manifest_files':len(read('manifest.json')),
        'ledger_lines':seal['lines'],'ledger_pairs':seal['lines']//2,'planner_calls_added_by_verification':0,
        'prefix_corruption_negative_tests':2},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
