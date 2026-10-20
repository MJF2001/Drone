"""Offline exact diagnostics, no coverage planner / SCIP / GLNS invocation."""
import collections,csv,hashlib,json,statistics,sys,time
from pathlib import Path
import independent as ind
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def plain(v):return json.loads(json.dumps(v))

def micro():
    states={};rows=[]
    for n in (1,2,4,5,6,7,8):
        case=read(f'saved_micro/events/N{n}.json');req=case['request']
        optimal=ind.global_cover(req);ties=ind.minimum_rank_ties(req)
        assert ties['best_minimum_rank_cover']['cost']>=optimal['cost']
        states[f'N{n}']={'global_optimum':optimal,'minimum_rank_ties':ties}
        for slot in ('rank0','cap0','cap2','capmax'):
            r=read(f'saved_micro/results/N{n}_{slot}.json');core=r['core_plan']
            if not core:continue
            packed=ind.exact(req,[b['path'] for b in r['core_detail']['blocks']])
            atomic=ind.exact(req,[s['cells'] for s in r['core_detail']['ranks']])
            assert len(core['route'])-1>=packed['cost']>=atomic['cost']>=optimal['cost']
            if slot=='rank0':assert len(r['core_detail']['ranks'])==ties['minimum_rank_count']
            rows.append({'plan_id':r['plan_id'],'case':f'N{n}','saved_core_steps':len(core['route'])-1,
                'rank_count':len(r['core_detail']['ranks']),'packed_exact':packed,'atomic_exact':atomic,
                'global_optimum':optimal['cost'],'search_gap':len(core['route'])-1-packed['cost'],
                'binding_cost':packed['cost']-atomic['cost'],
                'partition_service_gap':atomic['cost']-optimal['cost']})
    return {'states':states,'cores':rows,'planner_calls':0,'SCIP_calls':0,'GLNS_calls':0}

def current():
    rows=[];bycase=collections.defaultdict(dict)
    for job in read('protocol.json')['planned']:
        if job['kind']!='response':continue
        r=read('results/'+job['plan_id']+'.json');d=r['core_detail'];plan=r['core_plan']
        exact=ind.exact(r['request'],[b['path'] for b in d['blocks']]) if plan else None
        if plan:assert not ind.audit(r['request'],plan['route'])
        core_steps=len(plan['route'])-1 if plan else None
        if exact and exact['status']=='optimal':assert core_steps>=exact['cost']
        row={'plan_id':r['plan_id'],'case':job['case'],'seed':job['seed'],'arm':job['arm'],
             'Q':len(ind.targets(r['request'])),'rank_count':len(d.get('ranks',[])),
             'block_count':len(d.get('blocks',[])),'core_complete':r['core_complete'],
             'core_steps':core_steps,'selected_steps':len(r['route'])-1 if r['route'] else None,
             'selected_source':r['source'],'public_seconds':r['public_seconds'],
             'bootstrap_seconds':r['bootstrap_seconds'],
             'process_wall_seconds':read('supervisor/'+r['plan_id']+'.json')['process_wall_seconds'],
             'phases':r['phase_seconds'],'fixed_structure_exact':exact,
             'search_gap':core_steps-exact['cost'] if exact and exact['status']=='optimal' else None,
             'signature':ind.signature(d['ranks']) if 'ranks' in d else None}
        rows.append(row);bycase[job['case'],job['seed']][job['arm']]=row
    pairs=[]
    for (case,seed),arms in bycase.items():
        a,p,f=(arms[x] for x in ('ATOMIC','PACKED','FULL'))
        matched=a['signature']==p['signature'] and a['signature'] is not None
        comparison={'case':case,'seed':seed,'atomic_packed_same_partition':matched,
                    'all_three_complete':all(x['core_complete'] for x in arms.values()),
                    'core_steps':{k:x['core_steps'] for k,x in arms.items()},
                    'public_seconds':{k:x['public_seconds'] for k,x in arms.items()}}
        if matched and all(x['core_complete'] for x in (a,p)):
            ae,pe=a['fixed_structure_exact'],p['fixed_structure_exact']
            if ae['status']==pe['status']=='optimal':
                assert pe['cost']>=ae['cost'];comparison['exact_binding_cost']=pe['cost']-ae['cost']
            comparison['observed_packed_minus_atomic_steps']=p['core_steps']-a['core_steps']
            comparison['packed_minus_atomic_seconds']=p['public_seconds']-a['public_seconds']
        pairs.append(comparison)
    aggregate={}
    for arm in ('FULL','ATOMIC','PACKED'):
        selected=[x for x in rows if x['arm']==arm];completed=[x for x in selected if x['core_complete']]
        aggregate[arm]={'attempts':len(selected),'core_complete':len(completed),
            'sum_core_steps':sum(x['core_steps'] for x in completed),
            'median_public_seconds':statistics.median(x['public_seconds'] for x in selected),
            'sum_public_seconds':sum(x['public_seconds'] for x in selected),
            'sum_phase_seconds':{label:sum(x['phases'].get(label,0) for x in selected) for label in ('rank','packets','geometry_matrix','GLNS','rebuild','audit')},
            'positive_search_gap_count':sum(x['search_gap'] is not None and x['search_gap']>0 for x in completed),
            'exact_check_count':sum(x['fixed_structure_exact'] is not None and x['fixed_structure_exact']['status']=='optimal' for x in selected)}
    return {'rows':rows,'pairs':pairs,'aggregate':aggregate,'generated_cases':12,'response_attempts':len(rows),
            'matched_partition_pairs':sum(p['atomic_packed_same_partition'] for p in pairs),
            'positive_binding_pairs':sum(p.get('exact_binding_cost',0)>0 for p in pairs),
            'new_coverage_planner_calls':0}

def main():
    check='--check' in sys.argv
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in read('freeze.json').items())
    m=micro();c=current()
    if check:
        assert plain(m)==read('micro_analysis.json') and plain(c)==read('analysis.json')
    else:
        assert not (ROOT/'analysis.json').exists(),'do not overwrite evidence'
        save('micro_analysis.json',m);save('analysis.json',c)
        flat=[]
        for row in c['rows']:
            x={k:v for k,v in row.items() if k not in ('signature','fixed_structure_exact','phases')}
            x.update({'exact_cost':row['fixed_structure_exact'].get('cost') if row['fixed_structure_exact'] else None})
            x.update({'phase_'+k:v for k,v in row['phases'].items()});flat.append(x)
        fields=list(dict.fromkeys(k for x in flat for k in x))
        with (ROOT/'response_table.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(flat)
    print(json.dumps({'analysis':'PASS','read_only':check,'micro_cores':len(m['cores']),
        'aggregate':c['aggregate'],'matched_pairs':c['matched_partition_pairs'],
        'positive_binding_pairs':c['positive_binding_pairs'],'new_planner_calls':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
