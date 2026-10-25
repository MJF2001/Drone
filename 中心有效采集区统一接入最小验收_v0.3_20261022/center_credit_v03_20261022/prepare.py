"""Register all worlds, cases and finite query caps before any gate/real call."""
from pathlib import Path
import ast,shutil,difflib
from .utils import HERE,ROOT,read,dump,sha,now
from .worlds import build
from .fixtures import build as cases

def main():
    assert not (HERE/'registration.json').exists()
    old=ROOT/'斜向执行障碍发现首次闭环_v0.1_20261022'
    guards=read(old/'external_source_guards.json')
    records=read(old/'old_files.json')
    for p in old.rglob('*'):
        if p.is_file():
            digest=sha(p);guards[str(p)]=digest
            records.append({'path':str(p.relative_to(ROOT)),'sha256':digest})
    dump(HERE/'external_source_guards.json',guards)
    dump(HERE/'old_files.json',records)
    worlds=build();jobs=[]
    for i,w in enumerate(worlds):
        dump(HERE/'worlds_public'/(w['id']+'.json'),{'id':w['id'],'label':w['label'],**w['public']})
        dump(HERE/'worlds_private'/(w['id']+'.json'),w['private'])
        for method in (('H1','P2') if i%2==0 else ('P2','H1')):
            jobs.append({'id':w['id']+'_'+method,'world':w['id'],'method':method,'seed':20261022,
                'display_method':('PPCPP-H1' if method=='H1' else 'P2')+' + 中心区信用适配'})
    pure=cases()
    dump(HERE/'registration.json',{'utc':now(),'worlds':worlds,'jobs':jobs,'technical_fixtures':pure,
        'cell_length_m':1,'strict_delta_m':'1/5','region_side_m':'2/5','detection_band_unchanged':'1/8 L_infinity',
        'cases':35,'classes':16,'all_technical_session_cap':48,'technical_round_cap':2,
        'repair_policy':'at most one further bounded round, only failed/unrun; 48 total cases absolute cap',
        'real_core_cap':12,'sessions':6,'core_cap_per_session':2,'event_cap_per_session':1,'nonzero_segment_cap_per_session':1000,
        'execution_action_cap_per_session':212,'pipeline_seconds':30,'core_seconds_max':20,'connector_seconds':2,
        'post_candidate_absolute_seconds':28,'no_adaptive_world_changes':True,
        'per_pipeline_caps':{'candidate':25,'wrapper_geometry':327,'wrapper_distance':326,'wrapper_service':3624,
           'post_candidates':4096,'post_source':100,'post_output':100,'post_service':1200,
           'independent_geometry':427,'independent_distance':327,'independent_service':4824,
           'independent_region_point_tests':60000,'independent_region_boundary_parameters':24000},
        'per_execution_caps':{'actions':212,'main_boxes':424,'independent_boxes':424,'main_truth_geometry':212,
            'independent_truth_geometry':212,'main_service':2544,'independent_service':2544},
        'all_pure_caps':{'cases':48,'actions_per_case':8,'main_boxes':1536,'independent_boxes':1536,
            'main_geometry':450,'independent_geometry':450,'main_service':4608,'independent_service':15000,
            'main_candidates':25,'independent_region_point_tests':180000,
            'independent_region_boundary_parameters':60000,'negative_audit_attempts':2},
        'no_core_mechanism_changes':True,'nominal_grid_anchors_retained':True,
        'real_coverage_goal':'at least one diagonal actual segment with region credit but without crossing target center; if absent report unverified, do not extend'})
    for name in ('logs','outputs','calls','sessions','technical_rounds','source_snapshot'):
        (HERE/name).mkdir(exist_ok=True)
    for file in ('中心有效采集区统一接入最小验收执行稿_给sol_20261022.md','中心有效采集区模型确认_20261022.md','中心有效采集区暂定尺寸确认_20261022.md'):
        shutil.copyfile(ROOT/file,HERE/'source_snapshot'/file)
    (HERE/'source_snapshot/执行稿.md').write_bytes((ROOT/'中心有效采集区统一接入最小验收执行稿_给sol_20261022.md').read_bytes())
    (HERE/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    bindings=read(HERE/'source_bindings.json')
    package=HERE/'center_credit_v03_20261022'
    for name in ('worker.py','control.py','verify.py'):
        bindings.append({'source':str(old/name),'copy':str((package/name).relative_to(HERE)),
                         'source_sha256':sha(old/name),'changed':True})
    dump(HERE/'source_bindings.json',bindings)
    diffs=[]
    for row in bindings:
        original=Path(row['source']).read_text(encoding='utf-8-sig')
        current=(HERE/row['copy']).read_text(encoding='utf-8-sig')
        if original!=current:
            diffs.append(''.join(difflib.unified_diff(original.splitlines(True),current.splitlines(True),fromfile=row['source'],tofile=row['copy'])))
    (HERE/'适配源码.diff').write_text('\n'.join(diffs),encoding='utf-8')
    for p in HERE.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    dump(HERE/'namespace_expected.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')})
    print({'registered_worlds':3,'real_sessions':6,'real_core_cap':12,'fixed_cases':len(pure),'classes':16,'all_pure_cap':48,'core_calls':0})
