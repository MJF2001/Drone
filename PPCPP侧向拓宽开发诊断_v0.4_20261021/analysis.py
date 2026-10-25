"""Fixed denominators, signed paired contrasts and saved trajectory observations."""
from visit_a import *
KEYS=('length','completion_step','return_tail_steps','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180')
def job_row(j,st=None):
    file=H/'outputs'/f'{j["id"]}.json';row=dict(**j,ran=file.exists(),valid=False,timely=False,metrics=None,status='NOT_RUN',seconds=None,visits_A=None,pp_first_A_event=None,core_calls=None)
    if not file.exists():
        receipt_file=H/'logs'/f'{j["id"]}.receipt.json'
        if receipt_file.exists():row.update(ran=True,status=read(receipt_file)['status'])
        return row
    out=read(file);assert out['job']==j and out['input_sha256']==sha(H/j['input']);c=read(H/j['input']);x=out['result'];path=x['raw'].get('route',[]);m=dual(c,path) if path else None
    row.update(ran=True,valid=bool(m),timely=timely(x['entry_seconds'],bool(m)),metrics=m,status=x['raw'].get('status'),seconds=x['entry_seconds'],caller_wall_seconds=out['caller_wall_seconds'],overrun=max(0,x['entry_seconds']-20),raw_reason=x['raw'].get('reason'),core_calls=len(out['actual_core_calls']),source=x['raw'].get('source',x['raw'].get('selected')))
    if st and path:
        t0=rect(4,4,st['L'],st['w']);row.update(visits_A=visit(c,path,st['A'],t0),pp_first_A_event=first_pp_event(x['raw'],path,st['A']) if j['method']=='PPCPP' else dict(reason='P2 final route/search stages only; no PPCPP-style online decision trace'),completion_position=path[m['completion_step']])
    return row
def pair_summary(pp):
    return dict(pairs=len(pp),states=len({p['case'] for p in pp}),geometries=len({p['geometry'] for p in pp}),PP_shorter=sum(p['D']<0 for p in pp),equal=sum(p['D']==0 for p in pp),PP_longer=sum(p['D']>0 for p in pp),sum_D=sum(p['D'] for p in pp),PP_steps=sum(p['PPCPP']['metrics']['length'] for p in pp),P2_steps=sum(p['P2_MULTI']['metrics']['length'] for p in pp))
