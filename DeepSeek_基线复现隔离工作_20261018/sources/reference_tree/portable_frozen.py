from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/"研究方案_剩余覆盖重规划_20261009"/"算法小型验证_20261010"
FROZEN=ALGO/"frozen_baselines"/"v2_20261012"
sys.path.insert(0,str(ALGO/".deps"))
sys.path.insert(0,str(FROZEN/"source"))
from baseline_suite import solve,METHODS
PROFILE=json.loads((FROZEN/"runtime_profile.json").read_text(encoding="utf-8"))
