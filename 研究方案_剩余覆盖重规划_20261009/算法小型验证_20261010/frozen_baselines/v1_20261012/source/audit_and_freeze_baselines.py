"""Audit adapted baselines, then save a versioned source/runtime manifest."""
from pathlib import Path
from dataclasses import replace
import json,hashlib,random,time,sys,shutil,subprocess,platform
import oarp_replan,glns,pyscipopt
from model import Snapshot
from unified_geometry import UnifiedGeometry
from oarp_replan.tour import tour_replan
from scenarios import deserialize
from baseline_suite import solve,METHODS
from supplement_route_metrics import metrics

D=Path(__file__).parent;O=D/'results/run_32b_baseline_adaptation_audit_20261012'
F=D/'frozen_baselines/v1_20261012';B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def calibrate():
    records=[]
    for m in (0,1,2,4,8,16,32):
        for rep in range(3):
            rng=random.Random(32000+m*10+rep)
            ps=rng.sample([(x,y) for x in range(1,40) for y in range(1,40)],2*m+1)
            s=Snapshot('profile',frozenset((x,y) for x in range(41) for y in range(41)),frozenset(ps),frozenset(),(0,0),(0,0),(),0)
            g=UnifiedGeometry(s);blocks=[dict(kind='rank',path=(p,)) for p in ps]
            start=time.perf_counter();r=tour_replan(g,blocks,seconds=2,seed=rep)
            records.append(dict(cap=m,groups=len(blocks),seconds=time.perf_counter()-start,censored=r['solver'].get('timeout',False)))
    # Conservative observed monotone envelope, no cubic extrapolation beyond measured caps.
    sampled=[m for m in (0,1,2,4,8,16,32) if all(not r['censored'] for r in records if r['cap']==m)]
    limit=max(sampled);envelope=[]
    for m in range(limit+1):
        ceiling=min(k for k in sampled if k>=m)
        envelope.append(1.5*max(r['seconds'] for r in records if r['cap']<=ceiling)+.01)
    return dict(records=records,monotone_seconds=envelope,maximum_calibrated_cap=limit,
      mapping='2m+1 synthetic service groups; common geometry; 1.5x monotone observed envelope +10ms',
      caveat='synthetic estimate, not guaranteed deadline; capped at measured range; geometry constructor excluded, GTSP preparation included')

def fixtures():
    free=frozenset((x,y) for x in range(4) for y in range(3))
    route=((0,0),(1,0),(2,0),(3,0),(3,1),(2,1),(1,1),(0,1),(0,2),(1,2),(2,2),(3,2),(2,2),(1,2),(0,2),(0,1),(0,0))
    initial=free;s=Snapshot('fixture_all_covered',free,free,free,(2,1),(0,0),route,0)
    yield s,initial,True
    yield replace(s,name='fixture_no_targets',targets=frozenset(),covered=frozenset()),initial,True
    yield replace(s,name='fixture_pending_at_current',targets=frozenset({s.current}),covered=frozenset()),initial,True
    yield replace(s,name='fixture_tight_resource',distance_budget=1),initial,False
    split=free-{(1,y) for y in range(3)}
    yield replace(s,name='fixture_unreachable_base',free=split,targets=frozenset({(2,1)}),covered=frozenset()),initial,False

