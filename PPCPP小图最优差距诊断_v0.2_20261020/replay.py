"""Explicit fresh-directory replay. Refuses to modify any existing experiment."""
import argparse,subprocess,sys,shutil
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args();dest=Path(a.destination).resolve()
 assert not dest.exists(),'destination must not exist'
 assert dest.parent==H.parent,'use a fresh sibling directory under project root'
 dest.mkdir()
 for f in H.glob('*.py'):shutil.copy2(f,dest/f.name)
 shutil.copy2(H/'预登记.md',dest/'预登记.md')
 for name in ('setup.py','tests.py','prepare.py','run.py','verify.py'):
  with (dest/(name+'.log')).open('x',encoding='utf-8') as log:subprocess.run([sys.executable,'-B','-X','utf8',str(dest/name)],cwd=H.parent,stdout=log,stderr=subprocess.STDOUT,check=True)
 import json
 def read(p):return json.loads(p.read_text(encoding='utf-8'))
 for ref in (H/'execution').glob('*.json'):
  fresh=read(dest/'execution'/ref.name);gold=read(ref)
  assert fresh['raw']['route']==gold['raw']['route'] and fresh['raw']['trace']==gold['raw']['trace']
 for ref in (H/'exact').rglob('*.json'):
  if ref.name=='mapping.json' or ref.name.endswith('.request.json'):continue
  fresh=read(dest/ref.relative_to(H));gold=read(ref)
  for key in ('status','length','route','start','targets','last'):assert fresh[key]==gold[key],(ref,key)
 print('Fresh replay complete; saved independent verify.py.log plus matching route/trace and exact lengths. No new report/promotion. Original seal unchanged.')
if __name__=='__main__':main()
