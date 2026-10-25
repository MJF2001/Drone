"""Freeze worlds, fixtures and immutable dependencies before any experiment."""
from pathlib import Path
import shutil,ast,difflib
from loop_utils import HERE,ROOT,read,dump,sha,now
from worlds import build
from fixtures import build as fixtures

PACKAGE='diagonal_loop_audit_v01_20261022'

def main():
    assert not (HERE/'registration.json').exists(),'refuse overwrite'
    old=ROOT/'真实停止点接入H1_P2最小验收_v0.2_20261022'
    files=['common.py','v02_utils.py','exact.py','geometry.py','connector.py','h1_direction.py','h1_rewards.py',
           'native_loader.py','observe.py','context.py','audit_binding.py','derived/runtime_h1.py',
           'derived/candidate_h1.py','source_snapshot/h1_ppcpp.py','postsrc/engine.py','postsrc/geometry.py']
    bindings=[]
    for name in files:
        target=HERE/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(old/name,target)
        bindings.append({'source':str((old/name).relative_to(ROOT)),'copy':name,'sha256':sha(old/name)})
    # Only the public input adapter and no-motion initialization change; core path stays identical.
    original=(old/'pipeline.py').read_text(encoding='utf-8')
    changed=original.replace('from connector import parse, select, collect, credit_move, state_save, cells',
        'from connector import collect, credit_move, cells\nfrom public_contract import parse, select, state_save, heading as make_heading')
    start=changed.index('    h = [v.numerator')
    end=changed.index("    initial = case['metadata']['initial_targets']")
    changed=changed[:start]+"    heading = make_heading(pred,s,case,__import__('hashlib').sha256(input_bytes).hexdigest())\n"+changed[end:]
    changed=changed.replace("gamma_events=gamma_events, h_entry=pt(pred['h']), heading=heading,", 
                            "gamma_events=gamma_events, h_entry=None if pred['h'] is None else pt(pred['h']), heading=heading,")
    (HERE/'pipeline.py').write_text(changed,encoding='utf-8')
    (HERE/'动态状态接入适配.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),
        fromfile='approved_v0.2/pipeline.py',tofile='closed_loop/pipeline.py')),encoding='utf-8')
    def function(text,name):
        node=next(n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        return ast.get_source_segment(text,node)
    unchanged={name:function(original,name)==function(changed,name) for name in ('GuardedCounter','grid','native_points','main_audit')}
    assert all(unchanged.values())
    dump(HERE/'管线数值审核与预算未改.json',unchanged)
    # New independent audit package; old numeric/geometric/score auditors are unchanged.
    package=HERE/PACKAGE
    package.mkdir(exist_ok=True)
    prior=old/'h1p2_gate_audit_v02_20261022'
    for name in ('_geometry.py','_h1.py','_post_saved.py','_post_geometry.py','_common.py'):
        shutil.copyfile(prior/name,package/name)
        bindings.append({'source':str((prior/name).relative_to(ROOT)),'copy':PACKAGE+'/'+name,'sha256':sha(prior/name)})
    (package/'__init__.py').write_text('from ._audit import audit_one,load_auditor,audit_execution\nVERSION="FINITE_CLOSED_LOOP_V01"\n',encoding='utf-8')
    # Identity binder also tracks the added independent detector and execution auditor.
    binder=(HERE/'audit_binding.py').read_text(encoding='utf-8')
    binder=binder.replace("'._post_saved', '._post_geometry')","'._post_saved', '._post_geometry', '._detect')")
    binder=binder.replace("'h1_direction','h1_rewards','native_loader'","'h1_direction','h1_rewards','native_loader','public_contract','detector','executor'")
    (HERE/'audit_binding.py').write_text(binder,encoding='utf-8')
    bindings=[b for b in bindings if b['copy']!='audit_binding.py']
    dump(HERE/'bindings.json',bindings)
    dump(HERE/'audit_expected_identity.json',{'package':PACKAGE,
         'files':{str(p.relative_to(HERE)):sha(p) for p in package.glob('*.py')},
         'baseline_audit_path':str(ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/audit.py')})
    worlds=build()
    jobs=[]
    for i,world in enumerate(worlds):
        assert len(world['public']['F_nominal'])<=25 and len(world['public']['P'])<=12
        assert world['public']['base'] not in world['private']['O_truth']
        dump(HERE/'worlds_public'/(world['id']+'.json'),{'id':world['id'],'label':world['label'],**world['public']})
        dump(HERE/'worlds_private'/(world['id']+'.json'),world['private'])
        for method in (('H1','P2') if i%2==0 else ('P2','H1')):
            jobs.append({'id':world['id']+'_'+method,'world':world['id'],'method':method,'seed':20261022})
    gate=fixtures()
    assert len(gate)==12 and all(len(x['actions'])<=8 for x in gate)
    dump(HERE/'registration.json',{'utc':now(),'worlds':worlds,'jobs':jobs,'technical_fixtures':gate,
         'detector':{'metric':'L_infinity_distance_from_closed_obstacle_cell','distance':'1/8','rational_technical_parameter':True},
         'real_core_cap':12,'sessions':6,'core_cap_per_session':2,'nonzero_segment_cap_per_session':1000,
         'event_cap_per_session':1,'execution_action_cap_per_session':204,'pipeline_seconds':30,'core_seconds_max':20,
         'connector_seconds':2,'post_candidate_absolute_seconds':28,'technical_round_cap':2,
         'technical_sessions_per_round':12,'all_technical_session_cap':24,'fixed_routes_per_round':12,'new_core_in_technical':0,
         'per_pipeline_caps':{'candidate':25,'wrapper_geometry':327,'wrapper_distance':326,'wrapper_service':3624,
             'post_candidates':4096,'post_source':100,'post_output':100,'post_service':1200,
             'independent_geometry':427,'independent_distance':327,'independent_service':4824},
         'per_execution_caps':{'actions':204,'main_boxes':408,'independent_boxes':408,'main_truth_geometry':204,
             'independent_truth_geometry':204,'main_service':2448,'independent_service':2448},
         'per_technical_round_caps':{'sessions':12,'fixed_routes':12,'main_boxes':192,'independent_boxes':192,
             'main_truth_geometry':96,'independent_truth_geometry':96,'main_service':1152,'independent_service':1152,
             'public_preparation_candidates':25,'public_preparation_geometry':26},
         'no_adaptive_world_changes':True})
    guards=read(old/'external_source_guards.json')
    old_records=read(old/'old_files.json')
    for p in sorted(old.rglob('*')):
        if p.is_file():
            row={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
            old_records.append(row)
            guards[str(p)]=row['sha256']
    dump(HERE/'old_files.json',old_records)
    dump(HERE/'external_source_guards.json',guards)
    (HERE/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    shutil.copyfile(ROOT/'斜向执行发现障碍首次闭环验证执行稿_给sol_20261022.md',HERE/'source_snapshot/执行稿.md')
    for name in ('logs','outputs','calls','sessions','technical_rounds'):
        (HERE/name).mkdir(exist_ok=True)
    print({'worlds_frozen':3,'sessions':6,'real_core_cap':12,'technical_fixtures':12,
           'numeric_pipeline_functions_unchanged':unchanged,'old_guard_records':len(old_records),'core_calls_so_far':0})

if __name__=='__main__':
    main()
