"""Known-map residual sync candidate; not an autonomous CAP solver.

Explicit adaptation: batch-split disconnected remaining tasks at the next
region boundary and call the unchanged CAP global order policy once.
No target-state selection, no new movement, no original snapshot mutation.
"""
import copy
from structures import CapGraph
from primitives import components, cap_center

class KnownMapCapGraph(CapGraph):
    def sync(self, pending, current):
        pending = set(pending)
        if self.unknown:
            raise ValueError('known-map candidate only')
        old_remaining = set().union(*(n['R'] for n in self.nodes.values()))
        if not pending <= old_remaining:
            raise ValueError('sync cannot add or resurrect tasks; rebuild required')
        if current not in self.metric.free:
            raise ValueError('current not free')
        # Stage graph state so deadlines/unreachable ordering leave the graph
        # untouched. Metric diagnostic counters may still advance.
        staged = copy.copy(self)
        staged.nodes = copy.deepcopy(self.nodes)
        staged.events = copy.deepcopy(self.events)
        staged.order = list(self.order)
        staged.current = current
        replacements = []
        for i in sorted(self.nodes):
            self.metric.check('known_sync_node')
            n = staged.nodes[i]
            remaining = n['R'] & pending
            parts = components(remaining, self.metric.check)
            if len(parts) > 1:
                del staged.nodes[i]
                children = [staged.add(part) for part in parts]
                replacements.append(dict(parent=i, children=children,
                    parts=[sorted(p) for p in parts]))
            else:
                n['R'] = remaining
                n['state'] = 'E' if remaining else 'C'
                n['center'] = cap_center(remaining, self.metric.free)
        staged.order = [i for i in staged.order
                        if i in staged.nodes and staged.nodes[i]['state'] != 'C']
        if replacements:
            staged.events.append(dict(type='known_residual_split_batch',
                replacements=replacements, reason='actual_coverage_at_region_boundary'))
            staged.replan()
        self.metric.check('known_sync_commit')
        self.nodes, self.order, self.events = staged.nodes, staged.order, staged.events
        self.current, self.next_id = staged.current, staged.next_id

def restore(snapshot, metric, current):
    """Restore saved graph for boundary-only replay, not native hidden state."""
    g = object.__new__(KnownMapCapGraph)
    g.metric, g.current, g.unknown = metric, current, set()
    g.nodes = {n['id']: dict(A=set(map(tuple,n['A'])),R=set(map(tuple,n['R'])),
        center=tuple(n['center']) if n['center'] is not None else None,
        state=n['state']) for n in snapshot['nodes']}
    g.order, g.events = list(snapshot['order']), []
    g.next_id = max(g.nodes,default=-1)+1
    return g
