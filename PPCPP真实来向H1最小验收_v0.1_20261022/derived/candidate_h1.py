"""Independent H1 entry: frozen P0 flow only; LAST branch is excluded."""
import json,hashlib
from dataclasses import replace
from runtime_h1 import native,DeadlineExceeded,NoPath
VERSION='PPCPP_H1_ENTRY_v0.1'
def append_segment(route,pending,segment,mark):
 assert segment[0]==route[-1]
 for q in segment[1:]:mark('alternative_move');route.append(q);pending.discard(q)
def solve(s,initial,mode,seed,predator,heading_request,begin,deadline,phases,mark,clock,geometry):
 assert mode in ('PPCPP',)
 out=dict(version=VERSION,mode=mode,status='not_started',route=(),trace=[],selected=None,e=None,branches={},reason=None)
 try:
  mark('p0_before');a=clock();p0=native.solve(s,initial,deadline-clock(),seed,predator,heading_request,_clock=clock,_geometry=geometry);phases['p0']=clock()-a;out['branches']['P0']=p0
  mark('p0_done')
  if p0['status']!='core_complete':out.update(status=p0['status'],reason='original_branch_failed');return out
  pristine=json.dumps(p0,sort_keys=True);chosen=p0;out['selected']='P0'
  u=set(s.targets)-set(s.covered)-{s.current}
  mark('final_audit_before');a=clock();checked=native.single_cell_audit(s,tuple(chosen['route']));phases['final_audit']=clock()-a;mark('final_audit_after')
  out.update(status='core_complete' if checked['valid'] else 'core_invalid',route=tuple(chosen['route']) if checked['valid'] else (),trace=chosen['trace'],reason=checked['errors'] or None)
 except DeadlineExceeded:
  out.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 return out
