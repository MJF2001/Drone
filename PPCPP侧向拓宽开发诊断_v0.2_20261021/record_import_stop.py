"""Record mandated static-import stop; create an UNAPPLIED guard-only review diff."""
from pathlib import Path
import json,hashlib,ast,difflib,datetime
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP侧向拓宽开发诊断_v0.1_20261021'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,s):
    with p.open('xb') as f:f.write(s.encode('utf8'))
def main():
    assert read(H/'preflight/active_syntax.json')['passed'];block=read(H/'preflight/B_STATIC_BLOCK.json');assert block['worker_import_not_attempted']
    assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*')) and not list((H/'logs').glob('*')) and not list((H/'receipts').glob('*'))
    original=(H/'worker.py').read_text(encoding='utf8');split=original.index('assert Path(runtime.__file__).resolve()');prefix=original[:split];body=original[split:];proposed=prefix+'def main():\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(True))+"\nif __name__=='__main__':main()\n";oldtree=ast.parse(original);newtree=ast.parse(proposed);mainnode=next(n for n in newtree.body if isinstance(n,ast.FunctionDef) and n.name=='main');tail=oldtree.body[len(ast.parse(prefix).body):]
    assert ast.dump(ast.Module(body=tail,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=mainnode.body,type_ignores=[]),include_attributes=False)
    diff=''.join(difflib.unified_diff(original.splitlines(True),proposed.splitlines(True),fromfile='worker.py (current, unguarded)',tofile='worker.py (PROPOSED ONLY, main guard)'));put(H/'worker_main_guard_PROPOSAL_NOT_APPLIED.diff',diff)
    save(H/'worker_guard_proposal.json',dict(applied=False,source_sha256=sha(H/'worker.py'),proposed_normalized_text_sha256=hashlib.sha256(proposed.encode('utf8')).hexdigest(),change='Wrap existing task body from source assertions onward in main(); invoke only under __name__ guard. Existing body AST unchanged.',body_AST_equal=True,planner_calls=0,import_test_run=False,approval_required='Additional worker entry-structure repair beyond two authorized dictionary fixes; section3B requires stop first.'))
    save(H/'STOP.json',dict(status='STOPPED_AT_B_STATIC',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='worker module has unguarded top-level task execution/output write',source_file='worker.py',source_sha256=sha(H/'worker.py'),A_syntax_passed=True,A_files=12,B_dynamic_imports=0,C_synthetic_export_tests=0,negative_fixtures=0,rerun_stat_stubs=0,actual_entries=0,actual_cores=0,hypothesis_result='NOT_TESTED',no_seal_created=True,no_worker_import_executed=True,proposal_applied=False))
    ledger=dict(v01_actual_entries=0,v02_actual_entries=0,v02_actual_cores=0,upper_bound_unchanged=306,prep_entries=0,gate_entries=0,formal_entries=0,upstream_stopped_package_verifications=1,upstream_new_planner_calls=0,syntax_preflight_attempts=1,syntax_active_files=12,syntax_passed_files=12,static_import_safety_attempts=1,static_import_blocked_modules=1,dynamic_import_check_processes=0,synthetic_export_tests=0,negative_gate_fixtures=0,v02_statistic_stubs=0,old_eight_stub_PASS_reused=False,cold_worker_imports=0,worker_launch_attempts=0,real_histories=0,event_inputs=0,ordinary_graph_searches=0,coverage_exact_searches=0,P2_calls=0,LAST_calls=0,holdout_uses=0,unrun_prep=6,unrun_gate=12,unrun_formal=288,automatic_fixes_or_retries_after_block=0)
    save(H/'call_ledger.json',ledger)
    slots=read(OLD/'unrun_slots.json')
    for s in slots:s['reason']='v0.2 B_STATIC blocked unsafe worker import; not run';s['execution']='NOT_RUN'
    save(H/'unrun_slots.json',slots);save(H/'phase_status.json',dict(A='PASS_12_ACTIVE_SOURCES',B_STATIC='BLOCKED_WORKER_IMPORT_SIDE_EFFECTS',B_DYNAMIC='NOT_RUN',C='NOT_RUN',negative_fixtures='NOT_RUN',eight_stat_stubs='NOT_RUN_IN_V02',preflight_PASS='NOT_CREATED',seal1='NOT_CREATED',prep6='NOT_RUN',seal2='NOT_CREATED',gate12='NOT_RUN',formal288='NOT_RUN'))
    report='''# 侧向拓宽v0.2：两处语法修复完成，B项静态预检阻断

本版按接续稿完成了两处已授权字典语法修复，12个活动Python源码全部通过ast.parse。B项静态审查发现worker.py的任务体仍在模块顶层：普通导入会依赖sys.argv读取任务/输出路径、安装审计钩子，具备直接调用runtime.run_payload或p2_adapter.run_payload并写正式结果的路径。没有main守卫。

执行稿第3B节明确要求：**“若静态检查发现导入本身会求解或写正式结果，停并报告，不直接执行有副作用的导入。”** 因此在动态导入前停止，未用inventory分支退出、删掉worker导入或伪造argv来冒充普通导入安全；这些不能证明导入没有副作用。

## 已完成的修复与保全

v0.1停止包只读verify已实际全部通过，日志upstream_verify_stopped.log；原目录和冻结算法未修改。新版source_manifest逐项记录原/新hash：analysis.py和verify.py只做已批准visits_A/pp_first_A_event字典key:value修正，其余接续源码按字节复制。统一diff为v0.1_to_v0.2.diff。

六初始输入和原prep job/map定义逐字节相同；runtime/candidate/p2_adapter从冻结源二进制复制并与v0.1来源预期hash核对。没有复制旧seal、PASS、STOP或manifest充当新状态。旧失败源码仍保留在v0.1，未冒充新版活动源码。

preflight/active_syntax.json记录A项当时全部12活动源码hash和逐项PASS；新增停止包审计程序是停止后工具，不用于继续生产，单独列最终manifest。A通过不代表B/C/实验通过。

## B项具体证据与适用边界

preflight/import_static.json及B_STATIC_BLOCK.json列worker顶层的实际行号和调用表达式：sys.addaudithook、runtime.run_payload、p2_adapter.run_payload和写输出的open。worker.py与v0.1逐字节相同；此缺陷不是新增语法修复引入，而是本轮要求的静态检查新定位到的既有启动结构风险。

静态发现的是“存在导入触发任务的代码路径”，没有实际导入验证或试算。无任务argv时还会在顶层sys.argv访问处失败；提供真实任务argv则可能继续进入任务。无论哪种都不能算所要求的安全导入链。没有断言已经发生求解或写出正式结果。

## 尚未运行

B动态导入0、C合成导出—回读0、两个负向夹具0、新版八统计桩0；没有继承v0.1八桩PASS。技术预检总PASS及两阶段seal均未创建。生产预检门控接线尚未完成，不具备运行资格。

真实入口/核心均0，原6准备＋12门槛＋288正式全部未运行，上限仍306；真实历史/候选表/事件输入0。任务位置规则可生成48状态尚未验证，有限继续信号及路线优劣仍NOT_TESTED。无图搜索、P2/LAST/覆盖精确/留出或额外试运行。

## 未应用的最小修复提案

worker_main_guard_PROPOSAL_NOT_APPLIED.diff仅提出将既有任务体放进main，并以__name__守卫调用；其body AST与原任务体相同，未改几何、seed、预算、求解分支、计时块或算法。proposal JSON记录原hash、结构相同检查和未应用标志。**该提案没有应用到活动worker，也未做动态导入或算法验证。**

这是对两处字典修复之外的worker入口结构新增修复。稿件已规定B发现此问题必须先停，故留给负责人裁决；没有利用“必要门控”解释绕过明示停止条件自动继续。

## 停止包核验

verify_stopped_v02.py只读核对旧包hash、两处最小修复、冻结参考与六输入字节、A记录/B静态调用、无动态/合成/桩/真实运行、未应用提案和306未运行账。它不导入worker或planner，也不代表完成技术总门槛/实验；实际日志与收据另存。

更新根进度为“两处修复完成、A通过、B静态阻断、真实入口0”，封存等待审核；不创建后继实验、不提交推送。
'''
    put(H/'B静态预检停止报告.md',report)
    put(H/'review_packet.md','''# v0.2 B静态阻断审核入口

先读B静态预检停止报告.md和preflight/B_STATIC_BLOCK.json；两字典修复/A解析通过，真实入口0/306，B动态及C/负向夹具/新版8桩均未运行。

接续稿3B明示发现导入会求解/写正式结果时停止。worker顶层仍有实际规划入口和输出写入路径，没有main守卫；活动源未修这一新增结构风险。未应用提案worker_main_guard_PROPOSAL_NOT_APPLIED.diff及body AST相同证明可供裁决，不是已验收补丁。

停止包只读核验使用verify_stopped_v02.py，成功仅表示本停止记录成立，不表示研究假设或实验通过。原v0.1/冻结源保留。
''')
    print('Recorded B_STATIC stop; 0/306 entries, no dynamic import; additional guard-only diff UNAPPLIED for review.')
if __name__=='__main__':main()
