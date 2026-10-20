"""Post-batch strengthened audit: raw SCIP vectors and every GTSP matrix edge.
Read-only, stdlib + independent geometry; no planner or solver imports.
"""
import ast,collections,hashlib,json
from pathlib import Path
import independent as ind
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def endpoints(ranks):return {(r['axis'],s,tuple(r['cells'][i])) for r in ranks for s,i in (('L',0),('R',-1))}
def rankkey(r):return r['axis'],tuple(r['cells'][0]),tuple(r['cells'][-1])
def raw(result,record):
    assert record['status']=='optimal' and record['has_incumbent']
    vals=record['values'];mapping=record['mapping'];eps=1e-6
    o={ast.literal_eval(k):vals[v] for k,v in mapping['orientation'].items()}
    y={ast.literal_eval(k):vals[v] for k,v in mapping['endpoint'].items()}
    Q=ind.targets(result['request']);ranks=result['core_detail']['ranks']
    assert set(o)=={(a,p) for p in Q for a in ('H','V')}
    assert set(y)=={(a,s,p) for p in Q for a in ('H','V') for s in ('L','R')}
    assert all(v is not None and -eps<=v<=1+eps and abs(v-round(v))<eps for v in vals.values())
    dirs={tuple(p):r['axis'] for r in ranks for p in r['cells']}
    for p in Q:
        assert abs(o['H',p]+o['V',p]-1)<eps and o[dirs[p],p]>.5
        for axis,(dx,dy) in (('H',(1,0)),('V',(0,1))):
            for side,sign in (('L',-1),('R',1)):
                assert y[axis,side,p]+eps>=o[axis,p]-o.get((axis,(p[0]+sign*dx,p[1]+sign*dy)),0)
    now=endpoints(ranks);assert {k for k,v in y.items() if v>.5}==now
    assert abs(sum(y.values())/2-len(ranks))<eps
    old=read('events/'+result['request']['case_id']+'.json')['reference'] if result['method']=='REPLAN2' else []
    previous=endpoints(old);filtered={k for k in previous if k[2] in Q}
    alpha=len(now-filtered);beta=sum(dirs[p]==axis for axis,side,p in filtered-now)
    oldkeys={rankkey(r) for r in old};metrics={'rank_count':len(ranks),'new_rank_count':sum(rankkey(r) not in oldkeys for r in ranks),
        'added_endpoints':alpha,'extended_endpoints':beta,'endpoint_bound':alpha+beta/2}
    assert metrics==result['core_detail']['metrics']
    changed=0
    if result['method']=='REPLAN2':
        order=[(a,s,p) for p in sorted(Q) for a in ('H','V') for s in ('L','R')]
        names=mapping['auxiliary_beta_names'];assert len(order)==len(names)
        assert [int(n[1:]) for n in names]==sorted(int(n[1:]) for n in names)
        for k,name in zip(order,names):
            axis,side,p=k;assert vals[name]+eps>=(1-y[k] if k in previous else 0)+o[axis,p]-1
        assert abs(sum(vals[n] for n in names)-beta)<eps
        changed=sum(v for k,v in y.items() if k not in previous)+sum(vals[n] for n in names)/2
        assert abs(changed-metrics['endpoint_bound'])<eps and changed<=result['cap']+eps
    else:assert not mapping['auxiliary_beta_names']
    expected=len(ranks)+(changed/(result['cap']+1) if result['method']=='REPLAN2' else 0)
    assert abs(expected-record['objective'])<eps and abs(expected-result['core_detail']['objective'])<eps
    assert abs(record['dual_bound']-expected)<eps and record['gap']<eps

def matrix(result):
    d=result['core_detail'];states=[]
    for b in d['blocks']:
        p=list(map(tuple,b['path']));states.extend((p,p[::-1]))
        # Every declared block member must actually lie on the block at its span.
        for m in b['members']:
            ordered=list(map(tuple,m['cells']));ordered=ordered[::-1] if m['reverse'] else ordered
            assert p[m['start']:m['end']+1]==ordered
        assert sorted((m['axis'],tuple(m['cells'][0]),tuple(m['cells'][-1])) for m in b['members'])==sorted((a,tuple(p),tuple(q)) for a,p,q in b['rank_keys'])
    assert sorted(rankkey(r) for r in d['ranks'])==sorted((a,tuple(p),tuple(q)) for b in d['blocks'] for a,p,q in b['rank_keys'])
    start=len(states);end=start+1;states.extend(([tuple(result['request']['current'])],[tuple(result['request']['base'])]))
    g=ind.Geometry(result['request'])
    edges={(i,j):len(states[i])-1+len(g.path(states[i][-1],states[j][0]))-1
        for i in range(start+1) for j in range(end+1) if i!=j and j!=start}
    penalty=(len(states)+1)*(max(edges.values(),default=0)+1)
    mat=[[edges.get((i,j),penalty) for j in range(len(states))] for i in range(len(states))];mat[end][start]=0
    assert mat==d['tour']['matrix'];assert d['tour']['sets']==[[i,i+1] for i in range(0,start,2)]+[[start],[end]]
    return sum(len(row) for row in mat)

def main():
    records=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    rawcount=edges=0
    for job in read('protocol.json')['planned']:
        r=read('results/'+job['plan_id']+'.json')
        rr=[e for e in records if e.get('parent')==r['attempt_id'] and e['kind']=='SCIP' and e['event']=='end']
        assert len(rr)==1;raw(r,rr[0]);rawcount+=1;edges+=matrix(r)
        gl=[e for e in records if e.get('parent')==r['attempt_id'] and e['kind']=='GLNS' and e['event']=='end']
        assert len(gl)==1 and not gl[0]['timeout']
        assert r['core_detail']['status']=='optimal' and r['core_detail']['core_natural'] and r['core_complete']
    # Evidence corruption must be rejected by the mathematical checker itself.
    sample=read('results/prep_rect6x3.json')
    rr=next(e for e in records if e.get('parent')==sample['attempt_id'] and e['kind']=='SCIP' and e['event']=='end')
    bad=json.loads(json.dumps(rr));name=next(iter(bad['values']));bad['values'][name]=.25
    try:raw(sample,bad)
    except AssertionError:pass
    else:raise AssertionError('corrupt raw orientation accepted')
    bad=json.loads(json.dumps(sample));bad['core_detail']['tour']['matrix'][0][1]+=1
    try:matrix(bad)
    except AssertionError:pass
    else:raise AssertionError('corrupt matrix accepted')
    print(json.dumps({'extra_audit':'PASS','raw_SCIP_vectors':rawcount,'GTSP_matrices':rawcount,
        'matrix_entries_recomputed':edges,'corrupt_raw_vector_and_matrix_negatives':2,'new_solver_calls':0,
        'timing':'checker added after main batch; not claimed as a preflight'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