def compute():
    states=read(H/'states.json');sm={s['id']:s for s in states};rows=[job_row(j,sm[j['case']]) for j in read(H/'order.json')];rm={r['id']:r for r in rows};pairs=[]
    for s in states:
        for seed in SEEDS:
            p=rm[f'formal_{s["id"]}_{seed}_PPCPP'];q=rm[f'formal_{s["id"]}_{seed}_P2_MULTI'];delta={k:p['metrics'][k]-q['metrics'][k] for k in KEYS} if p['valid'] and q['valid'] else None
            if delta:assert delta['length']==delta['completion_step']+delta['return_tail_steps'] and delta['length']==sum(delta[k] for k in ('fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps'))
            pairs.append(dict(id=f'{s["id"]}_{seed}',case=s['id'],group=s['group'],geometry=s['geometry'],L=s['L'],w=s['w'],boundary_count=s['boundary_count'],condition=s['condition'],seed=seed,legal=p['valid'] and q['valid'],timely=p['timely'] and q['timely'],unavailable_reason=None if p['timely'] and q['timely'] else dict(PPCPP_status=p['status'],P2_status=q['status'],PPCPP_valid=p['valid'],P2_valid=q['valid'],PPCPP_seconds=p['seconds'],P2_seconds=q['seconds']),D=delta['length'] if delta else None,delta=delta,PPCPP=p,P2_MULTI=q))
    views={}
    for view in ('timely','legal'):
        eligible=[p for p in pairs if p['legal'] and (view=='legal' or p['timely'])];ss=[];contrasts=[];gg=[]
        for s in states:
            rr=[p for p in eligible if p['case']==s['id']];ss.append(dict(**s,n=len(rr),three_seeds_complete=len(rr)==3,raw=[dict(seed=p['seed'],D=p['D'],delta=p['delta'],PP=p['PPCPP']['metrics'],P2=p['P2_MULTI']['metrics']) for p in rr],mean_D=statistics.mean(p['D'] for p in rr) if rr else None,D_range=[min(p['D'] for p in rr),max(p['D'] for p in rr)] if rr else None,mean_delta={k:statistics.mean(p['delta'][k] for p in rr) for k in KEYS} if rr else None,PP_mean_steps=statistics.mean(p['PPCPP']['metrics']['length'] for p in rr) if rr else None,PP_mean_seconds=statistics.mean(p['PPCPP']['seconds'] for p in rr) if rr else None))
        for group in read(H/'groups.json'):
            raw=[]
            for seed in SEEDS:
                lookup={p['condition']:p for p in eligible if p['group']==group['id'] and p['seed']==seed};dd={cond:lookup[cond]['D'] if cond in lookup else None for cond in CONDS};h,u,m,ctrl=[lookup.get(cond) for cond in ('H_SIDE','U_SIDE','MIXED_SIDE','CONTROL')]
                inc={}
                for cond in CONDS[1:]:
                    event=lookup.get(cond)
                    if event and ctrl:inc[cond]=dict(D_event_minus_CONTROL=event['D']-ctrl['D'],PP_event_increment=event['PPCPP']['metrics']['length']-ctrl['PPCPP']['metrics']['length'],P2_event_increment=event['P2_MULTI']['metrics']['length']-ctrl['P2_MULTI']['metrics']['length'],new_targets=2*group['ell'])
                dec={k:h['delta'][k]-u['delta'][k] for k in KEYS} if h and u else None
                if dec:assert dec['length']==dec['completion_step']+dec['return_tail_steps'] and dec['length']==sum(dec[k] for k in ('fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps'))
                cr=dict(group=group['id'],geometry=group['geometry'],L=group['L'],w=group['w'],boundary_count=group['boundary_count'],seed=seed,D=dd,DH_minus_DU=h['D']-u['D'] if h and u else None,DM_minus_DU=m['D']-u['D'] if m and u else None,H_minus_U_decomposition=dec,event_control_increments=inc,evidence_available=bool(h and u and h['PPCPP']['visits_A']['capture_order'] and u['PPCPP']['visits_A']['capture_order']),warning='Position changes current/base distances and task layout. Descriptive matched contrasts, not pure causal loss or removable steps.');contrasts.append(cr);raw.append(cr)
            complete=all(r['DH_minus_DU'] is not None for r in raw);mean=statistics.mean(r['DH_minus_DU'] for r in raw) if complete else None;support=bool(complete and all(r['D']['H_SIDE']>0 and r['DH_minus_DU']>0 and r['evidence_available'] for r in raw) and mean>=2)
            gg.append(dict(group=group['id'],geometry=group['geometry'],L=group['L'],w=group['w'],boundary_count=group['boundary_count'],three_seed_H_U_complete=complete,raw=raw,mean_DH_minus_DU=mean,support=support if view=='timely' else False,appendix_not_signal_view=view=='legal',classification='incomplete' if not complete else 'support' if support and view=='timely' else 'reverse' if mean<0 else 'zero' if mean==0 else 'positive_below_registered_support'))
        strata={field:{str(v):pair_summary([p for p in eligible if p[field]==v]) for v in sorted({p[field] for p in pairs})} for field in ('condition','L','w','geometry','boundary_count')}
        views[view]=dict(all=pair_summary(eligible),events=pair_summary([p for p in eligible if p['condition']!='CONTROL']),controls=pair_summary([p for p in eligible if p['condition']=='CONTROL']),pair_ids=[p['id'] for p in eligible],states=ss,groups=gg,contrasts=contrasts,strata=strata)
    support=[g for g in views['timely']['groups'] if g['support']];geoms=sorted({g['geometry'] for g in support});lengths=sorted({g['L'] for g in support});widths=sorted({g['w'] for g in support});passed=len(geoms)>=3 and len(lengths)>=2 and len(widths)==2
    comparable=[g for g in views['timely']['groups'] if g['three_seed_H_U_complete']];selected=[]
    for label,key in [('maximum',lambda g:(-g['mean_DH_minus_DU'],g['L'],g['w'],g['boundary_count'])),('minimum',lambda g:(g['mean_DH_minus_DU'],g['L'],g['w'],g['boundary_count'])),('closest_zero',lambda g:(abs(g['mean_DH_minus_DU']),g['L'],g['w'],g['boundary_count']))]:
        choices=sorted([g for g in comparable if g['group'] not in {x['group'] for x in selected}],key=key)
        if choices:selected.append(dict(selection=label,**choices[0]))
    times={}
    def percentile(a,q):
        a=sorted(a);idx=(len(a)-1)*q;lo=int(idx);return a[lo]+(a[min(lo+1,len(a)-1)]-a[lo])*(idx-lo)
    for method in METHODS:
        rr=[r for r in rows if r['method']==method];tt=[r['seconds'] for r in rr if r['seconds'] is not None];times[method]=dict(planned=len(rr),ran=sum(r['ran'] for r in rr),valid=sum(r['valid'] for r in rr),timely=sum(r['timely'] for r in rr),late_legal=sum(r['valid'] and not r['timely'] for r in rr),no_valid_route=sum(r['ran'] and not r['valid'] for r in rr),mean=statistics.mean(tt) if tt else None,median=statistics.median(tt) if tt else None,p95=percentile(tt,.95) if tt else None,max=max(tt) if tt else None,source_counts=dict(collections.Counter(r.get('source') for r in rr if r['ran'])))
    return normal(dict(rows=rows,pairs=pairs,views=views,signal=dict(support_groups=[g['group'] for g in support],support_geometries=geoms,lengths=lengths,widths=widths,registered_pass=passed,threshold='>=3 base geometries, >=2 lengths, both widths; every seed DH>0 and DH-DU>0; mean DH-DU>=2'),detailed_examples=selected,time_summary=times))
def export():
    a=compute();save(H/'analysis.json',a);csvsave(H/'288正式调用完整指标.csv',[{**{k:v for k,v in r.items() if k not in ('metrics','visits_A','pp_first_A_event')},**(r['metrics'] or {}),'visits_A':r['visits_A'],'pp_first_A_event':r['pp_first_A_event']} for r in a['rows']]);csvsave(H/'144全部配对与不可用原因.csv',a['pairs'])
    for name,v in a['views'].items():
        csvsave(H/f'{name}_48状态三种子均值范围.csv',v['states']);csvsave(H/f'{name}_12匹配组信号.csv',v['groups']);csvsave(H/f'{name}_逐seed位置控制对比.csv',v['contrasts']);csvsave(H/f'{name}_分层.csv',[dict(dimension=d,value=value,**row) for d,vs in v['strata'].items() for value,row in vs.items()])
    save(H/'signal.json',a['signal']);save(H/'detailed_example_selection.json',a['detailed_examples']);print(json.dumps(dict(main={z:a['views']['timely'][z] for z in ('all','events','controls')},signal=a['signal'],times=a['time_summary']),ensure_ascii=False),flush=True)
if __name__=='__main__':export()
