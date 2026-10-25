from pathlib import Path
import json, hashlib, time
H=Path(__file__).resolve().parent
ROOT=H.parent
STRUCT=ROOT/'障碍后正反例任务次序与收尾结构对照_v0.1_20261023'
BASE=ROOT/'障碍后接续假设有限扩样_v0.1_20261023'
VAR=ROOT/'障碍后接续正反例受控变体_v0.1_20261023'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
def ps(x):return set(map(tuple,x))
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def log(p,x):
 with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
def guard():
 for p,v in read(H/'freeze.json').items():assert sha(H/p)==v,('active_source_changed',p)
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,('source_changed',p)
