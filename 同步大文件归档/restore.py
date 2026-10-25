"""Restore archived large evidence files without overwriting different contents."""
import gzip,hashlib,json,pathlib,tempfile,os
base=pathlib.Path(__file__).resolve().parent
root=base.parent
for row in json.loads((base/'manifest.json').read_text(encoding='utf8')):
    dest=(root/row['path']).resolve()
    if not dest.is_relative_to(root): raise ValueError('Path escapes repository')
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=row['sha256']: raise ValueError(f'Existing file differs: {dest}')
        print('already verified', row['path']); continue
    dest.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.restore-',dir=dest.parent)
    try:
        h=hashlib.sha256();size=0
        with os.fdopen(fd,'wb') as output,gzip.open(base/row['archive'],'rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''):
                h.update(block);size+=len(block);output.write(block)
        if h.hexdigest()!=row['sha256'] or size!=row['bytes']:raise ValueError('Archive verification failed')
        if dest.exists():raise FileExistsError(dest)
        os.rename(name,dest)
        print('restored',row['path'])
    finally:
        if os.path.exists(name):os.unlink(name)
