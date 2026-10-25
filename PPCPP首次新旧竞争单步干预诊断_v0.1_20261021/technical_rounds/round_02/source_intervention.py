"""One current-input-only action choice; no planner/reward/route imports."""
class ProtocolMismatch(RuntimeError):pass
def first_new_step(enabled,used,options,old_targets,new_targets,original):
    if not enabled or used:return None
    old=[o for o in options if tuple(o['cell']) in old_targets]
    new=[o for o in options if tuple(o['cell']) in new_targets]
    if not old or not new:return None
    if len(new)!=1:raise ProtocolMismatch('first competition new option must be unique')
    assert tuple(original) in {tuple(o['cell']) for o in options}
    return dict(forced_selected=tuple(new[0]['cell']),old_options=old,new_options=new)
def exception_budget(log):
    assert len(log)<=1,'more than one forced action is not permitted'
