"""Read-only verification of the uploaded full-folder snapshot."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    manifest=json.loads((ROOT/'GitHub上传文件清单_20261016.json').read_text(encoding='utf-8'))
    failures=[]
    for name,entry in manifest['files'].items():
        p=ROOT/name
        if not p.is_file():failures.append((name,'missing'))
        elif p.stat().st_size!=entry['bytes'] or sha(p)!=entry['sha256']:failures.append((name,'size_or_hash_mismatch'))
    print(json.dumps(dict(expected_files=len(manifest['files']),failed=len(failures),failures=failures,empty_directories_recorded=len(manifest['empty_directories'])),ensure_ascii=False))
    return bool(failures)
if __name__=='__main__':sys.exit(main())
