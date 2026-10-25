from common import *
def main():
 start=time.perf_counter();guard();assert read(H/'preseal_verify.json')['passed'] and read(H/'report_receipt.json')['passed'];assert not (H/'final_receipt.json').exists();assert not (H/'analysis_failures').exists()
 before=(H/'root_before.md').read_bytes();current=ROOT/'当前进度与下一步.md';assert current.read_bytes()==before
 dump(H/'分析源码冻结.json',{p.name:sha(p) for p in H.glob('*.py')})
 receipts={name:read(H/name) for name in ('setup_receipt.json','analysis_receipt.json','static_review_receipt.json','report_receipt.json','preseal_verify.json')}
 dump(H/'实际零调用与处理成本账.json',dict(utc=time.time(),scope='saved evidence/cost/static source review only',actual_new_calls=dict(core=0,history=0,public_post=0,path_distance_search=0,BFS=0,geometry_visibility=0,candidate_route=0,counterfactual_trial=0,training=0,profile_experiment=0,warmup=0,holdout=0),source_saved_data=dict(base_states=12,response_observations=36,response_views=72,history_only_boundary=6,variants_added_to_cost_sample=0,REF_added_as_candidate=0),FIRST=dict(imported=False,run=False,source_manifest_bindings=866,external_protocol_bindings=137,old_calls_not_repeated=True),processing_receipts=receipts,processing_cost_policy='JSON/text reads, bytes, hashing, exact/independent arithmetic, source lines, writes, wall times retained per stage; no claim zero computation',all_reported_original_call_times_are_historical=True,future_proposal_only=dict(approved=False,implemented=False,started=False,max_method_entries=48,max_core=72,max_post=72,max_pure_cases=12),failure_records=0,old_results_or_code_modified=False,final_postseal_verify_cost_location='verify_receipt.json',finalize_cost_location='final_receipt.json'))
 prefix='''# 最新完成：双候选完整试走既有证据与成本审查封存（2026-10-23）

障碍后双候选完整试走既有证据审查_v0.1_20261023 已按只读稿完成并停止交审。入口00_通俗结论与下一步建议.md、01_十二状态两候选参照与代价.md、02_保存计时边界与未知.md、03_旧FIRST重合与当前适配缺口.md、04_唯一待批准的最小成本核查协议.md、review_packet及final/verify回执。

本轮新增核心/历史/公共post/路径距离搜索/BFS/几何可视/候选路线/反事实/训练/profile实验全部0；只读JSON/hash、根式与转弯算术、时钟拆账和静态源码。开工实际执行影子包stdlib只读verify通过，核实际当前根，无需历史root投影；四包旧封存及逐级root_before/after链另核，旧FIRST866包内/137来源绑定通过，合计3805来源守卫。FIRST/规划器/post/几何模块未导入或运行，旧211门槛/282开发调用只作历史保存证据。

只取基础12状态/6几何、每例原seed一次，REF只作等价和费用背景、变体只作重复背景。保存q0/q1完整结果按认证直达距离取短、同长q0：4采用q1，7等长及1退化保留q0。默认直达总长1741.413810128→1690.503951355米，合计−50.909858773；六几何先各两状态均值再等权，距离均值−4.242488231米、逐状态相对差均值−3.696287625%，总路程比例−2.923478525%另列。只是保存结果中两候选较短者参照，非新算法实测、全局最优界或独立泛化成绩。

原生1870→1826少44步，但原生转弯总数+3（90°+6/180°−3/其他0）、累计角差整数计数认证恰0，保存浮点约−1.4e−14只是舍入。直达转弯总数+5（90°+3/180°−3/其他+5），累计角+3.071625454弧度，不能称全指标改善或节能。I主正例取q1，T退化保q0，L_A_p25原生+2但post−0.979486872，旧步数选优会漏掉；3不同路等长保q0，4同路等长保q0。全触发身份、完整pending/原旧序候选、两臂原生/直达责任资源及全部转弯保留；本12例首资格恢复恰等首次恢复，不能推广任意输入等价。

原42计时中6历史仅来源/费用边界，响应统计只36条REF/OFF/ALT。每状态每臂单次，固定REF→OFF→ALT新进程，详细profile关闭但OFF/ALT完整pending/逐决策/segment钩子仍存在。两个保存独立处理的主调用成本和平均0.467736秒（0.285493～0.771868），原生求解器自身和0.025638秒、公共post引擎和0.119076秒，分别占保存主时间5.48%/25.46%，其余69.06%是混合入口/日志/编码/信用报告区间。不能将相加改称共享前缀在线实现，不能减hook得干净时间或归因纯post/诊断，更不擅设工程足够快阈值。

逐字段时钟与层级保留：combined=raw_common+post_increment；native_entry包solver，solver包hook/原生完整审核；post_increment包engine及额外编码/信用/指标。必要原生合法覆盖返航、post几何/完整中心信用/资源检查必须算在线，主外独立BFS/奖励与报告图/封存另列；混在同一evaluate/engine的必要和报告费用不能精确分离，候选取得/复制/REF扫描/JSON单项未知。源scope概括disk在外不精确，entry/returned实际在主时钟内读写/fsync日志，按源码校正解释，不改旧记录。post.timing.encoding在JSON编码后才赋值，保存响应无该项，未知不填0。与旧FIRST/影子时间不算跨批因果速度比。

旧FIRST静态10项对照、22个源码片段/行号/hash保存：已有首次恢复完整分支、私有路径/pending/trace及来向复制、默认分支保留、直接复用赢家；旧最近/近基地/远基地候选、四邻接步数目标与当前q0/旧序q1及完整post目标不同。旧共享g与共享前缀是代码能力，当前中心区双候选共享续跑/缓存/跨接缝post兼容和节时未验证；当前两臂独立20秒native/post18软20迟到不证明共同截止下及时不退化。完整试走后取短者不是新创新，不能换名重做旧工作。

唯一优先建议：为回答是否确需近似，提交最小同机干净成本核查协议待批准，本轮未实施。原12状态/原seed、SINGLE默认完整处理与DIRECT2独立两臂全程post认证选短并复用赢家，两次重复共最多48方法入口/72核心/72post，纯项最多12且真实入口0，历史/热身0；先不共享前缀/缓存，不借保存答案免费取得候选。建议未来共同40秒总时钟含全部必要成本、保留源单层上限及所有超限失败，实施前另核截止传播；不声称默认及时必保。只是建议预算，实际调用仍全0，不自动批准或创建执行器。

独立stdlib核验从原36响应重建72视图实体长度/转弯，核12触发/两候选选择/责任回执与36时钟/导出、各阶段统计和六几何分组，整数平方因子/Fraction与独立Decimal相互核对通过；无新几何/BFS。分析失败0，所有读取/字节/hash/算术/静态行/写出及wall费用留账。失败估计器保持关闭，不改16/64/尾序/权重、不阶段B，不新图/留出/训练/推送。当前根仅前缀追加，旧正文、源码、数据、final均原样保留，封存后停止交负责人审核。

---

'''.encode('utf-8')
 after=prefix+before;(H/'root_after.md').write_bytes(after);current.write_bytes(after)
 excluded=['final_receipt.json','verify_receipt.json'];files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and str(p.relative_to(H)) not in excluded}
 final=dict(status='sealed_readonly_review_stopped',utc=time.time(),files=files,file_count=len(files),root_sha256=sha(current),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(SHADOW/'final_receipt.json'),source_guards=len(read(H/'source_guards.json')),states=12,response_observations=36,response_views=72,new_core=0,new_history=0,new_post=0,new_search=0,new_geometry=0,new_candidate=0,new_training=0,FIRST_run=False,independent_preseal_passed=True,single_priority_recommendation='minimal clean cost protocol pending separate approval',future_protocol_approved=False,future_protocol_started=False,old_files_readonly=True,analysis_failure_records=0,excluded_from_self_manifest=excluded,finalize_wall_seconds_before_receipt=time.perf_counter()-start)
 dump(H/'final_receipt.json',final);print(dict(sealed=True,files=len(files),actual_new_experiment_calls=0,future_protocol_started=False,root_sha256=final['root_sha256']))
if __name__=='__main__':
 try:main()
 except BaseException as e:fail_record('finalize',e);raise
