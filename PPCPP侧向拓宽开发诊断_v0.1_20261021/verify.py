"""One-command read-only evidence reconstruction. No planner/native imports."""
from analysis import *
import sys,xml.etree.ElementTree as ET
def csvcheck(name,rows):
    with (H/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict,tuple)) else '' if r.get(k) is None else str(r.get(k)) for k in keys} for r in rows];assert actual==expected,name
def verify():
    csv.field_size_limit(max(131072,max((p.stat().st_size for p in H.glob('*.csv')),default=0)))
    for name in ('seal1','seal2'):
        require(name);s=check_seal(name+'.json');assert sha(sys.executable)==s['python_sha256']
        for p,h in s['files'].items():assert sha(p)==h,p
    for stage in ('stat_stubs','prep','generated','gate','formal'):require(stage)
    if (H/'manifest.json').exists():
        for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    assert read(H/'stat_stub_results.json')['passed'] and len(read(H/'stat_stub_results.json')['tests'])==8
    for name in ('runtime.py','candidate.py','p2_adapter.py'):assert (H/'frozen_source_bytes'/name).read_bytes()==(P/name).read_bytes()
    maps=read(H/'maps.json');groups=read(H/'groups.json');states=read(H/'states.json');assert len(maps)==6 and len(groups)==12 and len(states)==48;BFS=0
    for m in maps:
        L,w=m['L'],m['w'];c0=read(H/m['input']);F=rect(0,0,L+8,w+8);T0=rect(4,4,L,w);assert set(map(tuple,c0['free']))==F and set(map(tuple,c0['targets']))==T0 and not c0['covered'] and c0['current']==c0['base']==[1,1] and c0['previous'] is None and c0['predator']==[-1,0] and c0['distance_budget']==1000000;assert set(map(tuple,c0['initial_targets']))==T0
        route=list(map(tuple,read(H/'outputs'/f'prep_{m["id"]}.json')['result']['raw']['route']));dual(c0,route);B={(x,4) for x in range(4,4+L)};first_B=sorted(route.index(p) for p in B)
        for group in [g for g in groups if g['geometry']==m['id']]:
            count=group['boundary_count'];cut=first_B[count-1];assert cut==group['history_cut'];hist=set(route[:cut+1])&T0;assert normal(sorted(hist))==group['H'] and len(hist&B)==count;histfile=read(H/'history'/f'{group["id"]}.json');assert histfile['prefix']==normal(route[:cut+1]) and histfile['old_suffix']==normal(route[cut:]);ell=L//3
            candidates=[dict(a=aa,k=len({(x,4) for x in range(aa,aa+ell)}&hist),ell=ell) for aa in range(4,4+L-ell+1)];assert candidates==group['candidates']
            for cond in CONDS[1:]:
                eligible=[c for c in candidates if position_label(c['k'],ell)==cond];chosen=min(eligible,key=lambda c:(abs(2*c['k']-ell),c['a']) if cond=='MIXED_SIDE' else (c['a'],));assert chosen==group['selection'][cond]
            dc=bfs(F,route[cut]);db=bfs(F,(1,1));BFS+=2;walk=read(H/'witnesses'/f'{group["id"]}.json')['route']
            for st in [s for s in states if s['group']==group['id']]:
                cond=st['condition'];A=set() if cond=='CONTROL' else rect(group['selection'][cond]['a'],2,ell,2);c=read(H/st['input']);assert set(map(tuple,st['A']))==A and not A&T0 and len(A)==(0 if cond=='CONTROL' else 2*ell);assert set(map(tuple,c['targets']))==set(map(tuple,c['published_targets']))==T0|A and not c['deferred_targets'];assert set(map(tuple,c['free']))==F and set(map(tuple,c['covered']))==hist;assert c['current']==list(route[cut]) and c['previous']==list(route[cut-1]) and c['base']==[1,1] and c['predator']==[-1,0] and c['distance_budget']==1000000-cut and c['old_route']==normal(route[cut:]) and set(map(tuple,c['initial_targets']))==T0;assert st['history_fraction']==len(hist)/len(T0);assert c['name'].startswith('dev_e') and all(z not in c['name'] for z in CONDS)
                dual(c,walk)
                if A:
                    dd=dict(A_to_current_min=min(dc[p] for p in A),A_to_base_min=min(db[p] for p in A),A_current_distance_range=[min(dc[p] for p in A),max(dc[p] for p in A)],A_base_distance_range=[min(db[p] for p in A),max(db[p] for p in A)]);assert dd==st['distance'];assert all(dc[p]==abs(p[0]-route[cut][0])+abs(p[1]-route[cut][1]) and db[p]==abs(p[0]-1)+abs(p[1]-1) for p in A)
                else:assert st['distance'] is None
    print('PASS both source/environment seals, binary-frozen references, 8 statistic stubs, six real histories,12 earliest boundary prefixes/candidate choices, fixed48 inputs and external witnesses',flush=True)
    allorder=read(H/'prep_order.json')+read(H/'gate_order.json')+read(H/'order.json');actual=[json.loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert len(allorder)==len(actual)==306 and [j['id'] for j in allorder]==[j['id'] for j in actual]
    for j in allorder:
        receipt0=read(H/'logs'/f'{j["id"]}.receipt.json');file=H/'outputs'/f'{j["id"]}.json';assert receipt0['markers']['entry_starts']<=1 and receipt0['markers']['core_starts']<=1
        if not file.exists():assert j['phase']=='formal' and receipt0['status'] in ('WATCHDOG','PROCESS_ABNORMAL');continue
        out=read(file);assert out['job']==j and out['input_sha256']==sha(H/j['input']) and out['result']['budget']==20 and out['result']['seed']==j['seed'];assert out['caller_wall_seconds']>=out['result']['entry_seconds'] and set(out['runtime_reads'])=={str(H/j['input'])};assert len(out['actual_core_calls'])==receipt0['markers']['core_starts']
        source_seal=read(H/j['seal'])['files']
        for p,h in out['imports'].items():assert source_seal[p]==h==sha(p)
        if j['method']=='PPCPP':assert out['result']['raw'].get('mode','PPCPP')=='PPCPP' and set(out['result']['raw'].get('branches',{}))<={'P0'}
        row=job_row(j);assert receipt0['valid']==row['valid'] and receipt0['timely']==row['timely']
        if j['phase']!='formal':assert row['valid'] and row['timely']
    a=compute();assert a==read(H/'analysis.json');assert len(a['rows'])==288 and len(a['pairs'])==144
    for row in a['rows']:
        if not row['valid']:continue
        st=next(s for s in states if s['id']==row['case']);A=set(map(tuple,st['A']));c=read(H/st['input']);r=list(map(tuple,read(H/'outputs'/f'{row["id"]}.json')['result']['raw']['route']));v=row['visits_A']
        if A:
            first={p:r.index(p) for p in A};assert v['first_A_capture']==min(first.values()) and v['A_completion']==max(first.values());flags=[p in A for p in r];starts=[i for i,inside in enumerate(flags) if inside and (i==0 or not flags[i-1])];ends=[i for i,inside in enumerate(flags) if inside and (i+1==len(r) or not flags[i+1])];assert [(z['start'],z['end']) for z in v['visits']]==list(zip(starts,ends));unfinished=[e for e in ends if e+1<len(r) and A-set(r[:e+1])];assert len(unfinished)==len(v['unfinished_exits']);assert v['old_remaining_at_A_completion']==len((rect(4,4,st['L'],st['w'])-set(map(tuple,c['covered'])))-set(r[:max(first.values())+1]))
        else:assert v['classification']=='not_applicable'
    csvcheck('288正式调用完整指标.csv',[{**{k:v for k,v in r.items() if k not in ('metrics','visits_A','pp_first_A_event')},**(r['metrics'] or {}),visits_A=r['visits_A'],pp_first_A_event=r['pp_first_A_event']} for r in a['rows']]);csvcheck('144全部配对与不可用原因.csv',a['pairs'])
    for name,v in a['views'].items():
        csvcheck(f'{name}_48状态三种子均值范围.csv',v['states']);csvcheck(f'{name}_12匹配组信号.csv',v['groups']);csvcheck(f'{name}_逐seed位置控制对比.csv',v['contrasts']);csvcheck(f'{name}_分层.csv',[dict(dimension=d,value=value,**row) for d,vs in v['strata'].items() for value,row in vs.items()])
    assert read(H/'signal.json')==a['signal'] and read(H/'detailed_example_selection.json')==a['detailed_examples'];assert BFS==read(H/'generation_ledger.json')['ordinary_BFS']==24
    print('PASS306 ordered slots/raw read isolation/core ledgers, dual full metrics, independent A first-index/visit audit, strict/late paired denominators, controls/contrasts/all seed means/ranges, registered signal and example selection',flush=True)
    print(json.dumps(dict(status='ALL PASS',new_planner_calls=0,coverage_exact_searches=0,ordinary_BFS_this_verify=BFS,signal=a['signal']),ensure_ascii=False),flush=True)
if __name__=='__main__':verify()
