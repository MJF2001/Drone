import sys,json
from pathlib import Path
REF=Path(r"D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018\sources\reference_tree")
ALGO=REF/"研究方案_剩余覆盖重规划_20261009"/"算法小型验证_20261010"
sys.path.insert(0,str(REF))
sys.path.insert(0,str(ALGO))
sys.path.insert(0,str(ALGO/".deps"))
import portable_frozen
print("FROZEN",portable_frozen.FROZEN)
print("METHODS",portable_frozen.METHODS)
print("solve from",portable_frozen.solve.__code__.co_filename)
import numpy,pyscipopt,glns
print("numpy",numpy.__version__,numpy.__file__)
print("pyscipopt",pyscipopt.__file__)
print("glns",glns.__file__, getattr(glns,"__version__",None))
