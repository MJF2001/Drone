"""Byte-preserving v0.4 preparation; no planner imports."""
from pathlib import Path
import hashlib,json,difflib,ast
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP侧向拓宽开发诊断_v0.3_20261021'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def main():
    old= json.loads((OLD/'completion_manifest.json').read_text(encoding='utf8'))['files']
    for n,h in old.items():assert sha(OLD/n)==h,n
    rows=[]
    for n in ('common.py','visit_a.py','generate.py','stat_stubs.py','worker.py','run.py','analysis.py','verify.py','protocol.md','maps.json','prep_order.json'):
        src=OLD/n;target=H/n
        with target.open('xb') as f:f.write(src.read_bytes())
        rows.append(dict(source=str(src),source_sha256=sha(src),target=str(target),initial_sha256=sha(target),reason='unchanged v0.3 bytes'))
    for folder in ('inputs','jobs','frozen_source_bytes'):
        (H/folder).mkdir()
        for src in sorted((OLD/folder).glob('*')):
            if src.is_file():
                target=H/folder/src.name
                with target.open('xb') as f:f.write(src.read_bytes())
                rows.append(dict(source=str(src),source_sha256=sha(src),target=str(target),initial_sha256=sha(target),reason='unchanged initial/job/frozen reference'))
    for folder in ('preflight','receipts','outputs','logs','history','witnesses','figures','technical_rounds'):(H/folder).mkdir()
    save(H/'source_manifest_initial.json',rows);save(H/'old_v03_hashes.json',{str(OLD/n):h for n,h in old.items()})
    print('Prepared v0.4 independent active copies; no previous PASS/seal/results copied; no solve')
if __name__=='__main__':main()
