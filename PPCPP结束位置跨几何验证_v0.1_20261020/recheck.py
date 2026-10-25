"""Separate bounded child per reviewed query. No planner/main BFS imports."""
import json,time,subprocess,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 if len(sys.argv)>1:
  from independent import oracle
  q=read(Path(sys.argv[1]))['request'];begin=time.perf_counter();n=oracle(set(map(tuple,q['free'])),tuple(q['start']),tuple(q['base']),set(map(tuple,q['targets'])),tuple(q['last']) if q['last'] is not None else None)
  print(json.dumps(dict(status='complete',length=n,seconds=time.perf_counter()-begin)));return
 rows=[]
 for req in sorted((H/'exact').glob('*/*.request.json')):
  result=req.with_name(req.name.replace('.request.json','.json'));r=read(result)
  if r['status']=='unresolved':continue
  dest=H/'rechecks'/req.parent.name/result.name;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():x=read(dest)
  else:
   start=time.perf_counter()
   try:
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'recheck.py'),str(req)],capture_output=True,text=True,encoding='utf-8',timeout=60)
    if p.returncode:x=dict(status='error',stdout=p.stdout,stderr=p.stderr)
    else:x=json.loads(p.stdout)
   except subprocess.TimeoutExpired:x=dict(status='unresolved',reason='independent_wall_60s')
   x.update(wall_seconds=time.perf_counter()-start,result_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),request_sha256=hashlib.sha256(req.read_bytes()).hexdigest())
   dest.write_text(json.dumps(x,indent=2),encoding='utf-8')
  if x['status']=='complete':assert x['length']==r['length'] and (r['status']=='infeasible')==(x['length'] is None)
  rows.append(dict(query=str(result.relative_to(H)),**x));print(req.parent.name,result.stem,x['status'],x.get('length'),flush=True)
 dest=H/'recheck_summary.json'
 if not dest.exists():dest.write_text(json.dumps(dict(calls=len(rows),completed=sum(x['status']=='complete' for x in rows),rows=rows),indent=2),encoding='utf-8')
if __name__=='__main__':main()
