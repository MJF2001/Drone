"""Validate the transferred runtime/portable loader without changing v2."""
from pathlib import Path
import contextlib
import hashlib
import importlib
import io
import json
import os
import platform
import sys
import traceback
import unittest

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
FROZEN=ALGO/'frozen_baselines/v2_20261012'
OUT=ROOT/'运行环境/验证记录_20261014'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    result=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        machine=platform.machine(),logical_cpus=os.cpu_count(),status='started',
        baseline_version='v2_20261012',profile_recalibrated=False)
    try:
        manifest=json.loads((FROZEN/'manifest.json').read_text(encoding='utf-8'))
        before={name:sha(FROZEN/'source'/name) for name in manifest['source_sha256']}
        assert before==manifest['source_sha256'],'frozen source hash mismatch'
        assert sha(FROZEN/'runtime_profile.json')==manifest['runtime_profile_sha256']
        expected_runtime=json.loads((FROZEN/'runtime.json').read_text(encoding='utf-8'))
        dependency_checks={name:sha(ALGO/'.deps'/name)==expected for name,expected in expected_runtime['dependency_sha256'].items()}
        assert all(dependency_checks.values()),'dependency hash mismatch'
        result['dependency_hashes_verified']=len(dependency_checks)
        result['frozen_source_hashes_verified']=len(before)
        import portable_frozen
        import numpy,glns,pyscipopt
        result['versions']=dict(numpy=numpy.__version__,glns=glns.__version__,pyscipopt=pyscipopt.__version__)
        paths={}
        for name in ('baseline_suite','model','audit','unified_geometry','p2_search_audit',
                     'unified_candidates','oarp_replan.ranks','oarp_replan.tour'):
            module=importlib.import_module(name);p=Path(module.__file__).resolve()
            assert p.is_relative_to(FROZEN/'source'),(name,str(p))
            paths[name]=str(p)
        result['implementation_paths']=paths
        result['dependency_paths']={m.__name__:m.__file__ for m in (numpy,glns,pyscipopt)}
        result['profile_sha256']=sha(FROZEN/'runtime_profile.json')
        result['profile_maximum_cap']=portable_frozen.PROFILE['maximum_calibrated_cap']
        modules=['test_oarp_core','test_bfs_metric_geometry','test_structure_candidates',
                 'test_scenarios_v3','test_baseline_contract']
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
            test=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        with (OUT/'02_regression_tests.log').open('x',encoding='utf-8') as f:f.write(stream.getvalue())
        result['regression_tests']=dict(run=test.testsRun,errors=len(test.errors),failures=len(test.failures),successful=test.wasSuccessful())
        result['test_sources']={name:dict(path=importlib.import_module(name).__file__,
            sha256=sha(Path(importlib.import_module(name).__file__))) for name in modules}
        assert test.wasSuccessful(),'regression tests failed'
        assert before=={name:sha(FROZEN/'source'/name) for name in before}
        result['hashes_unchanged']=True
        result['status']='verified_this_machine_runtime_and_regression'
        result['caveat']='Not performance validation, not proof of portability to other machines; historical profile retained.'
    except BaseException:
        result['status']='failed';result['traceback']=traceback.format_exc()
    with (OUT/'03_runtime_verification.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('test_sources','implementation_paths','dependency_paths')},ensure_ascii=False))
    return 0 if result['status'].startswith('verified') else 1


if __name__=='__main__':sys.exit(main())
