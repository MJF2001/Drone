import os
from common_orient import *
import entry
def imports():
 paths={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and not str(m.__file__).startswith('<')};paths|={str(Path(p).resolve()) for p in (entry.old.__file__,entry.new.__file__,entry.old.core.__file__,entry.validate.__code__.co_filename)};return sorted(paths)
def main():
 j=read(sys.argv[1]);seal=read(H/'environment_seal.json');assert seal['complete'] and sha(H/'environment_seal.json')==j['seal_sha256'];hashes={}
 for p in imports():
  if Path(p).is_file() and not Path(p).is_relative_to(Path(os.environ.get('WINDIR','C:/Windows'))):
   assert p in seal['files'],('unsealed module',p);assert sha(p)==seal['files'][p];hashes[p]=seal['files'][p]
 inp=Path(j['input']).resolve();reads=[]
 def audit(ev,args):
  if ev=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   mode=args[1]
   if not isinstance(mode,str) or 'r' in mode or '+' in mode:
    p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,p
 sys.addaudithook(audit);payload=inp.read_bytes();x=entry.run(payload,j['mode'],20,20261020,j['degree'],mutation=j['mutation']);x.update(job=j,production_hashes=hashes,imported_modules=imports(),runtime_reads=reads)
 Path(sys.argv[2]).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
