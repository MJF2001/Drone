"""Predeclared new parameter cases; all initial scans H to avoid stage-axis confound."""
from dataclasses import replace
import random
from model import Snapshot
from unified_geometry import UnifiedGeometry
from scenarios import rectangle,flight_domain
from scenarios_v2 import checkpoint
from audit import audit,environment_check


def cases():
    for length,width in ((23,6),(35,8)):
        for kind in ('open','corridor'):
            for phase,progress in enumerate((.35,.70)):
                seed=261011+length*100+width*10+phase+(10000 if kind=='corridor' else 0)
                rng=random.Random(seed)
                extension=rng.choice((7,10,13))
                old=rectangle(3,3,length,width)
                straight=rectangle(length+3,3,extension,width)
                corner=rectangle(length+3,3,width,width)|rectangle(length+3,width+3,width,extension)
                envelope=old|straight|corner
                domain=(rectangle(0,0,max(x for x,y in envelope)+4,max(y for x,y in envelope)+4)
                        if kind=='open' else flight_domain(envelope,1)|{(1,3),(2,3)})
                initial=Snapshot('initial',frozenset(domain),frozenset(old),frozenset(),(1,3),(1,3),(),0,4*len(domain))
                points=sorted(old,key=lambda p:(p[1],p[0] if (p[1]-3)%2==0 else -p[0]))
                route=UnifiedGeometry(initial).expand(points)
                assert audit(initial,route)['valid']
                state,prefix=checkpoint(initial,route,progress)
                eligible=sorted(set(state.old_route)&old-{state.current,state.base})
                rng.shuffle(eligible)
                blocked=None
                for x,y in eligible:
                    patch=rectangle(x,y,2,2)&domain
                    if not patch&{state.current,state.base}:
                        trial=replace(state,free=frozenset(domain-patch),targets=frozenset(old-((old-state.covered)&patch)))
                        if environment_check(trial) is None:
                            blocked=patch;break
                assert blocked is not None
                for family in ('straight','obstacle','corner_obstacle'):
                    published=old|(straight if family=='straight' else corner if family=='corner_obstacle' else set())
                    obstacles=set() if family=='straight' else blocked
                    deferred=(published-state.covered)&obstacles
                    s=replace(state,name=f'unified_{kind}_L{length}_W{width}_p{int(100*progress)}_{family}',
                        free=frozenset(domain-obstacles),targets=frozenset(published-deferred))
                    assert environment_check(s) is None
                    yield s,{'family':family,'domain_kind':kind,'length':length,'width':width,'seed':seed,
                        'extension':extension,'requested_progress':progress,'actual_progress':len(state.covered)/len(old),
                        'initial_targets':sorted(old),'published_targets':sorted(published),
                        'obstacles':sorted(obstacles),'deferred_targets':sorted(deferred),'domain':sorted(domain),
                        'prefix':prefix,'initial_policy':'raw_H_scan_canonical_connectors','flight_domain_fixed':True,
                        'scope':'new parameters within existing shape family; related states share initial history'}
