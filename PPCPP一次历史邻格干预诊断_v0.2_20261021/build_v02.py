"""Exclusive binary derivation; never alter v0.1 or frozen sources."""
from pathlib import Path
import hashlib,json,difflib
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP一次历史邻格干预诊断_v0.1_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020';S=R/'复杂障碍压力开发测试_v0.1_20261021'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,data):
    with p.open('xb') as f:f.write(data)
def save(p,x):put(p,json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
files=[]
def track(src,dst,kind,notes):files.append(dict(source=str(src),source_sha256=sha(src),target=str(dst),target_sha256=sha(dst),kind=kind,notes=notes))
expected=json.loads((S/'formal_seal.json').read_text(encoding='utf8'))
native=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
for src in (native,P/'runtime.py',P/'candidate.py'):assert sha(src)==expected[str(src)],src
for name in ('probe_common.py','probe_hook.py','decision_audit.py','analyze.py'):
    src=OLD/name;dst=H/name;put(dst,src.read_bytes());track(src,dst,'auxiliary_binary_copy','Previously untested auxiliary; must pass this version gates.')
src=P/'candidate.py';dst=H/'candidate.py';put(dst,src.read_bytes());assert dst.read_bytes()==src.read_bytes() and sha(dst)==expected[str(src)];track(src,dst,'required_exact_binary','Frozen original source, not v0.1 erroneous candidate.')
src=P/'runtime.py';dst=H/'runtime.py';raw=src.read_bytes();old="R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'".encode();new=("R/'"+H.name+"/native_probe.py'").encode();assert raw.count(old)==1;put(dst,raw.replace(old,new));track(src,dst,'intentional_diagnostic','Only native import path changed; original line endings retained.')
raw=native.read_bytes();eol=b'\r\n' if b'\r\n' in raw else b'\n'
def patch(old,new):
    global raw
    aa=old.replace('\n',eol.decode()).encode();bb=new.replace('\n',eol.decode()).encode();assert raw.count(aa)==1,old;raw=raw.replace(aa,bb)
patch('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parents[1]')
patch("VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'","VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'\nfrom probe_hook import force_history_step\nPROBE_ACTION=None\nPROBE_STAGE_HOOK=None")
patch('reason=None;accepted=None','reason=None;accepted=None;intervention=None')
patch('            while pending:',"            if PROBE_ACTION is not None:\n                intervention=dict(enabled=True,trigger_count=0)\n                force_history_step(s,previous,pending,route,trace,PROBE_ACTION,tick,deadline,intervention,PROBE_STAGE_HOOK)\n            while pending:")
patch('overrun_gt_10ms=seconds>budget+.01)',"overrun_gt_10ms=seconds>budget+.01,**({'intervention':intervention} if PROBE_ACTION is not None else {}))")
put(H/'native_probe.py',raw);track(native,H/'native_probe.py','intentional_diagnostic','Root relocation and once-only pre-loop hook/record; original while unchanged, original line endings retained.')
for folder in ('inputs','jobs','outputs','logs','receipts','fixtures'):(H/folder).mkdir()
CASES=('31x21_maze_p30','31x21_serpentine_p30');SEEDS=(20261020,20261021,20261022)
for case in CASES:
    src=S/'inputs'/f'{case}.json';dst=H/'inputs'/f'{case}.json';assert sha(src)==expected[str(src)];put(dst,src.read_bytes());track(src,dst,'required_exact_binary','Whole original input; no task/history/map change.')
for name in ('actions.json','fixed_order.json','equivalence_exclusions.json'):
    put(H/name,(OLD/name).read_bytes());track(OLD/name,H/name,'auxiliary_binary_copy','Unchanged actions, original24 order and seven explicit timing exclusions.')
for j in json.loads((H/'fixed_order.json').read_text(encoding='utf8')):save(H/'jobs'/f'{j["id"]}.json',j)
diff=''
for src,dst in ((native,H/'native_probe.py'),(P/'runtime.py',H/'runtime.py'),(P/'candidate.py',H/'candidate.py')):diff+=''.join(difflib.unified_diff(src.read_text(encoding='utf8').splitlines(True),dst.read_text(encoding='utf8').splitlines(True),fromfile=str(src),tofile=str(dst)))
put(H/'minimal.diff',diff.encode('utf8'));save(H/'copy_manifest.json',files)
save(H/'source_contract.json',{str(src):expected[str(src)] for src in (native,P/'runtime.py',P/'candidate.py',S/'inputs'/f'{CASES[0]}.json',S/'inputs'/f'{CASES[1]}.json')})
print('Built v0.2 using exclusive binary writes; exact frozen candidate and two inputs; no planner/stub calls.')
