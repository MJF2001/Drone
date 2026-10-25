"""Seal stopped batch and honest denominators. No solver/postprocessor evaluation."""
from collections import Counter
from pathlib import Path
import difflib
from common import HERE, ROOT, read, dump, sha, now

def main():
    assert not (HERE/'completion_manifest.json').exists(), 'refuse reseal'
    reg = read(HERE/'registration.json')
    status = read(HERE/'batch_status.json')
    assert status['attempted'] == ['01_H1'] and status['completed'] == [] and status['failed'] == 1 and status['not_run'] == 11
    freeze = read(HERE/'real_freeze.json')
    for name, digest in freeze['files'].items():
        assert sha(HERE/name) == digest, ('frozen_code_or_input_changed', name)
    for binding in read(HERE/'bindings.json'):
        assert sha(ROOT/binding['source']) == sha(HERE/binding['copy']) == binding['sha256']
    tech = read(HERE/'technical_rounds/round_1/result.json')
    real = read(HERE/'outputs/01_H1.json')
    saved = read(HERE/'post_stop_saved_reaudit.json')
    assert not real['passed'] and real['main_passed'] and saved['receipt']['passed']
    assert 'ImportError' in real['failure']['reason']
    assert real['native_counts']['core_started'] == real['native_counts']['core_returned'] == real['native_counts']['core_complete'] == 1
    tw, ti, tp = Counter(), Counter(), Counter()
    for row in tech['rows']:
        tw.update(row['wrapper_counts'])
        ti.update(row['independent_counts'])
        x = read(HERE/'technical_rounds/round_1'/(row['id']+'.json'))
        tp.update(x.get('post', {}).get('counts', {}))
    rw = real['wrapper_counts']
    def geometry_calls(values):
        return sum(value for name, value in values.items() if name.endswith('_geometry'))
    tech_geo = geometry_calls(tw)+tp['candidate']+tp['source_validation']+tp['output_validation']+ti['independent_geometry']
    real_geo = geometry_calls(rw)+sum(real['native_counts'].get('post_'+part+'_geometry', 0) for part in ('candidate','source','output'))
    account = {'utc': now(), 'planned_real_slots': 12, 'attempted_real_slots': 1, 'failed_real_slots': 1,
         'gate_completed_slots': 0, 'not_run_slots': 11, 'actual_H1_core_entries': 1, 'actual_P2_core_entries': 0,
         'native_core_started': 1, 'native_core_returned': 1, 'native_core_complete': 1,
         'new_native_routes': 1, 'new_real_postprocessed_suffixes': 1, 'new_full_main_routes': 1,
         'true_graph_searches': real['native_counts'].get('context_BFS_started',0)+real['native_counts'].get('distance_row_BFS_started',0)+real['native_counts'].get('Astar_started',0),
         'real_wrapper': rw, 'real_native_and_frozen_post': real['native_counts'],
         'original_external_pipeline_audit_calls': 0, 'original_external_auditor_import_failures': 1,
         'technical_rounds_used': 1, 'technical_tests_passed': 11, 'technical_tests_failed': 0,
         'technical_stub_attempts': tech['counts']['core_stub_attempts']+tech['counts']['post_stub_attempts'],
         'technical_stub_normal_returns': tech['counts']['core_stub_returns']+tech['counts']['post_stub_returns'],
         'technical_counts': tech['counts'], 'technical_wrapper': dict(tw), 'technical_independent': dict(ti),
         'technical_frozen_post': dict(tp), 'frozen_post_calls_total': 7, 'frozen_post_calls_technical': 6,
         'frozen_post_calls_real': 1, 'post_stop_saved_reaudit': saved['receipt']['counts'],
         'direct_geometry_predicates_technical': tech_geo, 'direct_geometry_predicates_real_main': real_geo,
         'direct_geometry_predicates_post_stop_saved': saved['receipt']['counts']['independent_geometry'],
         'direct_geometry_before_final_verify': tech_geo+real_geo+saved['receipt']['counts']['independent_geometry'],
         'final_verify_added_queries': 'See append-only verify_receipts; verifier hashes failed slot and saved re-audit receipt, does not retry failed pipeline.',
         'timing': real['timing'], 'detector': 0, 'closed_loop': 0, 'holdout': 0, 'push': 0}
    assert account['technical_stub_attempts'] == 12 and account['direct_geometry_before_final_verify'] == 328
    dump(HERE/'全部调用与失败分母.json', account)
    rows = []
    table = ['# 六状态12槽：事前预期与最终分母', '',
             '原预期全部为有限接口验收通过；实际首槽失败即止，预期未改。', '',
             '|槽|状态|预期q|真实核心|最终状态|', '|---|---|---|---|---|']
    for job in reg['jobs']:
        case = next(c for c in reg['cases'] if c['id'] == job['case'])
        ran = job['id'] == '01_H1'
        row = {'job': job, 'input_sha256': sha(HERE/job['input']), 'expected': case['expect'],
               'status': 'failed_external_auditor_import' if ran else 'not_run_after_stop',
               'core_called': ran, 'main_complete': ran, 'valid_gate_pass': False,
               'saved_output': 'outputs/01_H1.json' if ran else None}
        rows.append(row)
        table.append(f'|{job["id"]}|{case["label"]}|{case["expect"]["q"]}|'+('已调用并完成' if ran else '未调用')+'|'+
                     ('外部审核导入失败，主返回已保存' if ran else '停止后未运行')+'|')
    dump(HERE/'12槽最终状态及输入输出哈希.json', rows)
    (HERE/'六状态12槽结果.md').write_text('\n'.join(table)+'\n', encoding='utf-8')
    report = '''# 首连接真实接入：首槽中止报告

本轮未通过“H1/P2真实管线”的12入口验收。真实阶段只尝试槽01_H1，整槽失败1、通过0、余下11槽未运行；真实H1核心调用1，P2调用0。已按稿停止，不修冻结源码、不补跑、不利用剩余额度。不能把保存数据复核通过说成首槽已通过。

## 失败发生在哪里

首槽实际完成：给定S=(1/4,0)→q=(0,0)，根式资源/预测信用转换，真实H1核心完整格点返回，冻结直达及从S起的主审核和编码。随后worker.py第52行`from audit import load_auditor, audit_one`加载到了冻结基线目录的audit.py；该模块已被baseline_suite导入并占用sys.modules['audit']，没有本轮的load_auditor，因而ImportError。失败栈、加载来源、原生请求/返回、后处理原始JSON和完整主管线均保存。

这是可避免的包装命名冲突。技术桩进程先导入本轮audit，因此没有重现真实进程先加载冻结基线后的模块占用；冷导入检查验证了没有求解副作用和来源冲突，却未验证随后审核器的符号解析。这一缺口不能解释为H1算法失败，也不能据此推断P2行为。真实批开始后未改名、清缓存或重试。

停止后仅新增一个独立只读入口post_stop_reaudit.py，按文件显式加载原字节审核器，对已保存首槽复核一次通过。几何15、距离12、选择证据比较3、服务交点33，H1决策审核1、单位边4，冻结直达保存审核1；核心/选择器/后处理/图搜索新增0。原01_H1.json仍passed=false，batch_status仍failed=1/not_run=11。这是保存返回的可信性证据，不是一次新的真实验收，不重写历史状态。

## 已完成准备和实际计算

六状态和12槽预期、源码/hash、seed=20261022、交替方法顺序均在运行前固定。F≤25、任务≤12、E=100，初始任务=P含全部手工合成历史，捕食者[-3,-3]满足外侧合同；两方法旧参考均为空，来向明确synthetic。没有凭结果挑图或改元数据。

11项包装检查首轮全通过：10次核心桩尝试/返回，2次后处理桩尝试（1正常返回、1预期异常），合计12尝试/11正常响应；包括tuple/list、整数值Fraction与非整数拒绝、根式相消/取floor、JSON、空任务和拒绝分支。技术中真实执行冻结直达6次，真实核心0；新主管线实际直达1次，所以本轮后处理函数共7次，不能称几何或后处理0。没有启用第二/第三技术轮。

真实核心开始/返回/完成各1，原内部审核2且均合法；上下文BFS1和A*1均完成，距离行BFS0，共2次真实图搜索。奖励2次、候选评分2行、方向更新4次。入口候选3、资源检查3、排序比较2；直达source几何4、candidate几何3、output几何3，服务交点6，根式区间函数4次。

包装主审核的几何15次（输入1、入口3、原后缀4、直达后缀3、全路线4），距离构造14、服务交点15。技术全部直接几何288，真实主包装及直达25，停止后保存复核15，合计328；最终只读verify另记。内部图搜索与直接几何不混为一种查询。所有细项见全部调用与失败分母.json。

主管线实际约40.52毫秒，核心适配约23.63毫秒、直达适配约4.50毫秒；保留原始分阶段时间，不作性能比较。主管线未超30秒；本槽没有截止或超额问题。外部审核导入失败不在主管线计时内。原格点后缀4步，直达后缀3段、长度仍4，总长17/4；这只是首槽保存返回的描述，不作为收益或质量结论。实际S/h/H/E/M规划前后相同，q只在预测账采集，原真实E不取整。

## 完成边界和下一步

六状态仅首个轴向快照调用了H1；真实斜向、零接入、已采入口、空任务及P2各槽均未运行，不能称六类真实接入通过，也不能拿技术桩填补真实分母。留出、探测、未知障碍政策、移动执行器、闭环和推送均0。旧源/证据与首轮37失败原样保留。

当前可供负责人审核的是：固定输入/上限、通过的包装桩、一条真实返回及明确的导入故障。后续若获新稿，应独立版本修复审核器身份绑定，并让技术检查在与真实入口相同的导入顺序下验证，再决定是否只接续未运行槽；本轮不自动执行这些修复或复用旧输出。源码和预期保持冻结。封存核验状态见final_receipt.json，封存停止不是算法验收成功。
'''
    (HERE/'00_通俗中止报告.md').write_text(report, encoding='utf-8')
    review = r'''# 负责人审核入口：真实阶段首槽中止

先读00_通俗中止报告.md、六状态12槽结果.md及全部调用与失败分母.json。最终verify状态看final_receipt.json；它证明保存包完整，不把失败批改为验收通过。

- registration.json / inputs / real_freeze.json：六状态、12槽原预期和38项真实开始前冻结。运行后未修改。
- technical_rounds/round_1：11包装检查全通过，12桩尝试、11正常响应、核心0、冻结直达6。
- cold_import_precheck.json / static_import_review.json：无任务副作用、来源绑定；未验证审核器后续解析的缺口如实记录。
- batch_status.json / attempts.jsonl / logs/01_H1.log：首槽失败，11槽未运行；不可自行重启run_real.py。
- outputs/01_H1_native_return.json / 01_H1_post_return.json / 01_H1.json：真实原始请求/返回、主审核、主管线、失败栈。主完成不等于整槽通过。
- post_stop_saved_audit_preregister.json / post_stop_saved_reaudit.json：停止后一次保存数据独立复核，旧failed不回写，无任何新核心/后处理。
- bindings.json / old_files.json / external_source_guards.json / 新增包装.diff：跨版本原字节、旧源及差异。
- verify.py只核验保存数据及哈希；失败槽不重新调用管线。额外保存复核已有绑定收据，verify不再重做它，不生成第二份路线。

```powershell
.运行环境pythonpython.exe -B -X utf8 '真实停止点接入H1_P2最小验收_v0.1_20261022/verify.py'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

真实源码不修复、不重跑，封存停止交审。本轮未通过12入口有限接入验收，不作算法、速度、创新或安全结论。
'''
    (HERE/'review_packet.md').write_text(review, encoding='utf-8')
    diffs = []
    for name in ('common.py','fixtures.py','prepare.py','pipeline.py','native_loader.py','observe.py','audit.py',
                 'technical.py','worker.py','run_real.py','verify.py','post_stop_reaudit.py'):
        diffs.extend(difflib.unified_diff([], (HERE/name).read_text(encoding='utf-8').splitlines(True),
                                        fromfile='/dev/null', tofile='new/'+name))
    (HERE/'新增包装.diff').write_text(''.join(diffs), encoding='utf-8')
    dump(HERE/'frozen_implementation_unchanged_after_real_start.json', {'utc':now(),
         'all_real_freeze_files_unchanged':True, 'count':len(freeze['files']),
         'post_stop_additions_only':['post_stop_reaudit.py','seal.py','report/hash/receipts'],
         'historical_failed_status_not_rewritten':True})
    progress = '''# 最新结果：首连接真实接入首槽外部审核导入失败，已停止（2026-10-22）

真实停止点接入H1_P2最小验收_v0.1_20261022 已按执行稿停止封存，先看00_通俗中止报告.md及review_packet.md，最终包核验状态见final_receipt.json。本轮未通过12入口真实验收：尝试01_H1一槽、失败1、通过0、未运行11；真实H1核心1，P2核心0。不得把保存返回复核或技术桩算入真实通过，剩余额度不自动接续。

11项包装检查首轮全通过，12桩尝试/11正常响应，真实核心0；技术冻结直达6次。六状态、seed、空参考、初始任务/历史、捕食者及调用/时间上限事前冻结，无据结果改图/预期。冷导入没有求解副作用，但没有发现审核器后续名称解析冲突。

首槽H1与冻结直达及完整S起点主审核已完成，原生路线/请求、后处理原文、实际预测账和失败栈完整保存。worker.py:52随后from audit导入命中了冻结基线audit.py，缺本轮load_auditor而ImportError。这是包装模块命名冲突，不是H1算法反例；技术桩先加载本轮audit所以未覆盖真实顺序。真实开始后未修改任何38项冻结文件，未补跑/启用P2。

停止后只对保存首槽显式按文件加载原字节审核器，独立复核1次通过：几何15、距离12、交点33、H1决策1/单位边4，新核心/选择器/后处理/搜索0。旧槽仍passed=false，失败1/未运行11不回写。新只读入口不是运行时修复或真实重试。

实际核心开始/返回/完成1，内部审核2合法；上下文BFS1+A*1完成，距离行BFS0。真实直达1（加技术共7），几何候选3，原/新后缀4/3边。技术直接几何288、真实主流程25、保存复核15共328，核验新增查询另见收据。主管线约40.52ms未超30秒，仅描述首个保存返回，不作性能排名。真实斜向、零接入、已采格入口、空任务返航与P2均未验收。

封存后停止交审。以后需独立版本与同真实导入顺序的技术检查，再由负责人裁决修复/接续；本轮不自动重试、复用首槽或消耗剩余11入口。探测、任意实数停点、未知障碍/连续事件闭环、留出、速度与创新结论均未完成，旧源/证据不改、无推送。

---
'''
    path = ROOT/'当前进度与下一步.md'
    path.write_text(progress+path.read_text(encoding='utf-8'), encoding='utf-8')
    (HERE/'root_after.md').write_bytes(path.read_bytes())
    dump(HERE/'input_output_source_hashes.json', {str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
         if p.is_file() and (p.suffix=='.py' or 'inputs' in p.parts or 'outputs' in p.parts)})
    excluded = {'completion_manifest.json','final_receipt.json','封存只读核验.log'}
    files = {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and p.name not in excluded and 'verify_receipts' not in p.parts}
    dump(HERE/'completion_manifest.json', {'utc':now(), 'status':'SEALED_STOPPED_AFTER_SLOT_01_H1_AUDITOR_IMPORT_FAILURE',
         'files':files, 'root_before':sha(HERE/'root_before.md'), 'root_after':sha(HERE/'root_after.md'),
         'attempted_real_slots':1,'failed':1,'not_run':11,'true_H1_calls':1,'true_P2_calls':0,
         'saved_only_reaudit_passed_does_not_change_failure':True,'no_more_real_execution':True})
    print({'sealed_files':len(files),'attempted':1,'failed':1,'not_run':11,'H1_calls':1,'P2_calls':0,
           'frozen_runtime_files_unchanged':len(freeze['files']),'stop':True})

if __name__ == '__main__':
    main()
