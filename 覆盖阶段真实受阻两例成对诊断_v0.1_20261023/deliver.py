"""Create review indices, prepend root progress, seal; no experimental calls."""
from common import *
import sys,datetime,subprocess,difflib
def main():
 assert not (H/'final_receipt.json').exists()
 old=ROOT/'旧计划真实受阻PPCPP成对诊断_v0.1_20261023'
 for name in ('accepted_OFF_worker.py.txt','R_worker.diff'):(H/'source_snapshot'/name).write_bytes((old/'source_snapshot'/name).read_bytes())
 (H/'source_snapshot/runner_diff.patch').write_text(''.join(difflib.unified_diff((old/'run.py').read_text(encoding='utf-8').splitlines(True),(H/'run.py').read_text(encoding='utf-8').splitlines(True),fromfile='accepted_previous_runner',tofile='two_fixed_case_runner')),encoding='utf-8')
 dump(H/'图版目视核验.json',{'figures':2,'viewed_all':True,'paths':['figures/large_Z_corner_p30.png','figures/medium_Z_corner_p30.png'],'scope':'both full-resolution route panels inspected with view_image; six panels per case, local goal labels and red-N reference convention legible; first fixed original seed','new_search_calls':0})
 dump(H/'冻结元数据文字说明.json',{'frozen_plan_preserved':True,'field':'source_states_are_labels_only','legacy_text':'E changes only free','clarification':'Only one physical obstacle is added; active T is necessarily normalized to P∩F. Already explicit in frozen 01 protocol, input_contract, plan.input_contract, actual normalized E and final prechecks. Physical P/H/U unchanged. This descriptive inherited field must not be used to compare every non-free JSON field. No experiment/input change after formal start.'})
 ledger=read(H/'ledger.json');s=read(H/'summary.json');state=read(H/'两状态等权.json')
 packet={'status':'completed_pending_seal_stop_for_owner_review','draft':'覆盖阶段真实受阻两例成对诊断执行稿_给sol_20261023.md','primary':'B_E vs B_N actual PPCPP calls; R diagnostic and frozen P2 external reference only','processing':ledger,'cases':['large_Z_corner_p30','medium_Z_corner_p30'],'shapes':['Z'],'initial_U':[201,75],'old_edge_pending_not_initial_U':[141,46],'physical_H_preserved':True,'core_projection':False,'view_count':72,'E_N_pairs':{'B':6,'R':6,'C':6,'total':18},'B_C_pairs':12,'state_results':state,'all_saved_independent_receipts_passed':True,'formal_failure':None,'termination':s['termination'],'late':s['budget_and_late'],'B_changed_decision_anchor_credit_pairs':6,'shorter_reference_layer':'large R/C shorter; medium C shorter, R longer; C already shorter in N; no optimum/lower bound','concrete_behavior':'first full trace divergence at recovery goal, large record60 current28,28 and medium record29 current16,15; downstream credit order differs with opposite total-distance direction','necessary_detour_unknown':True,'causal_fault_proven':False,'new_intervention_started':False,'new_innovation_claim':False,'cross_shape_or_universal_claim':False,'P2_natural_means_finite_flow_not_optimal':True,'preparation_repairs_used':2,'export_only_failure_retained':'export_failure_v01.json and plot_saved.py; replacement plot_saved_v02.py reads saved coordinates only','metadata_note':'冻结元数据文字说明.json','stop_after_seal':True}
 dump(H/'review_packet.json',packet)
 (H/'review_packet.md').write_text('''# 负责人审核入口

先读00_通俗两例成对诊断报告.md及两张正反图，再读02全量配对、03成本转弯阶段说明。本轮36处理=24核心（PPCPP12/P2 12）+R12，72原/直达视图全部独立审核通过、覆盖返航资源合格，无正式失败/触顶/迟到/未运行。已停止新实验。

大Z：B原生+2米、直达+1.821854米，R_E比B_E短0.585786米。中Z：B原生0、直达−0.511215米，R_E反而比B_E长1.747283米。两例都在恢复目标首次分歧并改变后续信用序，但效果相反。大Z增量在覆盖中段，中Z末采变化使返航收益抵消覆盖小增量。P2在N/E均更短且全部有限流程自然完成；更短并不等于转弯少或最优。三层分别是必要绕行未知、存在更短参照、存在行为线索；尚未证明单一决策因果错误。

仅2个不同尺度Z族、各原3seed；不是跨形状或6个独立几何，不与上一批返航端混算。初始U为201/75，141/46仅旧失效边时计数。唯一输入selection及其v02引用，原物理H全部保留，包括后来封堵的已采格；核心直接接受H，无投影。旧首版E.json只作排除版本证据，未投入算法。

核对顺序：selection/history/input_contract/input_freeze（来源与合同）；plan/01协议/active_freeze/bindings/source_snapshot（预算/顺序/源码）；prechecks及两份失败与preparation_repairs（六身份、两轮技术修复、无核心）；attempts/status/outputs（36实账、全部原返回/路线/信用/独立回执）；72指标、18环境配对、12_B_C配对、12_B_R辅助配对、6组六分支逐seed（完整结果）；行为与阶段差异/顺序衔接与种子一致性/B阶段距离与末采补充/逐状态计时统计（解释）；调用与查询总账（计数别名不可相加）、ledger、失败触顶迟到及未运行、figure_receipts、图版目视核验、verify_receipt/final_receipt。

准备两轮仅修导入顺序与新历史schema绑定，不改算法/图/任务/预算。图导出v01缺matplotlib失败留档，v02以Pillow读保存坐标，无正式重跑。冻结计划一个继承描述字段过宽（E changes only free），规范T变化已在正式前协议/合同/预检中明确，保留原计划另列文字说明，不事后改冻结数据。

封存与只读verify之后停止，交负责人审核，不自动实现恢复目标规则、重启旧机制或追加正式批。未用留出、新图、新闭环、视觉、飞控或推送。
''',encoding='utf-8')
 # Verify before touching root progress. The verifier reads saved receipts, never executes geometry/cores.
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8')
 assert p.returncode==0,p.stdout+p.stderr
 receipt=json.loads(p.stdout);dump(H/'verify_receipt.json',receipt)
 root=ROOT/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();assert root.read_bytes()==before,'root changed independently; preserve, do not overwrite'
 prefix='''# 最新完成：覆盖阶段真实受阻两例成对诊断封存（2026-10-23）

覆盖阶段真实受阻两例成对诊断_v0.1_20261023 已按稿完成并停止交审。先读00_通俗两例成对诊断报告.md（含两张正反图）、02全量配对、03成本转弯阶段、review_packet、ledger及final_receipt。主对象B为当前快照真实重调PPCPP＋同直达，R仅旧连接修复诊断，C仅P2有限流程外部参照；没有新改进机制获证。

唯一输入为覆盖阶段受阻选例核查包usable_snapshots_v02所引用两例N/E_contract_v02，不新增选图、不运行未规范首版E。大Z [26,28]、中Z [14,15]均封堵已采格，初始U=201/75；141/46是走到旧失效边时的计数，不能当初始U。事件在初始快照公开，旧后缀未执行。P/H/S/来向/基地/资源/捕食者相同，T=P∩F随F规范，U不变、D空；实际核心允许H不在当前F/T，直接保留全部物理H，无投影或删历史。旧包与原证据只读。

六固定纯身份通过，经2轮准备技术修复（导入顺序、历史schema字段绑定），失败和源码均保留；两轮共10项尝试，另1次导入失败在项循环前；固定R桩4次（3成功/1缺责任拒绝），真实准备/热身核心0。正式36处理=核心24（PPCPP12/P2 12）+R12，72视图全部责任/返航/资源和独立审核通过，无正式失败/触顶/迟到/候选上限/未运行。B/R/C各6个E/N配对、合计18；B/C各环境共12配对。20秒核心/修复、直达18软/4096/20迟到标记、父150未提高，OFF详细核心查询null，独立新进程串行四线程变量1，到上限停。

大Z三seed同路线：B原生214→216，直达210.817338→212.639192，Δ=+1.821854415米（+0.864186%）；首个trace分歧在record60/current[28,28]/recovery，目标[25,28]→[25,27]，信用rank60…182变，末18项相同，末采[4,5]及返航项不变，增量在覆盖阶段。中Z：B原生104→104，直达96.439089→95.927874，Δ=−0.511214924米（−0.530091%）；record29/current[16,15]/recovery目标[13,15]→[13,14]，信用rank29…74变，末采[12,14]→[12,13]；直达覆盖项+0.236068、末采后−0.747283，总量变短。两例均决策/锚点/实际信用改变，但完整效果相反，不因见证点不同冒称顺序变。阶段内部中点非唯一物理入区时刻。

R_N与B_N原生/直达逐点相同。R_E运行时替换[61,63]/[30,32]两边区间，各4边替2边、保留全部其他有效旧片段，原生分别216/106，直达212.053406/97.675157。大Z R_E比B_E短0.585786438米，中Z R_E比B_E长1.747282902米；B/R在E原/直达路径和名义/信用序均不同，不能将差距全归一条连接或单次目标选择。R不是最优保序算法，绕行提前信用照实记录。正式R BFS6次/114出队/456邻居，旧边检测1908，费用实际计入，未免费借选例证书。

P2十二次均自然完成冻结有限流程（允许原子阶段pass_limit，不代表全局收敛），在N/E共12个B/C配对都更短，N已存在优势。大Z C_N=C_E=208；中Z C_N为93.041595/88.485281/91.062258，C_E为93.041595/89.071068/93.041595，未逆推未保存的内部最终顺序。必要绕行仍未知，存在更短可行参照与可核实恢复目标/后续覆盖线索，但尚未定位单一因果错误，不宣称必须重排、旧序更优或创新。

B六个时间配对4快2慢，最坏增加0.012545秒；大Z B_E端到端均值0.477548秒、R_E0.448848、C_E5.217995，中Z分别0.105916/0.091875/0.697710；三单跑不作稳定计时因果结论。B直达转弯大Z23→27、中Z31→32，C短不代表转弯少。每seed全量、状态等权、均值/中位/范围/P95/最坏和所有正反结果保存；两状态等权ΔB约+0.655320米会掩盖正反，不当普遍效果。仅跨尺度Z族线索，不是跨形状复现，不与返航批混算。

完整来源/合同/冻结、36attempt、原返回/post/信用/独立回执、72指标、18环境与12 B/C配对、阶段精确证书、成本/查询账与图版齐全。图导出首版缺matplotlib失败留档，另版Pillow仅读保存坐标，不重跑正式。冻结计划继承字段“E changes only free”文字过宽，规范T变化已在正式前协议/合同/预检明确，另存说明不改冻结记录。只读verify核全部来源及回执，无核心/R/post/几何/BFS新调用。

封存后停止交负责人审核，不自动实施机制、恢复旧单步/LAST/四方向/局部P2、追加新图/批、连续闭环、视觉、留出或推送。

---

'''
 root.write_bytes(prefix.encode('utf-8')+before);(H/'root_after.md').write_bytes(root.read_bytes())
 ledger['status']='sealed_stopped_for_owner_review';dump(H/'ledger.json',ledger);packet['status']='sealed_stopped_for_owner_review';packet['processing']=ledger;dump(H/'review_packet.json',packet)
 files={str(f.relative_to(H)):sha(f) for f in sorted(H.rglob('*')) if f.is_file() and f.name!='final_receipt.json'}
 dump(H/'final_receipt.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed_stopped_for_owner_review','files':files,'file_count':len(files),'root_path':str(root),'root_sha256':sha(root),'saved_verify_receipt':receipt,'processing_entries':36,'core_entries':24,'R_entries':12,'views':72,'formal_failures':0,'new_calls_after_batch':{'core':0,'R':0,'post':0,'geometry':0,'BFS':0},'scope':'two fixed different-scale Z coverage-blockage snapshots, opposite B distance response; no causal fault or innovation established'})
 print({'sealed':True,'files':len(files),'processing':36,'core':24,'R':12,'views':72,'root_updated':True,'stopped':True})
if __name__=='__main__':main()
