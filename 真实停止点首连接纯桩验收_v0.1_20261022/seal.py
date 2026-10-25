"""Documentation/hash sealing only. Does not run geometry, selector or stub."""
from collections import Counter
from pathlib import Path
import ast
import difflib
from io_utils import HERE, ROOT, write_json, read_json, sha, now

def code_segment(path, name):
    text = path.read_text(encoding='utf-8')
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(text, node)

def main():
    if (HERE/'completion_manifest.json').exists():
        raise SystemExit('Already sealed; refusing overwrite')
    reg = read_json(HERE/'门槛事前登记.json')
    rounds = [read_json(HERE/'repair_rounds'/f'round_{n}'/'result.json') for n in (1, 2)]
    accepted = rounds[-1]
    assert accepted['passed'] == 40 and accepted['failed'] == accepted['not_run'] == 0
    assert accepted['new_sessions'] == 37 and accepted['reused_prior_pass'] == 3
    assert not any(x['upper_bound_violations'] for x in rounds)
    oldfreeze = read_json(HERE/'round_1_freeze.json')
    newfreeze = read_json(HERE/'round_2_freeze.json')
    assert oldfreeze['files']['门槛事前登记.json'] == sha(HERE/'门槛事前登记.json')
    for name, digest in newfreeze['files'].items():
        assert sha(HERE/name) == digest
    unchanged = {name: oldfreeze['files'][name] == newfreeze['files'][name]
                 for name in ('exact.py', 'geometry.py', 'connector.py', 'fixtures.py', '01_接口与数值合同.md', '门槛事前登记.json')}
    assert all(unchanged.values())
    numerical = {name: code_segment(HERE/'repair_rounds/round_1/independent.py', name) == code_segment(HERE/'independent.py', name)
                 for name in ('number', 'canon', 'add', 'load', 'enclose', 'sign', 'floor_exact', 'metric', 'certified', 'hit')}
    assert all(numerical.values())
    write_json(HERE/'修复影响与未改项.json', {'unchanged_files': unchanged, 'independent_unchanged_numerical_functions': numerical,
               'changed': ['independent.legal: integer-valued grid extrema to int for range; rational endpoints unchanged',
                           'io_utils.tuple_coords: coordinate containers only; radical terms retain list schema',
                           'run_gate/verify: failed-slot-only resume, historical pass reuse and source mapping'],
               'expectations_changed': False, 'model_resource_candidate_policy_changed': False})
    pcount, icount = Counter(), Counter()
    for result in rounds:
        pcount.update(result['primary_counts'])
        icount.update(result['independent_counts'])
    repair = read_json(HERE/'repair_prechecks_result.json')
    assert pcount['sessions'] == 77 and pcount['stub_responses'] == 69
    assert pcount['sessions'] <= 162 and pcount['stub_responses'] <= 162
    technical = Counter()
    for n, result in enumerate(rounds, 1):
        for file in (HERE/'repair_rounds'/f'round_{n}'/'outputs').glob('*.json'):
            out = read_json(file)['session']
            if 'response_received' in out:
                technical['fixed_response_events'] += 1
                technical[out['response_received']['kind']+'_responses'] += 1
                technical['handwritten_suffix_edges_delivered'] += len(out['response_received']['points'])-1
            if 'plan' in out:
                technical['primary_accepted_technical_plans_including_failed_gate'] += 1
                technical['primary_accepted_technical_edges_including_failed_gate'] += len(out['plan']['points'])-1
    ledger = {'utc': now(), 'definition': 'Domain-function counters; Fraction arithmetic is internal, not additional LOS queries.',
              'registered_unique_slots': 40, 'final_valid_gate_slots': 40,
              'round_1': {'new_sessions': 40, 'passed': 3, 'failed': 37, 'not_run': 0},
              'round_2': {'new_sessions': 37, 'reused_prior_pass': 3, 'passed': 40, 'failed': 0, 'not_run': 0},
              'cross_round_new_sessions': 77, 'cross_round_stub_responses': 69,
              'historical_failed_slots': 37, 'unused_technical_rounds': 1,
              'cross_round_primary_counts': dict(pcount), 'cross_round_independent_counts': dict(icount),
              'targeted_repair_saved_audit_counts': repair['counts'], 'technical_polylines': dict(technical),
              'final_slot_response_statuses': accepted['response_statuses'], 'zero_calls': accepted['required_zeros'],
              'verify_geometry': 'Not included above. Every verify_receipts/verify_NNN.json records additional saved-only calls.',
              'native_algorithm_routes': 0, 'real_flight_prefixes': 0, 'manual_action_submissions': 24}
    write_json(HERE/'跨轮函数与几何实际账.json', ledger)
    mapping = []
    table = ['# 18类最终门槛与历史分母', '', '第一轮37个技术失败不回写；第二轮仅接续37槽，复用3个首轮通过。', '',
             '|槽|类|预期/实际|结果来源|门槛|', '|---|---|---|---|---|']
    ledgers = []
    for case, row in zip(reg['cases'], accepted['rows']):
        assert case['id'] == row['id']
        data = read_json(HERE/row['evidence_path'])
        out = data['session']
        mapping.append({'id': case['id'], 'group': case['group'], 'source': row['evidence_path'],
                        'sha256': row['evidence_sha256'], 'reused_prior_pass': row['reused'], 'status': row['status']})
        table.append(f'|{case["id"]}|{case["group_name"]}|{row["status"]} / {row.get("reason") or "—"}|'+
                     ('首轮保存通过' if row['reused'] else '第二轮新执行')+'|通过|')
        ledgers.append({'id': case['id'], 'actual_before': out.get('actual_before'), 'actual_after_planning': out.get('actual_after'),
                        'predicted_entry': out.get('predicted_entry'), 'request': out.get('request'),
                        'predicted_final': out.get('plan', {}).get('predicted_final'), 'manual_actions': data.get('actions', []),
                        'actual_final_after_manual_actions': data.get('actual_final'), 'actions_role': data.get('actions_role')})
    write_json(HERE/'40槽最终证据来源.json', mapping)
    write_json(HERE/'实际预测双账汇总.json', ledgers)
    (HERE/'18类结果与历史分母.md').write_text('\n'.join(table)+'\n', encoding='utf-8')
    diffs = []
    for oldname, newname in [('geometry.py', 'geometry.py'), ('audit_geometry.py', 'independent.py')]:
        src = ROOT/'任意方向合法直达有限诊断_v0.1_20261022'/oldname
        diffs.extend(difflib.unified_diff(src.read_text(encoding='utf-8').splitlines(True),
                     (HERE/newname).read_text(encoding='utf-8').splitlines(True), fromfile='old_geometry/'+oldname, tofile='new/'+newname))
    (HERE/'几何复用适配.diff').write_text(''.join(diffs), encoding='utf-8')
    added = []
    for name in ('exact.py', 'connector.py', 'fixtures.py', 'io_utils.py', 'prepare.py', 'run_gate.py', 'verify.py'):
        added.extend(difflib.unified_diff([], (HERE/name).read_text(encoding='utf-8').splitlines(True),
                                        fromfile='/dev/null', tofile='new/'+name))
    (HERE/'独立新增实现.diff').write_text(''.join(added), encoding='utf-8')
    report = '''# 首连接及距离/采集双账：有限纯桩报告

18类、40个固定槽已通过有限验收。实现能在本轮手工有理安全快照上选定唯一S→q，传递真实入向与根式资源，并用固定手写后缀检验连接、信用和返航；规划只改预测账，实际账由手工动作提交更新。这不是完整非格心PPCPP/P2接续，真实核心尚未连接。

## 结果与历史

最终40槽中，30槽接受完整手写路线；5槽按预期拒绝后缀（穿障碍、首点错误、缺任务、超额2槽）；3槽拒绝非法输入（外边界停止点、缺h、浮点分子）；2槽因首段资源不足没有入口。拒绝是预登记的正确结果，不是30/40成功率。零收益与算法失败尚无研究含义，因为本轮没有求解或比较算法。

首轮40槽中3通过、37技术失败，原代码、输入、失败栈及计数全部保留。36槽在独立审核的range收到整数值Fraction时中止，1槽因测试工具把根式项数组也转换成tuple而错误拒绝输入。修复只涉及格心边界的整数容器和坐标tuple转换；精确数值、主几何、入口政策、资源、预期均未改。先额外审核1份旧保存结果并检查tuple不改根式schema，然后第二轮只接续37个失败槽，3个已通过槽按原hash复用。最终40槽是跨两轮证据，不宣称40槽同轮新跑；首轮37失败不被改成通过，也不混入有效结论。

跨轮实际77会话、69固定桩响应，未使用第三轮。最终40槽全部有明确结果、未运行0；历史37失败保留。真实PPCPP/P2、BFS、A*、可视图、探测、闭环均0。全部840份旧H1文件按事前hash只读保护。留出未使用、无推送。

## 关键含义

距离按有理平方距离生成根式，保留精确表达、逐段来源和认证区间；E/M不取整。等距比较用精确点积，再按坐标。恰好9/4、差0.01不足、根式相消到整数额度2均按预期；整数额度只约束未来四邻接原路线，可能排除直达处理后才可负担的路线。

预测信用不回写实际；发布和等待无自动采集。初始任务中心可显式collect_here；重复采集不增加信用、重复动作id不二次扣费。手工中断只扣已提交距离和已到中心，未到q不记q。零段继承真实来向，非零按已飞段更新。24次手工提交中22次提交、2次重复id拒绝，包含14段移动/等待、7次显式采集、1次发布；这不是模拟飞行。

“途中两个格心信用”用独立手写长线段验证，因为最近格心政策选出的gamma不可能先经过另一个更近的自由格心。沿共享自由边的情形也用单独几何原语验证。共7条原语，不冒称它们全部发生在所选gamma上。第8类是资源不足无入口；给定安全S时不伪造所有几何候选非法的例子。完整后缀失败均不换q；返航即使无任务仍检验。

## 实际计算账与边界

两轮主实现候选检查/几何/距离各253次，候选资源检查253次，排序比较234次（其中角度平局分支52、坐标分支8，属于234的子计数）。主路线审核69次，路线几何175次；输入几何87、原语几何7、执行几何14，总主几何536次。主距离构造447次，服务交点276次；域点精确检查2251次。第一轮中止前已发生的查询均在账中。

独立审核两轮共76次会话审核尝试，几何329次、距离272次、服务交点243次；首轮未完成审核仍计尝试。另有修复前置保存复核1次：几何7、距离7、交点8。最终只读verify的新增保存几何、距离、服务检查单列在verify_receipts，不并作新的门槛槽或算法调用。函数账指领域接口，不把内部Fraction运算视为额外规划查询。技术折线/查询并不为0，详见跨轮函数与几何实际账.json。

本轮只支持合同中有限有理输入、公开确定地图与手写后缀，不证明任意实数/无理停点、近边界探测器、隐藏障碍安全、真实飞行安全、闭环、路线优势或创新。非法数值门槛直接测试浮点分子；其他浮点/非有限值由同一严格类型规则拒绝，未把每种类型都记为独立通过案例。完成封存后停止，不自动接H1/P2真实核心。最终封存核验状态以final_receipt.json为准。
'''
    (HERE/'00_通俗报告.md').write_text(report, encoding='utf-8')
    review = r'''# 负责人审核入口

先读00_通俗报告.md、01_接口与数值合同.md、18类结果与历史分母.md。最终核验实际状态看final_receipt.json及verify_receipts/verify_001.json。

- 门槛事前登记.json / 18类事前预期.md：40槽原始预期、各类至多3子例，预期未改。
- round_1_freeze.json / round_2_freeze.json及repair_rounds：首轮37失败原样保留，第二轮只接续37槽，3槽旧通过hash复用；来源见40槽最终证据来源.json。
- round_2_技术修复.diff / 修复影响与未改项.json：两处表示修复与接续包装，主数值/政策未改。
- 实际预测双账汇总.json：保存实际/预测与手工提交，不是执行器世界模拟。
- 跨轮函数与几何实际账.json / repair_prechecks_result.json：77会话69响应、失败尝试与额外保存审核分别计费；不得说几何查询0。
- source_snapshot / source_bindings.json / 旧H1两版只读哈希.json / 几何复用适配.diff / 独立新增实现.diff：来源、原包保护及实现差异。
- verify.py仅用独立slab/比值/有理二分算法审核保存候选证书、路线和动作，不调用主选择器/stub/提交器。每次运行另写verify_receipts并单列新增几何；现场根进度不要求永远等于历史快照。

复核命令（在项目根）：

```powershell
.\运行环境\python\python.exe -B -X utf8 '真实停止点首连接纯桩验收_v0.1_20261022/verify.py'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

封存后停止。仍需负责人决定是否、如何接入真实H1/P2；本轮不提供性能或创新结论，不读取未来事件或留出。
'''
    (HERE/'review_packet.md').write_text(review, encoding='utf-8')
    progress = '''# 最新完成：首连接与距离采集双账有限纯桩验收（2026-10-22）

真实停止点首连接纯桩验收_v0.1_20261022 已按授权完成18类40槽，先看00_通俗报告.md与review_packet.md，最终只读核验状态见final_receipt.json。最终30槽接受手写完整路线、5槽预期后缀拒绝、3槽预期输入拒绝、2槽资源不足无入口；不是算法成功率/性能比较。全部预期事前冻结，未改模型、额度或入口政策。

首轮40槽3通过/37技术失败原样封存：独立几何range收到整数值Fraction导致36槽审核中止；tuple工具误改根式数组导致1槽拒绝。仅修表示层及接续包装；主数值/几何/选择器源码和预期字节不变。额外1次保存结果独立复核后，第二轮仅执行37失败槽全部通过，复用3槽原通过，不重跑它们；首轮失败不回写。跨轮77纯桩会话、69固定响应，未运行0，第三轮未启用。真实PPCPP/P2/BFS/A*/可视图/探测/闭环均0；840份旧H1文件hash保护，无留出或推送。

实现保留S与锁定q、真实h（零段继承/非零更新）、精确根式E/M和认证floor后缀额度，完整后缀拒绝不换q。预测不提交实际；发布/等待不加信用，显式collect_here及实际中心到达才加H。24次手工提交含22成功/2重复id拒绝；不是探测世界或闭环。途中中心/沿共享边分别用手写原语证明，不能冒称被最近格心gamma实际采用。完整40槽证据来源、双账、全部失败及几何费用保存。

两轮主几何536、主距离447、服务交点276；独立几何329/距离272/交点243，另修复前置保存复核几何7/距离7/交点8。最终只读verify新保存几何等另见收据，不调用选择器/桩/真实算法。完成封存后停止交审，不自动启动真实H1/P2连接；非格心真实算法接续、未知障碍、安全/探测、任意无理停点、效率与创新均未确认。

---
'''
    root_progress = ROOT/'当前进度与下一步.md'
    root_progress.write_text(progress+root_progress.read_text(encoding='utf-8'), encoding='utf-8')
    (HERE/'根进度_执行后快照.md').write_bytes(root_progress.read_bytes())
    write_json(HERE/'源码与接口哈希.json', {p.name: sha(p) for p in HERE.glob('*.py')})
    excluded = {'completion_manifest.json', 'final_receipt.json', '封存只读核验.log'}
    files = {str(f.relative_to(HERE)): sha(f) for f in sorted(HERE.rglob('*'))
             if f.is_file() and f.name not in excluded and 'verify_receipts' not in f.parts}
    manifest = {'utc': now(), 'status': 'SEALED_FINITE_PURE_STUB_GATES_STOP', 'accepted_round': 2,
                'files': files, 'root_before': sha(HERE/'根进度_执行前快照.md'),
                'root_after': sha(HERE/'根进度_执行后快照.md'), 'verify_receipts_append_only': True,
                'scope': 'rational safe snapshot connector and ledgers, handwritten suffixes only',
                'cross_round_sessions': 77, 'cross_round_stub_responses': 69, 'native_core': 0}
    write_json(HERE/'completion_manifest.json', manifest)
    print({'sealed_files': len(files), 'gates': 40, 'cross_round_sessions': 77, 'stub_responses': 69, 'native_core': 0,
           'next': 'one saved-only verify then final receipt; stop'})

if __name__ == '__main__':
    main()
