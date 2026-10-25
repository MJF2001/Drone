"""Independent saved-prefix and first-occurrence verification; standard library.

Does not import audit.py or any project/algorithm module. Each trace pending
set is recomputed from the full literal prefix rather than its incremental
update implementation. Capture order uses per-cell first-index lookup.
"""
from pathlib import Path
import json,hashlib,collections,csv,ast,itertools,sys
H=Path(__file__).resolve().parent;B=H.parent/'PPCPP侧向拓宽开发诊断_v0.4_20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fingerprint(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def checkcsv(name,rows):
    p=H/name;csv.field_size_limit(max(131072,p.stat().st_size))
    with p.open(encoding='utf-8-sig',newline='') as f:got=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for row in rows for k in row));expected=[{k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,tuple,dict)) else '' if r.get(k) is None else str(r[k]) for k in keys} for r in rows];assert got==expected,name
def main():
    allowed={'pathlib','json','hashlib','collections','csv','math','sys','traceback','datetime','ast','itertools','statistics'}
    for p in H.glob('*.py'):
        t=ast.parse(p.read_text(encoding='utf8'))
        for node in ast.walk(t):
            if isinstance(node,ast.Import):assert all(x.name in allowed for x in node.names),(p,'nonstdlib_import')
            if isinstance(node,ast.ImportFrom):assert node.module in allowed,(p,'nonstdlib_from_import')
            if isinstance(node,ast.Call):assert ast.unparse(node.func) not in {'eval','exec','__import__','solve','bfs','dijkstra','run_payload','subprocess.run'},(p,'forbidden_call')
    source=read(H/'source_hash_manifest.json');assert sha(B/'completion_manifest.json')==source['source_completion_manifest_sha256']
    expected_source=read(B/'completion_manifest.json')['files'];assert len(source['files'])==len(expected_source)
    for x in source['files']:
        p=Path(x['path']);assert sha(p)==x['sha256']==x['expected_sha256']==expected_source[str(p.relative_to(B))]
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    data=read(H/'analysis.json');states=read(B/'states.json');prior=read(B/'analysis.json');assert len(states)==len(data['states'])==48
    assert all(v==0 for v in data['budgets'].values());ledger=read(H/'zero_call_ledger.json');assert not ledger['algorithm_modules_imported'] and not ledger['original_verify_rerun']
    summary={s['state']:s for s in data['states']};eq={s['state']:s for s in data['seed_equivalence']};variants={(v['state'],v['seed']):v for v in data['variants']};decisions={(d['state'],d['seed'],d['trace_index']):d for d in data['decisions']};seqs={(s['state'],s['seed'],s['method']):s for s in data['sequences']};integrity={(s['state'],s['seed']):s for s in data['call_trace_audits']};pairs={(p['case'],p['seed']):p for p in prior['pairs']};prior_rows={r['id']:r for r in prior['rows']};prior_states={s['id']:s for s in prior['views']['timely']['states']}
    checked=0;checked_seed_traces=0;canonical_seen=set();all_comp=collections.Counter();all_choices=collections.Counter();all_ties=0
    for st in states:
        sid=st['id'];c=read(B/st['input']);T0=set(map(tuple,c['initial_targets']));A=set(map(tuple,st['A']));hist=set(map(tuple,c['covered']));F=set(map(tuple,c['free']));assert not T0&A and not hist&A and hist<=T0
        assert T0=={(x,y) for x in range(4,4+st['L']) for y in range(4,4+st['w'])};assert set(map(tuple,c['targets']))==T0|A
        refs=[];route_hashes=[];trace_hashes=[]
        for seed in (20261020,20261021,20261022):
            jid=f'formal_{sid}_{seed}_PPCPP';out=read(B/'outputs'/f'{jid}.json');r=out['result']['raw']['route'];tr=out['result']['raw']['branches']['P0']['trace'];route_hashes.append(fingerprint(r));trace_hashes.append(fingerprint(tr));row=next(x for x in eq[sid]['seeds'] if x['seed']==seed);assert row['source_file_sha256']==sha(B/'outputs'/f'{jid}.json') and row['route_sha256']==route_hashes[-1] and row['non_time_trace_sha256']==trace_hashes[-1]
            rep=20261020 if eq[sid]['collapsed'] else seed;key=(sid,rep);v=variants[key];opps=[];inds=[]
            assert r[0]==c['current'] and r[-1]==c['base'];assert all(tuple(p) in F for p in r) and all(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for p,q in zip(r,r[1:]))
            for n,e in enumerate(tr):
                i=e['index'];end=tr[n+1]['index'] if n+1<len(tr) else len(r)-1;prefix=set(map(tuple,r[:i+1]));old=(T0-hist)-prefix;new=(A-hist)-prefix;assert e['current']==r[i] and e['pending_count']==len(old|new)
                d=decisions[sid,rep,n];canonical_seen.add((sid,rep,n));assert d['route_index']==i and d['next_trace_index']==end and d['literal_segment']==r[i:end+1]
                prev=r[i-1] if i else c['previous'];assert d['previous']==prev
                if e['kind']!='return':assert e['previous']==prev
                else:assert 'previous' not in e and not old and not new and n==len(tr)-1
                assert d['old_pending_count']==len(old) and d['new_pending_count']==len(new) and d['A_already_collected']==len(A&prefix)
                x,y=r[i];neighbors={(x-1,y),(x+1,y),(x,y-1),(x,y+1)}&F;oa=neighbors&old;na=neighbors&new
                assert d['old_legal_neighbors']==[list(p) for p in sorted(oa)] and d['new_legal_neighbors']==[list(p) for p in sorted(na)]
                opts=e.get('options',[]);oldopts=[o for o in opts if tuple(o['cell']) in old];newopts=[o for o in opts if tuple(o['cell']) in new]
                assert d['saved_options']==opts and d['old_options']==oldopts and d['new_options']==newopts
                assert d['goal']==e['goal'] and d['kind']==e['kind'] and d['trace_pointer']==f'$.result.raw.branches.P0.trace[{n}]'
                chosen='old' if tuple(e['goal']) in old else 'new' if tuple(e['goal']) in new else 'return';assert d['chosen_class']==chosen
                compete=e['kind']=='local' and bool(oa) and bool(na);assert d['is_competition']==compete
                if e['kind']=='local':
                    assert {tuple(o['cell']) for o in opts}==oa|na and end==i+1 and e['goal']==r[i+1]
                    maximum=max(o['score'] for o in opts);ties=any(o['score']==maximum for o in oldopts) and any(o['score']==maximum for o in newopts);assert d['cross_class_highest_score_tie']==ties
                    assert d['chosen_saved_score']==next(o['score'] for o in opts if o['cell']==e['goal'])
                elif e['kind']=='recovery':assert not oa and not na and not opts and e['goal']==r[end] and end>i
                else:assert e['kind']=='return' and e['goal']==r[end]==c['base']
                if compete:opps.append(d);inds.append(n)
                checked+=1
            assert integrity[sid,seed]['competition_trace_indices']==inds and integrity[sid,seed]['all_trace_prefix_neighbor_checks_passed']
            assert v['competition_count']==len(opps) and v['competition_trace_indices']==inds
            first_A=min((r.index(list(p)) for p in A),default=None);assert v['first_A_capture_index']==first_A
            entry=v['first_A_entry'];first=v['first_competition']
            if A:
                assert entry['route_index']==first_A
                if first_A:
                    owner=max(k for k,e in enumerate(tr) if e['index']<=first_A-1);e=tr[owner];d=decisions[sid,rep,owner];assert entry['owner_trace_index']==owner and entry['mode']==e['kind'] and entry['owner_pointer']==d['trace_pointer'] and entry['literal_segment']==d['literal_segment'];assert entry['was_competition']==d['is_competition'];assert entry['local_only_new_options']==bool(e['kind']=='local' and not d['old_options'] and d['new_options']);assert entry['local_single_new_option']==bool(e['kind']=='local' and len(e['options'])==1 and d['new_options']) if e['kind']=='local' else not entry['local_single_new_option']
                else:assert entry['mode']=='initial_occupancy'
            else:assert entry is None
            if opps:
                assert first['trace_index']==opps[0]['trace_index'] and first['chosen_class']==opps[0]['chosen_class'];assert v['first_competition_A_already_collected']==opps[0]['A_already_collected'];assert v['competition_before_first_A']==(opps[0]['route_index']<first_A);assert v['first_competition_is_first_entry_decision']==(opps[0]['trace_index']==entry['owner_trace_index'])
            else:assert first is None and not v['competition_before_first_A']
            for method in ('PPCPP','P2_MULTI'):
                name=f'formal_{sid}_{seed}_{method}';z=read(B/'outputs'/f'{name}.json');rr=z['result']['raw']['route'];expected=[]
                for p in (T0|A)-hist:expected.append(dict(route_index=rr.index(list(p)),cell=list(p),kind='old' if p in T0 else 'new'))
                expected.sort(key=lambda x:x['route_index']);stages=[]
                for kind,group in itertools.groupby(expected,key=lambda x:x['kind']):
                    g=list(group);stages.append(dict(kind=kind,captures=len(g),start_route_index=g[0]['route_index'],end_route_index=g[-1]['route_index']))
                s=seqs[sid,seed,method];assert s['captures']==expected and s['stages']==stages and s['pattern']=='→'.join(s['kind'] for s in stages) and s['alternations']==max(0,len(stages)-1)
                m=prior_rows[name]['metrics'];assert len(rr)-1==m['length'] and expected[-1]['route_index']==m['completion_step'];assert s['source_sha256']==sha(B/'outputs'/f'{name}.json')
            s=summary[sid];p=pairs[sid,seed];priorvalue=next(x for x in s['existing_by_seed'] if x['seed']==seed);assert priorvalue==dict(seed=seed,D=p['D'],delta_C=p['delta']['completion_step'],delta_R=p['delta']['return_tail_steps'])
            checked_seed_traces+=1
        assert eq[sid]['three_routes_equal']==(len(set(route_hashes))==1) and eq[sid]['three_non_time_traces_equal']==(len(set(trace_hashes))==1);assert eq[sid]['collapsed']==(len(set(route_hashes))==len(set(trace_hashes))==1)
        s=summary[sid];old=prior_states[sid];assert s['existing_mean_D']==old['mean_D'] and s['existing_D_range']==old['D_range'] and s['existing_mean_delta_C']==old['mean_delta']['completion_step'] and s['existing_mean_delta_R']==old['mean_delta']['return_tail_steps']
        vv=[v for k,v in variants.items() if k[0]==sid];assert s['any_competition']==any(v['competition_count']>0 for v in vv)
        for v in vv:
            all_comp[st['condition']]+=v['competition_count'];all_choices.update(v['competition_choice_counts']);all_ties+=v['competition_cross_class_ties']
    assert len(canonical_seen)==len(data['decisions']) and checked_seed_traces==144 and len(seqs)==288
    for cond in data['conditions']:
        rr=[s for s in data['states'] if s['condition']==cond['condition']];assert cond['states']==len(rr)==12 and cond['base_geometries']==len({r['geometry'] for r in rr})==6
        assert cond['with_competition_states']==sum(r['any_competition'] for r in rr) and cond['without_competition_states']==sum(not r['any_competition'] for r in rr)
        assert cond['first_competition_choice_state_counts']==dict(collections.Counter(r['first_competition_choice'] for r in rr));assert cond['first_entry_mode_state_counts']==dict(collections.Counter(r['first_entry_mode'] for r in rr));assert cond['canonical_competition_decisions']==all_comp[cond['condition']]
    checkcsv('48状态完整汇总.csv',data['states']);checkcsv('36事件状态主表.csv',[s for s in data['states'] if s['condition']!='CONTROL']);checkcsv('逐决策机会账.csv',data['decisions']);checkcsv('按条件状态与几何汇总.csv',data['conditions']);checkcsv('三seed等价表.csv',data['seed_equivalence'])
    if (H/'固定三组案例指针.json').exists():
        cases=read(H/'固定三组案例指针.json');assert [g['group'] for g in cases]==['g00_b009','g04_b028','g01_b009']
        for g in cases:
            assert len(g['states'])==4 and {s['condition'] for s in g['states']}=={'CONTROL','H_SIDE','MIXED_SIDE','U_SIDE'}
            for s in g['states']:
                v=variants[s['state'],20261020];assert s['first_competition']==v['first_competition'] and s['first_A_entry']==v['first_A_entry']
    assert not any(n in sys.modules for n in ('runtime','candidate','p2_adapter','ppcpp','p2_search_audit','common','analysis'))
    print('PASS source hashes and standard-library-only scripts; no planner import / graph search / original verify')
    print('PASS independent full-prefix/current/previous/pending/neighbor/option/goal/segment checks:',checked_seed_traces,'saved PPCPP traces,',checked,'seed-specific events,',len(canonical_seen),'canonical events')
    print('PASS independent per-cell first-index288 sequences,48 states/36 events/all seed denominators, first-A ownership, existing D/C/R, fixed cases and CSV round trips')
    print(json.dumps(dict(status='ALL PASS READONLY CHOICE AUDIT',canonical_competitions=dict(all_comp),canonical_actual_choice_counts=dict(all_choices),cross_class_highest_score_ties=all_ties,new_real_entries=0,new_core_calls=0,new_candidates=0,new_graph_searches=0,new_counterfactuals=0),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
