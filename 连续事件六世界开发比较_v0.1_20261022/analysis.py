"""Saved-log summaries, all responses and adopted/unexecuted route portions."""
from util import *
from comparison import three_views,cost,pointset
def collect():
    records=[];execution_segments=[];histories=[];attempts=[json.loads(x) for x in (H/'actual_attempts.jsonl').read_text(encoding='utf8').splitlines()] if (H/'actual_attempts.jsonl').exists() else []
    for sj in read(H/'session_order.json'):
        path=H/'sessions'/(sj['id']+'.json')
        if not path.exists():continue
        s=read(path)['sessions'][sj['method']];s0=s['summary'];times=[];walls=[];responses=[]
        for i,req in enumerate(s['requests']):
            slot=next(v for v in read(H/'call_slots.json') if v['session']==sj['id'] and v['tick']==req['tick']);rid=slot['id'];outp=H/'outputs'/(rid+'.json');out=read(outp) if outp.exists() else None;receiptp=H/'logs'/(rid+'.receipt.json');rec=read(receiptp) if receiptp.exists() else None
            if out:times.append(out['entry']['entry_seconds'])
            if rec:walls.append(rec['callback_total_wall_seconds'])
            responses.append(dict(id=rid,tick=req['tick'],admission=req['admission'],reason=req['reason'],entry_seconds=out['entry']['entry_seconds'] if out else None,native_status=req.get('response',{}).get('native_status') if req.get('response') else None,callback_wall=rec['callback_total_wall_seconds'] if rec else None))
            if 'plan_adopted' in req:
                end=s['requests'][i+1]['tick'] if i+1<len(s['requests']) else s['terminal']['tick'];moves=[a for a in s['actions'] if a['kind']=='move' and req['tick']<=a['tick']<end];plan=req['plan_adopted'];n=len(moves);assert [a['end'] for a in moves]==plan[1:n+1]
                execution_segments.append(dict(session=sj['id'],response_id=rid,from_tick=req['tick'],until_tick=end,actual_moves=n,executed_route=[plan[0]]+[a['end'] for a in moves],original_complete_plan=plan,unexecuted_suffix=plan[n:],unexecuted_steps=len(plan)-1-n,description='Unexecuted suffix is descriptive, never charged as actual movement'))
        cls=s0['move_classes'];arrivals=cls['fresh_target']+cls['initial_historical']+cls['session_repeat'];repeats=cls['initial_historical']+cls['session_repeat']
        records.append(dict(world=sj['world'],method=sj['method'],session=sj['id'],summary=s0,entry_timing=cost(times),callback_wall=cost(walls),responses=responses,target_arrivals=arrivals,repeated_target_arrivals=repeats,repeat_ratio=repeats/arrivals if arrivals else None,only_current_inspectable_complete=s0['status']=='success' and bool(s0['D']),all_published_complete=s0['status']=='success' and not (pointset(s0['P'])-pointset(s0['H']))))
    views=three_views(records,list(read(H/'worlds.json')))
    for wid in read(H/'worlds.json'):
        data={m:read(H/'sessions'/(wid+'_'+m+'.json'))['sessions'][m] if (H/'sessions'/(wid+'_'+m+'.json')).exists() else None for m in ('PPCPP','P2_MULTI')};requests={m:{r['tick']:r for r in s['requests']} if s else {} for m,s in data.items()};ticks=[0]+[e['tick'] for e in read(H/'worlds.json')[wid]['events']];events=[];first=None
        for t in ticks:
            p=requests['PPCPP'].get(t);q=requests['P2_MULTI'].get(t);different=[]
            if p and q:
                different=[k for k in ('current','previous','covered','distance_budget','old_route','initial_targets','targets','deferred_targets') if p['input'][k]!=q['input'][k]]
                if different and first is None:first=t
            events.append(dict(tick=t,paired_inputs_present=bool(p and q),different_fields=different,inputs={m:dict(payload_sha256=requests[m][t]['payload_sha256'],input=requests[m][t]['input'],actual_prefix=requests[m][t]['actual_prefix'],plan_before=requests[m][t]['plan_before'],cursor_before=requests[m][t]['cursor_before']) if t in requests[m] else None for m in requests}))
        action_maps={m:{a['tick']:a for a in s['actions']} if s else {} for m,s in data.items()};first_move=None
        for t in sorted(set(action_maps['PPCPP'])|set(action_maps['P2_MULTI'])):
            p=action_maps['PPCPP'].get(t);q=action_maps['P2_MULTI'].get(t)
            if not p or not q or (p['kind'],p.get('end'),p.get('current'))!=(q['kind'],q.get('end'),q.get('current')):first_move=t;break
        histories.append(dict(world=wid,first_observed_action_difference_tick=first_move,first_paired_input_difference_tick=first,events=events,independent_reconstruction_evidence={m:str(Path('sessions')/(wid+'_'+m+'.audit.json')) if data[m] else None for m in data}))
    used={r['id']:r for r in attempts};slots=[]
    for slot in read(H/'call_slots.json'):
        rid=slot['id'];receiptp=H/'logs'/(rid+'.receipt.json');receipt0=read(receiptp) if receiptp.exists() else None;s=next((r for r in records if r['session']==slot['session']),None)
        reason=None if rid in used else ('session not started due to batch technical stop' if s is None else 'session terminated/last-publication success before response: '+s['summary']['status']+' / '+str(s['summary']['reason']))
        slots.append(dict(slot=slot,attempt=used.get(rid),receipt=receipt0,unused_reason=reason))
    return dict(views=views,session_records=records,event_history_comparison=histories,actual_and_unexecuted_segments=execution_segments,slots=slots)
