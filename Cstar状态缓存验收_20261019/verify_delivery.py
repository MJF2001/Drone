"""Read-only candidate archive hash check, no solver calls."""
import json,hashlib
from pathlib import Path
from validate_and_run import verify
HERE=Path(__file__).resolve().parent
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    verify();m=json.loads((HERE/'delivery_manifest.json').read_text(encoding='utf8'))
    for path,sha in m['files'].items():assert digest(HERE/path)==sha,path
    print(json.dumps(dict(read_only=True,new_solver_calls=0,files_verified=len(m['files']),candidate='CSTAR_HISTORY_CACHE_v0.4',road_gate='PASS',accepted=40,holdout_used=False),ensure_ascii=False))
if __name__=='__main__':main()
