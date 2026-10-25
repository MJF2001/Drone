import argparse,subprocess,sys,shutil,json
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args();dest=Path(a.destination).resolve()
 assert not dest.exists() and dest.parent==H.parent,'require nonexistent sibling directory';dest.mkdir()
 for f in H.glob('*.py'):shutil.copy2(f,dest/f.name)
 shutil.copy2(H/'预登记.md',dest/'预登记.md')
 for name in ('setup.py','tests.py','gates.py','prepare.py','run.py','recheck.py','verify.py'):
  with (dest/(name+'.log')).open('x',encoding='utf-8') as log:subprocess.run([sys.executable,'-B','-X','utf8',str(dest/name)],cwd=H.parent,stdout=log,stderr=subprocess.STDOUT,check=True)
 for ref in (H/'execution').glob('*.json'):
  fresh=read(dest/'execution'/ref.name);gold=read(ref)
  for k in ('route','trace'):assert fresh['raw'][k]==gold['raw'][k],(ref,k)
 for ref in (H/'exact').glob('*/*.request.json'):
  path=ref.with_name(ref.name.replace('.request.json','.json'));fresh=read(dest/path.relative_to(H));gold=read(path)
  for k in ('status','length','route','start','base','targets','last'):assert fresh[k]==gold[k],(ref,k)
 print('Fresh raw-evidence replay complete; route/trace and exact witnesses match. Original seal unchanged; not new samples or approval.')
if __name__=='__main__':main()
