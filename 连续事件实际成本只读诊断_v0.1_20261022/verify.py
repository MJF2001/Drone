"""Independent saved-observation replay: arrivals before publications at ties.
No original/main analysis module import. No graph or new action is constructed.
"""
from common import *
CLASSES=('fresh_target','initial_historical','session_repeat','non_target')
def mapping(w,t):
    p=set(map(tuple,w['published']));f=set(map(tuple,w['free']));origin={x:'initial' for x in p};epoch='initial'
    for e in w['events']:
        if e['tick']<=t:
            for x in map(tuple,e['add_targets']):p.add(x);origin.setdefault(x,e['id'])
            f-=set(map(tuple,e['block']));epoch=e['id']
    return p,f,origin,epoch
def rows_stats(rows):
    c={k:0 for k in CLASSES};n90=n180=wait=0
    for a in rows:
        if a['kind']=='wait':wait+=1;continue
        c[a['classification']]+=1;n90+=a['turn_degrees']==90;n180+=a['turn_degrees']==180
    return dict(moves=sum(c.values()),waits=wait,move_classes=c,turns90=n90,turns180=n180)
def rebuild(sj,main):
    result=read(S/'sessions'/(sj['id']+'.json'));w=result['world'];s=result['sessions'][sj['method']];actions=s['actions'];moves=[(i,a) for i,a in enumerate(actions) if a['kind']=='move'];assert result['world']==read(S/'worlds.json')[sj['world']]
    # Sorting a fixed list of already recorded observations is not simulation.
    observations=[(0,1,'publication',None)]+[(e['tick'],1,'publication',None) for e in w['events']]+[(a['arrival_tick'],0,'arrival',(i,a)) for i,a in moves];observations.sort(key=lambda r:(r[0],r[1]));H0=set();cur=tuple(w['start']);previous=None;credits=[];derived={};last_vector=None
    def award(x,t,src,p,origin,epoch):
        if x in p and x not in H0:H0.add(x);credits.append(dict(point=list(x),tick=t,source=src,event_id=epoch,target_first_published=origin[x]))
    for t,_,kind,item in observations:
        if kind=='arrival':
            i,a=item;p,f,origin,epoch=mapping(w,a['tick']);q=tuple(a['end']);assert tuple(a['start'])==cur and q in f and abs(q[0]-cur[0])+abs(q[1]-cur[1])==1 and t==a['tick']+1
            cls='non_target' if q not in p else 'session_repeat' if q in H0 else 'fresh_target';vector=(q[0]-cur[0],q[1]-cur[1]);dot=last_vector[0]*vector[0]+last_vector[1]*vector[1] if last_vector else None;angle=None if dot is None else 90 if dot==0 else 180 if dot==-1 else 0;assert a['classification']==cls and a['turn_degrees']==angle
            derived[i]=dict(a,classification=cls,turn_degrees=angle);award(q,t,'arrival',p,origin,epoch);previous=cur;cur=q;last_vector=vector
        else:
            p,f,origin,epoch=mapping(w,t);assert cur in f and tuple(w['base']) in f;award(cur,t,'publication',p,origin,epoch)
    assert credits==s['credits'] and len(H0)==len(credits) and H0==set(map(tuple,s['summary']['H']))
    for i,a in enumerate(actions):
        if a['kind']=='wait':derived[i]=a
    derived_rows=[derived[i] for i in range(len(actions))];all_stats=rows_stats(derived_rows);assert all_stats['moves']==s['summary']['M'] and all_stats['waits']==s['summary']['waits'] and all_stats['move_classes']==s['summary']['move_classes']
    cuts=[0]+[e['tick'] for e in w['events']]+[s['terminal']['tick']];parts=[]
    for i in range(3):
        lo,hi=cuts[i:i+2];partrows=[a for a in derived_rows if lo<=a['tick']<hi];stats=rows_stats(partrows);seen=set(tuple(c['point']) for c in credits if c['tick']<=hi and (i==2 or c['tick']<hi or c['source']=='arrival'));p,f,_,_=mapping(w,hi if i==2 else hi-1);walked=[a for _,a in moves if a['arrival_tick']<=hi];state=dict(H=sorted(map(list,seen)),U=sorted(map(list,(p&f)-seen)),D=sorted(map(list,p-f-seen)),current=walked[-1]['end'] if walked else w['start'],previous=walked[-1]['start'] if walked else None,E=w['E0']-len(walked));creditids=[]
        for j,c in enumerate(credits):
            before_lo=c['tick']<lo or (c['tick']==lo and c['source']=='arrival');after_hi=c['tick']>hi or (c['tick']==hi and c['source']=='publication' and i<2)
            if not before_lo and not after_hi:creditids.append(j)
        expected=main['segments'][i]
        for k,v in stats.items():assert expected[k]==v,(sj['id'],i,k)
        assert expected['end_state']==state and [r['credit_index'] for r in expected['first_credits']]==creditids and expected['first_credit_count']==len(creditids)
        assert expected['zero_move_credit_count']==sum(credits[j]['source']=='publication' for j in creditids)
        parts.append(dict(**stats,end_state=state))
    assert sum(p['moves'] for p in parts)==all_stats['moves']
    snapshots=[]
    for i,req in enumerate(s['requests']):
        t=req['tick'];p,f,_,_=mapping(w,t);prior,_,_,_=mapping(w,t-1);p0=set(map(tuple,w['published']));before=p0 if t==0 else prior;seen=set(tuple(c['point']) for c in credits if c['tick']<=t);walked=[a for _,a in moves if a['arrival_tick']<=t];cur0=walked[-1]['end'] if walked else w['start'];prev0=walked[-1]['start'] if walked else None
        if i==0:old=[cur0]
        else:
            prior_req=s['requests'][i-1];n=sum(prior_req['tick']<=a['tick']<t for _,a in moves);old=prior_req['response']['route'][n:]
        snap=dict(name='stub_snapshot',free=sorted(map(list,f)),targets=sorted(map(list,p&f)),covered=sorted(map(list,seen)),published_targets=sorted(map(list,p)),deferred_targets=sorted(map(list,p-f-seen)),initial_targets=sorted(map(list,before|seen)),current=cur0,previous=prev0,base=w['base'],predator=[-1,0],old_route=old,distance_budget=w['E0']-len(walked),radius=0)
        assert snap==req['input'];wire=json.dumps(snap,sort_keys=True,separators=(',',':'),ensure_ascii=False);assert req['payload_utf8']==wire and req['payload_sha256']==hashlib.sha256(wire.encode()).hexdigest();snapshots.append(snap)
        slot=next(z for z in read(S/'call_slots.json') if z['session']==sj['id'] and z['tick']==t);out=read(S/'outputs'/(slot['id']+'.json'));assert out['entry']['response']==req['response'] and out['entry']['native_return']['raw']['route']==req['response']['route'] and sha(S/out['job']['input'])==req['payload_sha256'];assert req['admission']=='accepted' and req['response']['entry_seconds']<20
    c=snapshots[-1];pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));ct=cuts[2];cp=c['current']
    for cr in credits:
        if pending and cr['tick']>=cuts[2]:
            pending.discard(tuple(cr['point']))
            if not pending:ct=cr['tick'];cp=cr['point'];break
    assert not pending
    to=rows_stats([a for a in derived_rows if cuts[2]<=a['tick']<ct]);tail=rows_stats([a for a in derived_rows if ct<=a['tick']<cuts[3]]);final=main['final_completion'];assert final['completion_tick']==ct and final['completion_position']==cp and final['to_completion']==to and final['after_completion_to_base']==tail
    actual=[c['current']]+[a['end'] for _,a in moves if a['tick']>=cuts[2]];assert actual==s['requests'][-1]['response']['route'] and len(actual)-1==parts[-1]['moves']==final['complete_response_steps'];assert final['unexecuted_steps']==0 and final['waits_after_last_event']==to['waits']+tail['waits']
    # Every reported repeat/non-target run is an exact existing action slice.
    covered_indices=[]
    for run in main['all_repeat_and_non_target_runs']:
        ids=run['action_indices'];assert ids==list(range(ids[0],ids[-1]+1));assert run['steps']==len(ids);assert all(derived[j]['classification']==run['classification'] for j in ids);assert run['path']==[derived[ids[0]]['start']]+[derived[j]['end'] for j in ids];covered_indices+=ids
        src=run['first_move_source'];a=derived[ids[0]];request=max((r for r in s['requests'] if r['tick']<=a['tick']),key=lambda r:r['tick']);ri=sum(request['tick']<=x['tick']<a['tick'] for _,x in moves);assert src['route_segment_indices']==[ri,ri+1] and src['action']['json_pointer']==f'/sessions/{sj["method"]}/actions/{ids[0]}'
        native=read(src['response_output'])['entry']['native_return']['raw'];assert native['route'][ri:ri+2]==[a['start'],a['end']]
        if src['native_trace_index'] is not None:assert native['trace'][src['native_trace_index']]==src['native_trace_event']
    assert sorted(covered_indices)==[i for i,a in enumerate(derived_rows) if a.get('classification') in ('session_repeat','initial_historical','non_target')]
    return dict(session=sj,parts=parts,final_to_moves=to['moves'],final_tail_moves=tail['moves'],last_snapshot=c,credits=credits,M=all_stats['moves'],classes=all_stats['move_classes'])
