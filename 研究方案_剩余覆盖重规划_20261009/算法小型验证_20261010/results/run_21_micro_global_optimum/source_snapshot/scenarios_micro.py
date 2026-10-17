"""Small event snapshots; frozen geometry limits exact pending targets to 12."""
from dataclasses import replace
from model import Snapshot,Geometry
from scenarios import rectangle,flight_domain
from scenarios_v2 import checkpoint
from audit import environment_check


def cases():
    for length,width in ((4,2),(6,2),(4,3)):
        old=rectangle(1,1,length,width)
        straight=rectangle(length+1,1,2,width)
        corner=rectangle(length+1,width,2,1)|rectangle(length+1,width+1,2,2)
        envelope=old|straight|corner
        for kind in ('open','corridor'):
            domain=(rectangle(0,0,length+4,width+4) if kind=='open' else flight_domain(envelope,1))
            base=(0,1)
            initial=Snapshot('micro_initial',frozenset(domain),frozenset(old),frozenset(),base,base,(),0,4*len(domain))
            visits=sorted(old,key=lambda p:(p[1],p[0] if (p[1]-1)%2==0 else -p[0]))
            route=Geometry(initial).expand(visits)
            for progress in (.5,.75):
                state,prefix=checkpoint(initial,route,progress)
                for family in ('no_change','straight','obstacle','corner_obstacle'):
                    published=old|(straight if family=='straight' else corner if family=='corner_obstacle' else set())
                    blocked=set()
                    if family in ('obstacle','corner_obstacle'):
                        candidates=[p for p in state.old_route[1:] if p in old and p not in (state.current,base)]
                        if candidates:
                            blocked={candidates[len(candidates)//3]}
                    deferred=(published-set(state.covered))&blocked
                    s=replace(state,name=f'micro_{kind}_L{length}_W{width}_p{int(progress*100)}_{family}',
                        free=frozenset(domain-blocked),targets=frozenset(published-deferred))
                    assert len(s.targets-s.covered)<=12
                    assert environment_check(s) is None
                    yield s,{'family':family,'length':length,'width':width,'domain_kind':kind,'progress':progress,
                        'initial_targets':sorted(old),'published_targets':sorted(published),'deferred_targets':sorted(deferred),
                        'obstacles':sorted(blocked),'domain':sorted(domain),'prefix':prefix,
                        'initial_policy':'raw_H_snake','scope':'new micro templates for exact diagnosis, not large-map or field validation'}
