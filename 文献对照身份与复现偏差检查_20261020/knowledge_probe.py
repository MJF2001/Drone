"""Isolate a knowledge predicate on ONE identical graph; not a solver repair."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'Cstar状态缓存验收_20261019/runtime'))
from history_core.public_map import PublicMap
from history_adapter import HistoryCStar
c=json.loads((HERE/'micro/inputs/padding_2.json').read_text(encoding='utf-8'))
f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']))
known=PublicMap();known.update({p:True for p in f})
planner=HistoryCStar(tuple(c['current']),known,t,h,seed=20261018)
planner.graph.prune(planner.current);goal,route,retreat,why=planner.select_goal();planner.graph.update_state(planner.current,goal)
snapshot=planner.graph.snapshot();normal=planner.detect_holes(goal)
original=known.unknown_adjacent
try:
    known.unknown_adjacent=lambda p:False
    domain_closed_probe=planner.detect_holes(goal)
finally:known.unknown_adjacent=original
assert snapshot==planner.graph.snapshot()
assert not normal and domain_closed_probe
result=dict(scope='predicate-only counterfactual, identical graph and chosen goal, no TSP or navigation executed',new_solver_calls=0,current=planner.current,goal=goal,normal_holes=sorted(normal),domain_closed_probe_holes=sorted(domain_closed_probe),graph_unchanged=True,warning='does not establish a complete valid repair or improved road result',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(HERE/'knowledge_predicate_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(len(normal),len(domain_closed_probe))
