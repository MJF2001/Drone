"""Small independent acceptance probes; no changes to the submitted package."""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'DeepSeek_基线复现隔离工作_20261018'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TEMP'] = os.environ['TMP'] = str(HERE)
sys.path.insert(0, str(OUT / 'src'))
from problem import PlanRequest, Termination, validate_inputs
from adapters import registry
from audit_independent import audit_route

rows = []
def probe(label, method, request):
    start = time.perf_counter()
    result = registry.run(method, request)
    elapsed = time.perf_counter() - start
    audit = audit_route(request, result.route)
    rows.append(dict(label=label, method=method, status=result.status,
                     route=result.route, audit=audit, termination=result.termination,
                     stage_seconds=result.stage_seconds, elapsed=elapsed,
                     configured_limit=request.termination.time_limit_seconds))

free = frozenset((x, 0) for x in range(3))
empty = PlanRequest(case_id='review_empty_resource', free=free,
                    published_targets=frozenset(), covered=frozenset(),
                    current=(0, 0), base=(2, 0), remaining_resource=1)
validate_inputs(empty)
for method in ('EPSILON_STAR', 'CSTAR'):
    probe('empty_pending_return_exceeds_resource', method, empty)

grid = frozenset((x, y) for x in range(5) for y in range(5))
timed = PlanRequest(case_id='review_epsilon_deadline', free=grid,
                    published_targets=grid, covered=frozenset({(0, 0)}),
                    current=(0, 0), base=(0, 0), remaining_resource=1000,
                    termination=Termination(time_limit_seconds=1e-9))
probe('epsilon_deadline_not_enforced', 'EPSILON_STAR', timed)

normal = PlanRequest(case_id='review_p2_clock', free=free,
                     published_targets=free, covered=frozenset({(0, 0)}),
                     current=(0, 0), base=(0, 0), remaining_resource=100)
probe('p2_adapter_clock_before_stop', 'P2_MULTI', normal)

payload = {'planner_calls': len(rows), 'purpose': 'correctness probes, not performance comparison', 'rows': rows}
(HERE / 'review_probe_results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
for row in rows:
    print(json.dumps({k:row[k] for k in ('label','method','status','termination','stage_seconds','elapsed')}, ensure_ascii=False))
    print('audit_errors:', row['audit']['errors'])
