"""Report bookkeeping, source/output seal and authorized root prefix only."""
from common import *
from datetime import datetime,timezone
import ast
def finalize():
 assert not (H/'final_receipt.json').exists();before=(H/'root_before.md').read_bytes();assert (ROOT/'当前进度与下一步.md').read_bytes()==before
 assert read(H/'preseal_verify.json')['passed'] and read(H/'analysis_receipt.json')['errors']==0
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,p
 allowed={'common','pathlib','collections','fractions','json','hashlib','time','math','traceback','itertools'}
 imports={}
 for name in ('common.py','analyze.py','describe.py','verify.py'):
  tree=ast.parse((H/name).read_text(encoding='utf-8'));mods=[]
  for node in ast.walk(tree):
   if isinstance(node,ast.Import):mods.extend(n.name.split('.')[0] for n in node.names)
   elif isinstance(node,ast.ImportFrom) and node.module:mods.append(node.module.split('.')[0])
  assert set(mods)<=allowed,(name,mods);imports[name]=mods
 index=read(H/'pair_index.json');duplicate=read(H/'duplicate_levels.json');relations={r['key']:r for r in duplicate['relations']}
 lines=['# 全部配对的分层重复关系','', '|配对|原例参照|局部触发相同|F相同|旧序相同|OFF/ALT原生尾部相同|完整E合并|','|---|---|---|---|---|---|---|']
 for row in index:
  r=relations.get(row['key'])
  if r:lines.append(f"|{row['key']}|{r['origin']}|{r['same_local_trigger']}|{r['same_F']}|{r['same_old_order']}|{r['same_OFF_tail']} / {r['same_ALT1_tail']}|否|")
  else:lines.append(f"|{row['key']}|基础来源|不与别例强配|各自来源|各自来源|按hash组查看|否|")
 lines+=['', '基地、给定资源与捕食者在7个变体和各自原例中均相同；初始H、S、旧后缀和F差异逐字段保存在duplicate_levels.relations。完整E/旧序19个均不同，不因局部触发/尾部相同合并输入，也不把重复尾部当独立新模式。']
 (H/'03_重复关系逐项表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 first=read(H/'protocol/figure_index_first_pass.json');fig=read(H/'figure_index.json');setup=read(H/'setup_receipt.json');analysis=read(H/'analysis_receipt.json');desc=read(H/'description_receipt.json');verified=read(H/'preseal_verify.json')
 zero={k:0 for k in ('new_core','new_post','new_history','new_BFS','new_shortest_path','new_visibility','new_counterfactual_routes','new_candidate_generation','new_coverage_optimization','new_training','new_rule_implementation')}
 ledger=dict(actual_new_experiment_calls=zero,saved_pairs=19,saved_processing_routes=38,saved_views=76,source_split=dict(base_pairs=12,variant_pairs=7,inapplicable_variant_slots=5),phase_costs=dict(source_hash_setup=setup,primary_mapping_and_sequences=analysis,description_and_cost_partitions=desc,independent_saved_verification=verified,figure_first_pass_seconds=first['wall_seconds'],figure_final_pass_seconds=fig['wall_seconds']),render_revision='spacing and label readability only; first rendering source and receipt retained',import_scope=imports,measurement_scope='per-script wall excludes process startup/tool transport; those are not claimed zero; receipts count through receipt construction, not their own serialization',unknown=['no usable decision rule established','fixed H2 still not applicable/unconfirmed','block sequences do not measure physical crossings or deletable waste','partial trigger/tail repetition not complete-state equivalence','seen development data, no independent rule validation'])
 dump(H/'零新增调用与处理费用账.json',ledger)
 costlines=['# 本轮调用与计算费用','', '全部新增核心/post/历史/BFS/最短路/可视查询/反事实/候选/优化/训练/规则入口均0；19对、38处理路线、76视图全部是保存证据。没有把旧42或21入口记成本轮执行。','', '|阶段|脚本内墙钟秒|实际处理记录|','|---|---:|---|',f"|源及旧封存hash|{setup['wall_seconds']:.6f}|{setup['hash_operations']}次文件hash，{setup['bytes_hashed']}字节；{setup['unique_guard_files']}独立来源绑定|",f"|主标签与序列整理|{analysis['wall_seconds']:.6f}|779个原任务格标签、6108原生点扫描、6728保存post事件扫描、38条源边界对应|",f"|描述与费用分账|{desc['wall_seconds']:.6f}|19对；只从保存事件索引作边数与序列比较|",f"|独立保存证据核验|{verified['wall_seconds']:.6f}|原始轨迹与引擎信用重读；125485次矩形不等式、3046项坐标长度算术；无BFS或可视查询|",f"|示意图首版/排版修订|{first['wall_seconds']:.6f} / {fig['wall_seconds']:.6f}|19序列图＋4坐标图＋1总览；仅标签间距修订|",'', '完整字节、计数和费用在零新增调用与处理费用账及各阶段receipt。脚本墙钟不包括解释器启动和工具传输，未称这些成本为0；独立核验里的长度根式为保存点串算术，不是重新求路。最终封存后verify另存自己的墙钟。']
 (H/'04_零新增调用与费用边界.md').write_text('\n'.join(costlines)+'\n',encoding='utf-8')
 dump(H/'图版目视核验.json',dict(passed=True,contact='figures/十九对序列图总览.png',full_views=['figures/map__base__I_gap_B__p60.png','figures/map__base__T_gap_B__p25.png','figures/timeline__base__T_gap_B__p25.png'],revision='separated task count/last-cell captions and raised rectangle labels away from obstacle; no data changes',new_core=0,new_post=0,new_BFS=0,new_visibility=0))
 report=H/'00_通俗结构对照报告.md';s=report.read_text(encoding='utf-8');s=s.replace('触发在[24,9]附近','触发在[24,9]');report.write_text(s+'\n图示：[I任务交换与收尾](figures/map__base__I_gap_B__p60.png)、[T块序相同但展开不同](figures/map__base__T_gap_B__p25.png)、[十九对信用序总览](figures/十九对序列图总览.png)。[逐项重复关系](03_重复关系逐项表.md)、[零新增调用及费用](04_零新增调用与费用边界.md)。\n',encoding='utf-8')
 assert read(H/'pairs/base__I_gap_B__p60.json')['decision_available']['current']==[24,9]
 prefix='''# 最新完成：任务次序与收尾结构只读对照封存（2026-10-23）

障碍后正反例任务次序与收尾结构对照_v0.1_20261023 已按执行稿完成并停止交负责人讨论。入口00_通俗结构对照报告.md、01_19对完整索引与重复关系.md、02_决策前与事后信息分栏.md、03_重复关系逐项表.md、04_零新增调用与费用边界.md、review_packet及final/verify回执。

只读整理基础扩样12对和受控变体7对，共19保存配对/38处理路线/76原生直达视图；5个无资格槽仅保留缺口。新增核心/post/历史/BFS/最短路/可视查询/反事实/候选/优化/训练/规则实现全部0，不重跑旧42或21入口。源及旧回执完整hash先核，2373来源绑定，开工root_before绑定受控变体旧final根hash，旧基础final与变体root_before历史链保留。

任务块沿6张原地图已登记矩形坐标编号，779个P格唯一归属，pending分裂不拆块、不作连通分量。分别保存事件H/U及触发pending块计数，current/previous/q0/q1/d0/d1、同块关系、旧rank、公开障碍与F/基地/资源/捕食者；全部标为本轮保存资料提取，不称已在线使用。事后任务ID首次服务序/压缩块序/交错/首末完成时点、原生与post信用分开。38条post均在原生源索引对应的精确顶点切分，无触发pending提前获得post信用；一般不能同步时保未知的规则仍保留。

I_gap_B__p60触发剩B02左侧1格[13,7]和B04右侧32格。OFF先B02后B04，ALT先B04后B02，原生/直达块完成顺序均反转，末采[37,7]→[13,7]；共同覆盖少4步、原生返航44→20少24，净−28，post−28.763940280米。两个A仍同块交换与收尾但post幅度略变；两个B进度变体与原例局部触发及两臂原生尾部重复，不新增独立模式。完整E/旧序19签名均不同，不因局部重复合并。

T_gap_B__p25的q0/q1同在B04，两臂始终B04→B07→B08→B05→B06，块完成顺序没变。ALT恢复先采q0再到q1，随后块内采集与连接端点改变；B04末采[27,31]→[26,32]，B07入口[32,31]→[32,32]，最终B06末采[6,32]→[3,31]。固定新信用段的保存索引分账：首信用前均9步，采集跨度117→122、段间46→51，共同覆盖172→182多10；返航38→34少4，原生净+6、post+8.587181813。不是独立机制贡献或可删浪费。两个障碍变体同号退化；早公开变体目标对已换且物理同路，不称同一选择优劣反转。

全批反证保留：I_gap_A两进度块序不变仍改善（p60只剩一块，覆盖不变而返航少6）；L_gap_B等长不同路块序和末采不变；L_gap_A_p25减少B02新信用交错，覆盖−32却返航+34，原生+2、仅post−0.979486872。同块候选同时有改善/等长/退化，跨块正例集中同一已见I模式，不能立跨块/先远后近/保旧序规则。

独立校验未导入原规划器或公共post：按原矩形不等式、原始原生点串与engine.credit_witnesses（区别主分析views事件源）重建计数/次序/完成时点，独立整数有理根式重核76视图费用、14个不同路线共同p/C、38个信用段边数分账及全部层级重复，19对全通过；读取/标签/算术/报告/图均计时计数，不称零计算。24示意图含19序列/4原生坐标/总览，物理H与规划前缀已服务分开标注。

探索性块序不是旧H2替代指标，旧H2仍不适用/未确认，不回填通过、不报新机制通过率。结论：轨迹解释更清楚，但仍无可用判断规则。所有模式来自已见开发材料，不拼总体胜率，不当规则独立验证；F为宽矩形/P分段块，不推广为连续施工道路天然分区。已停止，不自动评分/前瞻/权重阈值/训练/新机制/新变体/留出/推送。当前根仅前缀追加，旧正文、旧报告与旧final原样保留。

---

'''
 new=prefix.encode('utf-8')+before;(ROOT/'当前进度与下一步.md').write_bytes(new);(H/'root_after.md').write_bytes(new)
 excluded={'final_receipt.json','verify_receipt.json'};files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in excluded}
 receipt=dict(status='sealed_readonly_structure_comparison_stopped_for_owner_discussion',utc=datetime.now(timezone.utc).isoformat(),files=files,file_count=len(files),root_sha256=sha(ROOT/'当前进度与下一步.md'),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(VAR/'final_receipt.json'),old_chain_bound=True,saved_pairs=19,saved_processing_routes=38,saved_views=76,source_split=dict(base_pairs=12,variant_pairs=7,inapplicable_gaps=5),all_new_experiment_calls=zero,independent_saved_verification_passed=True,new_rule=False,new_H2_pass_claim=False,excluded_from_self_manifest=sorted(excluded))
 dump(H/'final_receipt.json',receipt);print(json.dumps(dict(sealed_files=len(files),root_hash=receipt['root_sha256'],new_algorithm_calls=zero),ensure_ascii=False))
if __name__=='__main__':finalize()
