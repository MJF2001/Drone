"""Common serial-process wrapper; dispatch and provenance outside warm entry."""
import sys,json,os
from pathlib import Path
from isolation import select,sources
from runtime import run_payload
def main():
 job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));dest=Path(sys.argv[2]);inp=Path(job['input']).resolve();reads=[]
 select(job['method']);production_sources=sources(job['method'])
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   p=Path(os.fsdecode(args[0])).resolve();mode=args[1];isread=not isinstance(mode,str) or ('r' in mode or '+' in mode)
   if isread:reads.append(str(p));assert p==inp,('unapproved planning file read',str(p))
 sys.addaudithook(audit)
 payload=inp.read_bytes();mode='PPCPP' if job['method']=='PPCPP' else 'LAST'
 out=run_payload(payload,mode,job['budget'],job['seed'])
 out['job']=job;out['runtime_reads']=reads
 out['imported_modules']=sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and not str(m.__file__).startswith('<')})
 out['production_sources']=production_sources
 dest.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
