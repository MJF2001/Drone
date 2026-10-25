"""Report-only finalization; no planning, BFS or visibility queries."""
from common import *
from datetime import datetime,timezone
import difflib
def seal():
 assert not (H/'final_receipt.json').exists();assert read(H/'preseal_verify.json')['passed'];status=read(H/'status.json');summary=read(H/'summary.json');old=Path(read(H/'plan.json')['old_package']);before=(H/'root_before.md').read_bytes()
 assert status['failure'] is None and status['stage']=='finite_batch_ended' and (ROOT/'当前进度与下一步.md').read_bytes()==before
 assert read(old/'final_receipt.json')['root_sha256']==sha(H/'root_before.md');guard()
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v
 bindings=[]
 for name in ('expand_native.py','expand_hook.py','decision_audit.py','analysis_metrics.py','worker.py'):
  assert sha(H/name)==sha(old/name);bindings.append(dict(source=str(old/name),source_sha256=sha(old/name),active=name,active_sha256=sha(H/name),byte_identical=True))
 for name in ('common.py','run.py'):
  (H/'source_snapshot'/(name+'.diff')).write_text(''.join(difflib.unified_diff((old/name).read_text(encoding='utf-8-sig').splitlines(True),(H/name).read_text(encoding='utf-8-sig').splitlines(True),fromfile='old/'+name,tofile='variant/'+name)),encoding='utf-8')
 oldq=(old/'qualify.py').read_text(encoding='utf-8');assert (H/'qualification_primitives.py').read_text(encoding='utf-8')==oldq[:oldq.index('def prepare_states():')]
 dump(H/'bindings.json',dict(byte_identical_activity=bindings,qualification_primitives='byte-identical prefix functions of previous qualify.py',common_diff='absolute cap 42 to 36; history cap 6 to 0 only',run_diff='source, slot qualification and scheduling only',public_post='unchanged old runtime guards',new_mechanisms=0))
 for item in status['completed']:
  o=read(H/'outputs'/(item['id']+'.json'));assert o['passed'] and o['eligible'] and o['post_envelope']['fallback'] is None and o['independent']['passed'] and o['decision_audit']['passed']
 # Preserve the complete cheap pool in addition to the originally frozen
 # first20 and pool size. This is report arithmetic only, not new qualification.
 complete=[];projections=0;start=time.perf_counter()
 for src in read(H/'source_bindings.json'):
  c=read(src['old_input']);hist=read(src['history_output']);F=ps(hist['input']['free']);U=ps(c['targets'])-ps(c['covered']);b0=tuple(src['old_obstacle']);a,z=src['edge_vertices'];pool=[]
  for cell in sorted(F-U-{tuple(c['current']),tuple(c['base']),tuple(c['previous']),b0}):
   projections+=1
   if all(2*max(a[d],z[d])>=2*cell[d]-1 and 2*min(a[d],z[d])<=2*cell[d]+1 for d in (0,1)):pool.append(cell)
  pool.sort(key=lambda q:(sum(abs(x-y) for x,y in zip(q,b0)),q[0],q[1]));saved=read(H/'qualification'/(src['id']+'__A_scan.json'));assert norm(pool[:20])==saved['first20'] and len(pool)==saved['pool_size']
  complete.append(dict(origin=src['id'],ordered_full_pool=norm(pool),frozen_first20=saved['first20'],matches_frozen_pool=True))
 dump(H/'候选池完整静态重建.json',dict(pools=complete,scope='report-stage reconstruction of cheap AABB pool from frozen sources; no extra candidate qualification and no input changes',AABB_arithmetic_projections=projections,wall_seconds=time.perf_counter()-start,new_primary_qualification=0,new_core=0,new_post=0,new_visibility_queries=0,new_BFS=0))
 dump(H/'图版目视核验.json',dict(passed=True,contact_sheet='figures/十二槽图版总览.png',full_views=['figures/T_gap_B__p25__B1.png','figures/L_gap_B__p25__B1.png'],checks=['all12 slots visible including5 unrun','F/P/non-target flyable/H/obstacle layers','changed-target zero physical route case','pending-target-blocked rejection not counted as zero or task deletion'],not_another_geometry_audit=True))
 with (H/'00_通俗受控变体结果.md').open('a',encoding='utf-8') as f:f.write('\n图版入口：[十二槽总览](figures/十二槽图版总览.png)。原例图与新增/未运行图分开标注，见图版索引.json。完整AABB池在封存时由冻结来源静态重建，吻合资格前保存的前20及池大小；未额外执行资格或响应。\n')
 prefix='''# 最新完成：障碍后接续正反例受控变体封存（2026-10-23）

障碍后接续正反例受控变体_v0.1_20261023 已按执行稿完成并停止交审。先读00_通俗受控变体结果.md、03_逐例身份轨迹与费用.md、04_调用计时与未知.md、review_packet及final/verify回执。本批仅围绕已见I_gap_B__p60正例、T_gap_B__p25反例、L_gap_B__p25等长例三个开发起点，各A1/A2障碍位置和B1/B2公开时机四槽；不是随机扩样、独立验证或新增12几何，不与旧批合并算总体胜率。

开工旧包只读verify通过并复制回执，source_bindings追溯3条实际旧完整历史及指定全局post边/源索引。核心、动态触发/候选、一次例外独立审核、指标及worker共5文件逐字节复用；common只改36总入口/history0，资格函数复用旧前缀。六项纯身份首轮通过、准备修复0。所有变体构造/资格/缺槽/去重完成，冻结7唯一合格E和运行计划后才运行新响应。真实历史准备、新N/P2/R、热身/技术入口、留出及重跑均0。

12槽为7合格、5缺槽/不适用、重复0。实际21核心/21公共post（7 REF+7 OFF+7 ALT1）、42新增视图；7 OFF与本轮REF完整等价、7 ALT恰一次授权，21完整处理审核和7配对独立算术通过，真实失败/迟到/触顶0。15条件响应槽因资格不足未运行，不记持平或求解失败；未用预算未挪作补跑。核心选择共20、post18软/4096/20迟到、父150、原生4096边、四线程1、详细profile OFF/null保持。

I正例四变体仍短：A障碍[14,7]替换[15,7]/[16,7]，同一指定旧post边仍首先非法、S/H/U不变，目标对保持[13,7]→[37,7]，Δ恢复+2、Δraw−28，Δpost分别−28.000008258/−27.887045906米（旧−28.763940280）。恢复连接本身同路，OFF后续原生展开及公共直达变化，非符号反转。B50%/70%为H/U=56/56和79/33，均汇合到原例相同触发current/previous/pending、目标对及两臂原生尾部，效应精确保持−28.763940280；不能将不同责任的绝对路程相减称改进。

T反例A障碍[25,26]改[25,27]/[25,28]，目标对仍[24,31]→[25,31]；ALT恢复展开变化但Δraw+6、Δpost+8.587181813米精确保持退化。B15%（H/U27/149）首个恢复改成[24,15]→[24,16]、两臂物理同路零效应；这是触发及目标对改变，不是同一选择优劣反转。B35%切点已越过原受阻边，保留不适用。

L等长起点A允许池为空，两个位置槽缺失；B15%固定b0[14,7]尚未采，遮挡未采任务而拒绝、未删除责任；B35%已过原受阻边。四槽均无合格新比较，不得说等长结果已验证保持或算法无收益。

主资格8个A候选和4个B固定障碍实际检查（另2个B已过边先拒绝），共7 BFS/10310出队/41240邻居；主单格边297、独立几何597、AABB4621、信用448行/独立新信用999行及前缀451状态重建、前缀距离456项计账。A拒绝含2个仅格路阻断和2个旧post合法。资格前20与池大小保存；封存再由冻结来源静态补全池坐标，额外AABB算术单列，不新增资格。来源读取、纯检查、选择、主外审核、报告及图费用均保存，核心细查询null不是0。

H2不重设：6组不同路线首次分歧在恢复连接途中，固定L全空；1组物理同路无分歧，指标不适用/未确定，不称没有往返。I四组共同C−4/返航−24，T两个A共同C+10/返航−4，分账不作独立机制因果。原/直达信用顺序、末采、转弯、ΔG、目标旧rank及来源身份、同目标展开变化/同触发同号/目标问题改变的分组证据齐全。无前瞻、评分、奖励、在线判断器或新机制；不做总体概率、事件专属或普遍推广结论。

原始输出、7新配对与3旧只读参照、5不适用、全资格与hash、根历史链及图齐全。根仅前缀追加，开工字节绑定旧final根hash，旧正文及旧封存/旧final原样保留。完成即停止交负责人，不追加地图/候选/目标、无事件四格、闭环、迁移、留出或推送。

---

'''
 new=prefix.encode('utf-8')+before;(ROOT/'当前进度与下一步.md').write_bytes(new);(H/'root_after.md').write_bytes(new)
 excluded={'final_receipt.json','verify_receipt.json'};files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in excluded}
 final=dict(status='sealed_controlled_variants_stopped_for_owner_review',utc=datetime.now(timezone.utc).isoformat(),files=files,file_count=len(files),root_sha256=sha(ROOT/'当前进度与下一步.md'),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(old/'final_receipt.json'),previous_root_bound=True,planned_slots=12,qualified_new_E=7,missing_or_inapplicable=5,duplicates=0,actual_core=21,actual_post=21,new_views=42,new_histories=0,independent_reviews=21,valid_pairs=7,new_algorithmic_mechanisms=0,no_population_rate=True,excluded_from_self_manifest=sorted(excluded),additional_experiments_after_fixed_batch=0)
 dump(H/'final_receipt.json',final);print(json.dumps(dict(sealed_files=len(files),core=21,post=21,root_hash=final['root_sha256']),ensure_ascii=False))
if __name__=='__main__':seal()
