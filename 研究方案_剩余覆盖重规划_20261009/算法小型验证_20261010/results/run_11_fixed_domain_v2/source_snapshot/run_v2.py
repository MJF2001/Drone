"""Diagnostic v0.2: fixed flight permission, changing published inspection set."""
import argparse
from pathlib import Path
import hashlib
import json
import sys
from collections import Counter, defaultdict
from audit import audit, environment_check
from planners import solve
from scenarios import serialize
from scenarios_v2 import all_cases_v2
from run_experiments import write_json


def run(output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    archive = output/'source_snapshot'
    archive.mkdir()
    sources = list(root.glob('*.py'))+[root/'config.json']
    specification = root.parent/'论文资料汇总_三篇文献与论文主题_20261009'/'14_算法实验模型与诊断场景规范_20261010.md'
    sources.append(specification)
    hashes = {}
    for p in sorted(sources):
        data = p.read_bytes()
        (archive/p.name).write_bytes(data)
        hashes[p.name] = hashlib.sha256(data).hexdigest()
    write_json(output/'manifest.json', {'model': 'v0.2 fixed D, no occlusion',
        'python': sys.version, 'source_sha256': hashes, 'held_out': False,
        'algorithms': ['P1', 'P2'], 'time_limit_seconds': 5.0, 'repetitions': 1,
        'road_sizes': [[18, 6], [24, 9]], 'domain_types': ['open', 'corridor'],
        'coverage_progress': [.25, .75], 'capture_radius': 1,
        'budget': '4 * fixed domain cardinality', 'physical_calibration': None})
    cases = list(all_cases_v2())
    snapshots = [serialize(s, meta) for s, meta in cases]
    write_json(output/'snapshots.json', snapshots)
    records, failures = [], []
    for index, (s, meta) in enumerate(cases):
        reason = environment_check(s)
        order = ('P1', 'P2') if index%2 == 0 else ('P2', 'P1')
        for name in order:
            result = solve(s, name, 5)
            check = audit(s, result.route) if result.route else None
            correct = ((result.status == 'environment_infeasible' and result.reason == reason)
                if reason else bool(check and check['valid'] and result.status in ('planned', 'planned_at_timeout')))
            r = {'case': s.name, 'algorithm': name, 'domain_kind': meta['domain_kind'],
                 'family': meta['family'], 'route': result.route, 'audit': check,
                 'status': result.status, 'reason': result.reason, 'seconds': result.seconds,
                 'expected_case_handled': correct, 'certified_environment_reason': reason,
                 'searches': result.searches}
            records.append(r)
            if not correct:
                failures.append({k: r[k] for k in ('case', 'algorithm', 'status', 'reason')})
        write_json(output/'results.json', records)
        print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"] if r["audit"] else r["reason"]}'
              for r in records[-2:]), flush=True)
    by_case = defaultdict(dict)
    for r in records:
        if r['audit'] and r['audit']['valid']:
            by_case[r['case']][r['algorithm']] = r['audit']['length']
    wins, by_family, by_domain = Counter(), defaultdict(Counter), defaultdict(Counter)
    for s, meta in cases:
        pair = by_case[s.name]
        if len(pair) != 2:
            continue
        key = 'P1_shorter' if pair['P1'] < pair['P2'] else 'P2_shorter' if pair['P2'] < pair['P1'] else 'equal'
        wins[key] += 1
        by_family[meta['family']][key] += 1
        by_domain[meta['domain_kind']][key] += 1
    summary = {'snapshot_count': len(cases), 'execution_count': len(records), 'failures': failures,
        'expected_case_handled_count': sum(r['expected_case_handled'] for r in records),
        'wins': dict(wins), 'by_family': dict(by_family), 'by_domain': dict(by_domain),
        'environment_reasons': dict(Counter(meta['environment_reason'] for s, meta in cases)),
        'remaining_target_components': dict(Counter(meta['remaining_target_components'] for s, meta in cases)),
        'old_route_collision_count': sum(meta['old_route_collision'] for s, meta in cases),
        'statuses': dict(Counter(r['status'] for r in records)), 'held_out': False}
    write_json(output/'summary.json', summary)
    lines = ['# 固定飞行域v0.2诊断结果', '',
        '探索集；不是现场验证，不是算法最优性或创新性证明。单次计时不作可靠速度排名。', '',
        f'{len(cases)}个快照，{len(records)}次执行，异常{len(failures)}条。', '',
        '## 成对步数比较', '', '| 场景 | P1较短 | 相同 | P2较短 |', '| --- | ---: | ---: | ---: |']
    for family, counts in by_family.items():
        lines.append(f'| {family} | {counts["P1_shorter"]} | {counts["equal"]} | {counts["P2_shorter"]} |')
    lines += ['', '## 逐例步数', '', '| 快照 | P1 | P2 |', '| --- | ---: | ---: |']
    for s, meta in cases:
        pair = by_case[s.name]
        lines.append(f'| {s.name} | {pair.get("P1", "未完成")} | {pair.get("P2", "未完成")} |')
    lines += ['', '## 说明', '',
        '- 事件前后D固定，待检目标T扩展或飞行禁入B增加；区域外合法飞行是已公开先验，不是未来待检任务信息。',
        '- 两类D下初始路线与历史会不同，因此跨飞行域比较不是固定状态的单因素实验。',
        '- 全部算法仅接收当前快照，不接收元数据；无隐藏未来事件。',
        '- 3×3理想足迹、四邻接单位移动、沿途采集、返回基地；障碍仅禁入，不模拟遮挡。',
        '- 近远障碍按旧路线后缀位置放置，具体索引见元数据；不代表实际空间距离或现场事件概率。',
        '- 此次只运行既有P1/P2，没有修改算法规则，也没有加入文献算法复现。',
        '- 重复位置数与方向变化数保存在audit，不能转换为真实能耗。',
        '- 不与旧版本地图结果合并；没有连续事件试验，没有独立留出集。', '']
    (output/'结果报告.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    run(Path(p.parse_args().output))
