"""Post-hoc two-case search-depth check, NOT a new equal-budget benchmark."""
import json,time
from pathlib import Path
from scenarios import deserialize
from unified_geometry import UnifiedGeometry
from planners import candidates,nearest,two_opt,sequence_cost
from audit import audit

D=Path(__file__).parent;O=D/'results'/'run_26_unified_new_maps'
selected=['unified_open_L35_W8_p70_straight','unified_corridor_L23_W6_p70_corner_obstacle']
snapshots=json.loads((O/'snapshots.json').read_text(encoding='utf-8'))
results=[]
for record in snapshots:
    s=deserialize(record['snapshot'])
    if s.name not in selected:continue
    for axis in ('H','V'):
        for seed_kind in ('scan','nearest'):
            for passes in (8,128):
                begin=time.perf_counter();g=UnifiedGeometry(s)
                points=candidates(g,s.targets-s.covered-g.views[s.current],axis)
                if seed_kind=='nearest':points=nearest(g,points)
                before=g.expand(points)
                improved=two_opt(g,points,max_passes=passes)
                route=g.expand(improved)
                results.append({'case':s.name,'axis':axis,'seed_kind':seed_kind,'max_passes':passes,
                    'before_steps':len(before)-1,'after_steps':len(route)-1,
                    'sequence_cost':sequence_cost(g,improved),'seconds':time.perf_counter()-begin,
                    'audit':audit(s,route)})
                print(results[-1],flush=True)
(O/'posthoc_depth_check.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
