"""Frozen baseline_suite P2 branch, excluding ONLY its external audit."""
import time
from runtime import native
from baseline_suite import check_contract
from p2_search_audit import solve as p2_solve
def solve(s,initial,budget,seed):
 begin=time.perf_counter();check_contract(s,initial,budget)
 remaining=budget-(time.perf_counter()-begin)
 if remaining<=0:r=dict(route=(),source=None,status='deadline',seconds=time.perf_counter()-begin)
 else:
  try:r=p2_solve(s,remaining,'multi',seed)
  except ValueError as exc:
   if str(exc)!='infeasible input':raise
   r=dict(route=(),source=None,status='environment_infeasible',reason=str(exc),seconds=None)
 r['seconds']=time.perf_counter()-begin;r['method']='P2_MULTI';r['budget']=budget;r['seed']=seed
 r['fallback_selected']=r.get('source') in ('old_suffix','common_fallback','common_old_suffix','common_GD_adapter')
 r['overrun_gt_10ms']=r['seconds']>budget+.01
 return r
def run_payload(payload,budget,seed):
 import json
 from runtime import validate,snapshot
 begin=time.perf_counter();c=json.loads(payload);validate(c);s=snapshot(c)
 raw=solve(s,set(map(tuple,c['initial_targets'])),budget-(time.perf_counter()-begin),seed)
 a=time.perf_counter();wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':'));encoding=time.perf_counter()-a
 return dict(raw=raw,entry_seconds=time.perf_counter()-begin,budget=budget,method='P2_MULTI',seed=seed,phase_seconds=dict(encoding=encoding))
