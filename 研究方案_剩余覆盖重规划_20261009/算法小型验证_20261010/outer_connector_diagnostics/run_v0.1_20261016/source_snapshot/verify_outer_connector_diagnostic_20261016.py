"""Independent responsibility/BFS/route checks; never calls optimizer."""
from pathlib import Path
from collections import deque
from types import SimpleNamespace
import json,statistics,importlib.util
from run_outer_connector_diagnostic_20261016 import ROOT,ALGO,BASE,INPUT,OUT,A,SOURCE,read,write,sha,manifest,route_check,METHODS
VERIFY=BASE/'verification_v0.1_20261016'
def normalize(x):return json.loads(json.dumps(x))
def distance(free,a,b):
    q=deque([a]);d={a:0}
    while q:
        p=q.popleft()
        if p==b:return d[p]
        for z in ((p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)):
            if z in free and z not in d:d[z]=d[p]+1;q.append(z)
    raise AssertionError('unreachable required waypoint')
def assignment(c,cfg):
    old=list(map(tuple,c['old_route']));pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])}
    l,r=cfg['left'],cfg['right'];pre=pending.intersection(old[:l+1]);local=set(map(tuple,cfg['required']));post=pending-pre-local
    assert not pre&local and pre|local|post==pending
    def ordered(route,need):
        result=list(dict.fromkeys(p for p in route if p in need));assert set(result)==need;return result
    return normalize(dict(prefix_required=sorted(pre),local_required=sorted(local),suffix_required=sorted(post),prefix_visits=ordered(old[:l+1],pre),suffix_visits=ordered(old[r:],post)))
def segment_check(c,route,start,visits,end,shortest):
    r=list(map(tuple,route));free=set(map(tuple,c['free']));waypoints=[start]+list(visits)+[end]
    assert r and r[0]==start and r[-1]==end and set(r)<=free
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]))
    # Sequential waypoint boundaries, including repeated nonadjacent waypoints.
    cursor=0;expected=0
    for a,b in zip(waypoints,waypoints[1:]):
        assert r[cursor]==a
        n=distance(free,a,b)
        if shortest:assert cursor+n<len(r) and r[cursor+n]==b;cursor+=n
        else:
            while r[cursor]!=b:cursor+=1;assert cursor<len(r)
        expected+=n
    if shortest:assert cursor==len(r)-1==expected
    return expected
def check_inputs():
    from verify_road_range_diagnostic_20261015 import independent_plan
    manifest(INPUT);manifest(A);manifest(SOURCE);checks=[]
    for e in read(INPUT/'records.json'):
        c=read(Path(e['case']));original=read(Path(e['source_case']));prep=read(Path(e['saved_preparation']))
        assert sha(Path(e['case']))==e['case_sha256'] and sha(Path(e['source_case']))==e['source_sha256']
        assert sha(Path(e['saved_preparation']))==e['saved_preparation_sha256']
        assert c['metadata']['split']=='development' and c['metadata']['range_diagnostic']['role']=='event'
        assert all(c[k]==original[k] for k in original if k!='old_route')
        assert c['old_route']==(original['old_route'] if e['reference']=='RAW' else prep['raw']['route'])
        plan=independent_plan(c);assert e['plan']==plan;cfg=plan['plans']['R_PLUS1'];assigned=assignment(c,cfg);assert e['responsibilities']==assigned
        old=list(map(tuple,c['old_route']));l,r=cfg['left'],cfg['right'];seg=e['segments'];assert seg['LITERAL']==normalize([old[:l+1],old[r:]])
        lengths=[]
        for k,start,visits,end in [(0,tuple(c['current']),list(map(tuple,assigned['prefix_visits'])),old[l]),(1,old[r],list(map(tuple,assigned['suffix_visits'])),tuple(c['base']))]:
            n=segment_check(c,seg['RECONNECT'][k],start,visits,end,True)
            assert n<=len(seg['LITERAL'][k])-1;lengths.append(n)
        checks.append(dict(case=e['case'],reference=e['reference'],map_id=e['map_id'],left=l,right=r,required_count=len(cfg['required']),literal_outside=l+len(old)-1-r,reconnect_outside=sum(lengths),saved_steps=l+len(old)-1-r-sum(lengths),passed=True))
    assert len(checks)==20;return checks
