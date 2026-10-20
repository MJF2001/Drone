"""Construct hierarchy only; no planner run or performance experiment."""
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
NEW=HERE.parent/'DeepSeek_底层算法开发比较_20261018'
sys.path.insert(0,str(NEW/'src'))
import bootstrap
from epsilon_core.maps import MAPS
rows=[]
for n in (4,8):
 free=frozenset((x,y) for x in range(n) for y in range(n))
 maps=MAPS(free,free,frozenset())
 rows.append({'grid':[n,n], 'max_depth':maps.max_depth,
   'fine_E0_cells':len(maps.E0),
   'tree_blocks_by_level':{level:[(b.width,b.height) for b in blocks]
                          for level,blocks in maps.nodes_by_level.items()},
   'coarse_potential_entries':{level:len(v) for level,v in maps.E.items() if level>0},
   'original_text_rule':'coarsest tiling has four cells; finest coarse layer retains 2x2 blocks on these square grids'})
(HERE/'epsilon_structure_probe.json').write_text(json.dumps({'planner_calls':0,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
