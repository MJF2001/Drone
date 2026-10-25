"""Final read-only reproduction. No solver or exact-search calls."""
import json,sys,time
from pathlib import Path
from bridge_run import H,R,read,sha
from bridge_preflight import matching
from bridge_graph import structure
from bridge_analysis_v02 import compute,double,scalar
def verify():
    original=(H/'bridge_analysis.py').read_text(encoding='utf8')
    assert original.replace('else:assert cuts==read(H/','else:assert json.loads(json.dumps(cuts))==read(H/')==(H/'bridge_analysis_v02.py').read_text(encoding='utf8')
    for sealname in ('prep_seal.json','event_seal.json'):
        seal=read(H/sealname)
        for p,h in seal['files'].items():assert sha(p)==h,(sealname,p)
        print('PASS source/input seal',sealname,len(seal['files']),flush=True)
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    assert matching()==read(H/'matching_review.json')
    print('PASS deterministic geometry, real history, 24 matched triples, witness budgets',flush=True)
    for i,p in enumerate(sorted((H/'inputs').glob('*.json'))):
        c=read(p);st=read(H/'structure'/p.name);assert json.loads(json.dumps(structure(c)))==st['structure'],p
        if (i+1)%12==0:print('PASS graph connectivity, all-edge deletion bridges/cut lower bounds',i+1,'/72',flush=True)
    records=[json.loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()]
    assert len(records)==450 and len({r['id'] for r in records})==450
    assert all(r['code']==0 for r in records)
    assert all(a['finished_utc']<=b['started_utc'] for a,b in zip(records,records[1:]))
    assert [r['id'] for r in records if r['phase']=='prep']==read(H/'base_order.json')
    eventseal=read(H/'event_seal.json');prepseal=read(H/'prep_seal.json')
    assert prepseal['created_utc']<min(r['started_utc'] for r in records)
    assert max(r['finished_utc'] for r in records if r['phase']=='prep')<eventseal['created_utc']<min(r['started_utc'] for r in records if r['phase']=='gate')
    for phase,folder in (('prep','prep_outputs'),('gate','gate_outputs'),('formal','outputs')):
        rr=[r for r in records if r['phase']==phase]
        if phase!='prep':assert [r['id'] for r in rr]==[j['id'] for j in read(H/(phase+'_order.json'))]
        for record in rr:
            o=read(H/folder/(record['id']+'.json'));j=o['job'];seal=read(H/j['seal'])['files']
            assert o['input_sha256']==sha(H/j['input'])
            for p,h in o['imports'].items():assert sha(p)==h==seal[p],p
            assert o['native_file']==str((R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').resolve())
            assert o['native_sha256']==sha(o['native_file'])==seal[o['native_file']]
            assert record['started_utc']<=o['call_utc']<=record['finished_utc']
            if phase=='gate':
                x=o['result'];route=x['raw'].get('route');assert bool(route)==(j['expected']=='complete')
                if route:
                    c=read(H/j['input']);double(c,route)
                    if j['method']=='PPCPP':scalar.audit(c,x['raw']['branches']['P0'])
    print('PASS 450 serial calls, exact fixed orders, actual imports/native hashes, two-stage chronology and 12 gates',flush=True)
    assert compute()==read(H/'analysis.json')
    print('PASS 432 original outputs, every route dual metrics/native decisions, cut/group/entry-exit accounting, seed means/strata/signal/examples',flush=True)
    from bridge_independent_cuts import verify as independent_cuts
    print('PASS independent union-find cuts and side-transition/first-visit ledgers',independent_cuts(),flush=True)
    from bridge_example_paths import compute as example_compute
    assert json.loads(json.dumps(example_compute()))==read(H/'example_shortest_path_ledger.json')
    from bridge_supplement import compute as supplement_compute
    assert supplement_compute()==read(H/'supplement.json')
    import xml.etree.ElementTree as ET
    for path in (H/'figures').glob('*.svg'):assert ET.parse(path).getroot().tag.endswith('svg')
    print('PASS fixed illustration shortest-path ledgers and valid SVGs',flush=True)
    assert read(H/'call_ledger.json')==dict(history_preparation=6,gates=12,formal=432,total_real_entries=450,exact_search=0,extra_retries=0,holdout=0)
    print('ALL PASS. Verification performed zero planner calls and zero exact searches.',flush=True)
if __name__=='__main__':verify()
