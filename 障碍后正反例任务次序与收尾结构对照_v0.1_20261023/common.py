from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
import json,hashlib,time,math
H=Path(__file__).resolve().parent;ROOT=H.parent;COUNTS=Counter()
BASE=ROOT/'障碍后接续假设有限扩样_v0.1_20261023';VAR=ROOT/'障碍后接续正反例受控变体_v0.1_20261023'
def read(p):
 z=Path(p).read_bytes();COUNTS['json_files_read']+=1;COUNTS['json_bytes_read']+=len(z);return json.loads(z.decode('utf-8-sig'))
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s=json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n';p.write_text(s,encoding='utf-8');COUNTS['json_files_written']+=1;COUNTS['json_bytes_written']+=len(s.encode())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ps(x):return set(map(tuple,x))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
def terms(c):
 out={}
 for t in c['exact']['terms']:
  r=t['r'];out[r]=out.get(r,Q(0))+Q(t['c']['n'],t['c']['d']);COUNTS['certificate_terms_read']+=1
 return {r:q for r,q in out.items() if q}
def expr(d):return {'exact':{'terms':[dict(r=r,c=dict(n=q.numerator,d=q.denominator)) for r,q in sorted(d.items()) if q]}}
def add(a,b,sign=1):
 aa=terms(a);bb=terms(b)
 for r,q in bb.items():aa[r]=aa.get(r,Q(0))+sign*q;COUNTS['certificate_additions']+=1
 return expr(aa)
def number(n):return expr({1:Q(n)} if n else {})
def same(a,b):return terms(a)==terms(b)
def value(a):return sum(float(q)*math.sqrt(r) for r,q in terms(a).items())
