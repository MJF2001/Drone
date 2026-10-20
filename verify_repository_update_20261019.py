"""Read-only byte checks for the 2026-10-19 increment; no planner calls."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((ROOT/'GitHub更新文件清单_20261019.json').read_text(encoding='utf-8'))
    entries=dict(manifest['copied_files']);entries.update(manifest.get('additional_updated_files',{}))
    missing=[];mismatch=[]
    for name,entry in entries.items():
        path=ROOT/name
        if not path.is_file():missing.append(name)
        elif path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:mismatch.append(name)
    print(json.dumps({'files':len(entries),'missing':missing,'mismatch':mismatch,'planner_calls':0},ensure_ascii=False,indent=2))
    assert not missing and not mismatch
if __name__=='__main__':main()
