"""One-time report seal and root-prefix update, never executes algorithms."""
from common import *
from datetime import datetime,timezone
import difflib
def seal():
 assert not (H/'final_receipt.json').exists()
 status=read(H/'status.json');summary=read(H/'summary.json');ledger=read(H/'调用与查询总账.json');assert status['stage']=='finite_batch_ended' and status['failure'] is None
 assert ledger['actual_calls']=={'core':42,'post':42} and ledger['view_count']==84
 for item in status['completed']:
  o=read(H/'outputs'/(item['id']+'.json'));assert o['passed'] and o['eligible'] and o['post_envelope']['fallback'] is None
  assert o['independent']['passed'] and o['decision_audit']['passed'] and o['counts']['native_detail_profile'] is None
 before=(H/'root_before.md').read_bytes();assert (ROOT/'当前进度与下一步.md').read_bytes()==before
 previous=ROOT/'恢复目标收益事件依赖性补齐_v0.1_20261023/final_receipt.json';assert read(previous)['root_sha256']==sha(H/'root_before.md')
 guard()
 for path,v in read(H/'source_guards.json').items():assert sha(path)==v
 old=ROOT/'障碍后接续假设与扩样协议_v0.1_20261023'
 for file in old.iterdir():assert file.read_bytes()==(H/'protocol'/file.name).read_bytes()
 bindings=[]
 for newname,oldname in [('expand_native.py','recovery_diag_native.py'),('expand_hook.py','recovery_diag_hook.py'),('decision_audit.py','recovery_diag_decision_audit.py'),('worker.py','recovery_diag_worker.py')]:
  a=H/'source_snapshot'/oldname;b=H/newname
  bindings.append(dict(source=str(a),source_sha256=sha(a),active=newname,active_sha256=sha(b),byte_identical=sha(a)==sha(b)))
  (H/'source_snapshot'/(newname+'.diff')).write_text(''.join(difflib.unified_diff(a.read_text(encoding='utf-8-sig').splitlines(True),b.read_text(encoding='utf-8-sig').splitlines(True),fromfile=oldname,tofile=newname)),encoding='utf-8')
 assert bindings[0]['byte_identical'];dump(H/'bindings.json',bindings)
 for name,source in [('frozen_reference.py.txt',ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'),('common_post_engine.py.txt',ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/post/engine.py'),('common_center_service.py.txt',ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022/service.py')]:
  (H/'source_snapshot'/name).write_bytes(source.read_bytes())
 # These values transcribe the preceding completed read-only verification,
 # not a new execution or a substitute for the post-seal verification.
 dump(H/'preseal_verify.json',dict(passed=True,provenance='captured from completed verify_saved_results.py stdout before root update',hash_bindings_checked=2203,actual_entry_counts={'core':42,'post':42},reviewed_processing=42,views=84,root_history_chain=True,extra_saved_checks=dict(qualified_set_certificates=12,saved_collision_certificates=12,OFF_equivalence=12,first_trigger_and_candidate=12,shared_C_identities=16,empty_L_not_support=8,same_physical_route=4),outcomes_independently_recounted=dict(shorter=4,equal=7,longer=1,strict_geometries=3,strict_families=2),new_core_calls=0,new_post_calls=0,new_geometry_queries=0,new_BFS=0))
 dump(H/'图版目视核验.json',dict(passed=True,contact_sheet='12例图版总览.png',individual_full_views=['T_gap_B__p25.png','L_gap_A__p25.png'],history_overview='六图历史准备.png',checked=['F/P/non-target flyable/H/new obstacle layers','raw and post routes, base/current and real incoming heading','negative and geometric-only net-gain cases','captions and coordinate bounds'],scope='12-tile layout inspection plus two full case views and six-map history overview; not another geometry audit',new_core_calls=0,new_post_calls=0))
 dump(H/'计账边界补充.json',dict(initial_source_hash_items=1917,initial_source_hash_separate_seconds=None,initial_source_hash_time_status='not separately instrumented; not zero; initial shell wall in task history only',static_maps_generated=6,static_free_cells=8522,static_target_cells=779,phase_set_checks='inside each saved native_entry timer',pure_prechecks=dict(rounds=1,identities=6,repairs=0,real_calls=0),report_only_tools=['export_results.py','render_figures.py','verify_saved_results.py','seal.py'],report_tools_do_not_change_active_implementation=True,all_real_source_and_entry_records_retained=True))
 prefix='''# 最新完成：障碍后接续假设有限扩样封存（2026-10-23）

障碍后接续假设有限扩样_v0.1_20261023 已按核定稿完成并停止交审。入口00_通俗扩样结果与结论.md、03_12槽资格与配对表.md、04_机制与竞争解释逐例.md、05_调用计时与未知.md、review_packet、final_receipt及只读verify。原四份协议目录不改；新包保存字节副本与核定稿，四项修正生效：history非目标基地空H与event真实已采S分phase，H2用共同p/C，F宽矩形/P分段目标范围，旧计划次序备选身份标签与受阻段对应。

六项纯身份首轮通过，准备修复0，纯阶段真实入口0。六固定新开发几何I/L/T各2张，每图p25/p60共12槽；每图1次历史核心及post。所有历史及资格完成后冻结12个E再运行响应。资格14个单格尝试中12选中、2个grid_only_block拒绝，实际12 BFS/17032出队/68128邻居；主单格—边218次、AABB1257110次，独立资格与完整查询账保存。旧实际post确实受阻，初始U不变、物理H不回滚、待检与基地可达，未删除未采任务凑数。

42核心/42公共post：6历史+12 REF+12 OFF+12 ALT1；84原/直达视图、42独立完整处理审核、12配对独立算术全部通过；12 OFF与REF原生语义/路线、post/锚点/信用一致，12 ALT恰一次授权例外，其后原PPCPP。实际失败/迟到/触顶/未运行0，核心20秒含选择器，post18软/4096/20迟到、父150、四线程1、详细profile OFF/null。无热身/技术真实入口/重跑/P2/R/LAST/新N四格/留出/最优覆盖搜索。

12有效配对直达4短/7平/1长，其中4原/直达物理同路、3等长不同路；恢复备选11例多1米、I_gap_B_p60多2米。严格H1正例为I_gap_A两进度、I_gap_B_p60、L_gap_A_p25：3非等价几何跨I/L两族，所有六几何三族有合格E，达到预登记有限讨论门槛，不是创新或普遍优越。T族无改善，T_gap_B_p25最坏退化+8.587181813米/+3.908937%，退化1/12。六几何等权平均直达变化−3.370543%，仅本受控开发样本描述。

H2未确认：4例物理同路无分歧，8例固定首次分歧L全空，W=0是无适用对象，不能解释为没有往返；不扩邻域、不移动触发。共同p/C已保存并独立核16个恒等式。I_gap_A_p25共同覆盖−6/返航−6，p60共同覆盖0/返航−6；I_gap_B_p60共同覆盖−4/返航−24。L_gap_A_p25共同覆盖−32/返航+34、原生+2，公共直达后才净−0.979486872米，费用竞争解释必须保留。各自恢复后分账仅描述，不作H2判据。

旧计划次序备选不一律是保留旧目标：I_gap_B_p60默认已优先旧序，备选跳向其后。全部触发前E原生前缀与旧原生后缀前缀相同；10例位于旧受阻post源区间、2例更早，只作对应解释，不证明触发由障碍导致；无新N，不能称事件专属。A(q)从保存pending于报告阶段重算，未在线用于选择，费用主外单列。初始来源核哈希未单独计时标null，不冒充零成本。

图/完整指标/计时/查询/attempt/空与失败及未知、全部原始返回/信用/资格/一次例外证明与hash齐全。F均宽矩形，P只是I/L/T分段目标，非狭窄道路、复杂密集障碍或现场主实验；块数尺度任务量同时变化，不单归因形状。新增机制0条。已停止交负责人讨论，不自动开发规则、训练、迁移或扩批。开工root_before绑定旧final根hash，当前根仅前缀追加、旧正文逐字节保留，旧封存文件和final不改。

---

'''
 new=prefix.encode('utf-8')+before;(ROOT/'当前进度与下一步.md').write_bytes(new);(H/'root_after.md').write_bytes(new)
 excluded={'final_receipt.json','verify_receipt.json'}
 files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in excluded}
 final=dict(status='sealed_fixed_development_batch_stopped_for_owner_review',utc=datetime.now(timezone.utc).isoformat(),files=files,file_count=len(files),root_path=str(ROOT/'当前进度与下一步.md'),root_sha256=sha(ROOT/'当前进度与下一步.md'),root_before_sha256=sha(H/'root_before.md'),previous_final_sha256=sha(previous),previous_root_bound_to_start=True,actual_core=42,actual_post=42,views=84,valid_pairs=12,shorter=4,equal=7,longer=1,strict_H1_gate=True,H2_confirmed=False,formal_failures=0,new_algorithmic_mechanisms=0,excluded_from_self_manifest=sorted(excluded),new_experiments_after_fixed_batch=0)
 dump(H/'final_receipt.json',final);print(json.dumps(dict(sealed_files=len(files),root_sha256=final['root_sha256'],real_entries_unchanged=ledger['actual_calls']),ensure_ascii=False))
if __name__=='__main__':seal()
