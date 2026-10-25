"""Added AFTER technical stop: saved-data diagnosis and archive only.
No native/rule/auditor/post execution, no new path/geometry/credit searches.
The frozen implementation remains unchanged after the first real entry.
"""
from region_common import *
from collections import Counter
from html import escape
import ast
def seal():
 assert not (H/'final_receipt.json').exists();guard();state=read(H/'run_status.json');assert state['status']=='stopped_technical_error'
 from archive import make_reports
 make_reports()
 ledger=[json.loads(s) for s in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];starts=[s for s in ledger if s['event']=='started'];assert len(starts)==44 and all(sum(s['kind']==k for s in starts)==22 for k in ('core','post'))
 assert starts[-2]['job']==starts[-1]['job']=='formal__G1-A__ON'
 failed=read(H/'outputs/formal__G1-A__ON.json');ref=read(H/'outputs/formal__G1-A__ORIGINAL.json');assert not failed['passed'] and failed['last_stage']=='independent_review';assert failed['independent']['passed']
 check=failed['native']['raw']['rule']['check'];assert not check['activated'] and check['reason']=='geometry_conditions_failed'
 # Saved routes only: deliberately not a successful formal comparison.
 facts={'raw_route_same':failed['native']['raw']['route']==ref['native']['raw']['route'],'post_vertices_same':failed['post']['vertices']==ref['post']['vertices'],'saved_native_length':failed['views']['A']['metrics']['length'],'saved_post_length':failed['views']['B']['metrics']['length'],'not_valid_formal_pair':True,'rule_activation':False,'conditions':check['conditions'],'native_geometry_counts':failed['native']['raw']['geometry_counts'],'rule_counts':failed['native']['raw']['rule']['counts']}
 dump(H/'failed_pair_saved_facts.json',facts)
 # Prove the interface mismatch statically. No repeat of audit/solver/BFS.
 source=(H/'region_audit.py').read_text(encoding='utf-8');worker=(H/'worker.py').read_text(encoding='utf-8');pure=(H/'precheck.py').read_text(encoding='utf-8');rule=(H/'region_rule.py').read_text(encoding='utf-8')
 assert "r['check']==norm(check)" in source and "audit(c,raw,job['arm']=='ON')" in worker and 'audit(norm(c),norm(raw),True)' in pure and "'q0':q0" in rule
 first=read(H/'preparation/first_preflight_failure/history__G1-A.json');assert first['status']=='implementation_or_contract_error' and 'unbound source' in first['stdout']
 repair=read(H/'engineering_repair.json');assert repair['round']==1 and repair['actual_core']==repair['actual_post']==0
 original_freeze=read(H/'preparation/first_preflight_failure/active_freeze.json');current_freeze=read(H/'active_freeze.json');changed=[p for p in original_freeze if current_freeze[p]!=original_freeze[p]];assert set(changed)=={'register.py','precheck.py','runtime_guards.json'}
 assert read(H/'registration_receipt.json')['active_freeze_sha256']==sha(H/'preparation/first_preflight_failure/active_freeze.json')
 stable=['region_native.py','region_rule.py','region_audit.py','worker.py','frozen_reference.py','plan.json','pure_cases.json']
 assert all(sha(H/p)==original_freeze[p] for p in stable)
 eq=[]
 for sid in ('G1-A','G2-A','G5-A','G6-A'):
  r=read(H/f'outputs/equivalence__{sid}__OFF.json');assert r['passed'] and r['eligible'] and all(r['off_equivalence'].values());eq.append(sid)
 supplement={'passed':True,'scope':'static type/call-chain and ledger/repair/frozen-source bookkeeping ONLY; no rerun of failing algorithm audit; archive limitation explicitly disclosed','fixed_unique_pure_cases':16,'case_executions':32,'pure_rounds':2,'both_rounds_passed':True,'engineering_repairs_before_first_core':1,'post_entry_repairs':0,'pre_entry_worker_failures':1,'pre_entry_failure_evidence':'parent log/stdout + controller traceback only; worker JSON lost during basename-flattened archival','real_worker_jobs':22,'core_entries':22,'post_entries':22,'unspent_core':22,'unspent_post':22,'equivalence_slots_passed':eq,'qualified_slots':9,'ineligible_slots':['G2-B','G5-B','G6-B'],'formal_valid_pairs':0,'formal_failed_outputs':1,'algorithm_sources_unchanged_after_registration':stable,'engineering_changed_pre_entry':changed,'no_algorithm_queries_after_error':True}
 dump(H/'supplementary_static_review.json',supplement)
 text='''# 技术停止：审核器元组/列表接口不一致

12次历史、8次关闭等价入口均完成。9槽通过固定资格；G2-B、G5-B、G6-B的唯一登记障碍未严格穿过旧实际post后缀内部，均保留缺槽，不替换。四个指定门槛槽均合格，4对完整关闭等价通过。

正式按冻结顺序先运行G1-A原版，再运行开启版。开启版已完成核心与post，独立几何/中心信用/距离审核通过；随后逐决策审核在region_audit.py末尾综合日志断言失败。该结果整体标为implementation_or_contract_error，立即停止，绝不收为正式有效配对，也不把已完成的子审核说成完整验收通过。

静态定位：worker.py把内存原始raw直接交给audit；Priority.inspect保存的q0、representatives、Q等仍含元组。region_audit.py用`r['check']==norm(check)`把它与JSON列表结构比较，例如`(8,11)`与`[8,11]`不相等。纯桩第16项先把raw整体JSON规范化后才调用audit，因而没有覆盖真实内存调用链；第15项的tuple/list roundtrip也不足以证明混合类型接口等价。这是本轮可避免的审核器接口错误，不能归为规则路线收益负例。没有修复该源码或重新执行审核/BFS来宣称通过。

G1-A保存的规则检查未激活：d(R,B)=20，而d(R,S)+d(S,B)=14+8=22；d(X,R)=19，而d(X,S)+d(S,R)=5+14=19，严格不等式也不成立。保存原生与post路线分别与原版相同，长度均53；这些仅是失败文件里的只读事实，不能当成一对正式零收益结果，更不支持“留S收尾”的机制。后续全部开启/对照入口停止，三项机制的正式检验未知，正式有效配对0。

首次真实核心之前另发生过一次来源白名单错误：第一个工作进程在guard阶段拒绝未绑定的pyscipopt/_version.py，尚无核心/post入口。本轮使用了唯一一次事前工程修复，补齐冻结.deps依赖绑定并把来源检查加入纯桩第2项，16固定案例全部重测通过。原16通过记录、原源码/首个freeze、失败进程文件和diff完整保存在preparation/first_preflight_failure及engineering_repair.json。16为固定案例数，两轮共32次案例执行；真实调用后的修复为0。没有更改样本、规则、期望或预算。

事前故障归档有一项缺失：移动到同一目录时，父日志与worker JSON原文件同名，父日志覆盖了该次核心入口前失败的worker JSON。因此只保留了首故障的父进程日志/stdout、controller traceback、原源码/freeze及修复diff，不能声称该次worker JSON完整保留；engineering_repair的first_failed_worker字段实际指向父日志。22次真实核心/post的输入、完整worker输出、父日志、正式失败原文件均另存原路径且完整。本轮不掩盖此缺失，也不据缺失记录补填时钟或结果。

实际总计22核心+22post：历史12+12、关闭等价8+8、正式尝试2+2。另有1次在核心入口前失败的工作进程，单列，不算核心/post。未用22+22不挪用。正式失败、中止、资格不足与未运行不混入正式汇总；质量/泛化/速度/创新均无新成立结论。旧FIRST/LAST重合与无事件对照缺失保持。封存后停止，交负责人审核，不自动v0.2。
'''
 (H/'03_技术停止定位与未运行范围.md').write_text(text,encoding='utf-8')
 p=H/'00_通俗结果与结论边界.md';p.write_text(p.read_text(encoding='utf-8')+'\n实际停止原因：首个开启版逐决策审核遇到元组/JSON列表混合比较错误；已按稿立即停止，未修复补跑。12历史、9合格/3缺槽、4对关闭等价通过，正式有效配对0。此前核心入口前工程修复1轮，固定16项纯桩重测均通过。详见[技术停止定位](03_技术停止定位与未运行范围.md)。\n',encoding='utf-8')
 p=H/'review_packet.md';p.write_text(p.read_text(encoding='utf-8')+'\n首要审核：[技术停止与类型接口遗漏](03_技术停止定位与未运行范围.md)。supplementary_static_review绑定真实入口前唯一工程修复及真实入口后源码未改；post_stop_seal.py为错误发生后新增的只读诊断/归档脚本，不是候选实现修复。\n',encoding='utf-8')
 pairs=read(H/'formal_pairs_and_mechanism.json')
 for p in pairs:
  for k in ('mechanism_claim_1','mechanism_claim_2','mechanism_claim_3'):p.setdefault(k,None)
  if p['id']=='G1-A':p.update(status='technical_failure_excluded',reason='type mismatch in independent audit; not admitted as zero gain')
 dump(H/'formal_pairs_and_mechanism.json',pairs)
 missing=read(H/'missing_jobs.json');rows={r['id']:r for r in read(H/'state_registry.json')}
 for j in missing:
  sid=next(p['slot'] for p in read(H/'plan.json')['jobs'] if p['id']==j['id']);j['qualification_status']=rows[sid]['status'];j['reason']='fixed_obstacle_missed_actual_post_suffix' if rows[sid]['status']=='ineligible' else 'technical_stop_after_formal_G1-A_ON_audit'
 dump(H/'missing_jobs.json',missing)
 # A saved-response overlay, explicitly marked as a failed diagnostic output.
 c=failed['input'];labels=c['labels'];maxy=max(p[1] for p in c['free']);scale=20;pad=35
 def xy(p):return (pad+p[0]*scale,pad+(maxy-p[1])*scale)
 lines=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="570"><rect width="760" height="570" fill="white"/><text x="20" y="20" font-size="16">G1-A FAILED audit: rule inactive; saved routes identical (53)</text>']
 for label,pts in labels.items():
  for pt in pts:
   x,y=xy(pt);color={'C0':'gray','S':'#a43ba4','R':'#cd871b'}[label];lines.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="{color}"/>')
 for r,color,w,dash in ((ref,'#1368be',3,''),(failed,'#e37b15',2,'stroke-dasharray="5 4"')):
  points=' '.join(f'{xy(pt)[0]},{xy(pt)[1]}' for pt in r['post']['vertices']);lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{w}" {dash}/>')
 for pt,name,color in ((c['current'],'current','#137a40'),(c['base'],'base','#111'),((6,10),'blocked','red')):
  x,y=xy(pt);lines.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/><text x="{x+7}" y="{y-8}" font-size="12" fill="{color}">{name}</text>')
 lines.append('<text x="20" y="525" font-size="13">Blue original / orange dashed candidate. Saved only; NOT a valid formal pair.</text><text x="20" y="548" font-size="13">No active OTHER/TAIL mechanism established; audit failed before acceptance.</text></svg>')
 (H/'figures/G1-A_首对失败诊断.svg').write_text('\n'.join(lines),encoding='utf-8')
 before=(H/'root_before.md').read_bytes();assert (ROOT/'当前进度与下一步.md').read_bytes()==before
 progress='''# 最新进度：片区两阶段有限验证技术中止并封存待审（2026-10-23）

障碍后片区两阶段规则有限验证_v0.1_20261023 已按核定稿执行并在技术错误处停止。精确12槽、标签/C0/唯一障碍/最早切点/seed20261023和44核心+44post上限先冻结；没有按收益换坐标。独立候选PPCPP_REGION_TAIL_V1与公共post命名空间隔离，原文件未改。

实际22核心+22post：12槽历史全部完成，独立真实中心信用/来向和受阻资格核查为9合格、G2-B/G5-B/G6-B固定障碍未穿过旧实际post后缀故缺槽；4指定门槛槽均合格，原版/OFF共8入口完整等价通过；正式只尝试G1-A原版与ON两入口，ON在逐决策审核日志比较处失败，立即终止。正式有效配对0，剩余22+22预算不用，不换槽/补跑。

技术定位：worker传内存raw给审核器，Priority.check含元组，而末尾用r.check直接比较JSON norm(check)列表；纯桩第16项先norm(raw)后测，漏了真实混合类型调用链。此错误不是路线质量反例，不能把独立post子审核通过当整体通过。失败ON规则本身未激活，两保存路线均53且相同仅作失败文件事实，不纳正式零收益/机制支持。算法及审核器错误源码原样封存，真实入口后未修复或重跑。

另有首次核心前来源guard拒绝未登记pyscipopt依赖1次，当时核心/post为0；使用唯一事前工程修复补依赖白名单、把绑定检查前移纯桩，固定16案例两轮均通过（32案例执行），旧源码/失败/首freeze/diff均留存。真实入口后的工程修复0，未改规则/地图/预期/预算。该前置进程故障费用另列，不隐藏作核心调用。

入口00_通俗结果与结论边界.md、01_十二槽历史与资格.md、02_实现差异与审核范围.md、03_技术停止定位与未运行范围.md、review_packet.md；原始输出、实际账、逐决策/中心信用回执、全指标/缺槽/失败图、只读verify与补充静态修复链核验封存。未运行的机制与正式收益记未知；没有新速度/泛化/创新结论，LAST/FIRST重合及无事件对照缺失保持。只追加本根，不改旧final，停止交负责人审核，不自动第二版。

---

'''
 after=progress.encode('utf-8')+before;(ROOT/'当前进度与下一步.md').write_bytes(after);(H/'root_after.md').write_bytes(after)
 from verify import verify
 dump(H/'preseal_verify.json',verify(False))
 files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('final_receipt.json','verify_receipt.json')}
 dump(H/'final_receipt.json',dict(status='sealed_technical_stop_for_owner_review',files=files,file_count=len(files),root_sha256=sha(ROOT/'当前进度与下一步.md'),root_before_sha256=sha(H/'root_before.md'),actual_calls=read(H/'actual_call_summary.json'),formal_valid_pairs=0,algorithm_error_repaired_after_real_entry=False,run_status=state['status'],utc=time.time(),auto_next_version=False))
 result=verify();result['final_receipt_sha256']=sha(H/'final_receipt.json');dump(H/'verify_receipt.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':seal()
