"""Independent saved-output audit. No candidate regeneration or planner import.
Batch invokes audit_one exactly once per output. CLI default only checks sealed
artifacts and the saved independent audit receipts; it makes no new LOS calls.
"""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
import hashlib,json,time,math
from collections import Counter
import audit_geometry as A
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def audit_one(job,payload_bytes,output_bytes):
    start=time.perf_counter();src=json.loads(payload_bytes);r=json.loads(output_bytes);c=src['input'];path=src['raw']['route'];v=r['vertices'];U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));F=set(map(tuple,c['free']));n=len(path)-1;counts=Counter(geometry=0,service_intersections=0);assert r['id']==job['id']
    assert v[0]==c['current'] and v[-1]==c['base'];assert len(v)==len(r['edges'])+1;assert n<=Decimal(str(c['distance_budget']));assert len(r['edges'])<=n
    original=[];seen=set()
    for k,p in enumerate(path):
        p=tuple(p)
        if p in U and p not in seen:seen.add(p);original.append({'point':list(p),'index':k})
    assert seen==U and original==r['first_original']
    expected_cuts=([0]+[x['index'] for x in original]+[n]) if original else [0,n];assert len(r['parts'])==len(expected_cuts)-1
    cursor=0;sum_sq=[];bykind=Counter();credit_candidates={};points=[tuple(p) for p in v]
    if points[0] in U:credit_candidates[points[0]]=(-1,Fraction(0))
    for k,e in enumerate(r['edges']):
        left,right=e['left'],e['right'];assert left==cursor and left<right<=n;cursor=right;assert e['a']==path[left]==v[k] and e['b']==path[right]==v[k+1]
        p=r['parts'][e['part']];assert p['left']<=left<right<=p['right'];assert p['edge_start']<=k<p['edge_end'];assert e['kind']==p['kind']
        counts['geometry']+=1;assert A.legal(F,v[k],v[k+1]),('illegal_geometry',job['id'],k)
        # Independent credit algorithm records the lexicographically earliest
        # (edge, rational parameter) per task, rather than primary's seen sweep.
        for q in sorted(U):
            counts['service_intersections']+=1;t=A.hit(points[k],points[k+1],q)
            if t is not None:
                when=(k,t)
                if q not in credit_candidates or when<credit_candidates[q]:credit_candidates[q]=when
        sq=sum((a-b)**2 for a,b in zip(v[k],v[k+1]));assert sq<=(right-left)**2;sum_sq.append(sq)
    assert cursor==n or n==0;assert set(credit_candidates)==U
    actual=[{'point':list(p),'edge':when[0],'t':str(when[1])} for p,when in sorted(credit_candidates.items(),key=lambda z:(z[1],z[0]))];assert actual==r['first_actual'];assert r['actual_order_changed']==([x['point'] for x in original]!=[x['point'] for x in actual])
    def bounds(squares):
        with localcontext() as cx:
            cx.prec=60;lo=hi=Decimal(0)
            for sq in squares:
                root=math.isqrt(sq)
                if root*root==sq:a=b=Decimal(root)
                else:z=Decimal(sq).sqrt();a=z.next_minus();b=z.next_plus()
                cx.rounding=ROUND_FLOOR;lo+=a
                cx.rounding=ROUND_CEILING;hi+=b
            return lo,hi
    lo,hi=bounds(sum_sq);savedlo,savedhi=map(Decimal,r['Lshortcut_interval']);assert savedlo<=lo<=hi<=savedhi;assert savedhi<=n and savedhi<=Decimal(str(c['distance_budget']))
    covered=[]
    for k,p in enumerate(r['parts']):
        assert [p['left'],p['right']]==expected_cuts[k:k+2];covered+=list(range(p['left'],p['right']));ss=sum_sq[p['edge_start']:p['edge_end']];pl,ph=bounds(ss);a,b=map(Decimal,p['new_interval']);assert a<=pl<=ph<=b;bykind[p['kind']]+=p['L4'];assert p['L4']==p['right']-p['left']
    assert covered==list(range(n)) and sum(bykind.values())==n
    cross=Counter();trace=src['raw'].get('trace',[])
    for p in r['parts']:
        for i in range(p['left'],p['right']):
            hist=[t for t in trace if t['index']<=i];cross[p['kind']+' x '+(hist[-1]['kind'] if hist else 'unavailable')]+=1
    assert dict(cross)==r['trace_cross_original_moves']
    assert r['counts']['candidate']==len(r['query_log'])<=job['limits']['candidate_geometry'];assert r['counts']['source_validation']==n;assert r['counts']['output_validation']==len(r['edges']);assert r['counts']['service_intersections']==len(r['edges'])*len(U)
    assert counts['geometry']<=job['limits']['independent_geometry'] and counts['service_intersections']<=job['limits']['independent_service_intersections']
    return {'passed':True,'id':job['id'],'input_sha256':hashlib.sha256(payload_bytes).hexdigest(),'output_sha256':hashlib.sha256(output_bytes).hexdigest(),'counts':dict(counts),'seconds':time.perf_counter()-start,'independent_length_interval':[str(lo),str(hi)],'geometry_method':'closed forbidden squares exact slab intersection; bounding-box exterior forbidden','service_method':'earliest exact coordinate-parameter intersection per task'}
def main():
    for p,v in read(H/'frozen_manifest.json')['files'].items():assert sha(H/p)==v,p
    for p,v in read(H/'来源hash.json').items():assert sha(Path(p))==v,p
    if (H/'completion_manifest.json').exists():
        for p,v in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==v,p
    jobs=read(H/'117固定清单.json');status=read(H/'batch_status.json');passed=0
    for j in jobs:
        assert sha(H/j['payload'])==j['payload_sha256']
        ap=H/'audits'/(j['id']+'.json')
        if ap.exists():
            a=read(ap);assert a['passed'] and a['input_sha256']==sha(H/j['payload']) and a['output_sha256']==sha(H/'outputs'/(j['id']+'.json'));passed+=1
    assert passed==len(status['completed']);print(json.dumps({'passed':True,'fixed_routes':len(jobs),'independently_audited_outputs':passed,'this_readonly_receipt_check_geometry_queries':0,'saved_audit_geometry_queries':sum(read(p)['counts']['geometry'] for p in (H/'audits').glob('*.json'))},ensure_ascii=False))
if __name__=='__main__':main()
