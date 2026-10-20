"""Verify once and seal all independent-baseline deliverables."""
import hashlib,json,sys
from pathlib import Path
import verify
ROOT=Path(__file__).resolve().parent
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    result=verify.main()
    if '--check' in sys.argv:
        assert (ROOT/'manifest.json').exists();print('SEALED PACKAGE: PASS (read only)');return
    assert not (ROOT/'manifest.json').exists()
    save('verification_summary.json',result)
    data=(ROOT/'calls.jsonl').read_bytes()
    save('ledger_seal.json',{'bytes':len(data),'lines':len(data.splitlines()),'sha256':hashlib.sha256(data).hexdigest()})
    save('manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print('SEALED',len(json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))),'files')
if __name__=='__main__':main()
