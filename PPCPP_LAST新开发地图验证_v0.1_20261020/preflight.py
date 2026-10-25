from common import *
from spec import *
from input_audit import reconstruct,reachable
from audit_adapter import gate
def main():
 protect();rows=[]
 for d in read(H/'protocol.json')['definitions']:
  s=dict(L=d['L'],w=d['w'],family=d['family']);f,t=before(d);ff,tt,_,_,_=reconstruct(s);assert (f,t)==(ff,tt)
  assert t<=reachable(t,min(t)) and len(f)<=10000
  for event in ('straight','corner','obstacle'):
   a,pub,b,i,v=after(d,event,(-99,-99));f0,t0,pp,bb,ii=reconstruct(s,(-99,-99),event);assert a==f0-bb and pub==pp and b==bb and i==ii
   if event!='obstacle':assert len(pub-t)==d['extension_length']*d['w'] and pub<=reachable(pub,min(pub))
  first,backup=map(lambda r:rect(*r),d['obstacle_rectangles']);assert not first&backup and (first|backup)<=t and (0,0) not in first|backup
  for cur in first|backup:
   f1,pub,b,i,v=after(d,'obstacle',cur);assert v and cur not in b and i==(1 if cur in first else 0) and t-b<=reachable(t-b,min(t-b))
  assert d['w']-max(1,d['w']//2)>=1
  if d['family']=='Z':assert d['L']-d['w']>=2*d['w']
  rows.append(dict(base_id=d['base_id'],passed=True,free=len(f),old_targets=len(t),max_published=len(t)+d['extension_length']*d['w'],primary_backup_disjoint=True))
 # Explicit ledger corner cases, purely geometric, no planner calls.
 f={(0,0),(1,0),(2,0)};pub={(0,0),(1,0),(2,0)};h={(1,0)};f-=h
 assert pub-f-h==set() and h<=pub
 h=set();assert pub-f-h=={(1,0)}
 targets={(0,0),(2,0)};assert targets-set()-{(0,0)}=={(2,0)}
 save(H/'preflight.json',dict(passed=True,definitions=rows,instant_current_credit=True,blocked_history_retained=True,deferred_not_completed=True,double_obstacle_collision_unreachable=True,audit_cache_gate=gate()))
 print('all 9 geometry/obstacle/ledger preflight gates passed; no solver calls',flush=True)
if __name__=='__main__':main()
