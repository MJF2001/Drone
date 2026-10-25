import os,platform,ctypes,datetime
from common_orient import *
import worker,audit_orient
def verify():
 s=read(H/'environment_seal.json');assert s['complete']
 for p,h in s['files'].items():assert sha(p)==h,p
 return len(s['files'])
def main():
 prior=R/'PPCPP局部P2混合开发诊断_v0.1_20261020/environment_seal.json';base=read(prior)
 for p,h in base['files'].items():assert sha(p)==h,p
 paths=set(map(Path,base['files']));paths.update(Path(p) for p in worker.imports() if Path(p).is_file());paths.update(Path(p) for p in (audit_orient.scalar.__file__,audit_orient.metric.__code__.co_filename,audit_orient.cross.__code__.co_filename))
 paths.update(p.resolve() for p in H.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.md','.diff') and '__pycache__' not in p.parts)
 save(H/'environment_seal.json',dict(complete=True,created=datetime.datetime.now().astimezone().isoformat(),files={str(p):sha(p) for p in sorted(paths)},imports=worker.imports(),platform=platform.platform(),python=sys.version,executable=sys.executable,threads=1,parent_seal=str(prior),parent_sha256=sha(prior),native_modules=base['native_modules'],limitations='Full related Python/project/deps source/binary/config byte scope inherited+verified. System Windows DLLs only paths, not full-machine image; undiscovered dynamic native loads remain limitation.'))
 print('PRESEALED',verify(),'files, no real solves yet')
if __name__=='__main__':main()
