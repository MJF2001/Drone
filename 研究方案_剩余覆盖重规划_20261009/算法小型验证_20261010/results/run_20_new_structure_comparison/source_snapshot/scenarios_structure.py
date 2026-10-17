"""New parameter/seed holdout within a declared road-template family."""
from dataclasses import replace
import random
from model import Snapshot,Geometry
from scenarios import rectangle,flight_domain
from scenarios_v2 import checkpoint
from audit import environment_check,audit


def cases():
    index=0
    for length,width in ((21,5),(29,7)):
        for kind in ('open','corridor'):
            for phase in (0,1):
                rng=random.Random(20261011+index)
                extension=rng.choice((6,8,11))
                old=rectangle(3,3,length,width)
                straight=rectangle(length+3,3,extension,width)
                corner=rectangle(length+3,3,width,width)|rectangle(length+3,width+3,width,extension)
                envelope=old|straight|corner
                domain=(rectangle(0,0,max(x for x,y in envelope)+4,max(y for x,y in envelope)+4)
                    if kind=='open' else flight_domain(envelope,1)|{(1,3),(2,3)})
                initial=Snapshot('seed',frozenset(domain),frozenset(old),frozenset(),(1,3),(1,3),(),0,4*len(domain))
                # Neutral declared H/V scan history, not a history optimised by a tested candidate.
                points=sorted(old,key=(lambda p:(p[1],p[0] if (p[1]-3)%2==0 else -p[0])) if phase==0 else
                    (lambda p:(p[0],p[1] if (p[0]-3)%2==0 else -p[1])))
                route=Geometry(initial).expand(points)
                assert audit(initial,route)['valid']
                progress=rng.uniform(.3,.48) if phase==0 else rng.uniform(.57,.78)
                state,prefix=checkpoint(initial,route,progress)
                for family in ('straight','obstacle','corner_obstacle'):
                    published=old|(straight if family=='straight' else corner if family=='corner_obstacle' else set())
                    blocked=set()
                    if family!='straight':
                        eligible=[p for p in state.old_route if p in old and p not in (state.current,state.base)]
                        rng.shuffle(eligible)
                        for x,y in eligible:
                            patch=rectangle(x,y,3 if phase else 1,1 if phase else 3)&domain
                            if state.current not in patch and state.base not in patch:
                                blocked=patch
                                break
                    deferred=(published-set(state.covered))&blocked
                    s=replace(state,name=f'holdout_{kind}_L{length}_W{width}_h{phase}_{family}',
                        targets=frozenset(published-deferred),free=frozenset(domain-blocked))
                    reason=environment_check(s)
                    assert reason is None,reason
                    yield s,{'family':family,'domain_kind':kind,'length':length,'width':width,
                        'extension':extension,'seed':20261011+index,'requested_progress':progress,
                        'initial_targets':sorted(old),'published_targets':sorted(published),
                        'deferred_targets':sorted(deferred),'obstacles':sorted(blocked),'domain':sorted(domain),
                        'prefix':prefix,'flight_domain_fixed':True,'initial_policy':'H_or_V_raw_scan',
                        'holdout_scope':'new parameters and seeds; shared road-template family, not shape OOD'}
                index+=1
