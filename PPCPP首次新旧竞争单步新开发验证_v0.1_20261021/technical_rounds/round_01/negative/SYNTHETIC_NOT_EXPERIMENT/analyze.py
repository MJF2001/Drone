"""OFF/ON full-route contrasts, state-equal signal and all missing/negative results."""
from common import *
from evaluation import job_row
from decision_audit import paired_audit
def percentile(xs,p):
    if not xs:return None
    a=sorted(xs);v=(len(a)-1)*p;i=int(v);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(v-i)

KEYS=('overlap_ratio','length','completion_step','return_tail_steps','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','direction_changes')
def compute():
    rows=[job_row(j) for j in read(H/'order.json')];lookup={(r['job']['mode'],r['job']['state'],r['job']['seed']):r for r in rows};states=read(H/'states_metadata.json');pairs=[];ss=[]
    for st in states:
        pp=[];triggered=st['condition'] in ('MIXED_SIDE','U_SIDE')
        for seed in (20261020,20261021,20261022):
            off=lookup['OFF',st['id'],seed];on=lookup['ON',st['id'],seed];eligible=off['valid'] and on['valid'] and off['timely'] and on['timely'];delta={k:on['metrics'][k]-off['metrics'][k] for k in KEYS} if off['valid'] and on['valid'] else None;proof=None
            if delta:
                assert delta['length']==delta['completion_step']+delta['return_tail_steps']==sum(delta[k] for k in ('fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps'))
                proof=paired_audit(read(H/off['job']['input']),read(H/'outputs'/f'{off["job"]["id"]}.json'),read(H/'outputs'/f'{on["job"]["id"]}.json'))
                assert proof['triggered']==triggered
            pair=dict(state=st['id'],geometry=st['geometry'],condition=st['condition'],L=st['L'],w=st['w'],boundary_count=st['boundary_count'],seed=seed,trigger_expected=triggered,eligible=eligible,OFF=off,ON=on,delta=delta,action_proof=proof,missing_reason=None if eligible else dict(OFF_status=off['status'],ON_status=on['status'],OFF_timely=off['timely'],ON_timely=on['timely']));pairs.append(pair);pp.append(pair)
        complete=all(p['eligible'] for p in pp);means={k:statistics.mean(p['delta'][k] for p in pp) for k in KEYS} if complete else None
        ss.append(dict(**st,trigger_expected=triggered,three_seeds_complete_legal_timely=complete,by_seed=[dict(seed=p['seed'],eligible=p['eligible'],delta=p['delta']) for p in pp],mean_delta=means,range_delta_L=[min(p['delta']['length'] for p in pp),max(p['delta']['length'] for p in pp)] if complete else None,all_three_shorter=complete and all(p['delta']['length']<0 for p in pp),protection_equal=all(p['action_proof'] and p['action_proof'].get('protection_equal') for p in pp) if not triggered else None))
    trigger=[s for s in ss if s['trigger_expected']];protect=[s for s in ss if not s['trigger_expected']];complete=all(s['three_seeds_complete_legal_timely'] for s in trigger);net=sum(s['mean_delta']['length'] for s in trigger) if complete else None;support=[s for s in trigger if s['all_three_shorter']];geoms=sorted({s['geometry'] for s in support});lengths=sorted({s['L'] for s in support});widths=sorted({s['w'] for s in support});offpass=all(r['valid'] and r['timely'] and r['equivalence']['passed'] for r in rows if r['job']['mode']=='OFF');protected=all(s['protection_equal'] for s in protect)
    signal=dict(OFF_all_equivalent=offpass,all_protections_equal=protected,all24_trigger_states_complete_legal_timely=complete,trigger_state_equal_weight_net_sum_delta_L=net,three_seed_shorter_states=[s['id'] for s in support],support_geometries=geoms,lengths=lengths,widths=widths,registered_pass=bool(offpass and protected and complete and len(geoms)>=3 and len(lengths)>=2 and len(widths)==2 and net<0),rule='OFF/protection pass; >=3 base geometries with all3seed strictly shorter triggered state, >=2 lengths/both widths, all24 complete, state-equal net sum<0')
    strata={}
    for name,values in [('triggered',trigger),('protection',protect)]+[(c,[s for s in ss if s['condition']==c]) for c in ('CONTROL','H_SIDE','MIXED_SIDE','U_SIDE')]:
        ok=[s for s in values if s['three_seeds_complete_legal_timely']];strata[name]=dict(planned_states=len(values),complete_states=len(ok),states_shorter=sum(s['mean_delta']['length']<0 for s in ok),states_equal=sum(s['mean_delta']['length']==0 for s in ok),states_longer=sum(s['mean_delta']['length']>0 for s in ok),state_equal_weight_sum_delta_L=sum(s['mean_delta']['length'] for s in ok) if len(ok)==len(values) else None,mean_delta={k:statistics.mean(s['mean_delta'][k] for s in ok) for k in KEYS} if ok else None,worst_increase_steps=max((p['delta']['length'] for p in pairs if p['state'] in {s['id'] for s in values} and p['eligible']),default=None))
    timing={}
    for mode in ('OFF','ON'):
        rr=[r for r in rows if r['job']['mode']==mode];tt=[r['seconds'] for r in rr if r['seconds'] is not None];timing[mode]=dict(planned=len(rr),ran=sum(r['ran'] for r in rr),valid=sum(r['valid'] for r in rr),timely=sum(r['timely'] for r in rr),mean=statistics.mean(tt) if tt else None,median=statistics.median(tt) if tt else None,P95=percentile(tt,.95),max=max(tt) if tt else None,note='Fixed interleaved formal OFF/ON; same-batch descriptive comparison')
    return norm(dict(rows=rows,pairs=pairs,states=ss,strata=strata,signal=signal,timing=timing))
def export():
    a=compute();save(H/'analysis.json',a);save(H/'signal.json',a['signal']);save(H/'protection_equivalence.json',[dict(state=p['state'],seed=p['seed'],proof=p['action_proof']) for p in a['pairs'] if not p['trigger_expected']]);save(H/'all_action_audits.json',[dict(job=r['job'],audit=r.get('audit')) for r in a['rows']]);csvsave(H/'288调用完整指标.csv',[dict(**r['job'],valid=r['valid'],timely=r['timely'],status=r['status'],seconds=r['seconds'],**(r['metrics'] or {})) for r in a['rows']]);csvsave(H/'144全部OFF_ON配对.csv',[{k:v for k,v in p.items() if k not in ('OFF','ON')} for p in a['pairs']]);csvsave(H/'48状态三seed原值均值范围.csv',a['states']);csvsave(H/'分层结果.csv',[dict(layer=k,**v) for k,v in a['strata'].items()]);print(json.dumps(dict(signal=a['signal'],strata=a['strata'],timing=a['timing']),ensure_ascii=False),flush=True)
if __name__=='__main__':export()
