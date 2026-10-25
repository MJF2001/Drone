"""Discovery and complete project/runtime byte seal BEFORE gates."""
import os,platform,ctypes,datetime
from support import *
import worker,audit
def verify():
 s=read(H/'environment_seal.json');assert s['complete']
 for p,h in s['files'].items():assert sha(p)==h,p
 return len(s['files'])
def native_modules():
 ps=ctypes.WinDLL('psapi');kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p;handle=kernel.GetCurrentProcess();buf=(ctypes.c_void_p*2048)();needed=ctypes.c_ulong()
 ps.EnumProcessModules.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)];ps.GetModuleFileNameExW.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong]
 assert ps.EnumProcessModules(handle,buf,ctypes.sizeof(buf),ctypes.byref(needed));out=[]
 for mod in list(buf)[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
  b=ctypes.create_unicode_buffer(32768);ps.GetModuleFileNameExW(handle,mod,b,len(b));out.append(b.value)
 return sorted(set(out))
def main():
 paths=set();roots=[R/'运行环境/python',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012']
 for root in roots:paths.update(p.resolve() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
 for folder in (H,H/'inputs',H/'payloads'):paths.update(p.resolve() for p in folder.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md','.diff'))
 paths.update(Path(p) for p in worker.imports() if Path(p).is_file());paths.update(Path(p) for p in (audit.pa.__file__,audit.metric.__code__.co_filename,audit.cross.__code__.co_filename));paths.update(map(Path,read(H/'protocol.json')['sources']))
 dlls=native_modules();windir=Path(os.environ.get('WINDIR','C:/Windows'))
 paths.update(Path(p) for p in dlls if Path(p).is_file() and not Path(p).is_relative_to(windir))
 save(H/'environment_seal.json',dict(complete=True,created=datetime.datetime.now().astimezone().isoformat(),files={str(p):sha(p) for p in sorted(paths)},platform=platform.platform(),python=sys.version,executable=sys.executable,imports=worker.imports(),native_modules=dlls,threads=1,limitations='Project/runtime scope only; Windows system DLL paths recorded, not full-machine byte freeze; undiscovered dynamic libraries not certified. No upgrades or import optimization.'))
 print('ENVIRONMENT PRESEALED',verify(),'files, ZERO solver calls')
if __name__=='__main__':main()
