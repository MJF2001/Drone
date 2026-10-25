"""Pure geometry audit of contingency cases, no extra solver calls."""
from common import *
from spec import plans,definition,after,before
def main():
 rows=[]
 for p in plans():
  d=definition(p['scale'],p['family']);a,b=map(tuple,d['obstacle_candidates']);f,t=before(p['scale'],p['family'])
  assert a!=b and a in f&t and b in f&t and (0,0) not in (a,b)
  ff,tt,blocked,valid=after(p['scale'],p['family'],'obstacle',a);assert blocked=={b} and valid
  # Both invalid cannot occur for any legal single current with this frozen table.
  for current in f:
   _,_,blocked,valid=after(p['scale'],p['family'],'obstacle',current);assert valid and current not in blocked and len(blocked)==1
  rows.append(dict(base_id=p['base_id'],primary_collision_switch_verified=True,double_invalid_unreachable_for_frozen_table=True))
 save(H/'supplemental_geometry_audit.json',dict(phase='post-run read-only pure geometry audit; no formal inputs modified',solver_calls=0,rows=rows))
 print('6 fallback rules + all legal current coordinates checked; double-invalid unreachable in this table')
if __name__=='__main__':main()
