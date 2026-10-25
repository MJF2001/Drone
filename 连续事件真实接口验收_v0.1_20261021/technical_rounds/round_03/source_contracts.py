"""Pure input/response contracts. No algorithm or path construction."""
import json,math
ENTRY_BUDGET=20
SNAPSHOT_KEYS={'name','free','targets','covered','published_targets','deferred_targets','initial_targets','current','previous','base','predator','old_route','distance_budget','radius'}
class TechnicalError(RuntimeError):
    def __init__(self,reason,result=None):super().__init__(reason);self.result=result
def points(xs):return set(map(tuple,xs))
def point(p):return isinstance(p,(list,tuple)) and len(p)==2 and all(type(v) is int for v in p)
def safe(x):
    if isinstance(x,float) and not math.isfinite(x):return {'nonfinite_float':str(x)}
    if isinstance(x,dict):return {k:safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [safe(v) for v in x]
    return x
def wire(x):return json.dumps(safe(x),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def validate_world(w):
    assert set(w)=={'free','published','base','start','E0','T_max','events'}
    assert all(point(p) for p in w['free']+w['published']) and point(w['base']) and point(w['start'])
    assert type(w['E0']) is int and w['E0']>=0 and type(w['T_max']) is int and w['T_max']>0
    f=points(w['free']);assert tuple(w['base']) in f and tuple(w['start']) in f and points(w['published'])<=f
    assert len(f)==len(w['free'])
    ids=set()
    for e in w['events']:
        assert set(e)=={'tick','id','add_targets','block'} and type(e['tick']) is int and 0<e['tick']<w['T_max'] and isinstance(e['id'],str) and e['id'] and e['id'] not in ids
        assert all(point(p) for p in e['add_targets']+e['block']);ids.add(e['id'])
def admit(snapshot,response):
    if response is None:return 'solver_no_solution','missing_response'
    if not isinstance(response,dict):return 'technical_error','response_not_object'
    seconds=response.get('entry_seconds')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0:return 'technical_error','invalid_time_field'
    if seconds>=ENTRY_BUDGET:return 'deadline','entry_not_strictly_less_than_20'
    if 'route' not in response or not response['route']:
        return ('deadline','native_deadline_without_route') if response.get('native_status')=='deadline' else ('solver_no_solution','no_route')
    path=response['route'];f=points(snapshot['free']);u=points(snapshot['targets'])-points(snapshot['covered'])
    if not isinstance(path,list) or not all(point(p) for p in path):return 'invalid_route','route_points'
    if path[0]!=snapshot['current'] or path[-1]!=snapshot['base'] or not points(path)<=f:return 'invalid_route','endpoint_or_collision'
    if any(abs(p[0]-q[0])+abs(p[1]-q[1])!=1 for p,q in zip(path,path[1:])):return 'invalid_route','non_four_neighbor_move'
    if not u<=points(path):return 'invalid_route','coverage_omission'
    if len(path)-1>snapshot['distance_budget']:return 'resource_infeasible','full_route_exceeds_remaining_resource'
    return 'accepted',None
