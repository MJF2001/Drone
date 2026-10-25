"""Archive this technical stop; never imports project code or any planner."""
from pathlib import Path
import ast, json, hashlib, sys, datetime
H = Path(__file__).resolve().parent; R = H.parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def save(p, x):
    with Path(p).open('x', encoding='utf8') as f: json.dump(x, f, ensure_ascii=False, indent=2)
def text(p, value):
    with Path(p).open('x', encoding='utf8') as f: f.write(value)
def prepare():
    assert (H/'preflight/SEAL_CREATION_CONTRACT_BLOCK.json').exists()
    syntax = []
    paths = sorted(list(H.glob('*.py')) + list((H/'frozen_source_bytes').glob('*.py')))
    for p in paths:
        ast.parse(p.read_text(encoding='utf8'), filename=str(p))
        syntax.append(dict(path=str(p), sha256=sha(p), passed=True))
    save(H/'preflight/active_syntax.json', dict(active_files=syntax,
        scope='stop-time package source snapshot and three frozen byte references; not the completed production A dependency gate',
        production_gate_status='NOT_COMPLETED', total=len(syntax)))
    ledger = dict(real_entry_cap=306, v01_real_entries=0, v02_real_entries=0,
        real_entries=0, real_cores=0, history_prep_entries=0, gate_entries=0, formal_entries=0,
        ordinary_graph_searches=0, exact_coverage_searches=0, new_cold_planner_imports=0,
        required_B2_synthetic_entry_calls=0, required_B2_stub_core_calls=0,
        supplemental_isolated_seal_collision_attempts=1, supplemental_fake_inventory_subprocesses=1,
        supplemental_synthetic_seal_failures=1, production_seal_attempts=0,
        actual_histories=0, actual_prefixes=0, actual_event_inputs=0,
        hypothesis_result='NOT_TESTED', experiment_results_created=False)
    save(H/'call_ledger.json', ledger)
    slots = []
    for phase, count in [('prep',6),('gate',12),('formal',288)]:
        for i in range(count): slots.append(dict(phase=phase, planned_slot=i+1, execution='NOT_RUN',
            note='planned budget slot only; event state/job not generated or accepted'))
    save(H/'unrun_slots.json', slots)
    save(H/'technical_stage_status.json', {
        'upstream_v02_stop_verification':'ACTUALLY_PASSED',
        'guard_application_and_body_AST':'MATCHED_REVIEWED_PROPOSAL_PLUS_ONE_DECLARED_TECHNICAL_GATE',
        'A_full_dependency_gate':'NOT_COMPLETED; stop-time local source syntax snapshot only',
        'B1_actual_ordinary_import':'NOT_RUN', 'B2_required_four_fixtures':'NOT_RUN',
        'C_synthetic_export_readback':'NOT_RUN', 'D_eight_statistical_stubs':'NOT_RUN',
        'D_two_negative_gate_fixtures':'NOT_RUN',
        'supplemental_seal_contract_probe':'CONFIRMED_BLOCK; subprocess exit2, isolated child FileExistsError',
        'technical_total_PASS':'NOT_CREATED', 'seal1':'NOT_CREATED', 'seal2':'NOT_CREATED'})
    save(H/'STOP.json', dict(status='STOPPED_FOR_REVIEW', date='2026-10-21',
        reason='prepared frozen reference files conflict with seal.py exclusive creation',
        authorization_boundary='v0.3 execution draft section2: additional substantive error requires preserving evidence and stopping',
        root_cause='preparation copied frozen_source_bytes, while inherited stage1 seal still uses target.open(xb)',
        attribution='integration error between the v0.3 preparation choices and inherited seal contract; frozen algorithm error not established',
        production_seal_not_attempted=True, repair_applied=False, hypothesis_result='NOT_TESTED'))
    report = '''# v0.3准备／封存契约冲突停止报告

日期：2026-10-21。状态：技术停止，等待负责人审核。真实入口0/306、核心0；侧向位置假设仍为NOT_TESTED。

已在独立v0.3应用审查过的worker main守卫，并单独加入技术PASS门控。去掉明确新增的一条require('technical')后，原任务体AST相同；v0.2的两处字典修复保留。run/seal增加技术门控，verify增加原稿允许的CSV读取上限。来源、最小diff、原提案匹配记录均保存。未完成动态闭包与四启动夹具，不能声称作用域和命令行路径已验收。

这次停止来自准备流程自身的集成错误：prepare_v03.py提前按原字节复制了frozen_source_bytes/runtime.py、candidate.py、p2_adapter.py；继承的seal.py第一阶段仍用target.open('xb')独占创建同一路径。现有文件即使字节正确，独占创建也会报FileExistsError。我在准备时没有协调这两个步骤的文件所有权。不是冻结规划算法的错误，也没有算法失败结果。

隔离夹具probe_seal_collision.py执行实际seal.py源码，使用明确标记SYNTHETIC_NOT_EXPERIMENT的目录、common接口和清单子进程替身，复制“源和参考文件都已存在”的条件。实际源码在seal.py第17行抛FileExistsError；子进程非零，外层确认后退出2。未导入真实runtime/candidate/p2_adapter，未执行worker，没有合成或真实规划入口/核心。夹具用替身绕过的前置门控仅为定位文件创建行为，不代表生产门控通过；它也不替代B1、B2、C或D。

生产seal1未尝试。按v0.3执行稿第2节“发现额外实质错误则保留证据并停止”，未修seal、未移走或删除已复制参考文件、未伪造PASS、未继续实验。单独保存了停止时包内活动代码及三参考源码的语法快照；这不等于已完成A的实际依赖总门槛。B1/B2/C/D均未运行，新版技术总PASS、八桩PASS与两阶段seal均未创建。

原6份初始输入和准备调度存在且字节未改；真实历史、12前缀、位置候选表及48事件输入均未产生。6准备、12门槛、288正式共306槽全部NOT_RUN；普通图搜索和精确覆盖搜索均0。旧v0.1/v0.2与冻结原件不改，留出未用，未提交推送Git。

后续需负责人裁决准备与封存的文件所有权：例如封存时对已存在参考进行原字节验收，仅对不存在文件独占创建；或另定准备参考保存位置。这里仅说明修复方向，未应用补丁或创建后继版本。后续若授权接续，仍须重做完整技术预检，不可复用本停止包作生产PASS。

verify_stopped_v03.py只读核查旧证据hash、来源hash、守卫AST、停止时语法记录、冻结参考字节、隔离异常证据、未运行306槽和零调用账。通过只证明本停止包记录一致，不证明技术总门槛通过或研究假设成立。
'''
    text(H/'准备封存契约冲突停止报告.md', report)
    text(H/'review_packet.md', '''# v0.3审核入口

先读准备封存契约冲突停止报告.md，再看preflight/SEAL_CREATION_CONTRACT_BLOCK.json及隔离夹具stderr.log。

worker守卫已应用，动态验收尚未完成。准备提前复制冻结参考，与原seal独占创建发生冲突；实际seal源码在纯合成环境已复现FileExistsError。未运行生产seal，真实入口/核心0，306槽未运行，假设NOT_TESTED。

所有旧证据与冻结源码保留。未修新增缺陷、未自动启动下一版。只读核查：运行环境/python/python.exe -B -X utf8 本目录/verify_stopped_v03.py。仅核查停止包，不执行规划器。
''')
    progress = R/'当前进度与下一步.md'; original = progress.read_bytes()
    with (H/'root_progress_before_v03_stop.md').open('xb') as f: f.write(original)
    addition = '''# 最新停止：侧向拓宽v0.3准备参考复制与封存独占创建冲突（2026-10-21）

独立v0.3已应用worker main守卫及明确技术门控，原任务体剥离单条新增门控后AST相同，保留v0.2字典修复与允许的CSV读上限调整。准备时提前复制三份冻结字节参考，与继承seal.py第一阶段target.open('xb')发生文件创建契约冲突；隔离夹具执行实际seal源码复现FileExistsError，未加载真实规划器，也未运行生产seal。属于准备流程集成错误，不是算法失败。

按v0.3“额外实质错误即停”保留证据，未修改封存逻辑或自动接续。停止时包内源码语法快照保存，完整A依赖总门槛未完成，B1/B2/C/D未运行；总PASS、八桩PASS、seal1/2均未创建。真实入口0/306、核心0、图搜索0；6准备/12门槛/288正式全NOT_RUN，真实历史/前缀/事件输入0，研究假设仍NOT_TESTED。v0.1/v0.2与冻结源码不改，留出不用，Git不提交推送。审核入口：PPCPP侧向拓宽开发诊断_v0.3_20261021/review_packet.md及准备封存契约冲突停止报告.md。只读verify_stopped_v03仅验证停止包一致性，不能当技术总门槛或实验通过。

---

'''
    with progress.open('wb') as f: f.write(addition.encode('utf8') + original)
    with (H/'root_progress_after_v03_stop.md').open('xb') as f: f.write(progress.read_bytes())
    excluded={'manifest.json','completion_manifest.json','stopped_verify.log','verification_receipt.json'}
    save(H/'manifest.json', {str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in excluded})
    print('Stop evidence, local syntax snapshot, honest stage/call ledgers,306 unrun slots, review packet and root progress archived; no planner import', flush=True)
def complete():
    log=H/'stopped_verify.log';assert 'ALL PASS STOP-PACKAGE AUDIT ONLY' in log.read_text(encoding='utf8')
    save(H/'verification_receipt.json', dict(scope='STOP_PACKAGE_ONLY_NOT_EXPERIMENT', status='PASS',
        log_sha256=sha(log), verifier_sha256=sha(H/'verify_stopped_v03.py'), utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    save(H/'completion_manifest.json', dict(files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='completion_manifest.json'}, self_hash_excluded=True))
    print('Completion manifest saved; stopped package only; no production PASS created', flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['--complete']: complete()
    else: prepare()
