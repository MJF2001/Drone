"""Primary exact saved-length arithmetic using the accepted radical module."""
from common import ROOT
import sys,time
sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
from center_bench_v01_20261022.exact import Expr,certificate,Uncertain
KEYS={'N_T0','N_T1','E_T0','E_T1'}
def calculate(certs):
 start=time.perf_counter();assert set(certs)==KEYS,'missing/extra four-cell input'
 e={k:Expr.load(v['exact']) for k,v in certs.items()};dn=e['N_T0']-e['N_T1'];de=e['E_T0']-e['E_T1'];values={'D_N':dn,'D_E':de,'I':de-dn};out={}
 for k,v in values.items():
  try:sign=v.sign()
  except Uncertain:sign='uncertain'
  lo,hi=v.interval();out[k]={'sign':sign,'certificate':certificate(v),'interval':[str(lo),str(hi)],'display':float((lo+hi)/2)}
 return {'values':out,'counts':{'length_cert_loads':4,'expression_subtractions':3,'sign_calls':3,'certificate_calls':3,'interval_calls':3},'seconds':time.perf_counter()-start,'formula':'D_N=N_T0-N_T1; D_E=E_T0-E_T1; I=D_E-D_N','no_new_geometry_queries':True}
