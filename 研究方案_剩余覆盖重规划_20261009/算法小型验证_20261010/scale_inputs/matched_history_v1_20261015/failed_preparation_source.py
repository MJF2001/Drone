"""Development-only matched histories: fixed event geometry, no planner calls."""
from pathlib import Path
import argparse,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
INPUT=ALGO/'scale_inputs/development_v0.1_20261014'
PRE=ALGO/'development_preflights/v1_20261014'
OUT=ALGO/'scale_inputs/matched_history_v1_20261015'
VARIANTS=(('H',25),('H',50),('H',75),('V',50))
sys.path.insert(0,str(ALGO))
import scale_scene_generator_20261014 as g

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)

def prepare(out):
    anchor_ids=read(PRE/'protocol.json')['case_ids']
    source_paths=[Path(__file__),ALGO/'scale_scene_generator_20261014.py',
        ALGO/'prepare_scale_design_20261014.py',PRE/'protocol.json']
    for sid in anchor_ids:
        source_paths.append(PRE/'cases'/(sid+'.json'))
        source_paths.append(INPUT/(read(source_paths[-1])['metadata']['map_id']+'.json'))
    protected={str(p):sha(p) for p in source_paths}
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir();(out/'witnesses').mkdir()
    write(out/'protocol.json',dict(version='matched_history_v1_20261015',anchor_ids=anchor_ids,
        variants=VARIANTS,attempted_states=48,split='development',holdout_used=False,solver_called=False,
        rule='Reuse anchor published targets, obstacle cells and fixed domain; never relocate obstacles.',
        rejection='Record current collision/base or pending unreachable. No replacement or planner-based selection.',
        resource='One shared limit per map: twice maximum geometric witness steps over feasible variants.',
        seed='Anchor repeat_seed_0 shared across all history/progress variants of that map.',
        limitation='Same 12 development maps, not independent maps; H50 anchors participated in tuning.',
        source_hashes=protected))
    ledger=[];ids=[]
    for sid in anchor_ids:
        anchor=read(PRE/'cases'/(sid+'.json'));am=anchor['metadata'];mp=read(INPUT/(am['map_id']+'.json'))
        params=mp['parameters'];free0=frozenset(map(tuple,mp['domain']));old=frozenset(map(tuple,mp['initial_targets']))
        base=tuple(mp['base']);blocked=frozenset(map(tuple,am['obstacles']));family=[]
        assert am['split']==params['split']=='development'
        for history,progress in VARIANTS:
            name=am['map_id']+f'_fixed_event_{history}_p{progress}_'+am['event']
            route=tuple(map(tuple,mp['routes'][history]));state=g.checkpoint(old,route,progress)
            schedule={k:am[k] for k in ('map_id','split','scale','stratum','event','extension_percent','turn',
                'obstacle_shape','obstacle_distance','obstacle_seed','repeat_seed_0','repeat_seed_1')}
            schedule.update(state_id=name,history=history,progress_percent=progress)
            if state['current'] in blocked:
                entry=dict(state_id=name,status='input_infeasible',reason='fixed_obstacle_at_current')
                data=None
            else:
                entry,data=g.make_case(params,free0,old,base,state,schedule,
                    (blocked,dict(fixed_from_anchor=sid,anchor_placement=am['placement'])))
            entry.update(map_id=am['map_id'],variant=f'{history}{progress}',anchor_id=sid)
            if data:
                case,witness=data
                for key in ('free','targets','base'):
                    assert json.loads(json.dumps(case[key]))==anchor[key]
                assert case['metadata']['published_targets']==am['published_targets']
                case['metadata'].update(anchor_id=sid,variant=f'{history}{progress}',
                    fixed_event_geometry=True,obstacle_distance_interpretation='Anchor designation only; distances change with current.')
                family.append((entry,case,witness))
            else:
                entry['status']='input_infeasible'
                write(out/'cases'/(name+'_infeasible.json'),dict(entry=entry,current=state['current'],
                    covered=sorted(state['covered']),prefix=state['prefix'],old_route=state['old_route']))
            ledger.append(entry)
        limit=max([1]+[2*(len(w)-1) for _,_,w in family])
        for entry,case,witness in family:
            case['distance_budget']=limit
            case['metadata']['resource_rule']='shared_family_geometric_witness_limit'
            case['metadata']['witness_audit']=g.route_audit(frozenset(map(tuple,case['free'])),
                frozenset(map(tuple,case['targets'])),frozenset(map(tuple,case['covered'])),
                tuple(case['current']),tuple(case['base']),witness,limit)
            entry.update(snapshot_sha256=g.digest(case),witness_sha256=g.digest(witness),distance_budget=limit)
            write(out/'cases'/(case['name']+'.json'),case)
            write(out/'witnesses'/(case['name']+'.json'),dict(route=witness))
            ids.append(case['name'])
    assert len(ledger)==48 and all(sha(Path(p))==h for p,h in protected.items())
    write(out/'generation_ledger.json',ledger)
    result=dict(status='prepared_matched_development_inputs',attempted=48,feasible=len(ids),
        infeasible=48-len(ids),case_ids=ids,solver_called=False,holdout_used=False)
    write(out/'completion.json',result)
    write(out/'sha256.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({k:v for k,v in result.items() if k!='case_ids'},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT)
    prepare(p.parse_args().out)
