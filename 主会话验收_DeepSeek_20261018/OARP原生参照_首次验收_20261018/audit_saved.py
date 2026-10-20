"""Offline acceptance audit. No project imports and no solver calls.

Only selected pure functions are extracted with AST. A synthetic deadline probe
executes the delivered entry function with mock geometry/finalizer/result objects.
Writes only to this review directory. Does not edit the delivery or its ledger.
"""
import ast
import csv
import hashlib
import itertools
import json
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace, ModuleType
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DELIVERY = ROOT / 'DeepSeek_OARP原生参照核验_20261018'


def read(relative):
    return json.loads((DELIVERY / relative).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(path, names, env):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), env)
    return env


@dataclass(frozen=True)
class Rank:
    axis: str
    cells: tuple

    @property
    def key(self):
        return self.axis, self.cells[0], self.cells[-1]


class GridMetric:
    def __init__(self, free):
        self.free = set(free)

    def reachable(self, start):
        if start not in self.free:
            return set()
        seen, queue = {start}, deque([start])
        while queue:
            x,y = queue.popleft()
            for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if q in self.free and q not in seen:
                    seen.add(q)
                    queue.append(q)
        return seen


def route_audit(payload, state, execution, base, resource):
    route = list(map(tuple, payload['route']))
    free, published, covered = (set(map(tuple,state[k])) for k in ('free','published','covered'))
    q, d = (published-covered)&free, (published-covered)-free
    return {'valid': bool(route) and route[0] == tuple(execution['current'])
            and route[-1] == tuple(base) and set(route) <= free
            and all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:]))
            and q <= set(route) and len(route)-1 <= resource,
            'q_formula_matches': q == set(map(tuple,state['pending'])),
            'd_formula_matches': d == set(map(tuple,state['deferred'])),
            'expected_remaining_resource': resource, 'steps':len(route)-1}


def deadline_mock_probe():
    # The real delivered entry.run function, with no real planner or auditor.
    clock = SimpleNamespace(value=0.0)
    class DeadlineExceeded(Exception):
        pass
    class FakeDeadline:
        def __init__(self):
            self.limit, self.hit = 1.0, False
        @property
        def remaining(self):
            return self.limit-clock.value
        def check(self):
            if clock.value > self.limit:
                self.hit = True
                raise DeadlineExceeded('mock deadline')
        def elapsed(self):
            return clock.value
    flags = ('route_valid','coverage_complete','resource_valid','returned_base','rank_status',
             'rank_optimal','tour_status','core_candidate_valid','fallback_selected','natural',
             'termination_reason','call_within_budget','candidate_accepted_in_time','within_budget')
    audit = {'valid':True,'coverage_complete':True,'ends_at_base':True,'resource':{'ok':True}}
    def finalize(*args, **kwargs):
        clock.value += 2.0  # the final mandatory audit crosses a 1s deadline
        return {'audit':audit,'termination':{'natural':False},'reason':'fallback','status':'finished'}
    env = {'FLAG_KEYS':flags,'time':SimpleNamespace(perf_counter=lambda:clock.value),
           '_clock_deadline':lambda seconds, unused:FakeDeadline(),
           '_audit':lambda request, route:audit,'DeadlineExceeded':DeadlineExceeded,
           'methods':SimpleNamespace(METHOD_RANK0='rank0',fallback_route=lambda *a:((0,0),)),
           'finalize':finalize,
           '_result':lambda request,outcome,route,stages,flags,detail,environment,deadline,**kw:
             {'flags':dict(flags),'elapsed_at_return':deadline.elapsed(),'route':route,'stages':stages}}
    extract(DELIVERY/'src/entry.py', {'run'},env)
    old = sys.modules.get('problem')
    module = ModuleType('problem')
    module.environment_status = lambda request:{'ok':True}
    sys.modules['problem'] = module
    try:
        request = SimpleNamespace(current=(0,0),base=(0,0),pending=set(),free={(0,0)})
        result = env['run'](request,'rank0',seconds=1.0,seed=0,fallback_only=True)
    finally:
        if old is None:
            del sys.modules['problem']
        else:
            sys.modules['problem'] = old
    assert result['elapsed_at_return'] == 2.0
    assert result['flags']['call_within_budget'] is True
    assert result['flags']['candidate_accepted_in_time'] is True
    result['real_planner_calls'] = 0
    result['mock_only'] = True
    return result


