"""Report the completed run, including timeouts rather than filtering them away."""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path


root = Path(__file__).resolve().parent
folder = root/'results/run_14_single_cell_v3'
summary = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
rows = json.loads((folder/'results.json').read_text(encoding='utf-8'))
verified = json.loads((folder/'independent_verification.json').read_text(encoding='utf-8'))
assert not verified['errors']
assert len(rows) == 128
by_family = defaultdict(lambda: defaultdict(list))
for r in rows:
    by_family[r['family']][r['algorithm']].append(r)
with (folder/'results.csv').open('w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['case','family','algorithm','status','seconds','length','deferred_count','active_pending_count'])
    w.writeheader()
    for r in rows:
        w.writerow({k: (r['audit']['length'] if r['audit'] else None) if k == 'length' else r[k] for k in w.fieldnames})
wins = summary['wins']
lines = ['# 单格正下方采集模型重跑结果', '',
    '2026-10-10。探索性诊断，不是文献算法比较、实机实验或最终确认集。', '',
    '## 1. 本轮更改与不变项', '',
    '采集半径由1改为0：每次只检查正下方一格。新增障碍格既禁入又遮挡；未完成且被遮挡的地面保留在暂不可检查账本，不能计入已完成。', '',
    '重新生成初始P2路线、25%/75%检查进度对应的当前位置、真实覆盖历史与旧后缀。障碍沿重新生成的旧路线放置，因此不是只把旧快照改一个参数。', '',
    '保留两种道路尺寸、两种固定飞行域、八类事件、四邻接、返航、4×|D|距离预算与每次5秒计算上限。P1/P2核心算法代码未修改。每快照每方法一次，顺序轮换。', '',
    'P1保留旧访问顺序，新增目标按最小连接增量插入；P2重新生成剩余目标访问顺序，比较蛇形、最近邻及有限2-opt。两者都是自写工程原型，并非OARP、TRACE或C*。', '',
    '## 2. 完成与超时必须一起报告', '',
    '| 原型 | 正常返回可行路线 | 到时返回已有可行路线 | 到时没有可行路线 |',
    '| --- | ---: | ---: | ---: |']
for name in ('P1','P2'):
    c = Counter(r['status'] for r in rows if r['algorithm'] == name)
    lines.append(f'| {name} | {c["planned"]} | {c["planned_at_timeout"]} | {c["timeout"]} |')
lines += ['', f'64个快照、128次执行。独立复核输入账本、8组共同历史和已返回路线，发现错误{len(verified["errors"])}项；未返回路线记录{len(verified["unfinished_records"])}条。这些超时是本轮实际失败结果，不能解释为任务不可行，也不能称全部实验成功。', '',
    '## 3. 两者都返回有效路线时的步数比较', '',
    f'P1较短{wins.get("P1_shorter",0)}例，P2较短{wins.get("P2_shorter",0)}例，相同{wins.get("equal",0)}例。只在双方成功的共同案例中比较步数；其他案例保留在上面的完成统计中。', '',
    '| 事件 | 双方成功例数 | P1较短 | 相同 | P2较短 |', '| --- | ---: | ---: | ---: | ---: |']
labels = {'no_change':'无变化','straight':'直线扩展','corner':'拐角扩展','near_obstacle':'近处障碍','far_obstacle':'远处障碍','channel_obstacle':'通道障碍','straight_channel':'直线扩展＋通道障碍','corner_channel':'拐角扩展＋通道障碍'}
for family, c in summary['by_family'].items():
    lines.append(f'| {labels[family]} | {sum(c.values())} | {c.get("P1_shorter",0)} | {c.get("equal",0)} | {c.get("P2_shorter",0)} |')
lines += ['', '## 4. 遮挡目标与资源口径', '',
    f'{summary["cases_with_deferred_targets"]}/64例含暂不可检查目标，跨快照计数合计{summary["deferred_counts_across_snapshots"]}格；这不是独立真实路面的面积统计。已返回路线完成的是当前未遮挡有效目标并返航，不代表全部已发布路面均已检查。', '',
    '障碍较大可能减少有效检查任务，也可能增加绕行。只能在同一快照下比较方法；不能以不同障碍案例的总步数直接比较算法好坏。', '',
    '当前仍是二维离散问题；没有视觉误差、动态障碍运动、连续多事件、后台边飞边算或真实电量标定。', '',
    '## 5. 本轮判断', '',
    '单格规则使文献模型更易对齐，但没有自动带来创新。旧3×3模型的性能排名与采集位置偏移收益不能继续作为当前模型证据。', '',
    '本轮出现保留旧顺序更短的案例，因此不能再将全量重排描述为普遍更好。另一方面，P1在部分新增任务实例上没有及时给出可行路线；需将首次可行解与后续优化分开审查，不能通过删去超时案例美化路线结果。', '',
    '目前应保留两类参照，按已确定计划推进OARP原模型核心复现；本轮不足以选择论文主算法或宣称优于前人。', '',
    '## 6. 耗时与逐例结果', '',
    '| 原型 | 单次耗时中位数/ms | 最大/ms |', '| --- | ---: | ---: |']
for name, t in summary['timing'].items():
    lines.append(f'| {name} | {t["median_seconds"]*1000:.2f} | {t["max_seconds"]*1000:.2f} |')
lines += ['', '只跑一次，计时含达到5秒上限的执行，不作可靠速度排名。超时检查有少量调度/调用开销，5秒并非实机安全期限。', '',
    '| 快照 | P1步数 | P2步数 | 暂不可检查格数 |', '| --- | ---: | ---: | ---: |']
pairs = defaultdict(dict)
for r in rows:
    pairs[r['case']][r['algorithm']] = str(r['audit']['length']) if r['audit'] else r['status']
for d in json.loads((folder/'snapshots.json').read_text(encoding='utf-8')):
    pair = pairs[d['name']]
    lines.append(f'| {d["name"]} | {pair["P1"]} | {pair["P2"]} | {d["metadata"]["deferred_count"]} |')
lines += ['', '原始文件：`算法小型验证_20261010/results/run_14_single_cell_v3/`，包括snapshots.json、results.json/csv、summary.json、independent_verification.json和source_snapshot。36项单元检查通过；独立回放脚本为verify_v3.py。', '',
    '复核命令：`python -X utf8 verify_v3.py results/run_14_single_cell_v3`。', '']
content = '\n'.join(lines)
(folder/'结果报告.md').write_text(content, encoding='utf-8')
bundle = root.parent/'论文资料汇总_三篇文献与论文主题_20261009'
(bundle/'20_单格采集模型重跑结果_20261010.md').write_text(content, encoding='utf-8')
print(summary)
