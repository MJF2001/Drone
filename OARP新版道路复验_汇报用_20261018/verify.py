"""Read-only verification, no solver imports or calls."""
import collections,hashlib,json
from pathlib import Path
import independent as ind
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert all(sha(ROOT/p)==h for p,h in read('freeze.json').items())
    assert all(sha(p)==h for p,h in read('protection.json').items())
    assert all(sha(p)==h for p,h in read('dependencies_before.json')['files'].items())
    rows=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    starts={};ends={};active=set()
    for e in rows:
        assert e['event'] in ('start','end') and 'error' not in e
        target=starts if e['event']=='start' else ends;ident=e['attempt_id'];assert ident not in target;target[ident]=e
        if e['event']=='start':
            if e.get('parent'):assert e['parent'] in active
            active.add(ident)
        else:assert ident in active;active.remove(ident)
    assert not active and starts.keys()==ends.keys()
    counts=collections.Counter(e['kind'] for e in starts.values());assert counts['response']==20 and counts['SCIP']<=40 and counts['GLNS']<=20
    planned=read('protocol.json')['planned'];actual=[e['plan_id'] for e in starts.values() if e['kind']=='response']
    assert len(set(actual))==20 and set(actual)=={j['plan_id'] for j in planned}=={p.stem for p in (ROOT/'results').glob('*.json')}
    valid=complete=timely=core_candidates=0
    for j in planned:
        r=read('results/'+j['plan_id']+'.json');d=read('inputs/'+j['case']+'.json');req=r['request'];ident=r['attempt_id']
        assert starts[ident]['plan_id']==j['plan_id'] and ends[ident]['result_sha256']==sha(ROOT/'results'/f"{j['plan_id']}.json")
        assert r['input_sha256']==sha(ROOT/'inputs'/f"{j['case']}.json") and req['seed']==j['seed'] and req['case_id']==j['case']
        for a,b in (('F','free'),('C','covered'),('current','current'),('base','base'),('old_suffix','old_route')):assert req[a]==d[b]
        assert req['P']==d['metadata']['published_targets'] and req['resource']==d['distance_budget']
        assert r['method']=='RANK0' and r['cap'] is None and 'error' not in r['core_detail']
        ok=not ind.audit(req,r['route']);assert ok==r['flags']['route_valid'];valid+=ok
        assert r['flags']['call_within_budget']==(r['public_seconds']<120);timely+=ok and r['flags']['call_within_budget']
        for c in r['candidates']:assert not ind.audit(req,c['route']) and c['generated']<=c['audited']<120 and c['accepted']==c['audited']
        if r['candidates']:
            best=min(r['candidates'],key=lambda c:(len(c['route']),c['accepted']));assert best['route']==r['route'] and best['source']==r['source']
        if r['core_plan']:
            assert not ind.audit(req,r['core_plan']['route']);ind.check_strips(r['core_plan'],ind.targets(req))
            assert all(b['kind']=='rank' for b in r['core_detail']['blocks'])
            gl=[e for e in rows if e.get('parent')==ident and e['kind']=='GLNS']
            assert len(gl)==2;st=next(e for e in gl if e['event']=='start');en=next(e for e in gl if e['event']=='end')
            assert st['matrix']==r['core_detail']['tour']['matrix'] and st['sets']==r['core_detail']['tour']['sets']
            assert all(st['params'][k]==v for k,v in read('protocol.json')['GLNS'].items()) and st['params']['seed']==j['seed']
            tour=en['tour'];matrix=st['matrix'];assert len(tour)==len(st['sets']) and all(sum(v in g for v in tour)==1 for g in st['sets'])
            assert en['cost']==sum(matrix[a][b] for a,b in zip(tour,tour[1:]+tour[:1]))==len(r['core_plan']['route'])-1
        core_candidates+=r['flags']['core_candidate_valid'];complete+=r['core_complete']
        assert r['core_complete']==bool(r['flags']['core_candidate_valid'] and r['core_detail'].get('core_natural') and r['flags']['call_within_budget'])
        assert read('supervisor/'+j['plan_id']+'.json')['exit_code']==0
    assert ind.selftest()['passed']
    if (ROOT/'manifest.json').exists():assert all(sha(ROOT/p)==h for p,h in read('manifest.json').items())
    result={'verification':'PASS','full_calls':20,'counts':dict(counts),'legal_final_routes':valid,'core_candidates':core_candidates,
        'core_complete':complete,'timely_legal':timely,'protected_files_unchanged':len(read('protection.json')),'new_solver_calls':0}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':main()
