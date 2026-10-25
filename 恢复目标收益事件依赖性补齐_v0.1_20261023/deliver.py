"""Seal reviewed saved artifacts and prepend progress, no experimental calls."""
from common import *
import sys,subprocess,datetime
def main():
 assert not (H/'final_receipt.json').exists()
 summary=read(H/'summary.json');ledger=read(H/'ledger.json')
 dump(H/'图版目视核验.json',{'viewed_all':True,'figures':2,'fixed_seed':20261020,'paths':['figures/large_Z_corner_p30.png','figures/medium_Z_corner_p30.png'],'scope':'both figures inspected via view_image; four complete route cells plus separate N/E local overlays, stable T0/T1 and new/reused labels, same map extent within case, effect numbers and sign convention legible','new_core_post_geometry_BFS':0})
 packet={'status':'completed_pending_seal_stop_for_owner_review','draft':'恢复目标收益事件依赖性补齐执行稿_给sol_20261023.md','processing':ledger,'stable_mapping':{'N_OFF':'T0','N_ON':'T1','reused_E_ON':'T0','reused_E_OFF':'T1'},'new_N_off_equivalence':6,'new_N_on_unique_exception':6,'reused_E_outputs':12,'new_views':24,'reused_views':24,'combined_views':48,'four_cell_groups':6,'states':summary['states'],'large_decision':'N T0 shorter, E physical same-route tie; obstacle removes this T0 advantage, no E target-switch route benefit','medium_decision':'T0 shorter in both N and E; advantage already in N, nonzero post interaction strengthens by0.544804051m; native interaction zero; not event-exclusive innovation','strict_preference_reversal_found':False,'independent_arithmetic_groups':12,'cross_batch_time_interaction_or_speed_ranking':False,'two_target_chain_stopped':True,'new_third_target_local_intervention_or_performance_batch':False,'online_selector_or_innovation_claim':False,'exploratory_seen_two_scale_Z_only':True,'preparation_repairs':0,'formal_failures':0,'late_or_budget_events':0,'root_chain':'old files unchanged, old root hash binds exact root_before, prepend preserves all earlier bytes','stop_after_seal':True}
 dump(H/'review_packet.json',packet)
 (H/'review_packet.md').write_text('''# 负责人审核入口

先读00_通俗事件依赖性补齐报告.md的四格距离表与D_N/D_E/I/转弯表、两张固定首seed图，再读02_六组四格距离与效应表.md。本轮仅新增12 N核心+12 post+24视图，另引用12旧E处理/24旧视图，合计24条处理路线/48视图；不是24新增核心。六个新N_OFF全复现旧B_N，六个N_ON仅指定一次目标替换，全部决策/几何/信用独立审核通过，无正式失败/不适用/触顶/迟到/缺槽。

大Z：N,T0/T1=210.817338/213.403124米，E,T0/T1均212.639192且物理同路。D_N=−2.585786438、D_E=0、I=+2.585786438；原生−2/0/+2。障碍使T0原有优势消失为等长，未反转，不以E不同目标标签继续追收益。

中Z：N,T0/T1=96.439089/97.615528米，E,T0/T1=94.206631/95.927874米。D_N=−1.176439214、D_E=−1.721243264、I=−0.544804051；原生−2/−2/0。T0一般选择优势在N已存在，障碍使公共直达后的优势增强，原生差距交互却为零，不能包装事件专属创新。E中T0转弯+2，N中总转弯相同；大Z N更短T0转弯反而+6，代价保留。两例无严格优劣反转。

目标映射必须同时看环境+T0/T1+enabled：N_OFF=T0，N_ON=T1，复用E_ON=T0，复用E_OFF=T1。四格语义前缀/当前位置/上一格/完整pending一致，trace序号与路径index分别核；初始U201/75，分歧pending141/46。N原字节复用上轮实际N，没有从E手工补图；物理H保留，U不变，D空。E只读回执，不重跑其独立几何。

审核路径：selection/inputs/specs/input_freeze/source_guards/previous_verify_at_start/root_before（来源、合同、根链）；bindings/source_snapshot/01预登记/plan/active_freeze/prechecks（模块复用diff、12槽、六纯项、0修复）；attempts/status/logs/outputs（12新N原返回/post/信用和独立回执）；reused_E/index及12带标签只读包装（旧E原输出来源hash）；24新增N视图、24复用E视图、48总视图、24条路线来源索引；6组四格对照/四格路径与local机制证据/四格转弯表；独立算术核验（12组原/直达双实现）、两状态等权；12新增N入口计时/新N逐状态计时（不计算跨批时间交互）、调用与查询及算术总账、失败触顶迟到与未运行；figures/figure_receipts/图版目视核验、verify_receipt/final_receipt。

原生核心、钩子、独立决策审核器逐字节复用；其余变化只有模块名、N默认/替代/旧基准配置绑定和标签。公共post不改，原wire通过唯一id和带标签所有者绑定，不擅改公共响应。六纯项首次通过，无准备技术修复，正式后无实现改动/补跑。算术是实测计算，不新增几何/覆盖最优搜索；verify只读hash和保存回执，不重执行根式核验或算法。

停止这条两目标诊断链交负责人讨论：中Z可记录为一般恢复选择差异与环境交互并存，大ZE相同物理行动无收益。不是在线条件识别器、独立确认样本、跨形状泛化或原创性证据。无第三目标、第二次local、改平局、FIRST/rollout/候选择优、新地图/留出/性能批/连续闭环/视觉/飞控/推送。

旧122文件包及更早封存均不改；旧root hash绑定本轮开工root_before，新root仅前缀追加。只读verify分别核旧文件及根历史链，不将正常进度演进当旧算法证据损坏，不修改旧final_receipt。
''',encoding='utf-8')
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8');assert p.returncode==0,p.stdout+p.stderr
 receipt=json.loads(p.stdout);dump(H/'verify_receipt.json',receipt)
 root=ROOT/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();assert root.read_bytes()==before,'root changed independently; do not overwrite'
 prefix='''# 最新完成：恢复目标收益事件依赖性补齐封存（2026-10-23）

恢复目标收益事件依赖性补齐_v0.1_20261023 已按稿完成并停止这条两目标诊断链，交负责人审核。先读00_通俗事件依赖性补齐报告.md（四格距离表、D_N/D_E/I与转弯表、两张首seed图）、02_六组四格距离与效应表.md、review_packet、ledger及final_receipt。主问题仅是同两个固定目标的优势是否在N已存在、障碍是否改变相对效果；不是新算法/创新验收，不新增目标或排名。

稳定标签T0为原N默认（大Z[25,28]、中Z[13,15]），T1为原E默认（[25,27]、[13,14]）。N_OFF=T0、N_ON=T1，复用E_ON=T0、E_OFF=T1，输出/视图/引用同时存environment+target_label+enabled，不能直接按ON/OFF跨环境拼表。新N逐字节复用上轮实际冻结N，不从E补格或重准备历史；N指无本次新增障碍，非移除所有障碍。P/H/S/来向/基地/资源/捕食者/seed/旧后缀保持，F与T按原合同变化，物理H保留，初始U201/75不变、D空，分歧pending141/46完整集合及四格此前全部原生trace/路线前缀/来向一致，record60/29与path index分别核。

六固定纯项首次全过，准备修复0：来源合同/hash、标签反向拒绝、完整触发身份、原模块diff/解析/无执行导入、保存/零schema/规范化/独占、差分公式/零/相反/缺格及独立算术。纯label8（4负拒绝）、独占2、数字表6（5完整1缺格，两实现拒绝），无真实核心/post/几何/BFS。原生核心/钩子/独立决策审核器逐字节复用，其他仅模块命名、N默认/替代与基准配置、稳定标签；不重写算法或框架，不变公共post。先两状态首seed新N_OFF现场等价旧B_N后才N_ON，余四对臂先后交替，冻结12槽全部完成：新增N核心12/post12/视图24，六OFF全等价、六ON唯一授权并全部独立通过，失败/不适用/触顶/迟到/候选上限/缺槽0。旧E12处理与24视图只读复用，合计24条处理路线/48视图/六组四格，不是24新增核心。新E/R/P2/历史准备/热身/技术入口0，核心20/post18软4096/20迟到非硬中断/父150不变，新进程串行四线程1，详细profile两臂均OFF/null。

四格米（原生/直达）：大Z N,T0=214/210.817338，N,T1=216/213.403124，E,T0=E,T1=216/212.639192；中Z N,T0=104/96.439089，N,T1=106/97.615528，E,T0=102/94.206631，E,T1=104/95.927874。每状态三seed路线及长度相同，不当六几何。D_N=N0−N1、D_E=E0−E1、I=D_E−D_N（D负T0短、I负障碍增强T0相对优势）。大Z原生−2/0/+2，直达−2.585786438/0/+2.585786438（DN=−4+√2）：N的T0优势消失为E等长、无严格反转，E两目标原/直达路线/信用完全相同，继续关闭该目标替换解释R优势的线索。

中Z原生D_N/D_E/I=−2/−2/0；直达−1.176439214/−1.721243264/−0.544804051。DN=1−5√17+2√85，DE=−1+12√2−√313，I=−2+12√2+5√17−2√85−√313，认证严格为负。T0在N中已短，障碍再增强公共直达后的优势约0.544804米，一般选择差异与环境交互并存；原生交互恰0，不把该差称目标更近或事件专属创新。两例均无严格优劣反转，只是两个已见尺度Z、事后由分歧确定目标的探索补齐，非现场总体因果、显著性、在线识别或泛化证据。

物理解释：N中较远T1恢复4步先经过T0，近T0原策略并不继续T1，大Z去[25,29]、中Z去[12,15]；强制T1后分别去[25,26]/[13,13]，实际改变后续。E中较远T0恢复5步先经过T1；大Z近T1原local本来去T0，故合并决策但物理同路；中Z近T1按2.25同分选[12,14]而非T0，继续T0改变方向。恢复途中采集与评分/平局均留证，不一概称空飞，不转成延续一格/改平局在线规则。四格完整信用/末采/返航保存：大Z末采均[4,5]；中Z N0[12,14]、N1[13,16]、E0[12,12]、E1[12,13]。原生分账与post见证口径分开，中点非唯一物理入区时刻。

转弯代价：大Z N直达T0/T1=23/17（90°20/14、180°0/2、其他3/1），E均27；中Z N均31，E T0/T1=34/32、90°多2。新N主端到端均值大Z T0/T1=0.519225/0.517683秒，中Z=0.108715/0.113841，最坏0.549141；完整核心/钩子/包装/post/主外审核及逐seed均值中位范围P95最大保存，不把部分钩子秒当总诊断成本，不作稳定加速结论。旧E时间只历史引用，未算跨批E/N时间交互或速度排名。

新N额外说明距离24、1650决策状态/138351格次pending；post1668候选/277812服务交，独立决策45 BFS/105660出队/422640邻居另计主外，旧E费用不冒充新执行，核心细查询null、别名不重复相加。12组原/直达算术逐项通过已验Expr与独立Fraction/isqrt：主层48证书/36差分与符号，独立48解析/174项累计/27区间轮/30整数根界，计时约0.002119/0.001018秒，不称零计算，无几何/路线优化或覆盖最优搜索。所有源/hash/diff/12attempt/24新视图/24复用视图/48总视图/六四格与回执/负零结果/图版/算术与查询账齐全，正式后无修复补跑。

开工root字节与旧verify成功回执保留，旧122文件封存及更早证据不变；旧root hash绑定新root_before，当前root仅前缀追加保留全部旧正文，独立核历史链，不改旧final或误报正常进度演进。封存后停止这条两目标诊断链，回负责人决定机制线索保留或一般现象归档；不第三目标/第二次干预/改平局/FIRST/rollout/候选择优/性能批/新图/留出/闭环/视觉/飞控/推送。

---

'''
 root.write_bytes(prefix.encode('utf-8')+before);(H/'root_after.md').write_bytes(root.read_bytes())
 ledger['status']='sealed_two_target_chain_stopped_for_owner_review';dump(H/'ledger.json',ledger);packet['status']='sealed_two_target_chain_stopped_for_owner_review';packet['processing']=ledger;dump(H/'review_packet.json',packet)
 files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='final_receipt.json'}
 dump(H/'final_receipt.json',{'status':'sealed_two_target_chain_stopped_for_owner_review','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'file_count':len(files),'root_path':str(root),'root_sha256':sha(root),'start_root_sha256':sha(H/'root_before.md'),'previous_E_final_sha256':sha(Path(read(H/'selection.json')['previous_E_package'])/'final_receipt.json'),'saved_preseal_verify':receipt,'new_N_core':12,'new_N_post':12,'new_views':24,'reused_E_outputs':12,'reused_views':24,'combined_processing_routes':24,'combined_views':48,'four_cell_groups':6,'formal_failures':0,'new_calls_after_formal':0,'cross_batch_time_inference':False,'scope':'two seen Z states, fixed T0/T1; general recovery-choice advantage plus computation-pipeline interaction; no event-exclusive/online/innovation claim'})
 print({'sealed':True,'files':len(files),'new_N_core':12,'new_N_post':12,'new_views':24,'reused_views':24,'combined_views':48,'root_prepend_only':True,'two_target_chain_stopped':True})
if __name__=='__main__':main()
