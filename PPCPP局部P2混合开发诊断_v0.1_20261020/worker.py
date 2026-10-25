import os
from support import *
import entry,runtime,hybrid
def imports():
 paths={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and not str(m.__file__).startswith('<')}
 paths|={str(Path(p).resolve()) for p in [runtime.native.__file__,runtime.native.core.__file__,runtime.validate.__code__.co_filename]}
 return sorted(paths)
def main():
 job=read(sys.argv[1]);seal=read(H/'environment_seal.json');assert seal['complete'] and job['environment_sha256']==sha(H/'environment_seal.json');sources={}
 for p in imports():
  if Path(p).is_file() and not Path(p).is_relative_to(Path(os.environ.get('WINDIR','C:/Windows'))):
   assert p in seal['files'],('unsealed import',p);assert sha(p)==seal['files'][p];sources[p]=seal['files'][p]
 inp=Path(job['input']).resolve();reads=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   mode=args[1]
   if not isinstance(mode,str) or 'r' in mode or '+' in mode:
    p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,p
 sys.addaudithook(audit);payload=inp.read_bytes();x=entry.run(payload,job['method'],20,job['seed']);x.update(job=job,runtime_reads=reads,production_hashes=sources,imported_modules=imports())
 Path(sys.argv[2]).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
