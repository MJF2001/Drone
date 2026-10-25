"""Read-only case/segment registration and bounded geometry, no planner imports."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,hashlib,sys,time,math
H=Path(__file__).resolve().parent;R=H.parent;OFF=R/'中心区OFF全量质量时间开发比较_v0.1_20261022';HIST=R/'PPCPP_LAST新开发地图验证_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def ps(p):return set(map(tuple,p))
def digest_F(f):return hashlib.sha256(json.dumps(sorted(f),separators=(',',':')).encode()).hexdigest()
def source(case,seed,method):
    j=next(j for j in read(OFF/'plan.json')['formal'] if j['case']==case and j['seed']==seed and j['method']==method)
    file=OFF/'outputs'/(j['id']+'.json');return read(file),file

def prepare():
    assert not (H/'case_registry.json').exists()
    for d in ('maps','case_records','figures','sources','papers'):(H/d).mkdir(exist_ok=True)
    (H/'root_before.md').write_bytes((R/'当前进度与下一步.md').read_bytes())
    (H/'sources/执行稿.md').write_bytes((R/'事件连接变化正反例审查及前沿方法检索执行稿_给sol_20261023.md').read_bytes())
    states=read(OFF/'54状态等权结果.json');pairs=read(OFF/'同状态同seed配对.json');meta={x['id']:x for x in read(HIST/'protocol.json')['slots']};chosen=[];reasons={}
    groups={'obstacle':[s for s in states if s['event']=='obstacle'],'expansion':[s for s in states if s['event'] in ('corner','straight')]}
    for group,ss in groups.items():
        maximum=sorted(ss,key=lambda x:(-x['B_C_distance_extra'],x['case']))[0]
        nonpositive=[s for s in ss if s['B_C_distance_extra']<=0]
        negative=sorted(nonpositive,key=lambda x:x['case'])[0] if nonpositive else sorted(ss,key=lambda x:(x['B_C_distance_extra'],x['case']))[0]
        for s,role in ((maximum,'max_relative_gap'),(negative,'nonpositive_lex_first' if nonpositive else 'weak_counterexample_min_gap')):
            if s['case'] not in chosen:chosen.append(s['case'])
            reasons.setdefault(s['case'],[]).append({'group':group,'role':role})
    for group,ss in groups.items():
        used={meta[k]['base_id'] for k in chosen};eligible=[s for s in ss if meta[s['case']]['base_id'] not in used]
        if eligible:
            s=sorted(eligible,key=lambda x:(-x['B_C_distance_extra'],x['case']))[0];chosen.append(s['case']);reasons[s['case']]=[{'group':group,'role':'next_high_gap_different_base_from_all_already_selected'}]
    assert len(chosen)<=6;registrations=[];segments=[];guards={}
    for case in chosen:
        slot=meta[case];seed=next(j['seed'] for j in read(OFF/'plan.json')['formal'] if j['case']==case)
        b,bfile=source(case,seed,'PPCPP');c,cfile=source(case,seed,'P2_MULTI');beforefile=HIST/'prep/inputs'/(slot['base_id']+'.json');prepfile=HIST/'prep/results'/(slot['base_id']+'.json');witfile=HIST/'witnesses'/(case+'.json');afterfile=OFF/'inputs'/(case+'.json')
        before=read(beforefile);after=read(afterfile);prep=read(prepfile);wit=read(witfile);F0=ps(before['free']);F1=ps(after['free']);removed=F0-F1;T0=ps(before['published_targets']);T1=ps(after['published_targets'])
        assert prep['eligible'] and prep['raw']['route'][:wit['cut']+1]==wit['history'];assert after['old_route']==prep['raw']['route'][wit['cut']:]
        assert Path(prep['job']['input']).resolve()==beforefile.resolve() and all(Path(p).resolve()==beforefile.resolve() for p in prep['runtime_reads'])
        assert prep['runtime_reads'] and ps(before['initial_targets'])==T0
        suffix=after['old_route'];old_edges=list(enumerate(zip(suffix,suffix[1:])))
        touched=[v for v in old_edges if tuple(v[1][0]) in removed or tuple(v[1][1]) in removed]
        old_edge=touched[0] if touched else old_edges[0] if old_edges else None
        candidates=[(i,e) for i,e in enumerate(b['post']['edges']) if e['kind']=='between_first_services']
        if not candidates:candidates=list(enumerate(b['post']['edges']))
        selected_post=sorted(candidates,key=lambda z:(-sum((z[1]['a'][k]-z[1]['b'][k])**2 for k in (0,1)),z[0]))[0] if candidates else None
        picks=[]
        if old_edge:picks.append(('old_saved_suffix',old_edge[0],old_edge[1][0],old_edge[1][1],str(afterfile),'old_route',bool(touched)))
        if selected_post:
            i,e=selected_post;picks.append(('B_saved_between_service_edge',i,e['a'],e['b'],str(bfile),'post.edges',None))
        for kind,index,a,z,file,field,touch in picks:
            segments.append({'id':case+'__'+kind,'case':case,'kind':kind,'source_file':file,'source_sha256':sha(file),'field':field,'index':index,'a':a,'b':z,
                'selection_old_suffix_touches_removed':touch,'before_input':str(beforefile),'after_input':str(afterfile),'before_input_sha256':sha(beforefile),'after_input_sha256':sha(afterfile),
                'before_F_sha256':digest_F(F0),'after_F_sha256':digest_F(F1),
                'endpoints_old_published_task':[tuple(p) in T0 for p in (a,z)],'endpoints_new_task':[tuple(p) in T1-T0 for p in (a,z)],
                'relation_label':'new_task_relation_not_old_task_connection' if any(tuple(p) in T1-T0 for p in (a,z)) else 'old_tasks_or_base_transit_relation'})
        registration={'case':case,'slot':slot,'roles':reasons[case],'plot_seed':seed,'state_equal':next(s for s in states if s['case']==case),'all_three_seed_pairs':[p for p in pairs if p['case']==case],
            'before_map_source':str(beforefile),'before_actual_planning_job':prep['job'],'before_runtime_reads':prep['runtime_reads'],'old_plan_source':str(prepfile),'history_prefix_source':str(witfile),
            'after_source':str(afterfile),'free_removed':sorted(removed),'free_added':sorted(F1-F0),'new_published_targets':sorted(T1-T0),'published_removed':sorted(T0-T1),
            'S':after['current'],'previous':after['previous'],'base':after['base'],'predator':after['predator'],'resource':after['distance_budget'],'initial_H':after['covered'],
            'pending':sorted(ps(after['targets'])-ps(after['covered'])),'deferred':after['deferred_targets'],'maps_are_actual_prep_input_not_assumed_ground_truth':True}
        registrations.append(registration)
        for p in (bfile,cfile,beforefile,prepfile,witfile,afterfile):guards[str(p)]=sha(p)
        dump(H/'maps'/(case+'__before_free.json'),before['free']);dump(H/'maps'/(case+'__after_free.json'),after['free'])
    for p in (OFF/'final_receipt.json',OFF/'manifest.json',OFF/'54状态等权结果.json',OFF/'同状态同seed配对.json',OFF/'plan.json',OFF/'history_evidence.json',HIST/'prepare.py',HIST/'worker.py',HIST/'spec.py'):
        guards[str(p)]=sha(p)
    dump(H/'source_guards_A.json',guards);dump(H/'all54_state_equal_source.json',states)
    dump(H/'case_registry.json',{'created_utc_epoch':time.time(),'stage':'A_before_geometry_and_before_web','rule':'max and nonpositive lexical first per obstacle/expansion; if no nonpositive choose weak min; then high-gap base distinct from ALL four prior selected, obstacle extra then expansion extra; deduplicate no refill after analysis',
        'cases':registrations,'geometry_segments':segments,'segment_rule':'one saved old-suffix unit edge: earliest incident to removed free cell if present, else first; one saved B between-first-services edge: longest squared length, earliest tie, fallback any saved B edge. No new endpoints or lines generated.',
        'caps':{'cases':6,'existing_segments':12,'maps_per_segment':2,'maximum_single_map_legality_calls':24},'new_core_or_search_calls':0})
    dump(H/'A_registration_freeze.json',{'files':{str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in ('A_registration_freeze.json',)}})
    print({'registered_cases':chosen,'segments':len(segments),'new_core_calls':0,'geometry_calls_so_far':0})

def geometry():
    assert not (H/'geometry_receipt.json').exists()
    for name,digest in read(H/'A_registration_freeze.json')['files'].items():assert sha(H/name)==digest,name
    for p,digest in read(H/'source_guards_A.json').items():assert sha(p)==digest,p
    import geometry_predicate as G
    registry=read(H/'case_registry.json');counts=Counter(legal_calls=0,closed_forbidden_rectangle_tests=0);original=G.rectangle_intersects
    def counted(*args):counts['closed_forbidden_rectangle_tests']+=1;return original(*args)
    G.rectangle_intersects=counted;records=[]
    for s in registry['geometry_segments']:
        out=dict(s);out['legal']={}
        for stage,key in [('before','before_input'),('after','after_input')]:
            F=ps(read(s[key])['free']);assert digest_F(F)==s[stage+'_F_sha256'];counts['legal_calls']+=1
            out['legal'][stage]=G.legal(F,s['a'],s['b'])
        out['visibility_changed']=out['legal']['before']!=out['legal']['after'];records.append(out)
    assert len(records)<=12 and counts['legal_calls']==len(records)*2
    dump(H/'geometry_receipt.json',{'records':records,'counts':dict(counts),'existing_segment_pairs':len(records),'boundary':'strictly inside free-domain bounding box; closed forbidden unit squares including boundary/corner contact are forbidden; exact rational slab test',
        'predicate_byte_copy_of':'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/audit/_post_geometry.py','predicate_sha256':sha(H/'geometry_predicate.py'),
        'count_wrapper':'only counts existing rectangle predicate calls; no additional legal test','new_core_calls':0,'new_path_or_coverage_searches':0,'new_routes':0})
    print({'segment_pairs':len(records),'single_map_legality_calls':counts['legal_calls'],'changed':sum(s['visibility_changed'] for s in records)})

if __name__=='__main__':{'prepare':prepare,'geometry':geometry}[sys.argv[1]]()
