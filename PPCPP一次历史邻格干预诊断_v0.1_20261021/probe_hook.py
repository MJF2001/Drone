"""A single predetermined non-collecting step, outside the coverage loop."""
def force_history_step(s,previous,pending,route,trace,action,tick,deadline,record,hook=None):
    if hook:hook('force_before')
    tick()
    origin=tuple(action['current']);q=tuple(action['next']);expected=tuple(action['previous'])
    if s.current!=origin or previous!=expected or route!=[origin]:raise ValueError('mismatched_initial_state')
    if sum(abs(a-b) for a,b in zip(origin,q))!=1:raise ValueError('not_adjacent')
    if q not in s.free:raise ValueError('not_free')
    if q not in s.covered or q in pending:raise ValueError('not_initial_history')
    if not any(sum(abs(a-b) for a,b in zip(origin,p))==1 for p in pending if p in s.free):raise ValueError('no_pending_neighbor')
    if s.distance_budget<1:raise ValueError('insufficient_step_resource')
    if record['trigger_count']!=0:raise ValueError('second_trigger_forbidden')
    before=sorted(pending);record.update(deadline=deadline,action=[origin,q],route_index_before=0,before=dict(current=origin,previous=previous,pending=before,distance_used=0,distance_remaining=s.distance_budget))
    tick();route.append(q);pending.discard(q);assert sorted(pending)==before
    record.update(trigger_count=1,route_index_after=1,after=dict(current=q,previous=origin,pending=sorted(pending),distance_used=1,distance_remaining=s.distance_budget-1),added_steps=1,added_new_capture_credit=0)
    trace.append(dict(kind='forced_history_step',index=0,current=origin,previous=previous,goal=q,pending_count=len(pending),intervention=record))
    if hook:hook('force_after')
    tick()
