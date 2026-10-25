from common import *
from collections import Counter
def main():
 start=time.perf_counter();guard();summary=read(H/'summary.json');assert summary['gate']['passed'] is False;assert read(H/'preseal_verify.json')['passed'];assert read(H/'figure_receipt.json')['files'] and read(H/'report_receipt.json')['passed'];assert not (H/'final_receipt.json').exists()
 before=(H/'root_before.md').read_bytes();current=ROOT/'当前进度与下一步.md';assert current.read_bytes()==before;assert sha(current)==read(STRUCT/'final_receipt.json')['root_sha256']
 figures=read(H/'figure_receipt.json')['files']
 dump(H/'图版目视核验.json',dict(utc=time.time(),passed=True,reviewed=[f['file'] for f in figures],checks=['19 rows all retained with base/variant divider and zero reference','I true ALT ends left while substitute returns to right','T true ends left while both substitutes end right','L q0 estimate error makes small true improvement appear 10 metres','legends distinguish physical H, planned common credit, pending, raw and whole-route shortcut; no clipped titles/legend'],scope='visual QA only; legality and lengths independently audited from saved data',new_core=0,new_post=0))
 w=read(H/'workload.json');status=read(H/'status.json');extract=read(H/'extraction_receipt.json');technical=read(H/'technical/round1.json');counts=Counter()
 for r in extract['receipts']:counts['source_route_vertices_read_for_extraction']+=r['source_route_vertices_read'];counts['common_prefix_edges']+=r['common_edges'];counts['finite_edges']+=r['finite_edges']
 dump(H/'调用与处理费用账.json',dict(scope='stage A only, frozen configuration; no speed claim',actual_calls=w['calls'],caps=dict(prefix=38,tail=38,post=38,substitute_views=76,technical=20,repair_rounds=1),technical=dict(unique_cases=18,attempts=18,repairs=0,actual_micro_frozen_connector_contexts=1,actual_micro_frozen_connector_paths=2,actual_micro_astar_searches=1,public_post=0,real_core=0,stub_path_calls=technical['cases'][9]['actual']['path_queries']+1,stub_scope='incidental test two calls plus budget partial one call; missing-order rejects before path'),extraction_counts=dict(counts),main_counts=w['main_counts'],independent_counts=w['independent_counts'],timing_statistics=w['timing_statistics'],source_verification_receipts=[read(H/'protocol'/('source_verify_'+str(i)+'.json')) for i in range(3)],setup=read(H/'setup_receipt.json'),extraction_seconds=extract['wall_seconds'],prefix_audit_seconds=read(H/'crop_audit_receipt.json')['wall_seconds'],pure_technical_seconds=technical['wall_seconds'],batch_parent_seconds=status['wall_seconds'],predictions_seconds=read(H/'predictions_seal.json')['seconds'],comparison_seconds=read(H/'comparison_receipt.json')['seconds'],report_seconds=read(H/'report_receipt.json')['seconds'],figures_seconds=read(H/'figure_receipt.json')['seconds'],preseal_readonly_verification=read(H/'preseal_verify.json'),postseal_readonly_verification_location='verify_receipt.json (created exclusively after final seal)',failure=0,unavailable=0,late=0,not_run=0,alias_warning='post.service_intersections == post.post_service_intersections; do not add',unknowns=w['unobserved'],profile='OFF; import-only pure watcher separate',side_cost_boundary='all main/independent/code reading/hash/report work retained; uninstrumented fine counters null, never zero; no cross-batch timing ratio'))
 prefix='''# 最新完成：障碍后接续估计器影子诊断封存（2026-10-23）

障碍后接续估计器影子诊断_v0.1_20261023 已按固定稿完成阶段A并停止交审。入口00_通俗影子评估结论.md、01_规则与信息隔离.md、02_逐例预测与真实结果.md、03_计算工作量与未验证事项.md、review_packet、预测seal、调用费用账及final/verify回执。

只用基础12对和受控变体7对，共19保存配对/38臂，5无资格槽原样留缺口。旧三个包verify入口实际核验：基础及变体仅把根进度读路径投影到各自不变root_after，当前根后缀/hash链另核；结构包核实际当前根。来源2451绑定、原包及旧final不变，不写成负责人此前已全量复核。

16局部边/64总边/下一恢复前/末采点政策与旧任务序补尾及1e-8保护阈值在真实阶段前冻结；18纯技术首轮通过、修复0。38裁剪前缀独立核原始路线与完整pending、局部奖励/来向、最早截止；实际27臂停下一恢复前、11臂停16局部边，未读入真实返航。估计器每臂独立新进程，只可读一份裁剪包与冻结代码/config/运行时，实际open路径留证，原目录/其他输出/真值禁止。保留设计者已见案例的开发偏差，不称盲测。

新旧序补尾38条、公共直达38次、原生/直达替代视图76；真实历史/完整PPCPP/H1/P2/真实有限推演核心全0。冻结UnifiedGeometry端点排序A*同长规则，仅相对导入隔离，无路径平局改写；旧序遗漏拒绝、途中采格更新、完整轨迹接缝与原事件H保持。38臂均完整合法返航，主外独立BFS最短性/旧序/中心区信用/公共post审核通过，异常/不可用/超限/迟到/未运行均0，无补跑。预测文件及所有裁剪/输出/审核hash封存后才合并完整真值。

固定配置未过继续门槛。原I_gap_B_p60估计q1比q0长25.406018257米，真实却短28.763940280；OFF误差−6.584268089、ALT+47.585690448，误差差+54.169958537反号。OFF13边停左[13,7]、余32右格；ALT31边停右[38,10]、余左1+右15，旧序补尾先回左再右收尾，改写真实ALT最后左收尾安排。四I变体全漏，B进度变体重复同一触发与原生尾部，不当独立模式。

原T_gap_B_p25和两个A障碍变体均估计q1少2米，真实多8.587181813米，全误收。两臂均24边停[27,31]/[26,32]、余100任务；旧序先左后右并右收尾，真实先右后左。OFF/ALT误差+31.848240843/+21.261059030，误差差−10.587181813造成错误排序。早公开B变体目标对改变、真实同路等长且估计等长，不作避免原T退化。

基础12对：抓住3改善、漏1改善、误收1退化；7真实等长中6保留q0、L_gap_B_p60虚估q1短3.219810994。采用建议相对q0合计−13.558736680米，六基础几何等权均值−1.129894723；仅满足净负第三项，I/T两个必需项均失败。两候选遗憾合计37.351122093、最坏单例28.763940280，最坏实际退化8.587181813。变体7对单列：4漏改善/2误收退化/1等长，采用合计+17.174363625米，不与基础拼总体胜率。I_A两进度和L_A_p25识别方向，但L_A估计−10而真实仅−0.979486872、真实原生仍+2，夸大保留。5同路等长全估等长，3不同路等长中1误偏q1。

两臂尾段误差未抵消，逐对根式恒等式及阈值/选择/遗憾独立Fraction/isqrt从实体顶点重核76个估计/真实直达长度通过。完整替代估计没有真实候选上下界保证；误差与旧序补尾不对称相符，不作独立机制因果或断言延长前瞻一定解决。旧H2不改、仍未确认。

工作量完整保留：有限前缀边/补尾前责任逐臂，补尾2160任务连接+38返航、5677新边，完整替代原生6694边、公共post3426候选；尾部2204格中44顺带采，仍访问几乎全部尾部任务、构造完整路线再做全程post及信用。主路径缓存每臂新建，无跨臂复用；A*2198次、命中0，生产上下文BFS出队/A*展开细数null非0，distance_BFS_rows0不代表无BFS。独立审核另2198 BFS/3677578出队/14710312邻居，费用分开、不与别名相加。裁剪读取/尾段/post/必要合法性/主外审核/报告图及哈希均计账，读取保存前缀不能代替真实有限推演成本，无旧批速度比或加速声称。

结论：本固定尺子不能同时识别关键改善并避开关键退化，关闭此配置继续信号。仅此19对已见开发材料，不推广所有估计/前瞻无效；不调整长度/尾序/权重、不阶段B真实推演计时、不新图/留出/线上接管/推送。四张图及全部正负/等长、误差/失败空账、预测先封存证据齐全。当前根仅前缀追加，旧正文及旧封存原样保留，封存后停止交负责人审核。

---

'''.encode('utf-8')
 after=prefix+before;(H/'root_after.md').write_bytes(after);current.write_bytes(after)
 # No rewriting sealed output after this point. Only final receipt and the
 # excluded post-seal read-only verify_receipt may be created subsequently.
 excluded=['final_receipt.json','verify_receipt.json'];files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and str(p.relative_to(H)) not in excluded}
 final=dict(status='sealed_stopped_gate_failed',utc=time.time(),files=files,file_count=len(files),root_sha256=sha(current),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(STRUCT/'final_receipt.json'),policy_sha256=read(H/'manifest.json')['policy_sha256'],prediction_seal_sha256=sha(H/'predictions_seal.json'),prediction_before_truth=True,pairs=19,arms=38,new_substitute_views=76,new_tails=38,new_public_post=38,new_complete_core=0,new_true_finite_core=0,new_history_core=0,technical_cases=18,repairs=0,gate_passed=False,independent_preseal_passed=True,old_sources_readonly=True,stage_B_started=False,excluded_from_self_manifest=excluded,finalize_wall_seconds_before_receipt=time.perf_counter()-start)
 dump(H/'final_receipt.json',final);print(dict(sealed=True,files=len(files),root_sha256=final['root_sha256'],gate_passed=False,stopped=True))
if __name__=='__main__':main()
