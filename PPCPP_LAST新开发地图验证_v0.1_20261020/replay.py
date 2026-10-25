import sys,subprocess,shutil,argparse,json
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args();dest=Path(a.destination).resolve();assert not dest.exists() and dest.parent==H.parent;dest.mkdir()
 for f in H.glob('*.py'):shutil.copy2(f,dest/f.name)
 shutil.copy2(H/'预登记.md',dest/'预登记.md')
 for name in ('setup.py','preflight.py','prepare.py','novelty.py','gates.py','run.py'):
  with (dest/(name+'.log')).open('x',encoding='utf-8') as log:subprocess.run([sys.executable,'-B','-X','utf8',str(dest/name)],cwd=H.parent,stdout=log,stderr=subprocess.STDOUT,check=True)
 for ref in (H/'execution').glob('*.json'):
  old=read(ref);new=read(dest/'execution'/ref.name)
  for key in ('route','trace','status','e','selected'):assert old['raw'][key]==new['raw'][key],(ref,key)
  for branch in old['raw']['branches']:
   for key in ('route','trace','status'):assert old['raw']['branches'][branch][key]==new['raw']['branches'][branch][key]
 print('Fresh fixed-matrix replay complete; all full branch and selected traces match. Original seal unchanged; not additional samples or approval.')
if __name__=='__main__':main()
