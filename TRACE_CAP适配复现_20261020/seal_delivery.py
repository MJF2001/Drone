"""Seal once; --verify is read-only. Never overwrite a seal."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;manifest=HERE/'delivery_manifest.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if '--verify' in sys.argv:
    saved=json.loads(manifest.read_text(encoding='utf-8'))
    for p,h in saved.items():assert sha(HERE/p)==h,p
    print('PASS',len(saved),'sealed files')
else:
    assert not manifest.exists()
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p!=manifest}
    manifest.write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SEALED',len(files),'files')
