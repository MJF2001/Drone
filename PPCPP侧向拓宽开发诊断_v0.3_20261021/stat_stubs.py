"""Eight fixed pure statistic fixtures; zero planning calls."""
from visit_a import *
def run():
    rows=[]
    c=dict(free=sorted(rect(0,0,2,2)),targets=[(0,0),(1,0),(0,1)],published_targets=[(0,0),(1,0),(0,1)],covered=[(0,0),(1,0)],deferred_targets=[],current=(0,0),base=(0,0),distance_budget=100)
    m=dual(c,[(0,0),(1,0),(0,0),(0,1),(0,0)]);assert m['fresh_target_steps']==1 and m['historical_target_steps']==3;rows.append(dict(case=1,expectation='history traversal is not first new capture',passed=True,metrics=m))
    old={(0,1)};A={(1,0)};prefix=[(0,0),(1,0),(1,1),(0,1)];h=history(prefix,old,3);assert h==old and A&set(prefix) and not A&h;rows.append(dict(case=2,expectation='previous flight through not-yet-published A gives zero retroactive credit',passed=True,history=sorted(h)))
    assert [position_label(k,6) for k in (6,3,0)]==['H_SIDE','MIXED_SIDE','U_SIDE'];rows.append(dict(case=3,expectation='all/mixed/no history contact labels',passed=True))
    A={(1,0),(2,0)};c=dict(covered=[],current=(0,0));one=visit(c,[(0,0),(1,0),(2,0),(3,0)],A,{(3,0)});repeat=visit(c,[(0,0),(1,0),(0,0),(1,0),(2,0)],A,{(3,0)})
    assert one['classification']=='single_continuous_visit' and repeat['classification']=='unfinished_exit_and_reentry' and len(repeat['unfinished_exits'])==1 and repeat['reentries_before_A_completion']==1;rows.append(dict(case=4,expectation='continuous completion vs unfinished exit/reentry',passed=True,one=one,repeated=repeat))
    inside=visit(dict(covered=[]),[(1,0),(2,0),(3,0)],A,{(3,0)});assert inside['initial_A_occupancy'] and inside['entries_before_A_completion']==0 and inside['A_completion']==1 and len(inside['visits'])==1;rows.append(dict(case=5,expectation='inside start is initial visit, not an entry edge',passed=True,observed=inside))
    control=visit(c,[(0,0),(1,0)],set(),{(1,0)});assert control['classification']=='not_applicable' and control['entries_before_A_completion'] is None;rows.append(dict(case=6,expectation='CONTROL A statistics NA without division',passed=True,observed=control))
    return_visit=visit(c,[(0,0),(1,0),(2,0),(3,0),(2,0),(1,0),(0,0)],A,{(3,0)});assert not return_visit['unfinished_exits'] and return_visit['entries_before_A_completion']==1 and len(return_visit['visits'])==2;rows.append(dict(case=7,expectation='return through completed A is not unfinished exit',passed=True,observed=return_visit))
    assert timely(19.999999,True) and not timely(20,True) and not timely(20.000001,True) and not timely(1,False);rows.append(dict(case=8,expectation='strict full-entry <20; complete late P2 is legal-only, no internal reset',passed=True))
    return dict(tests=rows,passed=True,real_planner_calls=0,coverage_searches=0,ordinary_graph_searches=0)
if __name__=='__main__':
    x=run();save(H/'stat_stub_results.json',x);receipt('stat_stubs',[H/'stat_stub_results.json']);print('PASS 8 pure statistic fixture cases; real planner/graph calls=0')
