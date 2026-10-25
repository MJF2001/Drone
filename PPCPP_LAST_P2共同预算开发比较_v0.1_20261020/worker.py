import sys,json,os,time
from pathlib import Path
import runtime,candidate,p2_adapter
from support import *
def imported():
 paths={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and not str(m.__file__).startswith('<')}
 paths.update(str(Path(p).resolve()) for p in (runtime.native.__file__,runtime.native.core.__file__,runtime.validate.__code__.co_filename))
 return sorted(paths)
def check_imports(seal):
 result={}
 for p in imported():
  if Path(p).is_file():
   if str(Path(p)).lower().startswith(str(Path(os.environ.get('WINDIR','C:/Windows'))).lower()):continue
   assert p in seal['files'],('unsealed import',p)
   h=sha(p);assert h==seal['files'][p],('changed import',p);result[p]=h
 return result
def main():
 job=read(sys.argv[1]);seal=read(H/'environment_seal.json');assert seal['complete'];assert sha(H/'environment_seal.json')==job['environment_seal_sha256'];sources=check_imports(seal)
 inp=Path(job['input']).resolve();reads=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   mode=args[1]
   if not isinstance(mode,str) or 'r' in mode or '+' in mode:
    p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,('unapproved planning read',p)
 sys.addaudithook(audit);payload=inp.read_bytes()
 if job['method']=='P2_MULTI':x=p2_adapter.run_payload(payload,job['budget'],job['seed'])
 else:x=runtime.run_payload(payload,'LAST' if job['method']=='LAST_V2' else 'PPCPP',job['budget'],job['seed'])
 x.update(job=job,runtime_reads=reads,imported_modules=imported(),production_hashes=sources)
 Path(sys.argv[2]).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
