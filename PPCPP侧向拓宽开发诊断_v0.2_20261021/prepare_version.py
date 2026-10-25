"""Only authorized two dictionary repairs and binary provenance copies."""
from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP侧向拓宽开发诊断_v0.1_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data)
def save(p,x):put(p,json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
def main():
    old_manifest=json.loads((OLD/'completion_manifest.json').read_text(encoding='utf8'))['files']
    for name,h in old_manifest.items():assert sha(OLD/name)==h,('old evidence changed',name)
    sources=[];diff=''
    names=('common.py','visit_a.py','generate.py','stat_stubs.py','worker.py','seal.py','analysis.py','run.py','verify.py','bind.py','protocol.md','maps.json','prep_order.json')
    for name in names:
        src=OLD/name;dst=H/name;raw=src.read_bytes();patched=raw;kind='exact binary source copy'
        if name in ('analysis.py','verify.py'):
            for key in ('visits_A','pp_first_A_event'):
                old=(key+"=r['"+key+"']").encode();new=("'"+key+"':r['"+key+"']").encode();assert patched.count(old)==1,(name,key);patched=patched.replace(old,new)
            kind='authorized dictionary key/value syntax repair only'
        put(dst,patched);sources.append(dict(source=str(src),source_sha256=sha(src),target=str(dst),target_sha256=sha(dst),category=kind))
        if raw!=patched:diff+=''.join(difflib.unified_diff(raw.decode('utf8').splitlines(True),patched.decode('utf8').splitlines(True),fromfile=str(src),tofile=str(dst)))
    for folder in ('inputs','jobs'):
        for src in sorted((OLD/folder).glob('*.json')):
            dst=H/folder/src.name;put(dst,src.read_bytes());assert dst.read_bytes()==src.read_bytes();sources.append(dict(source=str(src),source_sha256=sha(src),target=str(dst),target_sha256=sha(dst),category='exact binary six initial inputs / unchanged prep job definitions'))
    expected=json.loads((OLD/'seal1.json').read_text(encoding='utf8'))['files']
    for name in ('runtime.py','candidate.py','p2_adapter.py'):
        src=P/name;assert sha(src)==expected[str(src)],src;dst=H/'frozen_source_bytes'/name;put(dst,src.read_bytes());assert sha(dst)==sha(src);sources.append(dict(source=str(src),source_sha256=sha(src),target=str(dst),target_sha256=sha(dst),category='exact binary frozen original reference'))
    for folder in ('preflight','receipts','outputs','logs','history','witnesses','figures'):(H/folder).mkdir()
    save(H/'source_manifest.json',sources);put(H/'v0.1_to_v0.2.diff',diff.encode('utf8'));save(H/'old_evidence_hashes.json',{str(OLD/name):h for name,h in old_manifest.items()})
    print('Applied only two authorized dictionary syntax repairs; binary copies verified; no old seals/PASS/STOP/results adopted; planner/core=0')
if __name__=='__main__':main()
