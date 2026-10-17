"""Predeclared structural stress templates; no performance-dependent filtering."""
from dataclasses import replace
import random
from model import Snapshot,Geometry
from scenarios import rectangle,flight_domain
from scenarios_v2 import checkpoint
from planners import components
from audit import environment_check


def templates():
    taper={(x,y) for x,w in enumerate((2,2,3,3,2,2),1) for y in range(1,w+1)}
    yield 'width_change',taper,rectangle(7,1,2,2),rectangle(7,2,2,3)
    elbow=rectangle(1,1,4,2)|rectangle(3,3,2,3)
    yield 'elbow',elbow,rectangle(3,6,2,2),rectangle(5,4,3,2)
    offset=rectangle(1,1,3,2)|rectangle(3,3,2,2)|rectangle(5,3,2,2)
    yield 'offset',offset,rectangle(7,3,2,2),rectangle(7,4,2,3)


def cases():
    group=0
    for shape,old,straight,corner in templates():
        assert not old&straight and not old&corner
        for kind in ('open','corridor'):
            envelope=old|straight|corner
            domain=(rectangle(0,0,max(x for x,y in envelope)+2,max(y for x,y in envelope)+2)
                if kind=='open' else flight_domain(envelope,1))
            base=(0,1)
            initial=Snapshot('stress_initial',frozenset(domain),frozenset(old),frozenset(),base,base,(),0,4*len(domain))
            for orientation in ('H','V'):
                visits=sorted(old,key=(lambda p:(p[1],p[0] if p[1]%2 else -p[0])) if orientation=='H' else
                    (lambda p:(p[0],p[1] if p[0]%2 else -p[1])))
                route=Geometry(initial).expand(visits)
                for progress in (.6,.8):
                    state,prefix=checkpoint(initial,route,progress)
                    rng=random.Random(20261011+group)
                    remaining=old-set(state.covered)
                    columns=sorted({x for x,y in remaining if x!=state.current[0]})
                    if not columns:
                        columns=sorted({x for x,y in old if x!=state.current[0]})
                    x=rng.choice(columns)
                    wall={p for p in old if p[0]==x}
                    extra=sorted(old-wall-{state.current,base})
                    wall.add(rng.choice(extra))
                    assert state.current not in wall and base not in wall
                    for family in ('straight','corner','obstacle','corner_obstacle'):
                        published=old|(straight if family=='straight' else corner if family in ('corner','corner_obstacle') else set())
                        blocked=wall if family in ('obstacle','corner_obstacle') else set()
                        deferred=(published-set(state.covered))&blocked
                        s=replace(state,name=f'stress_{shape}_{kind}_{orientation}_p{int(progress*100)}_{family}',
                            free=frozenset(domain-blocked),targets=frozenset(published-deferred))
                        assert len(s.targets-s.covered)<=12
                        reason=environment_check(s)
                        # No outcome-driven rejection or resampling, including infeasibility.
                        yield s,{'shape':shape,'family':family,'domain_kind':kind,'orientation':orientation,
                            'requested_progress':progress,'seed':20261011+group,'history_group':group,
                            'initial_targets':sorted(old),'published_targets':sorted(published),
                            'deferred_targets':sorted(deferred),'obstacles':sorted(blocked),'domain':sorted(domain),
                            'prefix':prefix,'initial_policy':'raw_H_or_V_scan',
                            'remaining_target_components':len(components(s.targets-s.covered)),
                            'environment_reason':reason,'flight_domain_fixed':True,
                            'scope':'purposeful small structural stress, not random field distribution'}
                    group+=1
