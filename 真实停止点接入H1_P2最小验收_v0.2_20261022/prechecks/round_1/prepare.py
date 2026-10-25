"""Prepare only: preserve numerical/runtime bytes; isolate audit imports by package."""
from pathlib import Path
import ast, shutil, difflib, sys
from v02_utils import HERE, ROOT, read, dump, sha, now

PACKAGE = 'h1p2_gate_audit_v02_20261022'

def segment(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(text, node)

def main():
    assert not (HERE/'registration.json').exists(), 'refuse overwrite'
    old = ROOT/'真实停止点接入H1_P2最小验收_v0.1_20261022'
    preserve = ['common.py','fixtures.py','pipeline.py','native_loader.py','observe.py','exact.py','geometry.py','connector.py',
                'h1_direction.py','h1_rewards.py','derived/runtime_h1.py','derived/candidate_h1.py',
                'source_snapshot/h1_ppcpp.py','postsrc/engine.py','postsrc/geometry.py']
    bindings = []
    for name in preserve:
        target = HERE/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old/name, target)
        bindings.append({'source':str((old/name).relative_to(ROOT)), 'copy':name,'sha256':sha(old/name),'mode':'BYTE_IDENTICAL'})
    package = HERE/PACKAGE
    package.mkdir()
    for source, target in [('geometry_audit.py','_geometry.py'),('h1_audit.py','_h1.py'),('postsrc/audit_geometry.py','_post_geometry.py')]:
        shutil.copyfile(old/source, package/target)
        bindings.append({'source':str((old/source).relative_to(ROOT)), 'copy':PACKAGE+'/'+target,
                         'sha256':sha(old/source),'mode':'BYTE_IDENTICAL'})
    (package/'_common.py').write_text('"""Package-local path helper; no generic common module import."""\nfrom pathlib import Path\nHERE = Path(__file__).resolve().parents[1]\n',encoding='utf-8')
    (package/'__init__.py').write_text('"""Unique independent audit package, no native imports."""\nfrom ._audit import audit_one, load_auditor\nVERSION = "H1P2_AUDIT_IDENTITY_V02_20261022"\n',encoding='utf-8')
    original = (old/'audit.py').read_text(encoding='utf-8')
    changed = original
    for before, after in [('from common import HERE','from ._common import HERE'),
                          ('import geometry_audit as A','from . import _geometry as A'),
                          ('import h1_audit\n','from . import _h1 as h1_audit\n')]:
        assert changed.count(before) == 1
        changed = changed.replace(before, after)
    node = next(n for n in ast.parse(changed).body if isinstance(n, ast.FunctionDef) and n.name=='load_auditor')
    lines = changed.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = ['def load_auditor():\n','    from . import _post_saved\n','    return _post_saved\n']
    changed = ''.join(lines)
    (package/'_audit.py').write_text(changed,encoding='utf-8')
    post_old = (old/'postsrc/audit_saved.py').read_text(encoding='utf-8')
    assert post_old.count('import audit_geometry as A') == 1
    post_new = post_old.replace('import audit_geometry as A','from . import _post_geometry as A')
    (package/'_post_saved.py').write_text(post_new,encoding='utf-8')
    unchanged = {name:segment(original,name)==segment(changed,name) for name in ('audit_route','audit_one')}
    unchanged['frozen_post_audit_one'] = segment(post_old,'audit_one') == segment(post_new,'audit_one')
    assert all(unchanged.values())
    dump(HERE/'audit_numerical_functions_unchanged.json',unchanged)
    diff = list(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='v0.1/audit.py',tofile='v0.2/'+PACKAGE+'/_audit.py'))
    diff += list(difflib.unified_diff(post_old.splitlines(True),post_new.splitlines(True),fromfile='v0.1/postsrc/audit_saved.py',tofile='v0.2/'+PACKAGE+'/_post_saved.py'))
    (HERE/'审核器仅导入隔离.diff').write_text(''.join(diff),encoding='utf-8')
    dump(HERE/'bindings.json',bindings)
    expected = {str(p.relative_to(HERE)):sha(p) for p in sorted(package.glob('*.py'))}
    dump(HERE/'audit_expected_identity.json',{'package':PACKAGE,'files':expected,
         'baseline_audit_path':str(ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/audit.py')})
    (HERE/'inputs').mkdir()
    for path in sorted((old/'inputs').glob('*.json')):
        shutil.copyfile(path,HERE/'inputs'/path.name)
    shutil.copyfile(old/'registration.json',HERE/'original_registration.json')
    reg = read(old/'registration.json')
    assert reg['jobs'][0]['id']=='01_H1' and len(reg['jobs'])==12
    reg['resume_jobs'] = reg['jobs'][1:]
    reg['v02'] = {'utc':now(),'new_real_core_cap':11,'cross_version_core_cap':12,
        'old_slot':'01_H1','old_slot_reuse_only':True,'no_algorithm_or_input_change':True,
        'new_stub_responses':0,'precheck_process_cap':12,'saved_data_audit_cap':12,
        'technical_round_cap':3,'planned_checks':[
            {'id':'A01','mode':'native_first'}, {'id':'A02','mode':'auditor_first'},
            {'id':'A03','mode':'baseline_symbols'}, {'id':'A04','mode':'worker_context'},
            {'id':'A05','mode':'verify_context'}, {'id':'A06','mode':'helper_stability'}]}
    dump(HERE/'registration.json',reg)
    guards = read(old/'external_source_guards.json')
    old_records = read(old/'old_files.json')
    for file in sorted(old.rglob('*')):
        if file.is_file():
            row = {'path':str(file.relative_to(ROOT)),'sha256':sha(file)}
            old_records.append(row)
            guards[str(file)] = row['sha256']
    dump(HERE/'old_files.json',old_records)
    dump(HERE/'external_source_guards.json',guards)
    old_tech = [old/'technical_rounds/round_1/result.json',old/'technical_freeze_1.json']+list((old/'technical_rounds/round_1').glob('T*.json'))
    dump(HERE/'旧11包装检查只读复用.json',{'new_stub_calls':0,'new_wrapper_test_runs':0,
         'files':{str(p.relative_to(ROOT)):sha(p) for p in old_tech},'passed':11,'failed':0,'old_stub_attempts':12})
    reuse_files = [old/'outputs/01_H1.json',old/'outputs/01_H1_native_return.json',old/'outputs/01_H1_post_return.json',
                  old/'post_stop_saved_reaudit.json',old/'batch_status.json']
    dump(HERE/'reuse_source.json',{'id':'01_H1','original_status':'failed',
         'main_source':str((old/'outputs/01_H1.json').relative_to(ROOT)),
         'files':{str(p.relative_to(ROOT)):sha(p) for p in reuse_files},'do_not_run_selector_core_or_post':True})
    (HERE/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    for name in ('logs','outputs','prechecks'):
        (HERE/name).mkdir()
    shutil.copyfile(ROOT/'H1_P2接入审核模块隔离修复与11槽接续执行稿_给sol_20261022.md',HERE/'source_snapshot/v0.2执行稿.md')
    print({'input_files_byte_bound':6,'resume_jobs':11,'prechecks_registered':6,
           'package':PACKAGE,'audit_math_unchanged':unchanged,'old_guards':len(old_records),'core_calls':0})

if __name__=='__main__':
    main()
