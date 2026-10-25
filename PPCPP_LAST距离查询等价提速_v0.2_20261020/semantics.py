"""Strict comparison, only explicit time/version paths are removed."""
import json
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
def p0_semantic(b):
 b=norm(b)
 for k in ('seconds','accepted_seconds','budget','overrun_gt_10ms'):b.pop(k,None)
 return b
def semantic(raw):
 r=norm(raw);r.pop('version',None)
 if 'P0' in r.get('branches',{}):r['branches']['P0']=p0_semantic(r['branches']['P0'])
 if 'P1' in r.get('branches',{}):r['branches']['P1'].pop('accepted_seconds',None)
 return r
def fingerprint(raw):return json.dumps(semantic(raw),ensure_ascii=False,sort_keys=True,separators=(',',':'))
def compare(a,b):
 assert a['budget']==b['budget']==20
 if a['eligible'] and b['eligible']:
  assert semantic(a['raw'])==semantic(b['raw']),'non-time semantic mismatch'
  return 'equal_complete'
 assert a['raw']['status']=='deadline' or b['raw']['status']=='deadline','non-time failure mismatch'
 return 'deadline_unpaired'
def last_capture(c,route):
 u=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])};last=None
 for q in map(tuple,route):
  if q in u:u.remove(q);last=q
 return dict(last=last,remaining=sorted(u))
