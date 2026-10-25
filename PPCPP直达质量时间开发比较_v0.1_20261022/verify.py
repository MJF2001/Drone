"""Saved-result verification only, never reruns planning/postprocessing/LOS."""
from pathlib import Path
from fractions import Fraction
import json,hashlib
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for n,h in read(H/'preregistration_seal.json').items():assert sha(H/n)==h,n
    for p,h in read(H/'source_seal.json').items():assert sha(Path(p))==h,p
    for n,h in read(H/'input_hashes.json').items():assert sha(H/n)==h,n
    if (H/'completion_manifest.json').exists():
        for n,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/n)==h,n
    plan=read(H/'plan.json');attempts=[json.loads(x) for x in (H/'attempts.jsonl').read_text(encoding='utf8').splitlines()];assert len(attempts)<=336 and len({a['id'] for a in attempts})==len(attempts);jobs=plan['technical']+plan['formal'];assert [a['id'] for a in attempts]==[j['id'] for j in jobs[:len(attempts)]];count=0;counts={k:0 for k in ('candidate','source_validation','output_validation','service_intersections','independent_geometry','independent_service')}
    for j in jobs:
        p=H/'outputs'/(j['id']+'.json')
        if not p.exists():continue
        x=read(p);assert x['job']==j and x['audit']['passed'];c=read(H/j['input']);raw=x['native']['raw'];old=raw['route'];post=x['post'];new=post['vertices'];U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));F=set(map(tuple,c['free']));assert old[0]==new[0]==c['current'] and old[-1]==new[-1]==c['base'];assert U<=set(map(tuple,old)) and all(tuple(p) in F for p in old);assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(old,old[1:]));n=len(old)-1;assert post['L4']==n<=c['distance_budget'];assert set(map(tuple,c['deferred_targets']))==set(map(tuple,c['published_targets']))-F-set(map(tuple,c['covered']));assert x['limits']['independent_geometry']==n and x['limits']['independent_service_intersections']==n*len(U)
        def encoded(a):return json.dumps(a,ensure_ascii=False,separators=(',',':')).encode('utf8')
        assert hashlib.sha256(encoded(x['audit_payload'])).hexdigest()==x['audit']['input_sha256'];assert hashlib.sha256(encoded(post)).hexdigest()==x['audit']['output_sha256'];assert len(post['edges'])<=n;assert set(map(tuple,[e['point'] for e in post['first_actual']]))==U;assert post['actual_order_changed']==([e['point'] for e in post['first_actual']]!=[e['point'] for e in post['first_original']]);cursor=0
        for i,e in enumerate(post['edges']):assert e['left']==cursor and e['right']>cursor;cursor=e['right'];assert e['a']==old[e['left']]==new[i] and e['b']==old[e['right']]==new[i+1]
        assert cursor==n;lo,hi=map(Fraction,post['Lshortcut_interval']);assert lo<=hi<=n and hi<=Fraction(str(c['distance_budget']));t=x['timing'];assert abs(t['original_seconds']+t['post_increment_seconds']-t['pipeline_seconds'])<1e-10;assert t['original_seconds']>=x['native']['entry_seconds']>=0;assert t['pipeline_seconds']>=t['original_seconds'];assert post['counts']['candidate']<=4096 and post['counts']['source_validation']==n and post['counts']['output_validation']==len(post['edges']);assert x['audit']['counts']['geometry']<=n and x['audit']['counts']['service_intersections']<=n*len(U)
        for k in ('candidate','source_validation','output_validation','service_intersections'):counts[k]+=post['counts'][k]
        counts['independent_geometry']+=x['audit']['counts']['geometry'];counts['independent_service']+=x['audit']['counts']['service_intersections'];count+=1
    assert count==len(read(H/'status.json')['completed'])
    if (H/'全部流水线.json').exists():
        import statistics,math
        rows=read(H/'全部流水线.json');summary=read(H/'summary.json');assert len(rows)==count
        for row in rows:
            x=read(H/'outputs'/(row['id']+'.json'));assert row['original_seconds']==x['timing']['original_seconds'] and row['pipeline_seconds']==x['timing']['pipeline_seconds'] and row['shortcut_lower']==x['post']['Lshortcut_interval'][0] and row['shortcut_upper']==x['post']['Lshortcut_interval'][1]
        for method in ('PPCPP','P2_MULTI'):
            rr=[r for r in rows if r['phase']=='formal' and r['method']==method];s=summary[method];assert len(rr)==s['n']==162;times=sorted(r['pipeline_seconds'] for r in rr);assert s['pipeline_seconds_median']==statistics.median(times) and s['pipeline_seconds_p95']==times[math.ceil(.95*len(times))-1] and s['pipeline_seconds_max']==max(times)
        ps=read(H/'同状态同seed配对.json');states=read(H/'54状态等权视图.json');assert len(ps)==162 and len(states)==54
        for state in states:
            aa=[p for p in ps if p['case']==state['case']];assert len(aa)==3;assert abs(state['saved_seconds']-sum(p['saved_seconds'] for p in aa)/3)<1e-10;lo=sum(Fraction(p['difference_lower']) for p in aa);hi=sum(Fraction(p['difference_upper']) for p in aa);sign='longer' if lo>0 else ('shorter' if hi<0 else ('equal' if all(p['interval_sign']=='equal' for p in aa) else 'uncertain'));assert sign==state['sign']
        assert abs(summary['B_vs_C']['state_equal_mean_saved_seconds']-sum(s['saved_seconds'] for s in states)/54)<1e-10
    print(json.dumps({'passed':True,'started':len(attempts),'saved_valid_pipelines':count,'new_planner_postprocessing_geometry_calls_in_verify':0,'saved_query_totals':counts},ensure_ascii=False))
if __name__=='__main__':main()