def main():
    O.mkdir(parents=True,exist_ok=False)
    if F.exists():raise FileExistsError(F)
    inputs=[D/'results/run_21_micro_global_optimum/snapshots.json',D/'results/run_26_unified_new_maps/snapshots.json']
    sources=[D/n for n in ['baseline_suite.py','p2_search_audit.py','unified_candidates.py','unified_geometry.py','bfs_metric_geometry.py','model.py','planners.py','audit.py','scenarios.py','supplement_route_metrics.py']]
    sources+=list((D/'oarp_replan').glob('*.py'))+[Path(__file__)]
    hashes={str(p):sha(p) for p in inputs+sources}
    write(O/'protocol.json',dict(methods=METHODS,seed='32000+case_index',micro_budget=.5,medium_budget=2,
      fixtures_budget=.5,inputs_and_sources_sha256=hashes,scale_benchmark=False,
      OARP='variant2; calibrated cap; original LP/MIP/certification logs; common geometry and fallback; mandatory full blocks',
      fairness='same one-cell model, known current map, start/base, cold per-method cache; sequential rotated order; total soft budget'))
    profile=calibrate();write(O/'runtime_profile.json',profile)
    cmd=[sys.executable,'-X','utf8','-m','unittest','test_oarp_core','test_bfs_metric_geometry','test_structure_candidates','test_scenarios_v3','test_baseline_contract']
    test=subprocess.run(cmd,cwd=D,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8')
    (O/'regression_tests.log').write_text(test.stdout,encoding='utf-8')
    if test.returncode:raise RuntimeError('regression tests failed; no freeze')
    cases=[]
    for batch,path,budget in [('micro',inputs[0],.5),('medium',inputs[1],2)]:
        for r in read(path):
            raw=r.get('snapshot',r);s=deserialize(raw);meta=r.get('metadata',raw.get('metadata'))
            cases.append((batch,s,set(map(tuple,meta['initial_targets'])),budget,True))
    cases.extend(('fixture',s,initial,.5,expected) for s,initial,expected in fixtures())
    results=[]
    for index,(batch,s,initial,budget,expected) in enumerate(cases):
        order=METHODS[index%3:]+METHODS[:index%3]
        for method in order:
            r=solve(s,initial,method,budget,32000+index,profile)
            if expected and not r['route']:raise AssertionError((s.name,method,'missing feasible route'))
            if not expected and r['route']:raise AssertionError((s.name,method,'infeasible fixture accepted'))
            r.update(case=s.name,batch=batch,expected_feasible=expected)
            if r['route']:r['metrics']=metrics(r['route'],s.targets,s.covered)
            results.append(r)
        write(O/'results.json',results)
        if index%8==0:print(f'{index+1}/{len(cases)} states checked',flush=True)
    # Snapshot-contract misuse must be rejected, not silently changed.
    s,initial,_=next(fixtures())
    for bad in [replace(s,radius=1),replace(s,free=s.free-{(3,2)})]:
        for method in METHODS:
            try:solve(bad,initial,method,.5,0,profile)
            except ValueError:pass
            else:raise AssertionError('invalid input accepted')
    assert hashes=={str(p):sha(p) for p in inputs+sources}
    sums=[]
    for batch in ('micro','medium','fixture'):
        for method in METHODS:
            rs=[r for r in results if r['batch']==batch and r['method']==method]
            sums.append(dict(batch=batch,method=method,n=len(rs),valid=sum(bool(r['route']) for r in rs),
              fallback_selected=sum(r['fallback_selected'] for r in rs),overrun_gt_10ms=sum(r['overrun_gt_10ms'] for r in rs),
              core_tours=sum('tour' in r.get('detail',{}) for r in rs),
              certified_repairs=sum(r.get('detail',{}).get('rank',{}).get('certification_repair',False) for r in rs)))
    write(O/'summary.json',sums)
    F.mkdir(parents=True)
    for p in sources:
        dest=F/'source'/p.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    shutil.copyfile(O/'runtime_profile.json',F/'runtime_profile.json')
    # Record exact local native dependencies without duplicating a large runtime.
    deps=D/'.deps';depfiles=[p for p in deps.rglob('*') if p.is_file() and p.suffix in ('.py','.pyd','.dll')]
    runtime=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),glns=glns.__version__,pyscipopt=pyscipopt.__version__,
      dependency_root=str(deps),dependency_sha256={str(p.relative_to(deps)):sha(p) for p in depfiles})
    write(F/'runtime.json',runtime)
    manifest=dict(version='v1_20261012',methods=METHODS,source_sha256={str(p.relative_to(D)):sha(p) for p in sources},
      runtime_profile_sha256=sha(F/'runtime_profile.json'),audit_summary=sums,input_sha256={str(p):sha(p) for p in inputs},
      caveats=['not complete paper reproductions','OARP C++ GLNS port, not Julia','empirical cap has no worst-case guarantee','SCIP certified repair is explicit adaptation','no real battery/dynamics','large-scale performance not validated'],
      frozen_dependencies='native packages referenced at original path and pinned by hash; source snapshot is preserved')
    write(F/'manifest.json',manifest)
    (F/'load_frozen.py').write_text("from pathlib import Path\nimport sys\nROOT=Path(__file__).parent\nsys.path.insert(0,"+repr(str(deps))+ ")\nsys.path.insert(0,str(ROOT/'source'))\nfrom baseline_suite import solve, METHODS\n",encoding='utf-8')
    # Verify the archive imports its own baseline file, not the working source.
    probe=subprocess.run([sys.executable,'-X','utf8','-c',"import load_frozen,baseline_suite;print(baseline_suite.__file__)"],cwd=F,capture_output=True,text=True,encoding='utf-8')
    assert probe.returncode==0 and str(F/'source') in probe.stdout,probe.stdout+probe.stderr
    write(O/'completion.json',dict(states=len(cases),runs=len(results),routes=sum(bool(r['route']) for r in results),all_checks_passed=True,
      contract_rejections=6,hashes_unchanged=True,frozen_version=str(F),regression_tests_passed=True))
    print(json.dumps(sums,ensure_ascii=False));print('FROZEN',F,flush=True)

if __name__=='__main__':main()
