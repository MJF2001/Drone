"""Saved-data-only final checks. Independent reward audit; no planner imports."""
from common import *
from analyze import compute
from decision_audit import saved_audit,paired_audit
import sys,ast
def csvcheck(name,rows):
    p=H/name;csv.field_size_limit(max(131072,p.stat().st_size))
    with p.open(encoding='utf-8-sig',newline='') as f:got=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict,tuple)) else '' if r.get(k) is None else str(r[k]) for k in keys} for r in rows];assert got==expected,name
def main():
    for n in ('technical','action_stubs','preseal','OFF','ON'):require(n)
    seal=preseal();assert sha(sys.executable)==seal['python_sha256']
    for p,h in seal['files'].items():assert sha(p)==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    for p,h in read(H/'old_v04_hashes.json').items():assert sha(p)==h,p
    for s in read(H/'states_metadata.json'):assert (H/'inputs'/f'input_{s["index"]:03d}.json').read_bytes()==(B/s['input']).read_bytes()
    order=read(H/'order.json');actual=[json.loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert len(order)==len(actual)==plan()['entry_cap'] and [j['id'] for j in order]==[j['id'] for j in actual]
    totals=collections.Counter()
    for j in order:
        q=read(H/'logs'/f'{j["id"]}.receipt.json');totals['entries']+=q['markers']['entries'];totals['cores']+=q['markers']['cores'];file=H/'outputs'/f'{j["id"]}.json'
        if not file.exists():assert j['mode']=='ON' and q['status'] in ('WATCHDOG','PROCESS_ABNORMAL');continue
        x=read(file);assert x['job']==j and x['input_sha256']==sha(H/j['input']) and x['result']['seed']==j['seed'] and x['result']['budget']==20 and x['result']['diagnostic_entry']==LABEL and x['result']['diagnostic_mode']==j['mode']
        assert set(x['runtime_reads'])=={str(H/j['input'])} and len(x['actual_core_calls'])==q['markers']['cores'] and x['caller_wall_seconds']>=x['result']['entry_seconds']
        for p,h in x['imports'].items():assert seal['files'][p]==h==sha(p)
    a=compute();assert a==read(H/'analysis.json');assert read(H/'OFF_metrics.json')==[r for r in a['rows'] if r['job']['mode']=='OFF']
    assert read(H/'protection_equivalence.json')==[dict(state=p['state'],seed=p['seed'],proof=p['action_proof']) for p in a['pairs'] if not p['trigger_expected']]
    csvcheck('288调用完整指标.csv',[dict(**r['job'],valid=r['valid'],timely=r['timely'],status=r['status'],seconds=r['seconds'],**(r['metrics'] or {})) for r in a['rows']]);csvcheck('144全部OFF_ON配对.csv',[{k:v for k,v in p.items() if k not in ('OFF','ON')} for p in a['pairs']]);csvcheck('48状态三seed原值均值范围.csv',a['states']);csvcheck('分层结果.csv',[dict(layer=k,**v) for k,v in a['strata'].items()]);assert read(H/'signal.json')==a['signal']
    assert not any(n in sys.modules for n in ('runtime','candidate','ppcpp_independent','p2_adapter'))
    print('PASS preseal/source/byte-identical inputs, fixed slots, input-read/core ledgers, all OFF equivalences and protection pairs',flush=True)
    print('PASS independent full-prefix/reward/goal/one-exception/credit/return/resource audits, dual metrics,144 pairs/48 states/all failures, explicit state-equal signal and CSV',flush=True)
    print(json.dumps(dict(status='ALL PASS',real_entry_markers=totals['entries'],real_core_markers=totals['cores'],new_planner_calls=0,external_BFS_this_verify=0,external_Dijkstra_this_verify=0,signal=a['signal']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