def main():
    checks=check_inputs();manifest(OUT);protocol=read(OUT/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    assert protocol['input_manifest_sha256']==sha(INPUT/'sha256.json')
    records={e['case']:e for e in read(INPUT/'records.json')}
    rows=[json.loads(s) for s in (OUT/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==len(protocol['jobs'])==120 and len({r['run_id'] for r in rows})==120
    spec=importlib.util.spec_from_file_location('_b1_frozen_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py');aud=importlib.util.module_from_spec(spec);spec.loader.exec_module(aud)
    audits=[];offline=[];stages=[];core_count=structural_count=0
    for row,j in zip(rows,protocol['jobs']):
        assert all(row[k]==v for k,v in j.items())
        p=OUT/'runs'/(j['run_id']+'.json')
        if row['worker_status']!='returned':assert not row['valid'];continue
        payload=read(p);raw=payload['raw'];c=read(Path(j['case']));e=records[j['case']]
        assert payload['case_sha256']==sha(Path(j['case'])) and payload['method']==j['method'] and payload['budget']==j['budget']
        assert payload['seed']==raw['seed']==c['metadata']['range_diagnostic']['paired_seed']
        assert raw['seconds']==row['seconds']<=payload['solve_plus_audits_seconds']+1e-6
        assert row['overrun_gt_10ms']==(raw['seconds']>j['budget']+.01)
        s=SimpleNamespace(free=set(map(tuple,c['free'])),targets=set(map(tuple,c['targets'])),covered=set(map(tuple,c['covered'])),current=tuple(c['current']),base=tuple(c['base']),radius=0,distance_budget=c['distance_budget'])
        route=tuple(map(tuple,raw['route']));a=aud.audit(s,route) if route else None
        valid=bool(a and a['valid']);assert valid==row['valid'];assert payload['independent_route_check']==route_check(c,route)
        if valid:assert a==raw['independent_audit'] and a['length']==row['steps']
        audits.append(dict(run_id=j['run_id'],valid=valid,steps=row['steps']))
        if j['method']=='P2_MULTI':continue
        d=raw['detail'];cfg=e['plan']['plans']['R_PLUS1'];segments=e['segments'][j['method']]
        if d['range_plan'] is not None:assert d['range_plan']==e['plan'];structural_count+=1
        if d['responsibilities'] is not None:assert d['responsibilities']==e['responsibilities']
        if d['outside'] is not None:
            o=d['outside'];assert [o['prefix'],o['suffix']]==segments
            assert o['saved_steps']==len(e['segments']['LITERAL'][0])+len(e['segments']['LITERAL'][1])-len(segments[0])-len(segments[1])
        for k in ('acceptances','core_acceptances'):assert all(0<=v['seconds']<=j['budget'] for v in d[k])
        stages.append(dict(run_id=j['run_id'],stages=d['stages'],fallback_selected=raw['fallback_selected'],engine_status=d.get('engine',{}).get('status')))
        if not raw['core_route']:continue
        core=tuple(map(tuple,raw['core_route']));patch=tuple(map(tuple,raw['core_patch']));core_count+=1
        assert patch[0]==tuple(c['old_route'][cfg['left']]) and patch[-1]==tuple(c['old_route'][cfg['right']])
        assert set(map(tuple,cfg['required']))<=set(patch)
        splice=segments[0][:-1]+[list(v) for v in patch]+segments[1][1:];assert normalize(core)==splice
        assert aud.audit(s,core)==raw['core_independent_audit'] and raw['core_independent_audit']['valid']
        if j['method']=='LITERAL':
            pre,post=e['segments']['RECONNECT'];replayed=pre[:-1]+[list(v) for v in patch]+post[1:]
            result=aud.audit(s,tuple(map(tuple,replayed)));assert result['valid']
            saved=len(core)-len(replayed);assert saved==len(segments[0])+len(segments[1])-len(pre)-len(post)
            offline.append(dict(run_id=j['run_id'],online=False,literal_core_steps=len(core)-1,replayed_steps=len(replayed)-1,saved_steps=saved,valid=True))
    paired=[]
    for ref in ('RAW','P2_REF'):
        for b in (1,20):
            lookup={(r['map_id'],r['method']):r for r in rows if r['reference']==ref and r['budget']==b}
            maps=sorted({k[0] for k in lookup})
            for x,y in [('RECONNECT','LITERAL'),('LITERAL','P2_MULTI'),('RECONNECT','P2_MULTI')]:
                vals=[];failed=[]
                for mid in maps:
                    a,z=lookup[mid,x],lookup[mid,y]
                    if not a['valid'] or not z['valid']:failed.append(mid);continue
                    vals.append(dict(map_id=mid,x_steps=a['steps'],y_steps=z['steps'],difference=a['steps']-z['steps'],relative=a['steps']/z['steps']-1))
                paired.append(dict(reference=ref,budget=b,x=x,y=y,shorter=sum(v['difference']<0 for v in vals),equal=sum(v['difference']==0 for v in vals),longer=sum(v['difference']>0 for v in vals),mean_relative=statistics.mean(v['relative'] for v in vals) if vals else None,sum_difference=sum(v['difference'] for v in vals),unpaired=failed,per_map=vals))
    stats=[]
    for ref in ('RAW','P2_REF'):
        for b in (1,20):
            for m in METHODS:
                rr=[r for r in rows if (r['reference'],r['budget'],r['method'])==(ref,b,m)];times=[r['seconds'] for r in rr if r['seconds'] is not None]
                stats.append(dict(reference=ref,budget=b,method=m,valid=sum(r['valid'] for r in rr),sum_steps=sum(r['steps'] for r in rr if r['valid']),mean_seconds=statistics.mean(times) if times else None,max_seconds=max(times) if times else None,overruns=sum(r['overrun_gt_10ms'] for r in rr),sources={str(v):sum(r['source']==v for r in rr) for v in {r['source'] for r in rr}}))
    VERIFY.mkdir(parents=True,exist_ok=False)
    summary=dict(calls=120,final_audits=len(audits),valid=sum(a['valid'] for a in audits),core_audits=core_count,structural_checks=structural_count,input_checks=len(checks),offline_replays=len(offline),overruns=sum(r['overrun_gt_10ms'] for r in rows),max_overrun_seconds=max((r['seconds']-r['budget'] for r in rows if r['seconds'] is not None),default=0),protected_unchanged=True,holdout_used=False)
    for name,obj in [('summary',summary),('input_checks',checks),('route_checks',audits),('offline_replays',offline),('paired_summary',paired),('method_summary',stats),('stages',stages)]:write(VERIFY/(name+'.json'),obj)
    write(VERIFY/'sha256.json',{str(p.relative_to(VERIFY)):sha(p) for p in VERIFY.rglob('*') if p.is_file()});print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':
    import sys
    if '--inputs' in sys.argv:print(json.dumps(check_inputs(),ensure_ascii=False))
    else:main()
