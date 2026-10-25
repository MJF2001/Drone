"""Isolated diagnostic against the UNMODIFIED v0.2, not a graded solve."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'修正版_v0.2/runtime'))
from history_adapter import HistoryCStar
from history_core.planner import WallClockCap
from history_core.public_map import PublicMap
f={(0,0),(1,0),(0,1),(1,1)};m=PublicMap();m.update({p:True for p in f})
p=HistoryCStar((0,0),m,{(1,0),(1,1)},set())
def interrupt():
    if len(p.path)>1:raise WallClockCap('injected before second unit step')
p._check_deadline=interrupt
try:p.navigate([(0,0),(1,1)],'diagnostic_partial_edge')
except WallClockCap:pass
missed=set(p.path)&p.pending
assert missed=={(1,0)}
print(json.dumps(dict(diagnostic_only=True,source='unchanged v0.2',path=p.path,pending=sorted(p.pending),visited_but_not_credited=sorted(missed),task_events=p.task_events),ensure_ascii=False,indent=2))
