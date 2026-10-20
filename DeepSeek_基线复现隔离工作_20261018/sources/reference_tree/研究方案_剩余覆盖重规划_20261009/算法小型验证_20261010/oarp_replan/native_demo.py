"""Native OARP rank IDs, obstacle at a service boundary, two core models.

Unit-step transitions; not the paper's robot-dynamics experiment.
"""
from dataclasses import replace
import json
from pathlib import Path
from model import Snapshot,Geometry
from audit import audit
from .ranks import rank_replan
from .tour import OldService,path_sets,tour_replan


def run():
    cells = frozenset((x,y) for x in range(7) for y in range(5))
    seed = Snapshot('native-initial',cells,cells,frozenset(),(0,0),(0,0),(),radius=0)
    initial_ranks = rank_replan(cells,variant=0)['ranks']
    blocks = path_sets(initial_ranks,(),(),cells)
    initial = tour_replan(Geometry(seed),blocks,seconds=1,seed=999)
    g = Geometry(seed)
    path,services = [seed.current],[]
    for state in initial['order'][1:-1]:
        segment = initial['states'][state]
        path.extend(g.path(path[-1],segment[0])[1:])
        start = len(path)-1
        path.extend(segment[1:])
        rank = initial_ranks[state//2]
        services.append(OldService(rank,start,len(path)-1))
    path.extend(g.path(path[-1],seed.base)[1:])
    assert tuple(path)==initial['route'] and audit(seed,tuple(path))['valid']
    cut = services[0].end_index
    covered = frozenset(path[:cut+1]) & cells
    remaining_services = tuple(OldService(s.rank,s.start_index-cut,s.end_index-cut)
        for s in services if not set(s.rank.cells) & covered)
    assert set(p for s in remaining_services for p in s.rank.cells)==cells-covered
    blocked = {(3,2)}
    assert not blocked & covered
    s = replace(seed,name='native-obstacle',free=cells-blocked,targets=cells-blocked,
        covered=covered,current=path[cut],old_route=tuple(path[cut:]))
    outcomes = []
    for variant in (1,2):
        for cap in (0,1,2,6,20):
            rank = rank_replan(s.targets-covered,tuple(r.rank for r in remaining_services),cap,variant)
            row = {'variant':variant,'cap':cap,'rank_result':{k:v for k,v in rank.items() if k!='ranks'}}
            if rank['ranks'] is not None:
                blocks = path_sets(rank['ranks'],remaining_services,s.old_route,s.free)
                tour = tour_replan(Geometry(s),blocks,seconds=1,seed=999)
                row.update({'route':tour['route'],'length':tour['length'],
                    'ranks':[{'axis':r.axis,'cells':r.cells} for r in rank['ranks']],
                    'audit':audit(s,tour['route']),'blocks':blocks})
                assert row['audit']['valid']
            outcomes.append(row)
    result = {'kind':'native rank initialization and identity; unit-step transition adaptation',
        'initial_rank_count':len(initial_ranks),'initial_route':initial['route'],
        'current':s.current,'covered':sorted(covered),'blocked':sorted(blocked),
        'old_remaining_ranks':[{'axis':r.rank.axis,'cells':r.rank.cells} for r in remaining_services],
        'outcomes':outcomes}
    destination = Path(__file__).parent/'native_core_example.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print([(r['variant'],r['cap'],r['rank_result']['status'],r.get('length')) for r in outcomes])


if __name__=='__main__':
    run()
