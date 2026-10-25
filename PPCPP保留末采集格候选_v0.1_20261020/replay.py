import argparse,subprocess,sys,shutil,json
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args();dest=Path(a.destination).resolve();assert not dest.exists() and dest.parent==H.parent;dest.mkdir()
 for f in H.glob('*.py'):shutil.copy2(f,dest/f.name)
 shutil.copy2(H/'预登记.md',dest/'预登记.md')
 for name in ('setup.py','gates_v02.py','run.py'):
  with (dest/(name+'.log')).open('x',encoding='utf-8') as log:subprocess.run([sys.executable,'-B','-X','utf8',str(dest/name)],cwd=H.parent,stdout=log,stderr=subprocess.STDOUT,check=True)
 for original in (H/'execution').glob('*.json'):
  ref=read(original);new=read(dest/'execution'/original.name)
  for field in ('route','trace','selected','e'):assert ref['raw'][field]==new['raw'][field],(original,field)
  for branch in ref['raw']['branches']:
   for field in ('status','route','trace'):assert ref['raw']['branches'][branch][field]==new['raw']['branches'][branch][field]
 print('Fresh 360-call replay finished; complete output traces match reference. Original seal unchanged; new calls are replay only, not extra samples.')
if __name__=='__main__':main()
