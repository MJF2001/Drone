"""Pure three-denominator descriptive comparison, never plans or searches."""
import statistics
METHODS=('PPCPP','P2_MULTI')
STATUSES=('success','environment_termination','deadline','solver_no_solution','resource_infeasible','tick_limit','invalid_route','technical_error','not_run')
def pointset(x):return set(map(tuple,x))
def cost(values):return dict(each=values,mean=statistics.mean(values) if values else None,median=statistics.median(values) if values else None,maximum=max(values) if values else None,total=sum(values))
def three_views(records,world_order):
    by={(r['world'],r['method']):r for r in records};full=[];success=[];comparable=[]
    failure={m:dict.fromkeys(STATUSES,0) for m in METHODS}
    for wid in world_order:
        pair={m:by.get((wid,m)) for m in METHODS}
        for m,r in pair.items():failure[m][r['summary']['status'] if r else 'not_run']+=1
        both=all(r and r['summary']['status']=='success' for r in pair.values())
        same=both and all(pointset(pair['PPCPP']['summary'][k])==pointset(pair['P2_MULTI']['summary'][k]) for k in ('H','D'))
        row=dict(world=wid,shape=wid.split('_')[0],both_success=both,final_H_D_identical=bool(same),methods=pair,delta_M_PPCPP_minus_P2=pair['PPCPP']['summary']['M']-pair['P2_MULTI']['summary']['M'] if both else None)
        full.append(row)
        if both:success.append(row)
        if same:comparable.append(row)
    worse_shapes=sorted({r['shape'] for r in comparable if r['delta_M_PPCPP_minus_P2']>0})
    return dict(full_world_denominator=len(world_order),statuses_per_method=failure,full_worlds=full,both_success=dict(denominator=len(success),out_of_worlds=len(world_order),pairs=success,conditional_selection=True),same_final_H_D=dict(denominator=len(comparable),out_of_worlds=len(world_order),pairs=comparable,conditional_selection=True),eligible_to_suggest_cost_location_discussion=len(worse_shapes)>=2,shapes_with_PPCPP_longer_in_comparable_pairs=worse_shapes,no_automatic_followup=True,no_significance=True)
