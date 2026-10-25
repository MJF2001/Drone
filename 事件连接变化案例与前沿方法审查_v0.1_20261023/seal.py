"""One-time archive of completed read-only research; runs only the receipt verifier."""
from pathlib import Path
import json,hashlib,datetime,subprocess,sys
H=Path(__file__).resolve().parent
assert not (H/'final_receipt.json').exists(),'already sealed'
root=H.parent/'当前进度与下一步.md'
before=(H/'root_before.md').read_bytes()
assert root.read_bytes()==before,'root changed independently; do not overwrite'
prefix='''# 最新完成：事件连接变化正反例与前沿方法审查封存（2026-10-23）

事件连接变化案例与前沿方法审查_v0.1_20261023 已按稿顺序完成阶段A固定案例及阶段B有限检索。先读00_通俗结论与审核入口.md、01_阶段A固定正反例结论.md、02_六例三seed与12段记录.md、03_前沿方法对照与裁决.md、四篇文献笔记、review_packet/ledger及final_receipt。

从当前OFF全54状态保存配对按三seed状态等权固定6例，未因没有支持换例；额外基础几何判据与段选择已预登记。medium_Z_obstacle_p70、large_I_straight_p70、medium_I_obstacle_p70、small_L_corner_p70仅事件后关联，状态等权B/C多走12.844%、47.314%、9.354%、44.180%；large_I_obstacle_p70和small_I_corner_p30等长反例保留。它们仍是开发快照诊断，非连续事件/留出或普遍结论。

12条已保存连接前后两域共24次独立合法性判定，全部前后合法，变化0；闭禁飞盒细测0，不能称零计算。三扩展例F不变，仅公开新任务；三障碍例旧剩余后缀未找到触删格单元边，依规则回退首边、不追正例。事件前实际prep输入/读取记录、旧计划及采用历史/后缀均追溯保留。P2内部最终visits未保存，包装锁定格心锚点与实际区域信用见证顺序分开，不补猜。不能将总差距归于一条边，也不能由12段证明所有最短连接不变。

阶段A先哈希固定，后检索10项候选、精读4项：TRACE v1预印本、OARP-Replan作者v2/T-RO2024、FALCON作者v2/T-RO卷2025、LS-MCPP AAAI2024。逐篇核真基线、机制/规模/时间/设备、条件保证、源码版本及旧尝试重合；4原PDF、8渲染页、一手来源/失败记录保留。部分中间检索逐字请求未独立单列，完整返回和原文另存，未声称请求日志完整。任务残余拓扑不同于可飞域，条带最优不同于整路线最优，探索体积覆盖不同于必检信用。

本轮未支持“事件连接损失触发少量重排”为新主机制，进入实现候选0；一般顺序改进和其他未查连接仍未解决。没有把已有树/GTSP/SOP/局部搜索换名为创新，无确认主算法，不重启局部P2/FIRST/LAST/四方向或性能批。规划/核心/路径及覆盖搜索/算法候选生成/新路线/新闭环全0；文献下载、处理和有限几何另记。只读verify不重判几何，原旧证据不覆盖，更新封存后停止交负责人审核，无新地图、模型、留出或推送。

---

'''
root.write_bytes(prefix.encode('utf-8')+before)
l=json.loads((H/'ledger.json').read_text(encoding='utf-8'))
l['status']='complete_sealed_stop_for_owner_review'
(H/'ledger.json').write_text(json.dumps(l,ensure_ascii=False,indent=2),encoding='utf-8')
r=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8')
if r.returncode:
 (H/'seal_verification_failure.txt').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
 raise RuntimeError('preseal verify failed; preserved failure; no final receipt')
receipt=json.loads(r.stdout)
(H/'verify_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='final_receipt.json'}
final={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed_stop_for_owner_review','files':files,'file_count':len(files),'root_progress_path':str(root),'root_progress_sha256':sha(root),'preseal_verify':receipt,'algorithm_calls':0,'additional_geometry_in_verify':0,'retained_stageA_legal_calls':24,'mechanisms_to_implement':0,'no_new_experiments_after_seal':True}
(H/'final_receipt.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'sealed':True,'file_count':len(files),'root_updated':True,'algorithm_calls':0,'geometry_calls_in_seal':0,'stopped_for_review':True},ensure_ascii=False))
