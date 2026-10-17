"""Reproducible exploratory run. Run tests first; never overwrites a run folder."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
from collections import defaultdict
from audit import audit, environment_check
from planners import solve
from scenarios import all_cases, serialize


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def run(output, initial_policy=None):
    root = Path(__file__).resolve().parent
    config = json.loads((root/'config.json').read_text(encoding='utf-8'))
    if initial_policy is not None:
        config['initial_route_policy'] = initial_policy
    # Fail rather than silently ignoring configured geometric/model changes.
    expected = {'footprint_radius': 1, 'grid_neighbours': 4, 'flight_margin': 2,
                'capture_at_every_grid_vertex': True, 'obstacle_occludes_image': False,
                'distance_budget_multiplier': 4, 'two_opt_max_passes': 8}
    for key, value in expected.items():
        if config[key] != value:
            raise ValueError(f'{key} requires an explicit implementation change')
    output.mkdir(parents=True, exist_ok=False)
    sources = sorted(root.glob('*.py'))+[root/'config.json']
    write_json(output/'manifest.json', {
        'date': config['date'], 'stage': config['stage'],
        'python': sys.version, 'platform': platform.platform(),
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'configuration': config})
    snapshots, records, failures = [], [], []
    for s, meta in all_cases(config):
        case_index = len(snapshots)
        snapshots.append(serialize(s, meta))
        certified = environment_check(s)
        for repeat in range(config['timing_repetitions']):
            order = ('P1', 'P2') if (case_index+repeat)%2 == 0 else ('P2', 'P1')
            for name in order:
                result = solve(s, name, config['algorithm_time_limit_seconds'])
                check = audit(s, result.route) if result.route else {
                    'valid': False, 'length': None, 'uncovered': len(s.targets-s.covered), 'errors': []}
                expected_infeasible = certified is not None
                if expected_infeasible:
                    correct = result.status == 'environment_infeasible' and result.reason == certified
                else:
                    correct = result.status in ('planned', 'planned_at_timeout') and check['valid']
                record = {'case': s.name, 'family': meta['family'], 'algorithm': name,
                          'repeat': repeat, 'seconds': result.seconds, 'searches': result.searches,
                          'status': result.status, 'reason': result.reason,
                          'certified_environment_reason': certified, 'expected_case_handled': correct,
                          'audit': check, 'route': result.route}
                records.append(record)
                if not correct:
                    failures.append({'case': s.name, 'algorithm': name, 'repeat': repeat,
                                     'status': result.status, 'audit': check})
        write_json(output/'snapshots.json', snapshots)
        write_json(output/'results.json', records)
        print(f'{s.name}: ' + ', '.join(
            f'{r["algorithm"]}={r["audit"]["length"] if r["audit"]["length"] is not None else r["reason"]}'
            for r in records if r['case'] == s.name and r['repeat'] == 0), flush=True)
    with (output/'results.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['case', 'family', 'algorithm', 'repeat', 'status', 'reason', 'seconds',
                  'searches', 'length', 'uncovered', 'valid', 'expected_case_handled']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({key: r.get(key, r['audit'].get(key)) for key in fields})
    by_pair = defaultdict(dict)
    for r in records:
        if r['repeat'] == 0 and r['audit']['valid']:
            by_pair[r['case']][r['algorithm']] = r
    wins = {'P1_shorter': 0, 'P2_shorter': 0, 'equal': 0}
    rows = defaultdict(lambda: {'P1': [], 'P2': []})
    for pair in by_pair.values():
        if len(pair) != 2:
            continue
        a, b = pair['P1']['audit']['length'], pair['P2']['audit']['length']
        wins['P1_shorter' if a < b else 'P2_shorter' if b < a else 'equal'] += 1
        for name in ('P1', 'P2'):
            rows[pair[name]['family']][name].append(pair[name]['audit']['length'])
    timing = {}
    for name in ('P1', 'P2'):
        times = sorted(r['seconds'] for r in records if r['algorithm'] == name and not r['certified_environment_reason'])
        timing[name] = {'median_seconds': statistics.median(times),
                        'p95_seconds_nearest_rank': times[max(0, (95*len(times)+99)//100-1)],
                        'max_seconds': max(times)}
    deterministic = all(len({tuple(map(tuple, r['route'])) for r in records
                             if r['case'] == s['name'] and r['algorithm'] == name}) == 1
                        for s in snapshots for name in ('P1', 'P2'))
    summary = {'snapshot_count': len(snapshots), 'execution_count': len(records),
               'expected_case_handled_count': sum(r['expected_case_handled'] for r in records),
               'failures': failures, 'paired_feasible_cases': len(by_pair), 'wins': wins,
               'timing': timing, 'repeat_routes_identical': deterministic,
               'held_out_test_used': False}
    write_json(output/'summary.json', summary)
    report = [
        '# 首轮工程原型：探索性验证结果', '',
        '日期：2026-10-10。以下为执行生成结果，不是论文性能结论。', '',
        f'共{len(snapshots)}个共同事件快照，每个原型重复{config["timing_repetitions"]}次，共{len(records)}次执行。',
        f'共同初始路线策略：{config["initial_route_policy"]}；初始路线在事件发生前生成，其耗时不计为事件后重规划耗时。',
        f'预期情况正确处理{summary["expected_case_handled_count"]}次；异常记录{len(failures)}条。', '',
        '## 可行实例的成对路线比较', '',
        f'按首轮执行逐例比较：P1较短{wins["P1_shorter"]}例，P2较短{wins["P2_shorter"]}例，相同{wins["equal"]}例。', '',
        '| 场景族 | 例数 | P1平均剩余长度 | P2平均剩余长度 |',
        '| --- | ---: | ---: | ---: |']
    for family, values in rows.items():
        report.append(f'| {family} | {len(values["P1"])} | {statistics.mean(values["P1"]):.2f} | {statistics.mean(values["P2"]):.2f} |')
    report += ['', '## 求解耗时（可行实例全部重复）', '',
               '| 原型 | 中位数/ms | P95/ms | 最大/ms |', '| --- | ---: | ---: | ---: |']
    for name, t in timing.items():
        report.append(f'| {name} | {t["median_seconds"]*1000:.2f} | {t["p95_seconds_nearest_rank"]*1000:.2f} | {t["max_seconds"]*1000:.2f} |')
    report += ['', '## 必须一起阅读的限制', '',
        '- 当前只是规则地图和公开事件快照的探索集，没有独立确认集，没有连续在线事件实验。',
        '- 采用3×3理想足迹、每个格点采集、道路外2格通行余量。障碍仅限制飞行，不模拟遮挡、真实相机或能耗。',
        '- P1保留旧访问顺序并最低增量插入；P2重建采集位置，采用蛇形/最近邻初解及有限2-opt。多个机制一起变化，不能据总差异判定单个机制贡献。',
        '- 两种方法都把仍合法且能完成更新后全部目标的旧后缀作为共同候选，避免重规划无谓劣化。',
        '- 目前比较的是采集位置访问原型，不是OARP整数条带划分、TRACE或C*的复现。P2不保证最优。',
        '- 旧路线由共同生成器产生，初始路线质量、足迹尺度、区域外通行范围会影响结果；后续需检查敏感性。',
        '- 5秒是本轮保护性求解上限，不是根据真实飞行距离得到的安全截止时间。耗时含规划预检与连接求解，独立事后审计不计入规划耗时。',
        '- 预检不可达与图像不可观测只适用于本离散无额外遮挡模型；资源不足没有被误称环境不可行。',
        f'- 同一快照重复路径一致：{deterministic}。计时仅代表当前Python实现和本机，不能宣称实时保证。',
        '', '原始快照见snapshots.json，全部路径与审计见results.json，逐次指标见results.csv，源码与配置哈希见manifest.json。',
        '可使用 replay_audit.py 对保存路径重新核查，不需重新运行求解器。', '']
    (output/'结果报告.md').write_text('\n'.join(report), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/run_01')
    parser.add_argument('--initial-policy', choices=('snake', 'optimized'))
    args = parser.parse_args()
    run(Path(args.output), args.initial_policy)
