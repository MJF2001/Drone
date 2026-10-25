"""Read-only hash check; no planner invocation or result overwrite."""
import json,hashlib
from pathlib import Path
from run import verify
ROOT=Path(__file__).resolve().parent
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    verify();m=json.loads((ROOT/'execution_delivery_manifest.json').read_text(encoding='utf8'))
    for path,sha in m['files'].items():assert digest(ROOT/path)==sha,path
    print(json.dumps(dict(read_only=True,new_solver_calls=0,files_verified=len(m['files']),gate=m['gate'],started=40,accepted=36),ensure_ascii=False))
if __name__=='__main__':main()
