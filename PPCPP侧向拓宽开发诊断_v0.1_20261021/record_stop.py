"""Record pre-entry launcher failure; no repair, planner import or graph search."""
from common import *
import ast,datetime
assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*')) and not list((H/'logs').glob('*'))
errors=[]
for p in sorted(H.glob('*.py')):
    try:ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    except SyntaxError as ex:errors.append(dict(file=p.name,sha256=sha(p),line=ex.lineno,offset=ex.offset,message=ex.msg,text=ex.text))
assert {x['file'] for x in errors}=={'analysis.py','verify.py'}
save(H/'syntax_findings.json',errors)
failure=dict(stage='preparation_launcher_import',observed_log='prep_execution.log',cause="analysis.py export dictionary uses visits_A=.../pp_first_A_event=... inside a dict literal; requires key:value syntax. verify.py has same latent report-table syntax error.",code='SYNTAX_ERROR_BEFORE_ANY_ENTRY',actual_process_entry_starts=0,actual_core_calls=0,sealed_source_changed=False,no_fix_or_retry=True,impact='Cannot launch real preparation through this frozen scheduler; no history, event inputs or algorithm comparison generated. Statistics stubs do not import these modules and did not establish full-source syntax validity.')
save(H/'failures.json',[failure]);save(H/'STOP.json',dict(status='STOPPED_BEFORE_PREPARATION_ENTRY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),failure=failure,decision='Stop under execution draft technical-error rule. Preserve first seal/source/logs, request responsible review for successor version.',hypothesis_result='NOT_TESTED',planned_cap=306,actual_entries=0))
slots=[]
for j in read(H/'prep_order.json'):slots.append(dict(**j,execution='NOT_RUN',input_exists=True,reason='pre-entry launcher syntax error'))
for i,(L,w) in enumerate((L,w) for L in (18,30,42) for w in (3,5)):
    gid=f'g{i:02d}'
    for count in (L//2,2*L//3):
        group=f'{gid}_b{count:03d}'
        for cond in CONDS:
            case=f'{group}_{cond}'
            if (L==18 and w==3 and count==9) or (L==42 and w==5 and count==28 and cond in ('H_SIDE','U_SIDE')):
                for method in METHODS:slots.append(dict(id=f'gate_{case}_{method}',phase='gate',case=case,method=method,seed=20261021,L=L,w=w,boundary_count=count,condition=cond,execution='NOT_RUN',input_exists=False,reason='real history and event input not generated'))
            for rep,seed in enumerate(SEEDS):
                state_index=next(midx for midx in range(48) if midx==i*8+((0 if count==L//2 else 1)*4)+CONDS.index(cond));methods=METHODS if (state_index+rep)%2==0 else METHODS[::-1]
                for method in methods:slots.append(dict(id=f'formal_{case}_{seed}_{method}',phase='formal',case=case,method=method,seed=seed,L=L,w=w,boundary_count=count,condition=cond,execution='NOT_RUN',input_exists=False,reason='real history and event input not generated'))
slots.sort(key=lambda x:({'prep':0,'gate':1,'formal':2}[x['phase']],x.get('L',0),x.get('w',0),x.get('boundary_count',0),CONDS.index(x['condition']) if 'condition' in x else 0,x['seed']))
assert len(slots)==306 and collections.Counter(x['phase'] for x in slots)==dict(prep=6,gate=12,formal=288)
save(H/'unrun_slots.json',slots);csvsave(H/'306未运行槽位.csv',slots)
save(H/'call_ledger.json',dict(actual_true_entries=0,actual_core_calls=0,prep_entries=0,gate_entries=0,formal_entries=0,planned_upper_bound=306,unrun_prep=6,unrun_gate=12,unrun_formal=288,pure_statistic_stub_cases=8,pure_statistic_stub_planner_calls=0,cold_import_inventory_processes=1,cold_import_solve_calls=0,first_seal_files=len(read(H/'seal1.json')['files']),second_seal_created=False,generated_initial_inputs=6,real_preparation_histories=0,event_prefixes=0,event_inputs=0,actual_position_candidate_tables=0,external_feasibility_walks=0,ordinary_graph_searches=0,coverage_exact_searches=0,P2_calls=0,LAST_calls=0,four_direction_calls=0,action_interventions=0,holdout_uses=0,retries=0,failed_launcher_invocations=1,latent_additional_syntax_findings=1))
report='''# 侧向拓宽固定批：准备启动前语法错误停止

本版没有执行真实历史准备、门槛或正式比较。真实入口0/306、核心0；算法问题仍为NOT_TESTED，不能说侧向拓宽无收益或有限继续信号未达到。

## 已做与未做

已经阅读执行稿、当前进度/规定研究资料、侧向场景只读整理及54状态读取核对、四方向结果和压力批实际入口/两指标源码。已锁定原PPCPP模式/P0及冻结P2，未改冻结原件。六份初始输入按指定L/w、T0/F、基地/捕食者/资源生成，未把未来A、事件时刻或标签传入。原runtime/candidate/p2_adapter字节参考保留。

八项纯统计桩实际全部通过，结果在stat_stub_results.json；这些只检验统计函数，新增规划/图搜索0。一次冷导入清单进程没有调用核心，不能当机制验收。第一阶段seal1.json实际封存10242来源/环境/代码/初始输入，第二阶段尚未创建。

启动run.py prep时，Python在导入analysis.py阶段报SyntaxError。analysis.py的CSV导出字典把键值写成visits_A=.../pp_first_A_event=...，而字典字面量应为key:value。run.py须先导入其job_row，因此没有进入main，也未启动worker或创建actual_order。失败完整日志prep_execution.log保留。

独立只读AST扫描又发现verify.py的同一报告表格构造位置也有相同潜在语法错误，均列syntax_findings.json。此扫描只定位源码，不运行planner或改文件。观察到的失败启动1次，另有潜在语法缺陷1处，不伪报两次算法失败。

这是执行方漏做封存前全部源码语法检查的准备错误；八项统计桩通过不能证明调度/分析/核验模块都能导入。seal证明保留了哪些字节，不证明程序有效。没有将其归咎为算法或输入合同错误。

## 停止及证据边界

执行稿第6节要求“技术异常、输入/导入哈希变化、指标不一致或路线审计错误立即停止，不继续用未知错误批量运行”。本错误虽在报告导出语句，但发生于真实准备启动器必需模块的导入；若修正后继续运行会改变已封存执行链，不能用纯离线报告/CSV修复例外来绕过。故本版不修程序、不重新封存继续跑，不创建后继版或补跑。

六个初始输入不等于六条真实历史；本版真实前缀0、位置候选k表0、实际事件输入0。48状态规则能否按真实历史生成尚未验证。306未运行槽位.csv与unrun_slots.json逐项记录原计划6准备/12门槛/288正式，事件槽位明确输入尚不存在；该账只是未运行计划，不是已生成48事件输入或已验证候选可行。

因此没有事件后路线、完整指标成绩、D_H−D_U支持/反向分组、三组详细案例或48路线图，均为未运行，不填0步、不用静态预测代替结果。当前假设及有限继续信号均未检验。没有P2/LAST/四方向/覆盖精确/动作干预或留出调用。

## 核验与交接

原verify.py有潜在语法问题，且完整批的前置数据不存在，未执行。新增verify_stopped.py只读检查停止包：第一阶段来源hash、冻结字节参考、六初始几何、8统计桩、两个静态语法缺陷、无真实输出与306未运行账。它不验证算法收益，也不生成输入或路线。实际是否通过见stopped_verify.log及verification_receipt.json；日志/收据与最终manifest自引用规则另列。

整个失败源/首次seal/日志保留。若要修正，须负责人决定后继版本，并在新封存前真正解析全部源码、验证启动导入链；本轮不自动修复或重跑。更新根进度为真实入口前停止，待负责人审核，不提交推送Git。
'''
with (H/'准备停止报告.md').open('xb') as f:f.write(report.encode('utf8'))
with (H/'review_packet.md').open('xb') as f:f.write('''# 准备停止审核入口

先读准备停止报告.md、STOP.json、syntax_findings.json、prep_execution.log和call_ledger.json。真实入口0/306、核心0，8项纯统计桩通过；实际历史/事件输入尚未生成，不能评价方向假设。

冻结原件和首次seal保留，不修封存执行链继续跑。原verify.py未执行；停止包只读核验使用verify_stopped.py，日志stopped_verify.log，不等同于完成实验核验。

需负责人决定是否另立后继修复，当前没有新机制、结果或自动接续。
'''.encode('utf8'))
print('STOP RECORDED: 0/306 real entries, 8 pure statistic stubs; launcher syntax failure and latent verifier syntax retained; no repair/retry')
