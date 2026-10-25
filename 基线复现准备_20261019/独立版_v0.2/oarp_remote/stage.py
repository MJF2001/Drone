"""Copy the previous implementation and preserve all previous evidence."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent
SOURCE=WORK/'OARP新版道路复验_短预算_20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (ROOT/'kernel.py').exists()
    for name in ('kernel.py','independent.py'):
        shutil.copyfile(SOURCE/name,ROOT/name)
    shutil.copytree(SOURCE/'sources',ROOT/'sources',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(SOURCE/'inputs',ROOT/'inputs')
    paths=[]
    for folder in ('OARP新版道路复验_短预算_20261018','OARP新版道路复验_汇报用_20261018','OARP原生参照修订_v0.2_20261018'):
        paths.extend(p for p in (WORK/folder).rglob('*') if p.is_file())
    paths.extend(p for p in (WORK/'DeepSeek_底层算法开发比较_20261018/runs').rglob('*.json') if p.is_file())
    protection={str(p):sha(p) for p in sorted(set(paths))}
    (ROOT/'protection.json').write_text(json.dumps(protection,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copyfile(SOURCE/'dependencies_before.json',ROOT/'dependencies_before.json')
    (ROOT/'sources_before.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'sources').rglob('*') if p.is_file()},ensure_ascii=False,indent=2),encoding='utf-8')
    print('STAGED; previous files protected:',len(protection),'planner calls: 0')
if __name__=='__main__':main()