def main():
    violations=install_guard();index=require_sources();saved=read(H/'三段实际账与完成尾段.json');order=read(S/'session_order.json');assert len(saved)==len(order)==12;rebuilt=[rebuild(sj,row) for sj,row in zip(order,saved)];by={r['session']['id']:r for r in rebuilt};costs=read(H/'六世界成本守恒分解.json');layers=read(H/'最后事件三层一致性.json');creditrows=read(H/'两对遮挡信用时间线.json')
    for row,layer in zip(costs,layers):
        wid=row['world'];p,q=[by[wid+'_'+m] for m in ('PPCPP','P2_MULTI')];d=p['M']-q['M'];assert row['delta_M']==d and row['three_segment_delta_M']==[a['moves']-b['moves'] for a,b in zip(p['parts'],q['parts'])] and row['all_four_class_delta']=={k:p['classes'][k]-q['classes'][k] for k in CLASSES};assert row['last_event_to_completion_delta']==p['final_to_moves']-q['final_to_moves'] and row['after_completion_return_delta']==p['final_tail_moves']-q['final_tail_moves'];assert row['last_event_to_completion_delta']+row['after_completion_return_delta']==row['three_segment_delta_M'][-1]
        a,b=p['last_snapshot'],q['last_snapshot'];physical_keys=dict(F='free',P='published_targets',H='covered',D='deferred_targets',current='current',previous='previous',base='base',E='distance_budget')
        for k,v in physical_keys.items():assert layer['physical_field_equal'][k]==(a[v]==b[v])
        assert layer['physical_field_equal']['U']==((set(map(tuple,a['targets']))-set(map(tuple,a['covered'])))==(set(map(tuple,b['targets']))-set(map(tuple,b['covered']))))
    for row in creditrows:
        for item in row['blocked_target_timeline']:
            for method,v in item['first_credit'].items():
                cr=next((c for c in by[row['world']+'_'+method]['credits'] if c['point']==item['point']),None);assert (v['credit'] if v else None)==cr
                if cr:assert cr['source']=='arrival' and cr['tick']<item['blocked_at']
                else:assert method=='P2_MULTI'
    if (H/'补充冻结来源hash.json').exists():
        for p,v in read(H/'补充冻结来源hash.json')['files'].items():assert sha(p)==v,p
    if (H/'I_M绘图仅用保存数据.json').exists():
        for method,r in read(H/'I_M绘图仅用保存数据.json').items():
            source=read(S/'sessions'/('I_M_'+method+'.json'))['sessions'][method];prefix=[read(S/'worlds.json')['I_M']['start']]+[a['end'] for a in source['actions'] if a['kind']=='move' and a['arrival_tick']<=48];assert prefix==r['route'] and r['last_event_input_current']==source['requests'][-1]['input']['current']
    if (H/'I_M独有采集格及原始输出指针.json').exists():
        for r in read(H/'I_M独有采集格及原始输出指针.json'):
            cs=by['I_M_'+r['method']]['credits'];assert r['first_credit'] in cs and r['first_credit']['point']==r['point'] and r['first_credit']['tick']<=48
    if (H/'原始证据副本清单.json').exists():
        for r in read(H/'原始证据副本清单.json'):assert sha(H/r['copy'])==sha(r['source'])==r['sha256'],r
    if (H/'completion_manifest.json').exists():
        for p,v in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==v,p
    extra_count=len(read(H/'补充冻结来源hash.json')['files']) if (H/'补充冻结来源hash.json').exists() else 0
    z=zeros('independent_saved_observation_verification',violations);print(json.dumps(dict(passed=True,worlds=6,sessions=len(rebuilt),responses=sum(len(read(S/'sessions'/(s['id']+'.json'))['sessions'][s['method']]['requests']) for s in order),actual_saved_moves=sum(x['M'] for x in rebuilt),first_credits=sum(len(x['credits']) for x in rebuilt),segments_checked=36,source_hashes_checked=len(index['files'])+extra_count,zero_calls=z,original_verifier_run=False),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
