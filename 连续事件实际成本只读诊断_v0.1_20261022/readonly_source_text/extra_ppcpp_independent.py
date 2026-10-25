"""CORE4-only isolation wrapper, NOT a fidelity-verified original PPCPP."""
from pathlib import Path
import sys,importlib.util,time,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import portable_frozen
from baseline_suite import check_contract
from model import DeadlineExceeded,NoPath
from unified_geometry import UnifiedGeometry,single_cell_audit
SOURCE=portable_frozen.ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py'
spec=importlib.util.spec_from_file_location('_ppcpp_core4_original_isolated',SOURCE)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
VERSION='PPCPP_CORE4_INDEPENDENT_WRAPPER_v0.1_20261019'
def solve(s,initial_targets,budget,seed=0,weights=(2.,.5)):
    begin=time.perf_counter();deadline=begin+budget;route=();detail={};status='not_started';reason=None
    try:
        check_contract(s,initial_targets,budget)
        if not math.isfinite(budget):raise ValueError('finite budget required')
        if len(weights)!=2 or any(not math.isfinite(w) or w<0 for w in weights):raise ValueError('invalid weights')
        g=UnifiedGeometry(s,deadline);reason=g.precheck()
        if reason:status='environment_infeasible'
        else:
            candidate=tuple(core.core_route(g,weights,detail))
            checked=single_cell_audit(s,candidate)
            g.check_time() # Complete audit and acceptance must finish by the common deadline.
            if checked['valid']:route=candidate;status='core_complete'
            else:status='core_invalid';reason=checked['errors']
    except DeadlineExceeded:status='deadline'
    except NoPath as e:status='planning_failure';reason=str(e)
    seconds=time.perf_counter()-begin
    return dict(version=VERSION,method='PPCPP_CORE4_INDEPENDENT_WRAPPER',route=route,status=status,reason=reason,
        source='PPCPP_core4' if route else None,seconds=seconds,budget=budget,seed=seed,weights=weights,
        fallback_selected=False,detail=detail,overrun_gt_10ms=seconds>budget+.01,
        limitation='Only framework candidate removal is validated; original-paper mechanism fidelity remains unverified.')
