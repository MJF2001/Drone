"""Close verified delivery and prepend progress, retaining all historical text."""
import datetime
from order_common import *
log=(H/'verify.log').read_text(encoding='utf8');assert log.rstrip().endswith('planner=0, coverage exact=0, route candidate=0.') and 'ALL PASS;' in log
for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='ALL PASS',actual_verify_invocations=1,technical_failures=0,retries=0,verify_script='order_verify.py',verify_sha256=sha(H/'order_verify.py'),verify_log_sha256=sha(H/'verify.log'),verified_manifest_sha256=sha(H/'manifest.json'),verification_distance_execution=read(H/'analysis.json')['distance_and_slice_execution'],new_planner_calls=0,new_coverage_exact_searches=0,candidate_generation=0,stopped_for_responsible_reviewer=True)
save(H/'verification_receipt.json',receipt)
entry='''# 最新完成：复杂障碍覆盖顺序分歧只读诊断已封存，待审核（2026-10-21）

完成复杂障碍覆盖顺序分歧只读诊断_v0.1_20261021。严格复用原16状态、96正式路线、48同输入同seed配对，2历史准备仅核来源；主及时障碍24配对/8状态/5几何，控制6/2/1，附全部合法含迟到障碍36/12/6、控制12/4/2。18迟到配对未进入主成绩。全批42配对首次采集顺序不同、6整条路线相同；主障碍18次PP更长、6同长、0更短。21x15_maze_p10三个seed顺序不同但同长，不能判作缺陷。

重建96条真实首次采集序列和576六档切片，分开记录完整轨迹共同前缀分叉A与采集顺序分歧B；后缀只审计字面原路线，不拼接或产生候选。保留全目标排名/步差、各状态合格n/均值范围/前五、事件专用分层和33项预定反向关系观测。固定选例6页，rooms/control主同长缺失，不由迟到补位。恢复候选距离/P2在线逐步trace缺失明确保留，未执行核心补记录。

唯一阅数后探索性线索：31x21_maze_p30与31x21_serpentine_p30的原始local候选只含未检邻格(5,3)，P2已有下一步走初始已采历史格(5,1)。支持6/24主障碍配对、2/8状态、2/5几何；仅2族2几何，未达3几何描述条件，未证明只改一步有效或能取得全部8/70步净差。其他12个主正差配对无此首分叉证据；同分坐标/剩余规整度不足以形成第二个独立假设。当前无已验证可实施机制或创新点，未重启LAST/四方向/局部P2，未加入终点奖励。

实际上游只读verify与本轮order_verify全部通过；预分析封存414来源hash/协议/代码，最终manifest/日志/收据/调用账保留。新增规划器/覆盖精确搜索/候选/地图/seed/预算档/留出/动作干预/路线拼接均0；本交付含上游核验及分析/最终核验实际48基地BFS、61普通Dijkstra（29唯一起终点、32独立全图）另账，不当覆盖求解或算法提速。未发生技术失败、重试或被替代运行。详见本目录通俗结论与完整诊断报告.md、review_packet.md、verify.log及verification_receipt.json。更新后停止，交负责人审核，不自动开发、实验或Git提交推送。

---

'''
progress=R/'当前进度与下一步.md';old=progress.read_text(encoding='utf8');assert not old.startswith('# 最新完成：复杂障碍覆盖顺序分歧只读诊断已封存')
with progress.open('w',encoding='utf8',newline='') as f:f.write(entry+old)
with (H/'完成后根进度快照.md').open('x',encoding='utf8') as f:f.write(entry+old)
with (H/'封存完成说明.md').open('x',encoding='utf8') as f:f.write('# 封存完成\n\n上游和本轮实际只读verify全部通过；verify.log及verification_receipt.json记录实际核验。本轮新增规划器/覆盖精确/候选/动作干预均0。预登记manifest.json核对248个交付文件，completion_manifest.json再覆盖核验日志、收据、本说明、封存脚本及完成后进度快照；根进度会继续维护，因此只将其快照列不可变hash。\n\n唯一探索性候选门假设仅两族两几何、未经干预，不是已验证机制。当前工作封存停止，由负责人审核；没有自动启动后续实验。\n')
save(H/'completion_manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='completion_manifest.json'})
for p,h in read(H/'completion_manifest.json').items():assert sha(H/p)==h,p
print('COMPLETE: original 248-file manifest unchanged; completion manifest verified; root progress prepended with history intact; stopped for review.')
