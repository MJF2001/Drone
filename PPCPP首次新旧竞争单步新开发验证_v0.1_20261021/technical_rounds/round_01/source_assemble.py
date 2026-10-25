"""One-time exclusive construction; no solver calls or imports."""
from pathlib import Path
import json,hashlib,difflib,ast
H=Path(__file__).resolve().parent;R=H.parent
D=R/'PPCPP首次新旧竞争单步干预诊断_v0.1_20261021'
B=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021'
P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,b):
    with p.open('xb') as f:f.write(b)
def js(p,x):put(p,json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
def main():
    old=json.loads((D/'completion_manifest.json').read_text(encoding='utf8'))['files']
    for n in ('runtime.py','candidate.py','native_diag.py','intervention.py','decision_audit.py','reference_contract.py','technical.py','analyze.py','common.py'):
        assert sha(D/n)==old[n],n
    for folder in ('inputs','jobs','outputs','logs','receipts','history','witnesses','figures','technical_rounds','frozen_source_bytes'):(H/folder).mkdir()
    rows=[]
    for n in ('runtime.py','candidate.py','native_diag.py','intervention.py','decision_audit.py','reference_contract.py'):
        put(H/n,(D/n).read_bytes());rows.append(dict(source=str(D/n),source_sha256=sha(D/n),target=n,target_sha256=sha(H/n),byte_identical=True))
    put(H/'technical_helpers.py',(D/'technical.py').read_bytes())
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(H/'frozen_source_bytes'/n,(P/n).read_bytes())
    common=(D/'common.py').read_text(encoding='utf8')
    common=common.replace("LABEL='PPCPP_FIRST_NEW_STEP_DIAG_v0.1'", "D=R/'PPCPP首次新旧竞争单步干预诊断_v0.1_20261021'\nLABEL='PPCPP_FIRST_NEW_STEP_DIAG_v0.1'")
    start=common.index('def preseal():');end=common.index('EQUIVALENCE_EXCLUSIONS=')
    common=common[:start]+'''def check_seal(name):
    require(name);s=read(H/(name+'.json'));assert s['complete'] and s['binding']==binding()
    for p,h in s['critical'].items():assert sha(p)==h,p
    return s
def plan():
    p=read(H/'plan.json')
    if H.name!='SYNTHETIC_NOT_EXPERIMENT':assert p==dict(counts=dict(prep=6,gate=96,formal=288),entry_cap=390,entry_budget=20,watchdog=90,threads=1,expected_triggered_states=24,expected_protection_states=24)
    else:assert read(H/'SYNTHETIC_NOT_EXPERIMENT.json')['synthetic_only']
    return p
''' + common[end:]
    geo=(B/'common.py').read_text(encoding='utf8');common+='\n'+geo[geo.index('def rect('):geo.index('def binding(')]
    common+='\nnormal=norm\ndual=both\nCONDS=(\'CONTROL\',\'H_SIDE\',\'MIXED_SIDE\',\'U_SIDE\')\nSEEDS=(20261020,20261021,20261022)\n'
    put(H/'common.py',common.encode('utf8'))
    gen=(B/'generate.py').read_text(encoding='utf8')
    gen=gen.replace("    for folder in ('inputs','jobs','outputs','logs','receipts','history','witnesses','figures'):(H/folder).mkdir()", "    assert not (H/'maps.json').exists()")
    gen=gen.replace('(18,30,42) for w in (3,5)','(24,36,48) for w in (4,6)')
    gen=gen.replace("method='PPCPP',seed=20261021", "method='PPCPP',mode='FROZEN',state=gid,seed=20261021")
    start=gen.index('    gates=[s for s in states');end=gen.index('    for j in gate+formal:')
    gen=gen[:start]+'''    assert [(m['L'],m['w']) for m in read(H/'maps.json')]==[(l,w) for l in (24,36,48) for w in (4,6)]
    gate=[];formal=[]
    for s in states:
        for mode in ('FROZEN','OFF'):gate.append(dict(id=f'gate_{s["id"]}_{mode}',phase='gate',case=s['id'],state=s['id'],input=s['input'],method='PPCPP',mode=mode,seed=20261020,budget=20,seal='seal2.json'))
        for rep,seed in enumerate(SEEDS):
            for mode in (('OFF','ON') if (s['index']+rep)%2==0 else ('ON','OFF')):formal.append(dict(id=f'formal_{s["id"]}_{seed}_{mode}',phase='formal',case=s['id'],state=s['id'],input=s['input'],method='PPCPP',mode=mode,seed=seed,budget=20,seal='seal2.json'))
    assert len(gate)==96 and len(formal)==288
''' + gen[end:]
    gen=gen.replace("save(H/'gate_order.json',gate);", "save(H/'states_metadata.json',states);save(H/'gate_order.json',gate);")
    put(H/'generate.py',gen.encode('utf8'))
    tree=ast.parse((B/'verify.py').read_text(encoding='utf8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
    start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='maps' for t in n.targets));end=next(i for i in range(start,len(fn.body)) if isinstance(fn.body[i],ast.Expr) and isinstance(fn.body[i].value,ast.Call) and isinstance(fn.body[i].value.func,ast.Name) and fn.body[i].value.func.id=='print')
    put(H/'independent_input_block.py.txt',ast.unparse(ast.Module(body=fn.body[start:end],type_ignores=[])).encode('utf8'))
    ana=(D/'analyze.py').read_text(encoding='utf8').replace('from decision_audit import job_row,paired_audit','from evaluation import job_row\nfrom decision_audit import paired_audit')
    ana=ana.replace("max=max(tt) if tt else None,note='OFF gate precedes ON phase; descriptive timing only, no fair speed ranking claim'", "P95=percentile(tt,.95),max=max(tt) if tt else None,note='Fixed interleaved formal OFF/ON; same-batch descriptive comparison'")
    ana=ana.replace("KEYS=('length'", "def percentile(xs,p):\n    if not xs:return None\n    a=sorted(xs);v=(len(a)-1)*p;i=int(v);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(v-i)\n\nKEYS=('overlap_ratio','length'")
    put(H/'analyze.py',ana.encode('utf8'))
    # Report drawing is the old saved-route renderer only, with new fixed cases.
    dt=(D/'deliver.py').read_text(encoding='utf8');put(H/'drawing.py',(dt[:dt.index('def main():')]).encode('utf8'))
    js(H/'copy_manifest.json',rows)
    diff=''.join(''.join(difflib.unified_diff((D/n).read_text(encoding='utf8').splitlines(True),(H/n).read_text(encoding='utf8').splitlines(True),fromfile=str(D/n),tofile=str(H/n))) for n in ('common.py','analyze.py'))
    put(H/'binding_and_reporting.diff',diff.encode('utf8'));put(H/'algorithm.diff',b'')
    js(H/'plan.json',dict(counts=dict(prep=6,gate=96,formal=288),entry_cap=390,entry_budget=20,watchdog=90,threads=1,expected_triggered_states=24,expected_protection_states=24))
    js(H/'stage_dependencies.json',dict(technical=[],seal1=['technical','action_stubs'],prep=['seal1'],generated=['prep'],inputs_audited=['generated'],seal2=['inputs_audited'],gate=['seal2'],formal=['gate']))
    put(H/'protocol.md',(R/'PPCPP首次新旧竞争单步新开发验证执行稿_给sol_20261021.md').read_bytes())
    js(H/'order_rule.json',dict(matrix=[[l,w] for l in (24,36,48) for w in (4,6)],old_matrix=[[l,w] for l in (18,30,42) for w in (3,5)],boundary=['L/2','2L/3'],condition_order=['CONTROL','H_SIDE','MIXED_SIDE','U_SIDE'],seeds=[20261020,20261021,20261022],first_mode='OFF if (state_index+repeat_index)%2==0 else ON',gate=['FROZEN','OFF'],prep_seed=20261021))
    put(H/'只读核验.ps1',("$ErrorActionPreference='Stop'\n& (Join-Path $PSScriptRoot '..\\运行环境\\python\\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n").encode('utf-8-sig'))
    print('Byte-frozen implementation copied; generation code fixed before any new input/entry')
if __name__=='__main__':main()
