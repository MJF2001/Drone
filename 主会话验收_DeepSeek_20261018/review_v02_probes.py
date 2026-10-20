import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
V02 = HERE.parent / 'DeepSeek_基线复现隔离工作_20261018' / 'revision_v0.2'
sys.path.insert(0, str(V02 / 'src_v02'))
import bootstrap_v02
from problem import PlanRequest, Termination
from adapters import registry, epsilon_star

registry.LEDGER = HERE / 'review_v02_call_ledger.csv'
registry.CONTEXT.update(kind='review', batch='main_review_v02')
free = frozenset({(0, 0), (1, 0), (2, 0)})
request = PlanRequest(case_id='review_v02_empty', free=free,
    published_targets=free, covered=free, current=(0, 0), base=(2, 0),
    remaining_resource=10, termination=Termination(time_limit_seconds=1))
rows = []

class ManualClock:
    now = 0.0
    def __call__(self):
        return self.now

fake = ManualClock()
original_path = epsilon_star.GridMetric.path
def crossing_path(metric, a, b):
    route = original_path(metric, a, b)
    fake.now = 2.0
    return route
original_adapter = registry.METHODS['EPSILON_STAR']['adapter']
registry.METHODS['EPSILON_STAR']['adapter'] = lambda req, clock=None: epsilon_star.run(req, clock, deadline_clock=fake)
with patch.object(epsilon_star.GridMetric, 'path', crossing_path):
    result = registry.run('EPSILON_STAR', request)
rows.append(dict(probe='empty_return_crosses_deadline', fake_elapsed=fake.now,
    limit=1, status=result.status, termination=result.termination, deadline=result.meta['deadline']))
registry.METHODS['EPSILON_STAR']['adapter'] = original_adapter

original_finalize = epsilon_star.finalize
def delayed_finalize(*args, **kwargs):
    time.sleep(0.05)
    return original_finalize(*args, **kwargs)
with patch.object(epsilon_star, 'finalize', delayed_finalize):
    start = time.perf_counter()
    result = registry.run('EPSILON_STAR', request)
    elapsed = time.perf_counter() - start
rows.append(dict(probe='finalize_excluded_from_adapter_total', elapsed=elapsed,
    adapter_call=result.stage_seconds['adapter_call'], status=result.status))

def failed_append(row):
    raise OSError('review_injected_ledger_write_failure')
with patch.object(registry, '_append', failed_append):
    result = registry.run('EPSILON_STAR', request)
rows.append(dict(probe='ledger_failure_suppressed', status=result.status,
    caller_received_exception=False, lost_record=registry.LAST_RECORD))

payload = dict(planner_calls=3, registered_in_review_csv=2,
    injected_registration_failure_record_preserved_here=1, rows=rows)
(HERE / 'review_v02_probe_results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
for row in rows:
    print(json.dumps({k:v for k,v in row.items() if k != 'lost_record'}, ensure_ascii=False))
