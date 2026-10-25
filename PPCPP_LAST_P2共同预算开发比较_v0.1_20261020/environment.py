"""Imports only, no planner invocation. Seal project runtime and related deps."""
import os,platform,ctypes,datetime
from support import *
import worker
def native_modules():
 ps=ctypes.WinDLL('psapi');kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p;handle=kernel.GetCurrentProcess();buf=(ctypes.c_void_p*2048)();needed=ctypes.c_ulong()
 ps.EnumProcessModules.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)];ps.GetModuleFileNameExW.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong]
 assert ps.EnumProcessModules(handle,buf,ctypes.sizeof(buf),ctypes.byref(needed));out=[]
 for mod in list(buf)[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
  text=ctypes.create_unicode_buffer(32768);ps.GetModuleFileNameExW(handle,mod,text,len(text));out.append(text.value)
 return sorted(set(out))
def verify():
 s=read(H/'environment_seal.json');assert s['complete']
 for p,h in s['files'].items():assert sha(p)==h,p
 return len(s['files'])
def main():
 assert not (H/'environment_seal.json').exists();paths=set();roots=[R/'运行环境/python',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012']
 for root in roots:
  paths.update(p.resolve() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
 paths.update(p.resolve() for p in H.glob('*.py'));paths.update(Path(p) for p in worker.imported() if Path(p).is_file())
 dlls=native_modules();windir=Path(os.environ.get('WINDIR','C:/Windows')).resolve()
 for p in dlls:
  q=Path(p)
  if q.is_file() and not q.is_relative_to(windir):paths.add(q)
 save(H/'environment_seal.json',dict(complete=True,created=datetime.datetime.now().astimezone().isoformat(),python=sys.version,executable=sys.executable,platform=platform.platform(),roots=list(map(str,roots)),threads={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},imports=worker.imported(),native_modules=dlls,files={str(p):sha(p) for p in sorted(paths)},limitations='System Windows DLLs are recorded by path, not frozen; this is project/runtime scope, not a full-machine image. Dynamically loaded libraries not exposed by this import discovery remain a limitation. No package upgrade/import-chain optimization.'))
 print('ENVIRONMENT SEALED',verify(),'files; ZERO planner calls',flush=True)
if __name__=='__main__':main()
