"""Authorized guard-only relocation, explicit technical gates and reader robustness."""
from pathlib import Path
import json,hashlib,ast,difflib
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP侧向拓宽开发诊断_v0.2_20261021'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def main():
    for name,h in json.loads((OLD/'completion_manifest.json').read_text(encoding='utf8'))['files'].items():assert sha(OLD/name)==h,name
    sources=[];diff='';comparison=None
    for name in ('common.py','visit_a.py','generate.py','stat_stubs.py','worker.py','seal.py','analysis.py','run.py','verify.py','protocol.md','maps.json','prep_order.json'):
        src=OLD/name;raw=src.read_bytes();txt=raw.decode('utf8').replace('\r\n','\n');new=txt;reason='unchanged binary v0.2 source'
        if name=='worker.py':
            split=txt.index('assert Path(runtime.__file__).resolve()');prefix=txt[:split];body=txt[split:];new=prefix+'def main():\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(True))+"\nif __name__=='__main__':main()\n"
            oldbody=ast.parse(txt).body[len(ast.parse(prefix).body):];mainnode=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef) and n.name=='main');assert ast.dump(ast.Module(body=oldbody,type_ignores=[]))==ast.dump(ast.Module(body=mainnode.body,type_ignores=[]))
            guard_proposal_hash=hashlib.sha256(new.encode()).hexdigest();assert guard_proposal_hash==json.loads((OLD/'worker_guard_proposal.json').read_text(encoding='utf8'))['proposed_normalized_text_sha256']
            needle="    j=read(sys.argv[1]);seal=";assert new.count(needle)==1;new=new.replace(needle,"    require('technical')\n"+needle);reason='exact reviewed main guard plus one explicit technical PASS requirement'
            comparison=dict(guard_matches_reviewed_proposal=True,proposal_text_sha256=guard_proposal_hash,old_body_AST_equal_before_gate=True,added_gate="require('technical')",gate_location='after explicit inventory branch, before job loading/algorithm')
        elif name=='run.py':new=new.replace('def run(phase):\n','def run(phase):\n    require(\'technical\')\n');reason='one fail-closed technical PASS check before original stage checks'
        elif name=='seal.py':new=new.replace('def run(stage):\n','def run(stage):\n    require(\'technical\')\n');reason='one fail-closed technical PASS check before new production seal'
        elif name=='verify.py':new=new.replace('def csvcheck(name,rows):\n','def csvcheck(name,rows):\n    csv.field_size_limit(max(131072,(H/name).stat().st_size))\n');reason='authorized read-side CSV size bound; no CSV encoding/value changes'
        if new!=txt:
            eol=b'\r\n' if b'\r\n' in raw else b'\n';result=new.replace('\n',eol.decode()).encode('utf8')
            diff+=''.join(difflib.unified_diff(txt.splitlines(True),new.splitlines(True),fromfile='v0.2/'+name,tofile='v0.3/'+name))
        else:result=raw
        put(H/name,result);sources.append(dict(source=str(src),source_sha256=sha(src),target=str(H/name),target_sha256=sha(H/name),reason=reason))
    for folder in ('inputs','jobs','frozen_source_bytes'):
        for src in sorted((OLD/folder).glob('*')):
            if src.is_file():dst=H/folder/src.name;put(dst,src.read_bytes());assert dst.read_bytes()==src.read_bytes();sources.append(dict(source=str(src),source_sha256=sha(src),target=str(dst),target_sha256=sha(dst),reason='binary unchanged reference or six initial/prep metadata'))
    for folder in ('preflight','receipts','outputs','logs','history','witnesses','figures'):(H/folder).mkdir()
    put(H/'v0.2_to_v0.3.diff',diff.encode('utf8'));save(H/'source_manifest.json',sources);save(H/'worker_structure_check.json',comparison);save(H/'old_v02_hashes.json',{str(OLD/name):h for name,h in json.loads((OLD/'completion_manifest.json').read_text(encoding='utf8'))['files'].items()})
    print('Prepared guard-only worker + explicit technical gates + CSV reader limit; no old PASS/seal copied; no solve calls')
if __name__=='__main__':main()
