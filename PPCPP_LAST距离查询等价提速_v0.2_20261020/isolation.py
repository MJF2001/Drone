"""Select the absolute candidate module BEFORE unchanged warm entry timing."""
import sys,importlib.util,hashlib
from pathlib import Path
import runtime
H=Path(__file__).resolve().parent
def select(method):
 assert method in ('PPCPP','LAST_V1','LAST_V2')
 path=H/('candidate_v2.py' if method=='LAST_V2' else 'candidate_v1.py')
 name='_isolated_last_v2' if method=='LAST_V2' else '_isolated_last_v1'
 if name not in sys.modules:
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sys.modules[name]=m
 sys.modules['candidate']=sys.modules[name]
 assert Path(sys.modules['candidate'].__file__).resolve()==path
 return sys.modules[name]
def run(payload,method,**kwargs):
 select(method)
 return runtime.run_payload(payload,'PPCPP' if method=='PPCPP' else 'LAST',**kwargs)
def sources(method):
 m=select(method)
 paths={Path(runtime.__file__),Path(m.__file__),Path(__file__),H/'worker.py',Path(runtime.native.__file__),Path(runtime.native.core.__file__),Path(runtime.validate.__code__.co_filename),Path(runtime.native.check_contract.__code__.co_filename),Path(runtime.native.single_cell_audit.__code__.co_filename)}
 for name in ('model','bfs_metric_geometry','unified_geometry','portable_frozen','baseline_suite','ppcpp_independent'):
  paths.add(Path(sys.modules[name].__file__))
 for cls in runtime.native.UnifiedGeometry.__mro__:
  mod=sys.modules.get(cls.__module__)
  if mod and getattr(mod,'__file__',None):paths.add(Path(mod.__file__))
 return {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
