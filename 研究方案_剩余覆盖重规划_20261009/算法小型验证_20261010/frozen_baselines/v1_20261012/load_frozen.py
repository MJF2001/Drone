from pathlib import Path
import sys
ROOT=Path(__file__).parent
sys.path.insert(0,'D:\\0A无人机仿真02\\问题分析+文献分析\\研究方案_剩余覆盖重规划_20261009\\算法小型验证_20261010\\.deps')
sys.path.insert(0,str(ROOT/'source'))
from baseline_suite import solve, METHODS
