"""I/O and zero-execution guard only. Never import a source-package module."""
from pathlib import Path
import json,hashlib,sys,os
H=Path(__file__).resolve().parent;R=H.parent;S=R/'连续事件六世界开发比较_v0.1_20261022'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def put(p,b):
    with Path(p).open('xb') as f:f.write(b)
def ps(x):return set(map(tuple,x))
def ls(x):return sorted(map(list,x))
def require_sources():
    index=read(H/'source_hashes.json')
    for p,v in index['files'].items():assert sha(p)==v,('source_drift',p)
    return index
def install_guard():
    violations=[];forbidden_names={'runtime','candidate','worker','session','executor','auditor','real_audit','p2_adapter','p2_search_audit','ppcpp_independent','last_native','model','planners','baseline_suite','unified_geometry','bfs_metric_geometry','heapq','_heapq'}
    forbidden_files=set(read(H/'source_hashes.json')['files'])
    class Block:
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden_names:violations.append(fullname);raise AssertionError('forbidden algorithm/graph module import: '+fullname)
    sys.meta_path.insert(0,Block())
    def profile(frame,event,arg):
        if event=='call':
            fn=frame.f_code.co_filename
            if fn in forbidden_files or fn.startswith(str(S)):
                violations.append(fn);raise AssertionError('source module execution forbidden: '+fn)
            if frame.f_code.co_name in ('solve','run_payload','run_world','invoke','reach','walk_component','p2_solve','core_route','precheck'):
                violations.append(frame.f_code.co_name);raise AssertionError('planner/graph call forbidden')
    sys.setprofile(profile)
    def audit(event,args):
        if event in ('subprocess.Popen','os.system','socket.connect'):violations.append(event);raise AssertionError('external execution forbidden')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2] if len(args)>2 else 0
            writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR)))
            if writing:assert H==p.parent or H in p.parents or p==R/'当前进度与下一步.md',('forbidden_write',p)
    sys.addaudithook(audit);return violations
def zeros(stage,violations):
    assert not violations
    return dict(stage=stage,planning_entries=0,native_core=0,candidates=0,coverage_exact=0,BFS=0,Dijkstra=0,Astar=0,counterfactual_routes=0,new_worlds=0,new_routes=0,new_stub_responses=0,new_simulation_closed_loops=0,source_modules_imported=0,guard_violations=[])
