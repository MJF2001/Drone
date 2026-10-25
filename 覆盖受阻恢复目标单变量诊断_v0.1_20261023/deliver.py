"""Review packaging and append-only root evolution; no experimental calls."""
from common import *
import sys,subprocess,datetime,difflib
def main():
 assert not (H/'final_receipt.json').exists()
 s=read(H/'summary.json');ledger=read(H/'ledger.json');b=read(H/'bindings.json')
 orig=Path(b['original_independent_auditor']).read_text(encoding='utf-8');new=(H/'recovery_diag_decision_audit.py').read_text(encoding='utf-8')
 (H/'source_snapshot/independent_auditor_vs_original.diff').write_text(''.join(difflib.unified_diff(orig.splitlines(True),new.splitlines(True),fromfile='frozen_independent_audit',tofile='unique_one_exception_audit')),encoding='utf-8')
 dump(H/'图版目视核验.json',{'viewed_all':True,'figures':2,'paths':['figures/large_Z_corner_p30.png','figures/medium_Z_corner_p30.png'],'fixed_seed':20261020,'scope':'both images inspected via view_image; full OFF/ON post routes, local native paths and goals, exact phase bars legible; equal-map scale within each case; large no-change and medium gain both kept','new_core_post_geometry_BFS':0})
 packet={'status':'completed_pending_seal_stop_for_owner_review','draft':'覆盖受阻恢复目标单变量诊断执行稿_给sol_20261023.md','processing':ledger,'initial_U':[201,75],'trigger_pending':[141,46],'states':s['state_results'],'OFF_old_equal_pairs':6,'ON_unique_authorized_pairs':6,'all_pairs_natural':s['all_natural_pairs'],'no_failure_inapplicable_late':s['failure'] is None and not s['excluded'] and not any(s['late_ids'].values()),'causal_statement':'large fixed old-goal replacement gives exactly same raw/post path, closes this specific explanation of old R advantage. Medium replacement reduces raw by2m and post by1.721243264m with 2 more turns; supports intervention benefit in this seen E only.','large_specific_old_goal_R_explanation_closed':True,'medium_seen_snapshot_goal_loss_supported':True,'remaining_unknown':['why old R is shorter in large','online conditions for selecting a beneficial alternative','other goals/shapes/unseen inputs'],'new_online_selector_or_innovation':False,'new_rollout_or_performance_batch_started':False,'new_N_R_P2':0,'old_N_target_is_offline_specified':True,'cross_shape_claim':False,'preparation_repair':1,'old_initial_pure_pass_count_incomplete_preserved':True,'export_failures':0,'root_chain_rule':'old package files unchanged; old root hash binds new root_before copied at start, current root only prepends new progress. Do not mutate old final_receipt.','stop_after_seal':True}
 dump(H/'review_packet.json',packet)
 (H/'review_packet.md').write_text('''# 负责人审核入口

先读00_通俗单变量诊断结论.md与两张固定首seed图，再读03_六配对与全指标入口.md。本轮12次完整PPCPP核心+12同版直达，24视图全部审核通过；6个OFF现场复现旧B_E，6个ON各仅指定恢复目标替换1次，其他规则独立审核通过，无正式失败/不适用/触顶/迟到/未运行。已停止新实验。

大Z无收益：OFF/ON原生216米、直达212.639192米，物理路线和信用序逐点相同。ON5步恢复等于OFF4步恢复后再1步原邻格移动；目标标签变，路线不变。关闭“只换回[25,28]可解释旧R短0.585786米”的具体线索，R差距原因仍未知，不换第三目标。

中Z有收益：原生104→102米、直达95.927874→94.206631米（−1.721243264米/−1.794310%）。恢复更远4→5步，但后续覆盖少2、返航少1，净−2；末采[12,13]→[12,12]。原生转弯34→36、直达32→34，代价保留。这只支持已见E快照中一次固定替换收益，不是新在线候选识别器、泛化或创新。两尺度均Z，不把6配对称6几何；旧FIRST已有类似恢复试走，未重启。

核对入口：selection/input_freeze/specs/previous_verify_at_start/root_before（唯一E输入、完整pending、旧目标来源、开工成功核验与根字节）；01预登记/plan/active_freeze/bindings/source_snapshot（最小diff、原源码、12槽及预算）；prechecks、prechecks_preparation_v01_passed_count_incomplete与preparation_repairs（八身份16项、1轮纯计账修复）；attempts/status/logs/outputs（12实账、原返回/后处理/公共信用和独立决策回执）；24视图、6对ON减OFF、逐决策干预证明（唯一变量和完整结果）；两状态等权/逐状态计时统计/12入口计时（全部分项及负例）；旧N_R_P2只读参考（历史时间不混新排名）；调用与查询总账/失败不适用触顶与未知/figure_receipts/图版目视核验；verify_receipt/final_receipt。

核验脚本只读绑定、计数和保存回执，不新运行核心/R/P2/直达/几何/BFS。正式后未改实现或补跑。上轮220文件封存不变，旧root hash对应本轮开工root_before；新root以前缀追加保留旧正文，历史链单独核。不要运行旧verify后把新root hash正常演进误报成旧算法证据损坏，更不要改旧final_receipt。

停止交负责人审核，无新图、留出、闭环、视觉、飞控、FIRST/LAST/多目标rollout/贪心择优/新性能批或推送。
''',encoding='utf-8')
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8');assert p.returncode==0,p.stdout+p.stderr
 receipt=json.loads(p.stdout);dump(H/'verify_receipt.json',receipt)
 root=ROOT/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();assert root.read_bytes()==before,'root independently changed; preserve, do not overwrite'
 prefix='''# 最新完成：覆盖受阻恢复目标单变量诊断封存（2026-10-23）

覆盖受阻恢复目标单变量诊断_v0.1_20261023 已按稿完成并停止交审。先读00_通俗单变量诊断结论.md（两张固定首seed图）、03_六配对与全指标入口.md、逐决策干预证明、review_packet、ledger及final_receipt。本轮仅问在同一个实际障碍E下，唯一指定分歧记录换回旧N目标，完整路线能否改善；不是新在线算法、性能排名或创新验收，不重启FIRST。

输入只用上轮实际运行并冻结、追溯usable_snapshots_v02的两个E_contract_v02，未用首版E。原P/H/F/T/S/来向/基地/资源/捕食者/旧后缀/seed均不变，保留封堵已采格物理H，初始U201/75；分歧pending141/46完整集合及此前完整语义/路线前缀匹配，不把预测进度写回初始H。大Z record60/current[28,28]/previous[29,28]默认[25,27]→替代[25,28]；中Z record29/current[16,15]/previous[15,15]默认[13,14]→[13,15]。trace序号与路径index分别从实际记录读取，恰同数不代替核对。

独立命名副本保留原默认min、原几何对象/路径平局、每格pending、奖励/捕食者/权重及之后全部原规则；ON每次仅该目标替换1次，OFF也完整诊断。两目标说明距离均4→5，替代不最近是明确授权偏离，安全/身份/完整责任审核不豁免。独立审核重算奖励/距离/逐格pending，只允许指定一次例外，后续全按原规则；中心区信用仍公共层事后计算，不反馈原生。

8固定纯身份首轮全过但拒绝桩部分查询未留存，经1轮纯计账修复补观测，旧通过结果/源码/diff保留，再同8项全过，共16项尝试。纯choose20、finish2、审核桩10、独占创建4；首轮拒绝查询未观测标未知非0，次轮6 BFS/90出队/360邻居全计账。真实准备/热身核心及真实post0。先两状态首seed OFF新调用全等价门槛通过再ON，其余seed配对臂先后交替，冻结12槽全部完成：PPCPP12/公共直达12/24视图，6OFF全复现旧B_E，6ON唯一授权且决策/几何/信用独立通过，无正式失败/不适用/触顶/迟到/候选上限/未运行。新N/R/P2、历史准备、新地图均0。核心20、post18软/4096/20迟到非硬中断、父150不变，新进程串行四线程1，核心详细profile两臂均OFF/null，与目标开关分开。

大Z三seed均零收益：OFF/ON原生216、直达212.639192米，原/直达路线逐点相同，全部锚点/实际信用序与事件相同，末采[4,5]、转弯原生27/直达27不变。ON5步恢复经[25,27]到[25,28]，恰等于OFF4步恢复后原local再1步到[25,28]，少一条local决策记录（202→201），原生分账60+4+143+9→60+5+142+9，仅边界重分。关闭“换回这个旧目标能解释旧R_E短0.585786米”的具体线索；ON不与R同路，R优势仍未定位单一原因，不换第三目标或改连接。

中Z三seed均有收益：原生104→102、直达95.927874→94.206631米，ON−OFF=−1.721243264米（−1.794310%），精确−1+12√2−√313<0。原生分账29+4+46+25→29+5+44+24，恢复+1/后续覆盖−2/末采后−1，净−2。ON衔接先采[13,14]再采[13,15]，不是空飞；OFF原local按同分平局转[12,14]。原生首次不同顶点34、直达32，实际信用从rank30至末74变，末采[12,13]→[12,12]；直达见证阶段首末间−1、末采后−0.721243，固定中点非唯一物理时刻，不强行把原生三段移植直达。原生转弯34→36、直达32→34（90度各+2）为代价。支持这个已见E中单次固定目标可干预的完整路线损失，不证明旧目标普遍优越/全部障碍增程可避免，更不是已实现在线判断器。

每seed全量后状态等权，2个尺度Z而非6几何；不以两状态等权−0.860622米掩盖大Z无效。主端到端均值大Z OFF0.534242/ON0.521192秒，配对Δ均值−0.013050（范围−0.040134至+0.004551）；中Z0.106618/0.113025，Δ+0.006407（−0.000155至+0.016778），单跑小样本不称稳定加速。钩子自计时大Z约0.013秒、中Z0.003秒，仅部分诊断成本，构造/编码均已计完整入口；旧批时间不混新排名，不将人工旧N目标当免费在线能力。

正式额外说明性距离查询24次，仅已定两目标；1650决策状态/138351格次pending。公共直达1692候选/279468服务交，独立决策审核45 BFS/105615出队/422460邻居另计主外，OFF核心详细查询null，计数别名不重复相加。完整12attempt/原返回/post/24视图/独立回执、六配对、阶段/计时/查询账、旧N_R_P2参考及图版/hash齐全。旧FIRST已有多目标完整试走择优与部分开发收益，本轮重合边界另存，不冒称创新。

开工root_before及上轮只读verify成功回执已保留；上轮220封存文件未改，旧final的root hash绑定本轮开工原字节，当前root仅前缀追加保留旧正文。新verify分别核旧文件和根历史链，不改旧final、不把进度演进误报算法证据损坏。封存后停止交审，不自动FIRST/LAST/rollout/择优/新开发性能批、第三目标、新图、留出、闭环、视觉、飞控或推送。

---

'''
 root.write_bytes(prefix.encode('utf-8')+before);(H/'root_after.md').write_bytes(root.read_bytes())
 ledger['status']='sealed_stopped_for_owner_review';dump(H/'ledger.json',ledger);packet['status']='sealed_stopped_for_owner_review';packet['processing']=ledger;dump(H/'review_packet.json',packet)
 files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='final_receipt.json'}
 dump(H/'final_receipt.json',{'status':'sealed_stopped_for_owner_review','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'file_count':len(files),'root_path':str(root),'root_sha256':sha(root),'historical_root_before_sha256':sha(H/'root_before.md'),'old_package_final_sha256':sha(Path(read(H/'selection.json')['old_package'])/'final_receipt.json'),'saved_preseal_verify':receipt,'core_entries':12,'post_entries':12,'views':24,'pairs':6,'formal_failure':None,'new_calls_after_formal':0,'scope':'two seen Z E snapshots, one offline fixed target per case; large no physical-route effect, medium shorter with more turns; no online algorithm/innovation/unseen claim'})
 print({'sealed':True,'files':len(files),'core':12,'post':12,'views':24,'root_prepend_only':True,'stopped_for_review':True})
if __name__=='__main__':main()
