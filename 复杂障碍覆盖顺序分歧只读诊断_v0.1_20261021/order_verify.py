"""One-command read-only audit. No planner imports, writes, or coverage search."""
import sys,csv,json,math,statistics,xml.etree.ElementTree as ET
from order_analysis import *

def csvverify(path,rows):
    with path.open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    keys=list(dict.fromkeys(k for r in rows for k in r));expected=[]
    for r in rows:
        expected.append({k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(dict,list,tuple)) else '' if r.get(k) is None else str(r.get(k)) for k in keys})
    assert actual==expected,str(path)

def independent_scanner(a):
    """Use target-specific first-index lookups, not the event scanner state machine."""
    count=0
    for r in a['routes']:
        c=read(S/'inputs'/f'{r["case"]}.json');path=list(map(tuple,read(S/'outputs'/f'{r["id"]}.json')['result']['raw']['route']));tt=set(map(tuple,c['targets']));hh=set(map(tuple,c['covered']));u=tt-hh-{path[0]};ee=sorted([(path.index(t),t) for t in u]);expected=[dict(target=list(t),rank=i+1,step=st) for i,(st,t) in enumerate(ee)]
        assert expected==r['acquisitions'];assert r['initial_acquisition']==normal(sorted({path[0]}&(tt-hh)));assert normal(sorted(u))==r['U']
        for prop in r['slices']['proportions']:
            need=(prop['percent']*len(u)+99)//100;step=ee[need-1][0] if need else 0;ss=r['slices']['snapshots'][str(step)];remain={t for st,t in ee if st>step}
            assert prop['step']==ss['step']==step and prop['count_threshold']==need;assert ss['remaining']==normal(sorted(remain));assert ss['position']==list(path[step]);assert ss['remaining_count']==len(remain);assert ss['full_suffix_length']==len(path)-1-step
            count+=1
    return count

def verify():
    for p,h in read(H/'source_hashes.json').items():assert sha(p)==h,p
    for p,h in read(H/'preseal.json')['files'].items():assert sha(H/p)==h,p
    assert sha(sys.executable)==read(H/'preseal.json')['executable_sha256']
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    for seal in ('prep_seal.json','formal_seal.json'):
        for p,h in read(S/seal).items():assert sha(p)==h,p
    print('PASS original provenance/414 source files, both upstream seals, pre-analysis protocol/code hashes, final manifest',flush=True)
    a=compute();assert a==read(H/'analysis.json');assert a['failures']==read(H/'failures.json')==[]
    assert independent_scanner(a)==576
    assert len(a['routes'])==96 and len(a['pairs'])==48
    for r in a['routes']:
        assert read(H/'acquisitions'/f'{r["id"]}.json')=={k:v for k,v in r.items() if k!='slices'};assert read(H/'slices'/f'{r["id"]}.json')==r['slices']
    csvverify(H/'48全配对索引与分歧.csv',a['pairs']);csvverify(H/'96路线指标.csv',[{k:v for k,v in r.items() if k not in ('slices','acquisitions','U')} for r in a['routes']]);csvverify(H/'全部目标排名与首次到达差.csv',a['rank_differences']);csvverify(H/'全部采集比例配对切片.csv',[dict(pair_id=p['id'],case=p['case'],rep=p['rep'],timely=p['timely'],**s) for p in a['pairs'] for s in p['slice_pairs']])
    for view,v in a['views'].items():
        csvverify(H/f'{view}_16状态均值范围与前五.csv',v['states']);csvverify(H/f'{view}_障碍分层.csv',[dict(dimension=field,value=value,**s) for field,vs in v['strata_events'].items() for value,s in vs.items()])
    csvverify(H/'48共同轨迹与采集分歧.csv',[{k:p[k] for k in ('id','case','rep','seed','timely','classification','route_status','common_vertex_count','common_state','PPCPP_next','P2_next','acquisition_divergence','delta')} for p in a['pairs']]);csvverify(H/'全批反向关系账.csv',a['counterexamples'])
    assert read(H/'counterexample_ledger.json')['records']==a['counterexamples']
    assert read(H/'figure_index.json')==dict(examples=a['examples'],missing=a['missing_example_categories'])
    from make_figures import draw
    prov=read(H/'decision_provenance_and_missing.json')
    csvverify(H/'固定深读决策出处与缺失.csv',prov)
    for i,ex in enumerate(a['examples']):
        p=next(p for p in a['pairs'] if p['id']==ex['pair_id']);c=read(S/'inputs'/f'{p["case"]}.json');assert read(H/'deep_reads'/f'{p["id"]}.json')==dict(selection=ex,pair=p);assert (H/'figures'/f'{p["id"]}.svg').read_text(encoding='utf8')==draw(p,a,c);ET.parse(H/'figures'/f'{p["id"]}.svg');assert prov[i]['direct_record']==p['decision_evidence'].get('direct_record') and prov[i]['pointer']==p['decision_evidence'].get('event_pointer')
    for r in read(H/'render_receipt.json')['rows']:
        assert sha(H/'figures'/r['svg'])==r['svg_sha256'];assert sha(H/'figures'/r['png'])==r['png_sha256'];assert (H/'figures'/r['png']).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    for anchor in read(H/'frozen_rule_anchors.json'):
        assert sha(anchor['file'])==anchor['sha256'];lines=Path(anchor['file']).read_text(encoding='utf8').splitlines()
        for excerpt in anchor['excerpts']:
            for ln in excerpt['lines']:assert lines[ln['line']-1]==ln['text']
    hyp=read(H/'探索性假设.json');assert len(hyp)==1;support=[p for p in a['pairs'] if p['timely'] and p['kind']!='control' and p['decision_evidence'].get('P2_next_in_recorded_options') is False and p['decision_evidence'].get('P2_next_was_initial_history') is True];assert [r['pair_id'] for r in hyp[0]['support']]==[p['id'] for p in support] and len(support)==6
    for r,p in zip(hyp[0]['support'],support):assert r['delta']==p['delta'] and r['saved_P2_next']==p['P2_next'] and r['seed']==p['seed']
    assert read(H/'distance_ledger.json')['analysis']==read(H/'distance_ledger.json')['verification_one_run']==a['distance_and_slice_execution']
    assert read(H/'call_ledger.json')['new_planner_calls']==read(H/'call_ledger.json')['new_coverage_exact_searches']==read(H/'call_ledger.json')['candidate_generation']==0
    print('PASS 96 actual acquisition sequences, 576 slices (independent first-index audit), dual metrics/old tail values, common-history literal suffixes and cost identities',flush=True)
    print('PASS every JSON/CSV row, 48 pairs, seed means/ranges/top-five, strict/late event/control denominators, ranks/Jaccard/strata/counterexamples',flush=True)
    print('PASS 6 fixed figure pages/selection/trace pointers/source anchors, explicit missing records, 1 post hoc hypothesis support and zero-call ledgers',flush=True)
    print('ALL PASS; this verify: 16 full base BFS +16 independent full-graph Dijkstra, 5312 vertex distances; planner=0, coverage exact=0, route candidate=0.',flush=True)

if __name__=='__main__':verify()
