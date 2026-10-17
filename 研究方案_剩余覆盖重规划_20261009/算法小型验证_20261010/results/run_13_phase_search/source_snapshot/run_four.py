"""Four-prototype exploratory comparison, using exactly saved stage-one inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import statistics
import sys
from collections import Counter, defaultdict
from audit import audit, environment_check
from planners import solve
from scenarios import deserialize
from run_experiments import write_json

NAMES = ('P1', 'P2', 'P3', 'P4')


def run(source, output):
    root = Path(__file__).resolve().parent
    config = json.loads((source/'manifest.json').read_text(encoding='utf-8'))['configuration']
    snapshots = json.loads((source/'snapshots.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    archived = output/'source_snapshot'
    archived.mkdir()
    hashes = {}
    for path in sorted(root.glob('*.py'))+[root/'config.json']:
        data = path.read_bytes()
        hashes[path.name] = hashlib.sha256(data).hexdigest()
        (archived/path.name).write_bytes(data)
    write_json(archived/'effective_config.json', config)
    write_json(output/'manifest.json', {'configuration': config, 'python': sys.version,
        'platform': platform.platform(), 'source_sha256': hashes,
        'snapshot_source': str(source.resolve()),
        'snapshot_sha256': hashlib.sha256((source/'snapshots.json').read_bytes()).hexdigest(),
        'algorithms': NAMES, 'stage': 'exploratory, not held out'})
    write_json(output/'snapshots.json', snapshots)
    records, failures = [], []
    for index, data in enumerate(snapshots):
        s = deserialize(data)
        certified = environment_check(s)
        for repeat in range(config['timing_repetitions']):
            shift = (index+repeat) % len(NAMES)
            order = NAMES[shift:]+NAMES[:shift]
            for name in order:
                result = solve(s, name, config['algorithm_time_limit_seconds'])
                check = audit(s, result.route) if result.route else {
                    'valid': False, 'length': None, 'uncovered': len(s.targets-s.covered), 'errors': []}
                correct = (result.status == 'environment_infeasible' and result.reason == certified
                    if certified else result.status in ('planned', 'planned_at_timeout') and check['valid'])
                r = {'case': s.name, 'family': data['metadata']['family'], 'algorithm': name,
                     'repeat': repeat, 'seconds': result.seconds, 'searches': result.searches,
                     'status': result.status, 'reason': result.reason,
                     'certified_environment_reason': certified, 'expected_case_handled': correct,
                     'audit': check, 'route': result.route}
                records.append(r)
                if not correct:
                    failures.append({k: r[k] for k in ('case', 'algorithm', 'repeat', 'status', 'reason')})
        write_json(output/'results.json', records)
        print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"]}'
              for r in records if r['case'] == s.name and r['repeat'] == 0), flush=True)
    pairs = defaultdict(dict)
    for r in records:
        if r['repeat'] == 0 and r['audit']['valid']:
            pairs[r['case']][r['algorithm']] = r['audit']['length']
    comparisons = {}
    for name in ('P1', 'P3', 'P4'):
        counter = Counter()
        for pair in pairs.values():
            if name in pair and 'P2' in pair:
                counter['shorter' if pair[name] < pair['P2'] else
                        'longer' if pair[name] > pair['P2'] else 'equal'] += 1
        comparisons[name+'_vs_P2'] = {k: counter[k] for k in ('shorter', 'equal', 'longer')}
    timing = {}
    for name in NAMES:
        times = sorted(r['seconds'] for r in records if r['algorithm'] == name and not r['certified_environment_reason'])
        timing[name] = {'median_ms': statistics.median(times)*1000,
                       'p95_ms': times[(95*len(times)+99)//100-1]*1000, 'max_ms': max(times)*1000}
    deterministic = all(len({tuple(map(tuple, r['route'])) for r in records
                            if r['case'] == s['name'] and r['algorithm'] == name}) == 1
                        for s in snapshots for name in NAMES)
    summary = {'snapshot_count': len(snapshots), 'execution_count': len(records),
               'expected_case_handled_count': sum(r['expected_case_handled'] for r in records),
               'failures': failures, 'comparisons': comparisons, 'timing': timing,
               'repeat_routes_identical': deterministic, 'held_out_test_used': False,
               'statuses': dict(Counter(r['status'] for r in records))}
    write_json(output/'summary.json', summary)
    lines = ['# 四种原型共同快照比较', '', '同一批既有探索快照，非独立确认集；不代表论文算法复现。', '',
             f'{len(snapshots)}个快照，{len(records)}次执行，异常{len(failures)}条。', '',
             '| 相对P2 | 更短 | 相同 | 更长 |', '| --- | ---: | ---: | ---: |']
    for name, values in comparisons.items():
        lines.append(f'| {name} | {values["shorter"]} | {values["equal"]} | {values["longer"]} |')
    lines += ['', '| 算法 | 中位数/ms | P95/ms | 最大/ms |', '| --- | ---: | ---: | ---: |']
    for name, t in timing.items():
        lines.append(f'| {name} | {t["median_ms"]:.2f} | {t["p95_ms"]:.2f} | {t["max_ms"]:.2f} |')
    lines += ['', '## 逐例步数', '', '| 快照 | P1 | P2 | P3 | P4 |', '| --- | ---: | ---: | ---: | ---: |']
    for case, pair in pairs.items():
        lines.append('| '+case+' | '+' | '.join(str(pair.get(n, '失败')) for n in NAMES)+' |')
    lines += ['', '## 解释边界', '',
        '- 共同3×3理想采集足迹、四邻接运动、2格道路外通行余量；障碍只限制飞行，不模拟图像遮挡或真实能耗。',
        '- 全部方法共享合法旧后缀候选、A*与独立路径审计、5秒上限。P2不保证最优。',
        '- P3按未完成目标格的四邻接连通性重建分组；保留旧路线首次涉及各组的顺序，新组最低连接代价插入；固定组顺序用两状态动态规划选正反方向。没有历史分解树输入，不能声称实现增量树维护。',
        '- P4在旧路线转弯、非法位置和不连续处切成直线包；保留承担目标的包，新增目标以共同采集位置作为单点包；用旧顺序和最近端点两种初解，方向动态规划加最多8轮包顺序反转改进。实际执行保留包内路径。',
        '- P3组内采用共同H/V蛇形采集候选，没有P2的组内最近邻和2-opt；P4有包级排序。因此该比较是完整原型效果，不能单独归因为分组或复用。',
        '- P3单连通块可能退化，但因排序器不同不必与P2数值相同。P3仅重建分组，尚不验证多事件历史维护收益。',
        '- 三次重复仅用于计时，不是三个独立场景。小地图、单次事件、没有留出集和物理标定。',
        '- 当前包顺序代价是连接加内部长度；完整展开后的覆盖与步数独立审计。包内途中已覆盖也不裁剪，是明确约束，不宣称最优复用。',
        '', '完整路线见results.json；输入见snapshots.json；本次源码已保存在source_snapshot中。', '']
    (output/'结果报告.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(Path(args.source), Path(args.output))
