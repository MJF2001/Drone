"""Design-document archival only: no algorithm, geometry or sample generator.
Never imports or executes any old verifier/planner/post module.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,time
H=Path(__file__).resolve().parent;ROOT=H.parent
OLD=ROOT/'障碍后双候选完整试走既有证据审查_v0.1_20261023'
C=Counter()
def read(p):
 b=Path(p).read_bytes();C['json_reads']+=1;C['json_bytes']+=len(b);return json.loads(b.decode('utf-8-sig'))
def sha(p):
 b=Path(p).read_bytes();C['hash_reads']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def write(p,x):
 s=json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
 with Path(p).open('x',encoding='utf-8') as f:f.write(s)
 C['json_writes']+=1;C['json_write_bytes']+=len(s.encode())
def prepare():
 start=time.perf_counter();assert not (H/'manifest.json').exists();(H/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes());(H/'protocol').mkdir(exist_ok=True)
 source=ROOT/'障碍后片区次序与收尾规则设计执行稿_给sol_20261023.md';(H/'protocol/执行稿.md').write_bytes(source.read_bytes())
 oldfinal=read(OLD/'final_receipt.json');oldverify=read(OLD/'verify_receipt.json');assert oldverify['passed'] and oldverify['final_receipt_sha256']==sha(OLD/'final_receipt.json');assert oldfinal['root_sha256']==sha(H/'root_before.md');assert (H/'root_before.md').read_bytes()==(OLD/'root_after.md').read_bytes()
 guards=read(OLD/'source_guards.json')
 for p,v in guards.items():assert sha(p)==v,p
 for p,v in oldfinal['files'].items():assert sha(OLD/p)==v,p;guards[str(OLD/p)]=v
 for name in ('final_receipt.json','verify_receipt.json'):guards[str(OLD/name)]=sha(OLD/name)
 refs=[
 'AGENTS.md',
 '研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/02_论文主题与具体研究问题.md',
 '研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/42_三种基线适配审查与冻结说明_20261012.md',
 '研究方案_剩余覆盖重规划_20261009/00_阅读入口.md',
 '障碍后正反例任务次序与收尾结构对照_v0.1_20261023/00_通俗结构对照报告.md',
 '障碍后接续估计器影子诊断_v0.1_20261023/00_通俗影子评估结论.md',
 'PPCPP首次恢复完整试走_v0.1_20261020/预登记.md',
 'PPCPP保留末采集格候选_v0.1_20261020/预登记.md',
 'PPCPP_LAST新开发地图验证_v0.1_20261020/预登记.md',
 'PPCPP局部P2混合开发诊断_v0.1_20261020/预登记.md',
 'PPCPP两窗口结构候选_v0.1_20261020/预登记.md',
 '障碍后接续假设有限扩样_v0.1_20261023/expand_native.py',
 '障碍后接续假设有限扩样_v0.1_20261023/expand_hook.py',
 '障碍后接续假设有限扩样_v0.1_20261023/decision_audit.py',
 '中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/metrics.py',
 '中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/post/engine.py',
 '障碍后接续假设有限扩样_v0.1_20261023/state_registry.json',
 '障碍后接续正反例受控变体_v0.1_20261023/state_registry.json']
 reference=[]
 for rel in refs:
  p=ROOT/rel;guards[str(p)]=sha(p);reference.append(dict(path=str(p),sha256=sha(p),use='static source/contract/provenance only; no proposed-rule evaluation'))
 guards[str(source)]=sha(source);write(H/'sources.json',reference);write(H/'source_guards.json',guards)
 slots=[dict(id=f'G{g}-{v}',base=f'G{g}',variant=v,status='proposed_pending_approval_not_snapshot') for g in range(1,7) for v in ('A','B')]
 write(H/'sample_slots_draft.json',dict(status='draft only',slots=slots,contains_coordinates=False,snapshots_generated=0,old_cases_classified_by_new_rule=0))
 write(H/'manifest.json',dict(status='design_draft_pending_owner_decision',rule_count=1,mechanism='persistent OTHER/TAIL goal priority; not one intervention',small_definition='unique strict minimum pending count; relative not absolute',spatial_definition='fixed disjoint nonadjacent task labels; base-facing pending representatives; exact legal local-distance predicates',all_new_policy_items_pending_approval=True,rule_implemented=False,rule_tested=False,old_rule_classifications=0,geometry_queries_performed=0,new_snapshots=0,future_proposed_budget=dict(history_core=12,history_post=12,equivalence_core=8,equivalence_post=8,formal_core=24,formal_post=24,total_core=44,total_post=44,pure_cases=16),actual_new_calls={k:0 for k in ('algorithm_implementation','real_core','history','public_post','geometry','shortest_path','coverage_search','candidate_route','training','new_experiment','pure_algorithm_cases')},prior_cost_protocol_pursued=False,prior_estimator_stage_B_reopened=False,created_utc=time.time()))
 write(H/'开工静态来源核验.json',dict(passed=True,source_bindings=len(guards),current_root_equals_previous_root_after=True,previous_final_bound=True,old_verify_reexecuted=False,old_saved_success_receipt_hash_bound=True,old_scripts_imported=False,scope='hashes/saved receipt/root byte chain only; not rerun old semantic audit or new rule',seconds=time.perf_counter()-start,counts=dict(C)))
 print(dict(prepared=True,source_bindings=len(guards),proposed_slots=12,new_rule_evaluations=0,seconds=time.perf_counter()-start))
def seal():
 start=time.perf_counter();assert read(H/'preseal_verify.json')['passed'];before=(H/'root_before.md').read_bytes();current=ROOT/'当前进度与下一步.md';assert current.read_bytes()==before
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,p
 write(H/'实际零调用与设计处理账.json',dict(status='design draft pending approval',actual_new_calls=read(H/'manifest.json')['actual_new_calls'],source_rule_or_algorithm_imports=0,old_verifier_runs=0,old_case_rule_predictions=0,snapshots_generated=0,parameter_search=0,rule_candidates_evaluated=0,recommended_rule_count=1,processing='reading, source hashing, static reasoning, handwritten pseudocode and document packaging only; not zero computation',prepare_receipt=read(H/'开工静态来源核验.json'),preseal_document_integrity_receipt=read(H/'preseal_verify.json'),future_proposed_calls_not_executed=read(H/'manifest.json')['future_proposed_budget'],prior_cost_protocol_pursued=False,estimator_stage_B_reopened=False,seal_cost_location='final_receipt.json',postseal_integrity_check_location='verify_receipt.json',human_reasoning_time_not_individually_measured=True))
 prefix='''# 最新进度：片区次序与收尾规则设计草案待核定（2026-10-23）

障碍后片区次序与收尾规则设计_v0.1_20261023 仅完成设计草案并封存交负责人核定。入口00_固定规则通俗说明与待裁决.md、01_确定性规则伪代码与接口改动.md、02_小规模正反结构验证协议_待核定.md，附03来源重合、设计审阅、manifest/hash与零调用账。没有规则实现/验证通过结论。

用户确认的是“障碍后将适合返航衔接的少量任务留后，可能缩短全程”的研究假设，不等于已确认下列定义。唯一建议为持续OTHER/TAIL两阶段目标优先级：首次恢复只检查一次，符合条件后先选其他片，清完再释放S；同时修改紧邻候选过滤与恢复目标集合，不再称一次干预。其他片之间沿用原选择，不做完整片区排列搜索，不完整试走/有限前瞻/旧序补尾/完整长度估计择优。

四定义均待核定：沿用事前矩形任务标签、非空片原任务集不相接且唯一归属，pending碎裂不拆片；“少量”暂指唯一严格最少计数，不设绝对数量/比例，49对50也可能满足，语义局限交负责人裁决；每片以当前pending中到基地合法格路最近者代表，坐标平局；对所有其他片要求S代表在其到基地最短连接上、经S再去其他片比当前位置直去更远。只用当前公开图局部距离，建议最多3个距离行，费用/代表近似局限列明，本轮未计算。

默认目标已在其他片、同片/同目标、单片、最少数并列、分区相接/漏归属/重叠、信息不足时不启动，且不等以后有利机会。激活后原完整Q/物理H/F/暂缓不改，原Q奖励先计算再过滤，不能把允许目标集E冒充完整pending。S沿途必须照采，可提前耗尽并取消优先级，不保证实际最后采到S；原生预测与公共直达信用分账，不用post反馈Q。原机会检查失败后的原策略回退、激活后取消优先级和最终超限/资源失败明确区分，无免费默认完整备份。

接口稿列新增状态、首次恢复准备、紧邻分支、恢复分支、逐边信用/释放、全Q空才返航、资源终审与完整post；旧choose单钩子不足，旧审核完整Q无邻格才恢复的断言须独立阶段感知适配，不整体豁免。规则目标约束、原生实际留后和post实际留后分开检验。所有这些都是伪代码规范，未实现或纯桩运行。

拟一轮6新基底各两相关状态共12槽，顺路/近基地折返、位置控制、任务量4→8与8并列、单片/同目标保护、多片障碍绕行俱全；坐标/C0/唯一事件障碍和规模未核定、未生成快照。G1/G2明确为同一真实历史的两个障碍位置变体，避免声称同一确定性输入有两个历史入口；G3/G4历史可能变化，不称单变量因果。结构按事件输入登记，若首次恢复前已变则保留真实触发率，不换切点。真实历史、旧实际post剩余段被新增单格阻断、未采责任不删、基地/全部任务可达是未来资格条件，失败不补槽。

全部预算只是建议待批准：历史12核心/12post，4固定槽各原版/关闭规则等价共8/8，正式12×两法24/24，总上限44核心+44post、纯桩最多16。主对照仅原PPCPP+同版直达；无P2/无事件四格/留出。拟继续门槛为全正确及时、保护状态等价、每有效对无严格距离退化、至少两非复制非D4基底严格改善且有实际原生/post留后证据、六基底等权净负；全部待核定，不把阈值设为已批准。质量反例留表跑完固定有限矩阵，技术/责任错误即停，无自动调参或扩样。

FIRST/LAST、两窗口结构、局部P2等项目预登记仅静态确认重合；LAST的分阶段留末任务、FIRST完整分支选短不改名创新。本方案不删S通行、不完整试走选短，但差别不等于创新。旧I/T/L只作已见设计参照，本轮没有把新判据应用到19例或用结果挑参数。旧估计器不改16/64/尾序/权重、不恢复阶段B；上一轮成本审查保留，其未实施计时协议本轮不推进。

实际新增算法实现、真实核心/历史/post、几何/最短路/覆盖搜索、候选路线、训练、新实验与纯算法桩全部0。只做阅读/静态推理/伪代码文档/hash归档，保存字节和费用；开工仅核旧保存成功回执/hash与实际当前根链，不重跑旧verify或导入算法。归档verify通过只证明文档/hash/预算算术/根链完整，不证明规则正确、有效或快。当前根仅前缀追加，旧正文/冻结源码/结果/稿件不改；设计草案待负责人核定，完成后停止，不自动按稿实现或运行。

---

'''.encode('utf-8')
 after=prefix+before;(H/'root_after.md').write_bytes(after);current.write_bytes(after)
 excluded=['final_receipt.json','verify_receipt.json'];files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and str(p.relative_to(H)) not in excluded}
 write(H/'final_receipt.json',dict(status='design_draft_sealed_pending_approval_stopped',utc=time.time(),files=files,file_count=len(files),root_sha256=sha(current),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(OLD/'final_receipt.json'),rule_count=1,rule_implemented=False,rule_tested=False,new_snapshots=0,actual_new_calls=read(H/'manifest.json')['actual_new_calls'],old_results_readonly=True,document_integrity_preseal_passed=True,scientific_rule_validation_claim=False,auto_execution=False,excluded_from_self_manifest=excluded,seal_seconds_before_receipt=time.perf_counter()-start))
 print(dict(sealed=True,files=len(files),rule_implemented=False,rule_tested=False,stopped=True))
if __name__=='__main__':
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='seal':seal()
 else:prepare()
