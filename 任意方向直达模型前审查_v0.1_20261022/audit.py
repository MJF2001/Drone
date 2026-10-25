"""Saved-index/length audit only. No line-of-sight or hypothetical segments."""
from pathlib import Path
import json,hashlib,math,sys
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP初始解路线改进设计前审查_v0.1_20261022';B=R/'连续事件六世界开发比较_v0.1_20261022'
sources={}
def read(p):
    p=Path(p);b=p.read_bytes();sources[str(p.resolve())]=hashlib.sha256(b).hexdigest();return json.loads(b.decode('utf8'))
def ps(x):return set(map(tuple,x))
def save(n,x):
    with (H/n).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def guard():
    class Block:
        def find_spec(self,n,path=None,target=None):
            if n.split('.')[0] in {'runtime','model','executor','worker','planners','candidate','heapq','_heapq','p2_search_audit','ppcpp'}:raise AssertionError('production/graph import forbidden')
    sys.meta_path.insert(0,Block())
    def profile(f,e,a):
        if e=='call' and f.f_code.co_name in {'solve','run_payload','run_world','reach','walk_component','lineofsight','line_of_sight','precheck'}:raise AssertionError('planning/geometry query forbidden')
    sys.setprofile(profile)
def physical(c):
    return dict(F=sorted(map(list,ps(c['free']))),P=sorted(map(list,ps(c['published_targets']))),H=sorted(map(list,ps(c['covered']))),U=sorted(map(list,ps(c['targets'])-ps(c['covered']))),D=sorted(map(list,ps(c['deferred_targets']))),current=c['current'],previous=c['previous'],base=c['base'],E=c['distance_budget'])
def main():
    guard();manifest=read(OLD/'completion_manifest.json')['files']
    for p,v in manifest.items():assert hashlib.sha256((OLD/p).read_bytes()).hexdigest()==v,('old_package_conflict',p)
    for p,v in read(OLD/'来源hash.json').items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==v,('source_conflict',p)
    old=read(OLD/'60份保存结构全表.json');assert len(old)==60;rows=[]
    for r in old:
        c=read(r['input']);o=read(r['output']);native=o['result'] if 'result' in o else o['entry']['native_return'];raw=native['raw'];path=raw['route'];first=[];seen=ps(c['covered']);T=ps(c['targets']);F=ps(c['free']);P=ps(c['published_targets']);D=ps(c['deferred_targets'])
        assert T==P&F and D==P-F-seen and seen<=P
        for i,p in enumerate(path):
            q=tuple(p)
            if q in T and q not in seen:first.append(dict(point=p,index=i));seen.add(q)
        assert first==r['first_services'];n=len(path)-1;lengths=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:])];assert all(x==1 for x in lengths) and sum(lengths)==r['steps']<=c['distance_budget'];assert path[0]==c['current'] and path[-1]==c['base'] and ps(path)<=F
        segments=[]
        if first:
            f=[e['index'] for e in first];cuts=[(0,f[0],'start_to_first')]+[(a,b,'between_first_services') for a,b in zip(f,f[1:])]+[(f[-1],n,'last_to_base')]
        else:cuts=[(0,n,'empty_task_to_base')]
        assigned=[];cross={};totals={k:0 for k in ('start_to_first','between_first_services','last_to_base','empty_task_to_base')}
        for a,b,kind in cuts:
            segments.append(dict(kind=kind,left=a,right=b,start=path[a],end=path[b],saved_moves=b-a,saved_euclidean_length=sum(lengths[a:b])));totals[kind]+=b-a
            for i in range(a,b):
                assigned.append(i);tr=next((s['kind'] for s in r['segments'] if s['left']<=i<s['right']),'unattributed');key=kind+' x '+tr;cross[key]=cross.get(key,0)+1
        assert assigned==list(range(n)) and sum(totals.values())==n==sum(cross.values())
        refs=[]
        if r['batch']=='54_states':
            for ref in r['P2_reference']:
                z=read(ref['source']);j=z['job'];ic=read(Path(ref['source']).parent.parent/j['input']);fields={k:physical(c)[k]==physical(ic)[k] for k in physical(c)};refs.append(dict(output=ref['source'],input=str(Path(ref['source']).parent.parent/j['input']),physical_equal=all(fields.values()),fields=fields,seed=j['seed'],saved_length=len(z['result']['raw']['route'])-1))
        else:
            sid=r['case']+'_P2_MULTI';s=read(B/'sessions'/(sid+'.json'))['sessions']['P2_MULTI'];ic=s['requests'][-1]['input'];fields={k:physical(c)[k]==physical(ic)[k] for k in physical(c)};refs.append(dict(output_session=str(B/'sessions'/(sid+'.json')),request_index=2,physical_equal=all(fields.values()),fields=fields,reason=None if all(fields.values()) else 'Different actual histories/current/residual task; cannot force same-input pair'))
        rows.append(dict(batch=r['batch'],case=r['case'],input=r['input'],output=r['output'],input_keys=sorted(c),physical=physical(c),explicit_obstacles=c.get('obstacles'),obstacle_status='No separate obstacle field; F itself is the allowed lattice domain, outside F prohibited; cannot infer continuous boundary convention from graph',grid_coordinate_semantics='integer grid vertices/positions; proposed unit cell center embedding is a model choice',radius_field=c.get('radius'),effective_old_radius=0,effective_radius_source='frozen runtime.snapshot hardcodes0; missing field is not missing one-cell contract',current_is_base=c['current']==c['base'],start_credit=bool(first and first[0]['index']==0),empty_remaining_task=not first,first_services=first,L4=n,original_euclidean_length=sum(lengths),service_segments=segments,service_totals=totals,service_trace_cross=cross,P2_pairings=refs,resource=dict(original_distance_budget=c['distance_budget'],meaning='remaining four-neighbor unit movement allowance, not seconds or energy',new_unit_mapping_unapproved=True),timing=dict(saved_entry_seconds=native['entry_seconds'],saved_budget=native['budget'],meaning='warm planning wall time; not flight duration or distance'),missing_required_fields=[k for k in ('free','published_targets','targets','covered','deferred_targets','current','previous','base','distance_budget') if k not in c],shortcut_length=None,geometry_gain=None,fixed_order_optimum=None,free_order_optimum=None))
    save('60份字段与原路线段账.json',rows);save('来源hash.json',sources);save('零调用账.json',dict(planning_entries=0,core=0,BFS=0,Dijkstra=0,Astar=0,visibility_graph=0,visibility_queries=0,coverage_exact=0,candidate_routes=0,shortcut_solves=0,new_routes=0,new_worlds=0,continuous_closed_loops=0,old_verify_runs=0,production_modules_imported=0));print(json.dumps(dict(records=len(rows),batches={b:sum(r['batch']==b for r in rows) for b in ('54_states','6_last_responses')},missing_fields=sum(bool(r['missing_required_fields']) for r in rows),six_same_input=[r['case'] for r in rows if r['batch']=='6_last_responses' and r['P2_pairings'][0]['physical_equal']],start_credit=sum(r['start_credit'] for r in rows),empty_tasks=sum(r['empty_remaining_task'] for r in rows),new_geometry_queries=0),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
