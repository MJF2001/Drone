"""Verify the complete saved source package by hash, never run its verifier."""
from common import *
import datetime
def main():
    assert not (H/'source_hashes.json').exists();files={};manifest=read(S/'completion_manifest.json')
    for n,v in manifest['files'].items():assert sha(S/n)==v,('source_manifest_conflict',n);files[str(S/n)]=v
    files[str(S/'completion_manifest.json')]=sha(S/'completion_manifest.json');final=read(S/'final_verification_receipt.json');assert final['manifest_sha256']==files[str(S/'completion_manifest.json')];files[str(S/'final_verification_receipt.json')]=sha(S/'final_verification_receipt.json')
    seal=read(S/'seal.json');paths=[R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/runtime.py',R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/candidate.py',R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/p2_adapter.py']
    frozen=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'
    paths += [frozen/n for n in ('p2_search_audit.py','baseline_suite.py','planners.py','model.py')]
    (H/'readonly_source_text').mkdir();source_rows=[]
    for i,p in enumerate(paths):
        key=str(p.resolve());assert seal['files'][key]==sha(p);files[key]=sha(p);copy_name=f'{i:02d}_'+p.name;put(H/'readonly_source_text'/copy_name,p.read_bytes());source_rows.append(dict(source=key,copy=copy_name,sha256=files[key],read_as_text_only=True))
    save(H/'source_hashes.json',dict(files=files,source_package=str(S),source_manifest_files=len(manifest['files']),source_manifest_sha256=sha(S/'completion_manifest.json'),frozen_source_text=source_rows,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),old_verify_executed=False,graph_searches=0))
    put(H/'执行稿.md',(R/'连续事件实际成本位置只读诊断执行稿_给sol_20261022.md').read_bytes());print('PASS source hash gate',len(files),'sources; no old verifier or algorithm executed',flush=True)
if __name__=='__main__':main()
