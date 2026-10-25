import json,hashlib,shutil,platform,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not (H/'protocol.json').exists();cases=[];files={}
 for batch,folder in [('main36','PPCPP结束位置跨几何验证_v0.1_20261020'),('supp24','PPCPP小图最优差距诊断_v0.2_20261020')]:
  for src in sorted((R/folder/'inputs').glob('*.json')):
   ident=batch+'__'+src.stem;dest=H/'inputs'/f'{ident}.json';dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
   cases.append(dict(id=ident,batch=batch,name=src.stem,input=str(dest.relative_to(R)),source=str(src.relative_to(R)),sha256=sha(src)))
   files[str(src.relative_to(R))]=sha(src);files[str(dest.relative_to(R))]=sha(dest)
 # Freeze existing runtime dependencies without making reference results available to solvers.
 old=json.loads((R/'PPCPP小图最优差距诊断_v0.2_20261020/protocol.json').read_text(encoding='utf-8'))
 for p in old['files']:
  if not p.startswith('PPCPP小图最优差距诊断_v0.2_20261020/') and not p.startswith('实验结论与PPCPP改进讨论_20261020/'):
   f=R/p;files[p]=sha(f)
 for p in [H/'预登记.md',R/'实验结论与PPCPP改进讨论_20261020/交给6.1sol_保留末采集格候选执行稿_v1_20261020.md']:files[str(p.relative_to(R))]=sha(p)
 protocol=dict(version='v0.1_20261020',cases=cases,files=files,rule='input nearest-to-base target, one reservation branch with F-e then restore F; strict shorter complete cost; no alternative e',budgets=dict(common_warm_entry=20,watchdog=90),formal=dict(methods=['PPCPP','LAST'],repetitions=[0,1,2],max_calls=360,order='for repetition then sorted inputs; method order alternates by input index+repetition'),gates=dict(development='60 inputs x PPCPP/ONE/LAST =180 fresh gate calls',fixtures=9,deadline_stages=['p0_done','candidate_distance','phase1','release','return','final_audit_before','final_audit_after','encode_before','encode_after']),environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform()),read_scope='Production imports only frozen source and local runtime; reads only local input. No exact/analysis/reference/result access; audit read paths recorded per process.')
 (H/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8');print('protocol/input list fixed',len(cases),sha(H/'protocol.json'))
if __name__=='__main__':main()
