"""One exclusive preparation of the pre-registered six development worlds."""
from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent;R=H.parent;S=R/'连续事件真实接口验收_v0.1_20261021'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def rect(x,y,w,h):return {(a,b) for a in range(x,x+w) for b in range(y,y+h)}
def points(x):return sorted(map(list,x))
def generate():
    worlds={};meta={}
    for shape in ('I','L','T'):
        for size,L,w in (('S',12,3),('M',24,4)):
            wid=shape+'_'+size;F=rect(0,0,3*L+8,2*L+8);P=rect(4,4,(2*L if shape=='T' else L),w)
            if shape!='I':P|=rect(4+L-w,4+w,w,L)
            A=rect(4+L//3,2,L//3,2);B=rect(4+2*L//3,4,2,1)
            worlds[wid]=dict(free=points(F),published=points(P),start=[1,1],base=[1,1],E0=10*len(F),T_max=10*len(F),events=[dict(tick=L//2,id='e1_add',add_targets=points(A),block=[]),dict(tick=2*L,id='e2_block',add_targets=[],block=points(B))])
            meta[wid]=dict(development=True,shape=shape,scale=size,L=L,w=w,area_F=len(F),initial_targets=len(P),added_targets=len(A),blocked_cells=len(B),fixed_template_not_independent_field_sample=True)
    return worlds,meta
def main():
    assert not (H/'config.json').exists()
    for n in ('inputs','jobs','outputs','logs','sessions','receipts','technical_rounds','frozen_source_bytes','figures'):(H/n).mkdir()
    old=json.loads((S/'completion_manifest.json').read_text(encoding='utf8'))['files']
    for n,v in old.items():assert sha(S/n)==v,('previous_manifest_drift',n)
    names=('executor.py','contracts.py','entry.py','worker.py','session.py','auditor.py','real_audit.py','reference_contract.py','seal.py')
    copies=[]
    for n in names:
        with (H/n).open('xb') as f:f.write((S/n).read_bytes())
        copies.append(dict(name=n,source=str(S/n),source_sha256=sha(S/n),target_sha256=sha(H/n),byte_identical=True))
    a=(S/'util.py').read_text(encoding='utf8');b=a.replace('real_entry_cap=18,entry_budget=20,watchdog=90,seed=20261021,threads=1,stub_cap_all_rounds=24,technical_round_cap=3','real_entry_cap=36,entry_budget=20,watchdog=90,seed=20261022,threads=1,stub_cap_all_rounds=12,technical_round_cap=2');assert a!=b
    (H/'util.py').write_text(b,encoding='utf8');(H/'binding_only.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(S/'util.py'),tofile=str(H/'util.py'))),encoding='utf8')
    copies.append(dict(name='util.py',source=str(S/'util.py'),source_sha256=sha(S/'util.py'),target_sha256=sha(H/'util.py'),byte_identical=False,reason='Only new batch cap/seed/technical caps in config assertion; all runtime semantics unchanged'))
    save(H/'copy_manifest.json',copies);save(H/'inherited_manifest_identity.json',dict(source=str(S/'completion_manifest.json'),sha256=sha(S/'completion_manifest.json'),files_readonly_checked=len(old),new_graph_searches=0,new_solver_calls=0))
    save(H/'source_lock.json',json.loads((S/'source_lock.json').read_text(encoding='utf8')))
    worlds,meta=generate();save(H/'worlds.json',worlds);save(H/'world_metadata.json',meta)
    order=[];slots=[]
    for i,wid in enumerate(worlds):
        methods=('PPCPP','P2_MULTI') if i%2==0 else ('P2_MULTI','PPCPP')
        for method in methods:
            sid=wid+'_'+method;order.append(dict(id=sid,world=wid,method=method,seed=20261022))
            for t in [0]+[e['tick'] for e in worlds[wid]['events']]:slots.append(dict(id=sid+f'_t{t:03d}',session=sid,method=method,tick=t,seed=20261022))
    assert len(slots)==36 and len(order)==12
    save(H/'session_order.json',order);save(H/'call_slots.json',slots);save(H/'config.json',dict(real_entry_cap=36,entry_budget=20,watchdog=90,seed=20261022,threads=1,stub_cap_all_rounds=12,technical_round_cap=2))
    with (H/'执行稿.md').open('xb') as f:f.write((R/'连续事件六世界固定开发比较执行稿_给sol_20261022.md').read_bytes())
    with (H/'继承计时与接线合同.md').open('xb') as f:f.write((S/'计时与接线合同.md').read_bytes())
    (H/'只读核验.ps1').write_text("$ErrorActionPreference = 'Stop'\n& (Join-Path $PSScriptRoot '..\\运行环境\\python\\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')\nif ($LASTEXITCODE -ne 0) { throw '只读核验失败' }\n",encoding='utf8')
    save(H/'binding_files.json',sorted([p.name for p in H.iterdir() if p.is_file() and not p.name.endswith('_execution.log')]+['binding_files.json']))
    print('Prepared fixed I/L/T x S/M;12 sessions;36 slots; no algorithm/fixture callbacks',flush=True)
if __name__=='__main__':main()
