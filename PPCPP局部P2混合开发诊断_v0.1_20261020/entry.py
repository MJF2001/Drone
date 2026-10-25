import time
from support import *
from runtime import *
import hybrid
from p2_adapter import solve as global_p2
def run(payload,method,budget,seed):
 if method=='LOCAL_P2':return hybrid.run(payload,budget,seed)
 begin=time.perf_counter();env=json.loads(payload);c=env['state'];validate(c);s=snapshot(c)
 if method=='PPCPP':raw=native.solve(s,pts(c['initial_targets']),budget-(time.perf_counter()-begin),seed,tuple(c['predator']),tuple(c['previous']) if c['previous'] else None)
 else:raw=global_p2(s,pts(c['initial_targets']),budget-(time.perf_counter()-begin),seed)
 a=time.perf_counter();wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':'));encoding=time.perf_counter()-a;elapsed=time.perf_counter()-begin
 if method=='PPCPP' and elapsed>=budget:raw.update(status='deadline',route=())
 return dict(raw=raw,budget=budget,seed=seed,entry_seconds=elapsed,phase_seconds=dict(encoding=encoding),eligible=bool(raw['route']) and elapsed<budget)
