"""Snapshot the independently audited candidate; clean-process replay 12 states.

This does not replace v2, add methods to its suite, or run holdout comparisons.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
GRID=ALGO/'development_preflights/ppcpp_weight_grid_v0.1_20261014'
VERIFIED=ALGO/'development_preflights/ppcpp_weight_grid_v0.1_20261014_verification'
BASE=ALGO/'frozen_baselines/v2_20261012'
OUT=ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014'

LOADER='''"""Independent development candidate; not complete original PPCPP."""
from pathlib import Path
import hashlib, importlib, importlib.util, json
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'portable_frozen.py').is_file())
import sys
sys.path.insert(0,str(ROOT))
import portable_frozen
BASE=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012'
if portable_frozen.FROZEN.resolve()!=BASE.resolve():raise RuntimeError('wrong geometry base')
MANIFEST=json.loads((HERE/'manifest.json').read_text(encoding='utf-8'))
for name,expected in MANIFEST['files_sha256'].items():
    if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=expected:raise RuntimeError(('candidate hash mismatch',name))
for name,expected in MANIFEST['base_source_sha256'].items():
    if hashlib.sha256((BASE/'source'/name).read_bytes()).hexdigest()!=expected:raise RuntimeError(('base hash mismatch',name))
for name in ('baseline_suite','model','audit','unified_geometry','bfs_metric_geometry'):
    if not Path(importlib.import_module(name).__file__).resolve().is_relative_to(BASE/'source'):
        raise RuntimeError(('cached non-frozen module',name))
PROFILE=json.loads((HERE/'profile.json').read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('_frozen_ppcpp_core4_v01',HERE/'source/candidate_ppcpp_core4_20261014.py')
IMPLEMENTATION=importlib.util.module_from_spec(spec)
spec.loader.exec_module(IMPLEMENTATION)
def solve(snapshot,initial_targets,budget,seed=0):
    return IMPLEMENTATION.solve(snapshot,initial_targets,budget,seed,
        (PROFILE['weights']['omega_s'],PROFILE['weights']['omega_b']))
'''


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,data):
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def worker(case_file,destination):
    spec=importlib.util.spec_from_file_location('_ppcpp_loader',OUT/'load_candidate.py')
    loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
    from model import Snapshot
    d=json.loads(case_file.read_text(encoding='utf-8'));pts=lambda k:frozenset(map(tuple,d[k]))
    s=Snapshot(d['name'],pts('free'),pts('targets'),pts('covered'),tuple(d['current']),
        tuple(d['base']),tuple(map(tuple,d['old_route'])),d['radius'],d['distance_budget'])
    result=loader.solve(s,set(map(tuple,d['metadata']['initial_targets'])),20,d['metadata']['repeat_seed_0'])
    write(destination,dict(raw=result,implementation_path=loader.IMPLEMENTATION.__file__,
                           profile=loader.PROFILE))


def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    verification=json.loads((VERIFIED/'summary.json').read_text(encoding='utf-8'))
    completion=json.loads((GRID/'completion.json').read_text(encoding='utf-8'))
    assert verification['decision_replays']==192 and verification['hashes_verified']
    winner=completion['selected_pair'];assert winner and winner==verification['selected_pair']
    protocol=json.loads((GRID/'protocol.json').read_text(encoding='utf-8'))
    assert all(sha(Path(p))==value for p,value in protocol['hashes'].items())
    base_manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'source').mkdir()
    for name in ('candidate_ppcpp_core4_20261014.py','test_candidate_ppcpp_core4_20261014.py'):
        shutil.copy2(ALGO/name,OUT/'source'/name)
    shutil.copy2(ALGO/'candidate_specs/PPCPP_CORE4_v0.1_20261014.json',OUT/'original_specification.json')
    profile=dict(candidate='PPCPP_CORE4',version='v0.1_20261014',
        status='development_validated_candidate_not_independent_test_validated',
        weights=dict(omega_s=winner['weights'][0],omega_b=winner['weights'][1]),
        geometry_base='v2_20261012',source='predeclared 16x12 development grid; independent decision replay',
        selection_objective=winner['ratio_fraction'],holdout_used=False,
        caveats=['not complete original PPCPP', 'not paper innovation', 'no formal equal-budget baseline ranking yet',
                 'grid-selected weights are not globally optimal', 'historical v2 baseline suite unchanged'])
    write(OUT/'profile.json',profile)
    (OUT/'load_candidate.py').write_text(LOADER,encoding='utf-8')
    (OUT/'README.md').write_text(
        '# PPCPP_CORE4 v0.1_20261014\n\n独立开发候选，不覆盖三方法v2。'
        '仅完成单元测试与开发调参/重放，不是完整PPCPP复现，不是论文创新或留出测试结论。\n\n'
        'load_candidate.py验证本候选与v2源码哈希，并固定使用profile.json中的权重。'
        'original_specification.json保留调参前草案，formal_weights=null属于历史状态；实际配置以profile.json为准。\n',encoding='utf-8')
    manifest=dict(candidate='PPCPP_CORE4',version='v0.1_20261014',
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},
        base_source_sha256=base_manifest['source_sha256'],
        geometry_profile_sha256=base_manifest['runtime_profile_sha256'],
        selection_evidence=dict(protocol_sha256=sha(GRID/'protocol.json'),completion_sha256=sha(GRID/'completion.json'),
            independent_verification_sha256=sha(VERIFIED/'summary.json')),
        freeze_script_sha256=sha(Path(__file__)),formal_baseline_suite_modified=False)
    write(OUT/'manifest.json',manifest)
    replay=VERIFIED/'clean_process_replay';replay.mkdir(exist_ok=False)
    env=dict(os.environ,**protocol['thread_environment'])
    rows=[]
    try:
        for case_index,sid in enumerate(protocol['case_ids']):
            input_file=ALGO/'development_preflights/v1_20261014/cases'/(sid+'.json')
            destination=replay/f'case_{case_index:02d}.json'
            with (replay/f'case_{case_index:02d}.log').open('x',encoding='utf-8') as log:
                result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',
                    str(input_file),str(destination)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50)
            assert result.returncode==0
            saved=json.loads(destination.read_text(encoding='utf-8'))
            original=json.loads((GRID/'runs'/f"c{case_index:02d}_w{winner['pair_index']:02d}.json").read_text(encoding='utf-8'))['raw']
            raw=saved['raw']
            assert raw['route']==original['route'] and raw['detail']['core_route']==original['detail']['core_route']
            assert raw['source']==original['source'] and raw['detail']['core_valid_before_deadline']
            assert raw['independent_audit']['valid'] and raw['core_independent_audit']['valid']
            assert Path(saved['implementation_path']).resolve()==OUT/'source/candidate_ppcpp_core4_20261014.py'
            rows.append(dict(case=sid,selected_route_identical=True,core_route_identical=True,
                frozen_implementation_loaded=True,selected_valid=True,core_valid=True))
        assert all(sha(Path(p))==value for p,value in protocol['hashes'].items())
        write(replay/'comparison.json',rows)
        finished=dict(status='candidate_snapshot_and_clean_replay_verified',cases=12,
            selected_route_identical=12,core_route_identical=12,profile=profile,
            base_hashes_unchanged=True,holdout_used=False)
        write(OUT/'completion.json',finished)
        write(replay/'summary.json',finished)
        write(OUT/'artifact_sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(finished,ensure_ascii=False))
    except BaseException:
        write(OUT/'aborted_freeze.json',dict(status='aborted_candidate_snapshot',replayed=len(rows),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':worker(Path(sys.argv[2]),Path(sys.argv[3]))
    else:main()
