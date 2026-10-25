"""Read-only saved-data verification, no planner imports or graph searches."""
from common import *
from analyze import compute
from evaluation import job_row
from input_audit import geometry_check
import sys
def csvcheck(name,rows):
    p=H/name;csv.field_size_limit(max(131072,p.stat().st_size))
    with p.open(encoding='utf-8-sig',newline='') as f:got=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict,tuple)) else '' if r.get(k) is None else str(r[k]) for k in keys} for r in rows];assert got==expected,name
def main():
    for n in ('technical','action_stubs','seal1','prep','generated','inputs_audited','seal2','gate','formal'):require(n)
    for name in ('seal1','seal2'):
        seal=check_seal(name);assert sha(sys.executable)==seal['python_sha256']
        for p,h in seal['files'].items():assert sha(p)==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    synthetic=H.name=='SYNTHETIC_NOT_EXPERIMENT'
    if not synthetic:
        for row in read(H/'copy_manifest.json'):assert sha(row['source'])==row['source_sha256']==sha(H/row['target'])==row['target_sha256'] and row['byte_identical']
        assert (H/'algorithm.diff').read_bytes()==b''
        audit=geometry_check(False);expected=read(H/'input_audit.json');audit['ordinary_BFS']=24;assert audit==expected
        assert read(H/'states_metadata.json')==read(H/'states.json')
        states=read(H/'states.json');gate=[];formal=[]
        for st in states:
            for mode in ('FROZEN','OFF'):gate.append(f'gate_{st["id"]}_{mode}')
            for i,seed in enumerate(SEEDS):
                for mode in (('OFF','ON') if (st['index']+i)%2==0 else ('ON','OFF')):formal.append(f'formal_{st["id"]}_{seed}_{mode}')
        assert gate==[j['id'] for j in read(H/'gate_order.json')] and formal==[j['id'] for j in read(H/'order.json')]
    cfg=plan();orders=read(H/'prep_order.json')+read(H/'gate_order.json')+read(H/'order.json');actual=[json.loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()]
    assert len(orders)==len(actual)==cfg['entry_cap'] and [j['id'] for j in orders]==[j['id'] for j in actual];totals=collections.Counter()
    for phase in ('prep','gate','formal'):assert sum(j['phase']==phase for j in orders)==cfg['counts'][phase]
    for j in orders:
        q=read(H/'logs'/f'{j["id"]}.receipt.json');text=(H/'logs'/f'{j["id"]}.txt').read_bytes();assert q['job']==j and q['markers']==dict(entries=text.count(b'ENTRY_START '),cores=text.count(b'CORE_START '));assert max(q['markers'].values())<=1
        totals.update(q['markers']);f=H/'outputs'/f'{j["id"]}.json'
        if not f.exists():assert j['phase']=='formal' and q['status'] in ('WATCHDOG','PROCESS_ABNORMAL');continue
        assert sha(f)==q['output_sha256'];x=read(f);assert x['job']==j and x['input_sha256']==sha(H/j['input'])
        assert set(x['runtime_reads'])=={str(H/j['input'])} and len(x['actual_core_calls'])==q['markers']['cores'] and x['caller_wall_seconds']>=x['result']['entry_seconds']
        assert x['result']['budget']==20 and x['result']['seed']==j['seed'] and set(x['result']['raw'].get('branches',{}))<={'P0'}
        seal=read(H/j['seal'])
        for p,h in x['imports'].items():assert seal['files'][p]==h==sha(p)
        row=job_row(j);assert q['valid']==row['valid'] and q['timely']==row['timely']
        if j['phase']!='formal':assert row['valid'] and row['timely']
    a=compute();assert a==read(H/'analysis.json') and read(H/'formal_metrics.json')==a['rows']
    assert read(H/'gate_metrics.json')==[job_row(j) for j in read(H/'gate_order.json')]
    assert read(H/'prep_metrics.json')==[job_row(j) for j in read(H/'prep_order.json')]
    assert read(H/'OFF_equivalence.json')==[dict(job=r['job'],equivalence=r['equivalence'],all_metrics_equal=True) for r in read(H/'gate_metrics.json') if r['job']['mode']=='OFF']
    assert read(H/'protection_equivalence.json')==[dict(state=p['state'],seed=p['seed'],proof=p['action_proof']) for p in a['pairs'] if not p['trigger_expected']]
    assert read(H/'all_action_audits.json')==[dict(job=r['job'],audit=r.get('audit')) for r in a['rows']]
    csvcheck('288调用完整指标.csv',[dict(**r['job'],valid=r['valid'],timely=r['timely'],status=r['status'],seconds=r['seconds'],**(r['metrics'] or {})) for r in a['rows']]);csvcheck('144全部OFF_ON配对.csv',[{k:v for k,v in p.items() if k not in ('OFF','ON')} for p in a['pairs']]);csvcheck('48状态三seed原值均值范围.csv',a['states']);csvcheck('分层结果.csv',[dict(layer=k,**v) for k,v in a['strata'].items()]);assert read(H/'signal.json')==a['signal']
    assert not any(n in sys.modules for n in ('runtime','candidate','ppcpp_independent','p2_adapter','last_native'))
    print('PASS byte-identical native/hook/timing/candidate/action auditor; two source/input seals; new-bound technical gates; true histories/candidates; all formal/gate pairs and CSV',flush=True)
    print(json.dumps(dict(status='ALL PASS',real_entry_markers=totals['entries'],real_core_markers=totals['cores'],new_planner_calls=0,ordinary_BFS_this_verify=0,ordinary_Dijkstra_this_verify=0,signal=a['signal']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
