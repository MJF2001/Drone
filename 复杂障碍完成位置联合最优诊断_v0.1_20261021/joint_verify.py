"""One-key read-only audit. Never imports or calls either exact solver."""
import json,csv,xml.etree.ElementTree as ET
from joint_common import H,R,read,sha,normal,account,query
from joint_generate import construct,layouts
from joint_analysis import compute
from joint_proof import audit
def csvcheck(path,rows):
    with path.open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    assert len(actual)==len(rows)
    for saved,row in zip(actual,rows):
        for k,v in row.items():
            text='' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else str(v)
            assert saved[k]==text,(path,k)
def verify():
    for filename in ('prep_seal.json','event_seal.json'):
        for p,h in read(H/filename)['files'].items():assert sha(p)==h,p
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    print('PASS two-stage source/environment/input seals and final manifest',flush=True)
    rebuilt=construct();assert rebuilt['states']==read(H/'states.json') and rebuilt['histories']==read(H/'histories.json')
    for name,c in rebuilt['inputs'].items():assert c==read(H/'inputs'/f'{name}.json')
    for j in read(H/'prep_order.json'):account(read(H/j['input']),read(H/'prep_outputs'/f'{j["id"]}.json')['result']['raw']['route'])
    assert rebuilt['ordinary_graph_counts']==read(H/'generation_counts.json')
    print('PASS original layout AST/rng, 2 real histories/4 earliest prefixes, all16 inputs/H/heading/old plans/deferred/connectivity, D4 and dedup basis',flush=True)
    calls=[json.loads(s) for s in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert len(calls)==98 and len({r['id'] for r in calls})==98
    assert all(r['code']==0 for r in calls) and all(x['finished_utc']<=y['started_utc'] for x,y in zip(calls,calls[1:]))
    phases=[('prep','prep_outputs','prep_order.json'),('gate','exact','gate_order.json'),('formal','outputs','formal_order.json'),('exact','exact','exact_templates.json')]
    for phase,folder,orderfile in phases:
        assert [r['id'] for r in calls if r['phase']==phase]==[j['id'] for j in read(H/orderfile)]
        for record in [r for r in calls if r['phase']==phase]:
            x=read(H/folder/f'{record["id"]}.json');j=x['job'];frozen=read(H/j['seal'])['files'];assert record['started_utc']<=x['call_utc']<=record['finished_utc']
            for p,h in x['imports'].items():assert sha(p)==h==frozen[p],p
            assert j==read(H/'jobs'/f'{j["id"]}.json')
            if phase in ('prep','formal'):
                assert x['input_sha256']==sha(H/j['input']);c=read(H/j['input']);account(c,x['result']['raw']['route']);assert x['result']['eligible'] and x['result']['entry_seconds']<20
            else:
                assert x['request']==read(H/j['request']) and x['request_sha256']==sha(H/j['request']);assert x['query_seconds']<60
                if phase=='gate':
                    g=next(g for g in read(H/'gate_fixtures.json') if g['id']==j['fixture']);assert x['request']==g['request'];r=x['result'];assert r['length']==g['expected'] and r['status']==('optimal' if g['expected'] is not None else 'infeasible');audit(x['request'],r,H/x['certificate'])
                    if r['route']:account(g['input'],r['route'],x['request']['last'])
    prep=read(H/'prep_seal.json')['created_utc'];event=read(H/'event_seal.json')['created_utc'];assert prep<min(r['started_utc'] for r in calls)
    assert max(r['finished_utc'] for r in calls if r['phase']=='prep')<event<min(r['started_utc'] for r in calls if r['phase']=='gate')
    print('PASS 98 actual serial calls:18 PPCPP/80 exact;8 manual gates×2; strict clocks, actual source hashes, sequence and seal chronology',flush=True)
    a=compute();assert a==read(H/'analysis.json')
    csvcheck(H/'16状态最优分解.csv',a['rows']);csvcheck(H/'全部精确路线双指标.csv',a['all_exact_solution_metrics']);csvcheck(H/'分层.csv',[dict(dimension=field,value=value,**x) for field,vals in a['strata'].items() for value,x in vals.items()])
    for row in a['rows']:
        fig=read(H/'figures'/f'{row["id"]}.json');assert fig['row']==row and fig['state']==next(s for s in rebuilt['states'] if s['id']==row['id']);assert fig['input_sha256']==sha(H/'inputs'/f'{row["id"]}.json');assert ET.parse(H/'figures'/f'{row["id"]}.svg').getroot().tag.endswith('svg')
    for r in read(H/'geometry_opening_audit.json'):
        st=next(s for s in rebuilt['states'] if s['id']==r['id']);f=set(map(tuple,rebuilt['inputs'][r['id']]['free']));template=layouts(st['w'],st['h'])[st['kind']];assert r['newly_opened']==normal(sorted(f-template))
    ledger=read(H/'call_ledger.json');assert ledger['PPCPP_entries']==18 and ledger['coverage_exact_searches']==80 and ledger['verification_coverage_searches']==0 and ledger['verification_planner_calls']==0
    print('PASS all64 formal saved proofs with predecessor/depth/low-level closure, independently executed BFS-Dijkstra pairs, full metrics/last-acquisition/resource, G=O+E, all strata/zero cases/figures',flush=True)
    print('ALL PASS. Verification launched0 planner or coverage exact searches. Ordinary graph BFS this verify=32 (16 input reconstruction+16 metric distance tables).',flush=True)
if __name__=='__main__':verify()
