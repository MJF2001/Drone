"""Replay the exact 25-test regression set while counting local planner-engine calls."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
import outer_connector_candidate_20261016 as candidate
original=candidate.engine_solve
calls=[]
def counted(snapshot,budget,*args,**kwargs):
    calls.append({"snapshot":snapshot.name,"pending_targets":len(snapshot.targets),"budget_seconds":budget})
    return original(snapshot,budget,*args,**kwargs)
candidate.engine_solve=counted
loader=unittest.TestLoader()
suite=unittest.TestSuite([loader.loadTestsFromName("test_continuous_history_20261016"),
                          loader.loadTestsFromName("test_outer_connector_20261016")])
result=unittest.TextTestRunner(verbosity=2).run(suite)
summary={"status":"PASS" if result.wasSuccessful() else "FAIL","tests_run":result.testsRun,
         "failures":len(result.failures),"errors":len(result.errors),
         "counted_range_engine_planner_calls":len(calls),"calls":calls,
         "formal_development_map_calls":0,"posthoc_synthetic_regression":True}
print("COUNTED_REGRESSION_SUMMARY="+json.dumps(summary,ensure_ascii=False))
dest=Path(__file__).with_name("counted_25_regression_summary_20261017.json")
dest.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
sys.exit(0 if result.wasSuccessful() and result.testsRun==25 else 1)
