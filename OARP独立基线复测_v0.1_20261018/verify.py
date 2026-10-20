"""Read-only independent audits, full run joins, immutable evidence hashes."""
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
    assert all(sha(ROOT/p)==h for p,h in read('sources_before.json').items())
    rows=[json.loads(line) for line in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    starts={};ends={};active=set()
    for e in rows:
        assert e['event'] in ('start','end') and 'error' not in e
        ident=e['attempt_id'];dest=starts if e['event']=='start' else ends
        assert ident not in dest;dest[ident]=e
        if e['event']=='start':
            assert not e.get('parent') or e['parent'] in active
            active.add(ident)
        else:
            assert ident in active;active.remove(ident)
            assert starts[ident]['kind']==e['kind'] and starts[ident].get('parent')==e.get('parent')
    assert not active and starts.keys()==ends.keys()
    counts=collections.Counter(e['kind'] for e in starts.values());protocol=read('protocol.json');jobs=protocol['planned']
    assert counts['response']==len(jobs)==60 and counts['SCIP']<=120 and counts['GLNS']<=60
    actual=[e['plan_id'] for e in starts.values() if e['kind']=='response']
    assert len(set(actual))==60 and set(actual)=={j['plan_id'] for j in jobs}=={p.stem for p in (ROOT/'results').glob('*.json')}
    by_budget={str(b):{'n':0,'legal':0,'timely':0,'core_complete':0,'steps':0,'seconds':0.0,'bootstrap_seconds':0.0,'stage_seconds':{}} for b in (1,20,120)}
    for job in jobs:
        r=read('results/'+job['plan_id']+'.json');d=read('inputs/'+job['case']+'.json');req=r['request'];ident=r['attempt_id']
        assert starts[ident]['plan_id']==ends[ident]['plan_id']==r['plan_id']==job['plan_id']
        assert starts[ident]['freeze_sha256']==sha(ROOT/'freeze.json')
        assert ends[ident]['result_sha256']==sha(ROOT/'results'/f"{job['plan_id']}.json")
        assert req['case_id']==job['case'] and req['seed']==job['seed']
        assert 'old_route' not in req and 'old_suffix' not in req
        assert job['input_sha256']==r['input_sha256']==sha(ROOT/'inputs'/f"{job['case']}.json")
        for a,b in (('F','free'),('C','covered'),('current','current'),('base','base')):assert req[a]==d[b]
        assert req['P']==d['metadata']['published_targets'] and req['resource']==d['distance_budget']
        assert r['method_label']==protocol['method'] and r['method']=='RANK0' and r['cap'] is None
        assert r['external_candidate_policy']=='none' and r['initial_geometry_cache']=='empty'
        assert not r['flags']['fallback_selected'] and 'error' not in r['core_detail']
        assert r['source'] in (None,'core')
        legal=not ind.audit(req,r['route']);assert legal==r['flags']['route_valid']==r['audit']['valid']
        assert r['flags']['call_within_budget']==(r['public_seconds']<job['budget'])
        assert r['flags']['within_budget']==bool(legal and r['flags']['candidate_accepted_in_time'] and r['public_seconds']<job['budget'])
        assert len(r['candidates'])<=1
        for c in r['candidates']:
            assert c['source']=='core' and not ind.audit(req,c['route'])
            assert 0<=c['generated']<=c['audited']<job['budget'] and c['accepted']==c['audited']
            assert c['route']==r['route']==r['core_plan']['route']
        for c in r['diagnostics']:
            assert c['source']=='core'
            assert not c['audit']['valid'] or c['audited']>=job['budget']
        assert r['flags']['core_candidate_valid']==bool(r['candidates'])
        if r['core_plan']:
            # A diagnostic core plan may exceed the resource budget; only accepted
            # candidates must satisfy it. Its grid motion and coverage must hold.
            assert set(ind.audit(req,r['core_plan']['route']))<= {'resource'}
            ind.check_strips(r['core_plan'],ind.targets(req))
            if r['core_plan']['strips']:
                assert all(b['kind']=='rank' for b in r['core_detail']['blocks'])
                gl=[e for e in rows if e.get('parent')==ident and e['kind']=='GLNS']
                assert len(gl)==2
                st=next(e for e in gl if e['event']=='start');en=next(e for e in gl if e['event']=='end')
                assert st['matrix']==r['core_detail']['tour']['matrix'] and st['sets']==r['core_detail']['tour']['sets']
                assert all(st['params'][k]==v for k,v in protocol['GLNS'].items()) and st['params']['seed']==job['seed']
                tour=en['tour'];matrix=st['matrix'];assert len(tour)==len(st['sets'])
                assert all(sum(v in group for v in tour)==1 for group in st['sets'])
                assert en['cost']==sum(matrix[a][b] for a,b in zip(tour,tour[1:]+tour[:1]))==len(r['core_plan']['route'])-1
        assert r['core_complete']==bool(r['flags']['core_candidate_valid'] and r['core_detail'].get('core_natural') and r['flags']['call_within_budget'])
        assert all(0<=v<=r['public_seconds']+1e-6 for v in r['stage_seconds'].values())
        assert sum(r['stage_seconds'].values())<=r['public_seconds']+1e-6
        assert read('supervisor/'+job['plan_id']+'.json')['exit_code']==0
        assert Path(r['imports']['rank']).resolve()==(ROOT/'sources/oarp_replan/ranks.py').resolve()
        assert Path(r['imports']['tour']).resolve()==(ROOT/'sources/oarp_replan/tour.py').resolve()
        g=by_budget[str(job['budget'])];g['n']+=1;g['legal']+=legal;g['timely']+=r['flags']['within_budget'];g['core_complete']+=r['core_complete']
        if legal:g['steps']+=len(r['route'])-1
        g['seconds']+=r['public_seconds'];g['bootstrap_seconds']+=r['bootstrap_seconds']
        for name,v in r['stage_seconds'].items():g['stage_seconds'][name]=g['stage_seconds'].get(name,0.0)+v
    assert ind.selftest()['passed']
    for g in by_budget.values():
        g['total_steps']=g.pop('steps') if g['legal']==g['n'] else None
    if (ROOT/'ledger_seal.json').exists():
        data=(ROOT/'calls.jsonl').read_bytes();seal=read('ledger_seal.json')
        assert len(data)==seal['bytes'] and len(data.splitlines())==seal['lines'] and hashlib.sha256(data).hexdigest()==seal['sha256']
    if (ROOT/'manifest.json').exists():
        assert all(sha(ROOT/p)==h for p,h in read('manifest.json').items())
    result={'verification':'PASS','full_calls':60,'counts':dict(counts),'by_budget':by_budget,
        'old_files_unchanged':len(read('protection.json')),'rank_tour_sources_unchanged':True,'new_solver_calls':0}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':main()
