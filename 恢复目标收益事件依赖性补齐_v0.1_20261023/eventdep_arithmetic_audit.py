"""Independent Fraction/isqrt interval arithmetic; no primary/exact imports."""
from fractions import Fraction as Q
from math import isqrt
from collections import Counter
import time
def audit(certs,primary):
 start=time.perf_counter();assert set(certs)=={'N_T0','N_T1','E_T0','E_T1'},'missing four-cell input';counts=Counter(certificates_parsed=0,term_accumulations=0,interval_rounds=0,integer_sqrt_bounds=0)
 parsed={}
 for k,c in certs.items():
  terms={};counts['certificates_parsed']+=1
  for term in c['exact']['terms']:
   r=term['r'];assert type(r) is int and r>0;v=Q(term['c']['n'],term['c']['d']);terms[r]=terms.get(r,Q())+v
  parsed[k]=terms
 # Independent signed linear combination, including cross-form I directly.
 weights={'D_N':{'N_T0':1,'N_T1':-1},'D_E':{'E_T0':1,'E_T1':-1},'I':{'E_T0':1,'N_T1':1,'E_T1':-1,'N_T0':-1}};results={}
 for name,w in weights.items():
  ts={}
  for k,co in w.items():
   for r,v in parsed[k].items():ts[r]=ts.get(r,Q())+co*v;counts['term_accumulations']+=1
  ts={r:v for r,v in ts.items() if v};sign=0 if not ts else 'uncertain';lo=hi=Q()
  if ts:
   for bits in (64,128,256,512):
    lo=hi=Q();den=1<<bits;counts['interval_rounds']+=1
    for r,v in ts.items():
     if r==1:a=b=Q(1)
     else:
      root=isqrt(r*den*den);a=Q(root,den);b=a if root*root==r*den*den else Q(root+1,den);counts['integer_sqrt_bounds']+=1
     lo+=v*(a if v>0 else b);hi+=v*(b if v>0 else a)
    if lo>0:sign=1;break
    if hi<0:sign=-1;break
  expected={t['r']:Q(t['c']['n'],t['c']['d']) for t in primary['values'][name]['certificate']['exact']['terms']}
  assert ts==expected and primary['values'][name]['sign']==sign,(name,ts,expected,sign)
  results[name]={'sign':sign,'independent_interval':[str(lo),str(hi)],'terms':{str(r):str(v) for r,v in ts.items()}}
 return {'passed':True,'values':results,'counts':dict(counts),'seconds':time.perf_counter()-start,'scope':'independent signed coefficients and rational isqrt bounds; no root simplification search, no epsilon, no route/geometry queries'}