def main():
    manifest = read('manifests/delivery_sha256.json')
    before = {rel:digest(DELIVERY/rel) for rel in manifest['files']}
    bad = [rel for rel,value in manifest['files'].items() if before[rel] != value]
    ledger_before = digest(DELIVERY/'logs/calls_ledger.csv')
    proc = subprocess.run([sys.executable,'-B','-X','utf8',str(DELIVERY/'verify_delivery.py')],
                          capture_output=True,text=True,encoding='utf-8',timeout=30)
    original_checker = {'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
    rows = list(csv.DictReader((DELIVERY/'logs/calls_ledger.csv').open(encoding='utf-8-sig')))
    starts = [r for r in rows if r['phase']=='start']
    grouped = Counter(r['run_id'] for r in starts)
    duplicate = {k:v for k,v in grouped.items() if v>1}
    cases = read('protocol/cases.json')
    preparations = {p['name']:p for p in cases['preparations']}
    route_checks, event_checks = [], []
    for path in sorted((DELIVERY/'artifacts/responses').glob('*.json')):
        item = json.loads(path.read_text(encoding='utf-8'))
        event = read(f"artifacts/events/{item['case_id']}.json")
        prep = event['event']['prep']
        execution = read(f'artifacts/executions/{prep}.json')
        audit = route_audit(item,event['state'],execution,preparations[prep]['base'],1000-execution['steps_used'])
        audit.update(plan_id=item['plan_id'],fallback=item['flags']['fallback_selected'],
                     natural=item['flags']['natural'])
        route_checks.append(audit)
    methods = extract(DELIVERY/'src/methods.py',{'_strips_from_tour','_axis'}, {})
    touring = extract(DELIVERY/'sources/frozen/source/oarp_replan/tour.py',{'path_sets'}, {})
    n1 = read('artifacts/events/N1.json')
    prep = read('artifacts/plans/prep_rect.json')
    execution = read('artifacts/executions/prep_rect.json')
    remnants = [r for r in n1['remnants'] if r['cells']]
    ranks = [Rank(r['axis'],tuple(map(tuple,r['cells']))) for r in remnants]
    services = [SimpleNamespace(rank=rank,start_index=r['original_indices'][0],
                                end_index=r['original_indices'][-1]) for rank,r in zip(ranks,remnants)]
    route, free = tuple(map(tuple,prep['route'])),set(map(tuple,n1['state']['free']))
    original_blocks = touring['path_sets'](ranks,services,route,free)
    q = set(map(tuple,n1['state']['pending']))
    missing = q - {p for b in original_blocks for p in b['path']}
    corrected = [SimpleNamespace(rank=rank,start_index=min(r['original_indices']),
                                 end_index=max(r['original_indices'])) for rank,r in zip(ranks,remnants)]
    corrected_blocks = touring['path_sets'](ranks,corrected,route,free)
    remaining = q - {p for b in corrected_blocks for p in b['path']}
    assert missing == {(1,1),(2,1)} and not remaining
    block = corrected_blocks[0]
    states = [block['path'],tuple(reversed(block['path'])),((0,2),),((0,0),)]
    strips = methods['_strips_from_tour']([block],states,(2,0,3),{},'probe')
    atom = strips[0]
    straight = len({p[1] for p in atom[2]})==1 if atom[1]=='H' else len({p[0] for p in atom[2]})==1
    assert not straight
    singleton = {'kind':'rank','rank_keys':[('H',(1,1),(1,1))],'path':((1,1),)}
    singleton_out = methods['_strips_from_tour']([singleton],[((1,1),),((1,1),),((0,0),),((0,0),)],
                                                (2,0,3),{singleton['rank_keys'][0]:'H'},'probe')
    assert singleton_out[0][1] == 'V'
    selector = extract(DELIVERY/'src/run_micro.py',{'choose_obstacle'},{'GridMetric':GridMetric})['choose_obstacle']
    native_plan = SimpleNamespace(route=route,strips=[SimpleNamespace(**{**s,'cells':tuple(map(tuple,s['cells']))})
                                                     for s in prep['strips']])
    current, base = tuple(execution['current']),tuple(prep['end'])
    covered = set(map(tuple,n1['state']['covered']))
    event_n3 = read('artifacts/events/N3.json')
    chosen,reason = selector(event_n3['event'],free,q,covered,current,base,native_plan,execution)
    branch_event = {**event_n3['event'],'new_obstacles':'connector_branch_probe'}
    forced_choice,forced_reason = selector(branch_event,free,q,covered,current,base,native_plan,execution)
    eligible, past_annotation_candidates = [], []
    pending_strips = [s for s in native_plan.strips if set(s.cells)&q]
    indices = sorted({i for s in pending_strips for i in range(s.connector_start,s.service_start)})
    for i in indices:
        p = route[i]
        if p in (current,base) or p in q or p not in free:
            continue
        reached = GridMetric(free-{p}).reachable(current)
        if base in reached and q <= reached:
            destination = eligible if i >= execution['current_index'] else past_annotation_candidates
            destination.append({'index':i,'cell':p,'already_covered':p in covered})
    assert chosen == (1,1) and forced_choice is None and not eligible
    assert past_annotation_candidates[0]['cell'] == (0,1)
    n6 = read('artifacts/events/N6.json')
    allresponses = [json.loads(p.read_text(encoding='utf-8')) for p in (DELIVERY/'artifacts/responses').glob('*.json')]
    previous = json.loads((ROOT/'主会话验收_DeepSeek_20261018/OARP参照核查与MLC精读_20261018/probe_results.json').read_text(encoding='utf-8'))
    expected_objective = {(r['case_id'],r['cap']):r['oracle']['objective']
                          for r in previous['rank'] if r['allow_repair']}
    independent = extract(ROOT/'主会话验收_DeepSeek_20261018/OARP参照核查与MLC精读_20261018/probe_reference.py',
                          {'independent_partitions','independent_metrics'}, {})
    n2_q = set(map(tuple,read('artifacts/events/N2.json')['state']['pending']))
    pre_event_ranks = [(r['axis'],tuple(map(tuple,r['cells']))) for r in remnants]
    min_original_bound = min(independent['independent_metrics'](part,pre_event_ranks,n2_q)['bound']
                             for part in independent['independent_partitions'](n2_q))
    saved_math = read('artifacts/strip_math.json')['items']
    matches = 0
    for r in saved_math:
        if r['kind'] != 'strip':
            continue
        expected = expected_objective[r['case_id'],r['cap']]
        matches += (r['objective'] is None and expected is None) or (
            r['objective'] is not None and expected is not None and abs(r['objective']-expected)<1e-6)
    math_tree = ast.parse((DELIVERY/'tools/run_math.py').read_text(encoding='utf-8'))
    gtsp_fn = next(n for n in math_tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_gtsp_items')
    specs = ast.literal_eval(next(n.value for n in gtsp_fn.body if isinstance(n,ast.Assign)
                                  and any(isinstance(t,ast.Name) and t.id=='specs' for t in n.targets)))
    brute_gtsp = []
    for spec in specs:
        blocks = spec['blocks']
        values = []
        for order in itertools.permutations(range(len(blocks))):
            for direction in itertools.product((0,1),repeat=len(blocks)):
                cursor, cost = (0,3), 0
                for k in order:
                    service = blocks[k][::(-1 if direction[k] else 1)]
                    cost += abs(cursor[0]-service[0][0])+abs(cursor[1]-service[0][1])+len(service)-1
                    cursor = service[-1]
                values.append(cost+abs(cursor[0])+abs(cursor[1]-3))
        saved = next(r for r in read('artifacts/gtsp_math.json')['items'] if r['case_id']==spec['case_id'])
        brute_gtsp.append({'case_id':spec['case_id'],'recomputed_cost':min(values),
                           'saved_cost':saved['exact_cost'],'matches':min(values)==saved['exact_cost']})
    result = {
        'new_planner_calls':0,'original_checker':original_checker,
        'delivery_manifest':{'count':len(before),'mismatches':bad,
                             'files_unchanged_after_review':all(digest(DELIVERY/rel)==h for rel,h in before.items()),
                             'ledger_unchanged':digest(DELIVERY/'logs/calls_ledger.csv')==ledger_before,
                             'prefix_seal_files':len(list((DELIVERY/'manifests').glob('ledger_seal_*.json')))},
        'ledger':{'starts':len(starts),'ends':sum(r['phase']=='end' for r in rows),
                  'start_kinds':dict(Counter(r['kind'] for r in starts)),
                  'duplicate_run_ids':duplicate},
        'routes':{'checked':len(route_checks),'valid_at_actual_remaining_resource':sum(r['valid'] for r in route_checks),
                  'detail':route_checks},
        'N1_pure_replay':{'services':[(s.start_index,s.end_index) for s in services],
                         'blocks':original_blocks,'missing':sorted(missing),
                         'only_minmax_index_change_blocks':corrected_blocks,
                         'only_minmax_index_change_missing':sorted(remaining),
                         'decoded_packet_as_single_strip':strips,'strip_is_straight':straight,
                         'valid_old_suffix_steps':len(route[execution['current_index']:])-1},
        'axis_probe':{'solver_rank_axis':'H','new_interface_axis':singleton_out[0][1]},
        'N3_pure_replay':{'actual_choice':chosen,'actual_reason':reason,
                          'forced_connector_branch_choice':forced_choice,'forced_connector_branch_reason':forced_reason,
                          'eligible_future_original_connector_annotations':eligible,
                          'past_annotation_candidates_excluded':past_annotation_candidates,
                          'same_coordinate_future_route_indices':[i for i,p in enumerate(route)
                                                                 if i>execution['current_index'] and p==(0,1)],
                          'future_vs_past_interpretation':'only indices at or after the current execution boundary qualify; future service-tail reclassification is not silently added'},
        'N6_obstacle':n6['state']['new_obstacles'],
        'post_event_reference':{'N1_reference_cells':sorted(q),
                               'N2_reference_cells':sorted({tuple(p) for r in read('artifacts/events/N2.json')['remnants'] for p in r['cells']}),
                               'blocked_cell_wrongly_removed_from_reference':(1,1) not in {tuple(p) for r in read('artifacts/events/N2.json')['remnants'] for p in r['cells']},
                               'N2_minimum_bound_against_true_pre_event_reference':min_original_bound},
        'sparse_case':{'protocol_initial_current':preparations['prep_sparse']['current'],
                       'execution_steps':read('artifacts/executions/prep_sparse.json')['steps_used']},
        'fallback_and_natural':sum(r['flags']['fallback_selected'] and r['flags']['natural'] for r in allresponses),
        'saved_subproblem_review':{'certified_objectives_match_previous_independent_oracle':matches,
                                  'certified_items':40,'tolerance':1e-6,
                                  'strict_diagnostics':[(r['case_id'],r['status'],r['objective']) for r in saved_math if r['kind']!='strip'],
                                  'decoded_rank_vectors_saved':sum('ranks' in r for r in saved_math),
                                  'independent_gtsp_cost_recomputation':brute_gtsp},
        'deadline_mock':deadline_mock_probe(),
        'time_difference_sample':next({'run_id':r['run_id'],'wall':r['call_total_seconds'],
                                      'reported_adapter':r['adapter_call_seconds']} for r in rows
                                     if r['phase']=='end' and 'inject_slow' in r['run_id']),
    }
    (HERE/'review_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('routes','N1_pure_replay','ledger')},
                     ensure_ascii=False,indent=2))
    print('ledger starts:',len(starts),'duplicate identities:',len(duplicate))
    print('N1 missing:',sorted(missing),'routes valid:',sum(r['valid'] for r in route_checks),'/',len(route_checks))


if __name__=='__main__':
    main()
