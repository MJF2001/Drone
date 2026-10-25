"""Pre-analysis provenance seal, no planner imports/calls."""
import sys,time
from tail_analysis import H,R,S,MD,sha,save
def seal():
    paths={p.resolve() for p in S.rglob('*') if p.is_file()}
    paths|={MD/'metrics.py',MD/'crosscheck.py',R/'复杂障碍末端返航差距只读归因执行稿_给sol_20261021.md',R/'AGENTS.md'}
    docs=R/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009'
    paths|={docs/'02_论文主题与具体研究问题.md',docs/'42_三种基线适配审查与冻结说明_20261012.md',R/'研究方案_剩余覆盖重规划_20261009/00_阅读入口.md'}
    save(H/'presources.json',{str(p):sha(p) for p in sorted(paths)})
    files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file()}
    save(H/'preseal.json',dict(stage='after_upstream_verify_before_new_analysis',created_utc=time.time(),files=files,python=sys.version,executable=sys.executable,executable_sha256=sha(sys.executable),note='Seals statistical rules/code, metric implementations by reference and full prior evidence. Later report/render/verify artifacts are covered by final manifest, not falsely predating analysis.'))
    print('PREANALYSIS SEALED',len(paths),'source files;',len(files),'new files',flush=True)
if __name__=='__main__':seal()
