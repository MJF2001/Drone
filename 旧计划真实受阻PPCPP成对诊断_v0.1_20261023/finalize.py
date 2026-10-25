from common import *
import sys,subprocess,datetime
def main():
 assert not (H/'final_receipt.json').exists()
 root=ROOT/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();assert root.read_bytes()==before,'root independently changed; do not overwrite'
 r=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8')
 assert r.returncode==0,r.stdout+r.stderr
 receipt=json.loads(r.stdout);dump(H/'verify_receipt.json',receipt)
 prefix='''# 最新完成：旧计划真实受阻PPCPP成对诊断v2封存（2026-10-23）

旧计划真实受阻PPCPP成对诊断_v0.1_20261023 已按用户v2完成，暂停旧稿不合并执行。先读00_通俗成对诊断报告.md（报告导出v0.2）、02_全量配对与状态等权表.md、03_时间转弯与阶段解释.md、review_packet、ledger及final_receipt。主对象为B=PPCPP＋直达，R仅诊断工具，P2为外部参照，不以追平P2为门槛。

先扫描31/54来源状态，按字典序与不同base优先冻结large_I/L/Z、medium_I/L/Z六p30切点。N从实际prep地图/目标、原生完整旧路及witness前缀重建，不拼入旧corner扩展任务；E只新增非目标通路障碍[0,1]，其余核心输入、H/S/来向/捕食者/基地/资源全部相同。六例均首个坐标单格合格，旧后缀严格内部受阻，剩余责任与基地仍可达。限定切点当场新增公开的快照，不模拟原已存在障碍探测、斜段停止或闭环。三形状/六base仍全是同坐标返航端阻断，且无small例，不能当多样内部瓶颈结论，不换例追收益。

12固定纯案例经1轮准备修复通过，首轮第4项合法旧分隔点被合并的问题及源码原样保留；固定身份12、两轮共16项尝试，真实技术/热身0。随后正式108处理槽=核心72（PPCPP36/P2 36）+R36；同快照N/E双方都真实处理，216原/直达视图全部独立通过、100%责任并返航，失败/触顶/迟到/未运行0。原生/修复20秒，post18软/4096/20迟到标记、父150秒未提高；OFF详细核心查询null，不伪造零。到上限停止，无补跑。

18组B增程均正，三seed状态等权平均0.402383米、相对平均0.554572%；范围0.337580–0.427828米，最大相对1.362373%。B_N/E完整trace、名义锚点、实际信用及末采相同，至最后锚点前缀逐点相同；保存阶段根式证明增量全部在返航标签内，转弯各增1次other。B原生N/E边数差0，R原生+2；R_E与B_E原生格路不同，经过共同直达后逐点相同18/18、ΔR=ΔB，不是路线收益或最优性证明。报告首草稿误把R原生+2归给B，已保留首版并仅凭保存指标修成报告v0.2，无求解/几何重跑。

B配对端到端时间变化均值+0.002734秒，中位+0.001378，范围−0.052332至+0.032388；不精确归因固定毫秒成本。R_E比B_E平均少0.016468秒但为同路线诊断，未宣布新改进算法。P2 N/E均自然完成有限流程，N已更短、E亦更短18/18；外部更短参照不是下界，不将E差距或流程环境交互差称障碍可避免损失。六例均第二档：有同条件更短参照，未定位PPCPP事件决策原因。未形成跨几何覆盖顺序缺陷线索，不建议新干预，也不宣称普遍无需重排或局部修复最优。

选例几何654合法性/6闭盒/648开内部相交、连通BFS6次（7866弹出/31464邻居）另计；正式R BFS18次（216弹出/864邻居），运行时旧边检测3888，未免费借选例证书。post候选10152、原边11516/输出10098、主虚拟合法性10098、独立post合法性10098，信用/距离/格心及纯桩两轮全账与未观测口径保存，不重复相加计数别名。108原返回/post/信用/独立回执、全部指标/三seed配对/阶段证书/正负图/来源冻结及哈希齐全。

只读verify核772旧来源、全部冻结和108回执，新增核心/R/post/几何/BFS0；旧内容保留。更新封存后停止交审，无新地图、新增区域方向、LAST/四方向/局部P2/首次竞争、新性能批、新闭环、留出、训练安装或推送。

---

'''
 (H/'root_pre_finalize.md').write_bytes(root.read_bytes());root.write_bytes(prefix.encode('utf-8')+before);(H/'root_after.md').write_bytes(root.read_bytes())
 l=read(H/'ledger.json');l['status']='complete_sealed_stopped_for_owner_review';dump(H/'ledger.json',l)
 packet=read(H/'review_packet.json');packet['status']='sealed_stopped_for_owner_review';packet['processing']=l;dump(H/'review_packet.json',packet)
 files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='final_receipt.json'}
 dump(H/'final_receipt.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed_stopped_for_owner_review','files':files,'file_count':len(files),'root_path':str(root),'root_sha256':sha(root),'saved_verify_receipt':receipt,'processing_entries':108,'core_entries':72,'R_entries':36,'views':216,'formal_failures':0,'new_calls_after_batch':{'core':0,'R':0,'post':0,'geometry':0,'BFS':0},'scope':'introduced-at-cut old-native-return blockage snapshots; no coverage-order defect established; no universal optimality claim'})
 print({'sealed':True,'files':len(files),'processing':108,'core':72,'R':36,'views':216,'root_updated':True,'stopped':True})
if __name__=='__main__':main()
