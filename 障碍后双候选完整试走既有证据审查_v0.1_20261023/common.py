from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
from math import isqrt
import json,hashlib,time
H=Path(__file__).resolve().parent;ROOT=H.parent
BASE=ROOT/'障碍后接续假设有限扩样_v0.1_20261023'
VAR=ROOT/'障碍后接续正反例受控变体_v0.1_20261023'
STRUCT=ROOT/'障碍后正反例任务次序与收尾结构对照_v0.1_20261023'
SHADOW=ROOT/'障碍后接续估计器影子诊断_v0.1_20261023'
FIRST=ROOT/'PPCPP首次恢复完整试走_v0.1_20261020'
C=Counter()
def read(p):
 b=Path(p).read_bytes();C['json_reads']+=1;C['json_read_bytes']+=len(b);return json.loads(b.decode('utf-8-sig'))
def textread(p):
 b=Path(p).read_bytes();C['text_reads']+=1;C['text_read_bytes']+=len(b);return b.decode('utf-8-sig')
def sha(p):
 b=Path(p).read_bytes();C['hash_reads']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s=json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
 with p.open('x',encoding='utf-8') as f:f.write(s)
 C['json_writes']+=1;C['json_write_bytes']+=len(s.encode())
def ps(x):return set(map(tuple,x))
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
def expr(c):
 d={}
 for t in c['exact']['terms']:
  r=t['r'];d[r]=d.get(r,Q(0))+Q(t['c']['n'],t['c']['d']);C['certificate_terms']+=1
 return {r:v for r,v in d.items() if v}
def add(*signed):
 d={}
 for s,e in signed:
  for r,v in e.items():d[r]=d.get(r,Q(0))+s*v;C['coefficient_additions']+=1
 return {r:v for r,v in d.items() if v}
def interval(e,bits=128):
 scale=1<<bits;lo=hi=Q(0)
 for r,v in e.items():
  k=isqrt(r*scale*scale);a=Q(k,scale);b=a if k*k==r*scale*scale else Q(k+1,scale);lo+=v*(a if v>0 else b);hi+=v*(b if v>0 else a);C['integer_root_bounds']+=1
 return lo,hi
def sign(e):
 if not e:return 0
 lo,hi=interval(e);assert lo>0 or hi<0,'uncertified sign';return 1 if lo>0 else -1
def value(e):return float(sum(interval(e))/2)
def cert(e):return {'exact':{'terms':[dict(r=r,c=dict(n=v.numerator,d=v.denominator)) for r,v in sorted(e.items())]}}
def guard():
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,('old source changed',p)
def fail_record(stage,ex):
 import traceback
 d=H/'analysis_failures';d.mkdir(exist_ok=True);i=len(list(d.glob('*.json')))+1;dump(d/(f'{i:02d}_{stage}.json'),dict(stage=stage,utc=time.time(),failure=repr(ex),traceback=traceback.format_exc(),counts=dict(C),old_files_unchanged=True))
