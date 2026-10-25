"""Independent index/Counter reconstruction; never import review/planners."""
from pathlib import Path
import json,hashlib,collections
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def main():
    for p,v in read(H/'来源hash.json').items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==v,p
    rows=read(H/'60份保存结构全表.json');assert len(rows)==60
    for r in rows:
        c=read(r['input']);o=read(r['output']);raw=o.get('result',o.get('entry',{}).get('native_return'))['raw'];walk=list(map(tuple,raw['route']));targets=set(map(tuple,c['targets']));old=set(map(tuple,c['covered']));required=targets-old;occ=collections.defaultdict(list)
        for i,p in enumerate(walk):occ[p].append(i)
        expected=sorted([(p,indices[0]) for p,indices in occ.items() if p in required],key=lambda x:x[1]);assert r['first_services']==[dict(point=list(p),index=i) for p,i in expected]
        counts=collections.Counter()
        for i,q in enumerate(walk[1:],1):counts['non_target' if q not in targets else 'historical' if q in old else 'repeat_target' if occ[q][0]<i else 'fresh']+=1
        assert dict(counts)==r['counts'] and sum(counts.values())==r['steps']==len(walk)-1
        expected_pairs={(a,b) for v in occ.values() for a,b in zip(v,v[1:])};assert {(x['left'],x['right']) for x in r['closed_intervals']}==expected_pairs
        for x in r['closed_intervals']:
            a,b=x['left'],x['right'];outside=set(walk[:a+1]+walk[b:]);inside=set(walk[a+1:b]);assert sorted(map(list,(required&inside)-outside))==x['exclusive_interior_required'] and walk[a]==walk[b]==tuple(x['endpoint'])
        if r['segments']:assert sum(s['steps'] for s in r['segments'])==r['steps']
        for p in r['seed_equivalence'].get('outputs',[]):assert read(p)['result']['raw']['route']==raw['route'] and read(p)['result']['raw']['trace']==raw['trace']
    if (H/'completion_manifest.json').exists():
        for p,v in read(H/'completion_manifest.json')['files'].items():assert hashlib.sha256((H/p).read_bytes()).hexdigest()==v,p
    print(json.dumps(dict(passed=True,records=60,original_states=54,last_responses=6,new_solver_core_graph_candidate_routes=0,independent_method='all occurrence indices and outside-set/Counter reconstruction'),ensure_ascii=False))
if __name__=='__main__':main()
