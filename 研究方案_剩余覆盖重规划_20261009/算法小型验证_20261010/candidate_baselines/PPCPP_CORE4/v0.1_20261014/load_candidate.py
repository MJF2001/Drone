"""Independent development candidate; not complete original PPCPP."""
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
