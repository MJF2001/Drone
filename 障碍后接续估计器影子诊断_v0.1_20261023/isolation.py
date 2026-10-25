"""Program data-access guard. Not a general OS security sandbox."""
from pathlib import Path
import sys,os
def install(home,allowed_input):
 home=Path(home).resolve();allowed_input=Path(allowed_input).resolve();runtime=Path(sys.base_prefix).resolve();counts={'open_events':0,'allowed_reads':0,'blocked_reads':0,'allowed_writes':0};reads=set()
 def hook(event,args):
  if event!='open':return
  name,mode,flags=args
  if isinstance(name,int):return
  p=Path(os.fsdecode(name)).resolve();counts['open_events']+=1
  writing=isinstance(mode,str) and any(x in mode for x in 'wax+') or isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
  if writing:
   if not p.is_relative_to(home):raise PermissionError('write_outside_shadow_package')
   counts['allowed_writes']+=1;return
  allowed=p==allowed_input or p.is_relative_to(runtime) or p.is_relative_to(home) and (p.suffix in ('.py','.pyc') or p.name in ('manifest.json','freeze.json'))
  if not allowed:counts['blocked_reads']+=1;raise PermissionError('estimator_read_not_whitelisted: '+str(p))
  counts['allowed_reads']+=1;reads.add(str(p))
 sys.addaudithook(hook)
 return counts,reads
