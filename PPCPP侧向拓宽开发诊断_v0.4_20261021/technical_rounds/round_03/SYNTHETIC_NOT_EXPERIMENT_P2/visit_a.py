"""Observe first captures and maximal in-A intervals from a literal saved path."""
from common import *
def visit(c,path,A,T0):
    r=list(map(tuple,path));A=set(map(tuple,A));T0=set(map(tuple,T0));h=set(map(tuple,c['covered']));initial={r[0]}&(A-h) if r else set();seen=set(h);events=[];first={}
    for i,p in enumerate(r):
        if p in (T0|A)-seen:
            first[p]=i;events.append(dict(index=i,cell=p,kind='new_A' if p in A else 'old_U',positive_step=i>0));seen.add(p)
    if not A:return normal(dict(applicable=False,reason='CONTROL_no_A',initial_A_occupancy=False,initial_A_capture=[],capture_order=events,first_A_capture=None,A_completion=None,old_remaining_at_A_completion=None,visits=[],entries_before_A_completion=None,unfinished_exits=[],reentries_before_A_completion=None,classification='not_applicable'))
    required=A-h;complete=max((first[q] for q in required),default=0) if required<=set(first) else None;firstcap=min((first[q] for q in required if q in first),default=None)
    runs=[];i=0
    while i<len(r):
        if r[i] not in A:i+=1;continue
        begin=i
        while i+1<len(r) and r[i+1] in A:i+=1
        end=i;remaining=required-set(r[:end+1]);runs.append(dict(start=begin,end=end,initial_occupancy=begin==0,entry_edge_index=begin if begin else None,exit_edge_index=end+1 if end+1<len(r) else None,remaining_A_on_exit=len(remaining),before_A_complete=complete is not None and begin<=complete,unfinished_exit=bool(end+1<len(r) and remaining)))
        i+=1
    before=[v for v in runs if complete is not None and v['start']<=complete];unfinished=[v for v in runs if v['unfinished_exit'] and (complete is None or v['end']<complete)];entries=[v for v in before if v['start']>0];reentries=[v for v in entries if any(z['end']<v['start'] for z in unfinished)]
    return normal(dict(applicable=True,initial_A_occupancy=bool(r and r[0] in A),initial_A_capture=sorted(initial),capture_order=events,first_A_capture=firstcap,A_completion=complete,old_remaining_at_A_completion=len((T0-h)-set(r[:complete+1])) if complete is not None else None,visits=runs,entries_before_A_completion=len(entries),unfinished_exits=unfinished,reentries_before_A_completion=len(reentries),classification='incomplete' if complete is None else 'single_continuous_visit' if len(before)==1 else 'unfinished_exit_and_reentry',A_count=len(A)))

def first_pp_event(raw,path,A):
    A=set(map(tuple,A));trace=raw.get('branches',{}).get('P0',{}).get('trace',[]);route=list(map(tuple,path))
    if not A:return dict(applicable=False,reason='CONTROL_no_A')
    for i,e in enumerate(trace):
        end=trace[i+1]['index'] if i+1<len(trace) else len(route)-1;start=e['index'];option=any(tuple(o['cell']) in A for o in e.get('options',[]));segment=route[start:end+1]
        if tuple(e['current']) in A or tuple(e['goal']) in A or option or any(p in A for p in segment):return normal(dict(applicable=True,trace_index=i,pointer=f'$.result.raw.branches.P0.trace[{i}]',event=e,saved_literal_segment=segment,end_index=end,option_mentions_A=option,segment_touches_A=any(p in A for p in segment),evidence='Direct saved trace only; no missing scores or unrun alternatives reconstructed.'))
    return dict(applicable=True,trace_index=None,reason='no_saved_event_involves_A')
