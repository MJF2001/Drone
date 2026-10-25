from diag_common import *
if __name__=='__main__':
 hybrid,runtime=production();import environment,worker
 n=environment.verify();files=dict(read(S/'environment_seal.json')['files'])
 for p in D.rglob('*'):
  if p.is_file() and p.suffix in ('.py','.json','.md') and '__pycache__' not in p.parts:files[str(p.resolve())]=sha(p)
 save(D/'environment_seal.json',dict(complete=True,phase='before4 positive entries and all exact solves; no new solves so far',parent_seal=str(S/'environment_seal.json'),parent_sha256=sha(S/'environment_seal.json'),files=files,python=sys.version,limitations=read(S/'environment_seal.json')['limitations']))
 print('PRESEALED',len(files),'files; prior runtime verified',n)
