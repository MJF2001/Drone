from common import *
import sys,subprocess,datetime
def main():
 assert not (H/'final_receipt.json').exists()
 root=ROOT/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();assert root.read_bytes()==before,'root independently changed; do not overwrite'
 for x in read(H/'usable_snapshots_v02.json')['selected']:
  folder=(H/x['N']).parent
  (folder/'README.md').write_text('''# 该快照仅用于选例交审

有效配对为N.json与E_contract_v02.json，入口清单见包根usable_snapshots_v02.json。初版E.json仅改F，尚未按已采障碍格派生active targets，不可直接投入算法；它和首轮freeze.json为来源审计原样保留。

v02仅使T=P∩F、D=P−F−H，P/H/初始未采U及所有其他状态不变，几何域未变、证书复用且无重跑。阻断证书见certificate.json；来源/责任契约及新hash见contract_certificate_v02.json、contract_freeze_v02.json。本轮未运行PPCPP/P2/R/直达或性能批。
''',encoding='utf-8')
 packet=read(H/'review_packet.json');packet['compare_previous_return_case']='Previous six choices [0,1] blocked only after each old suffix last first-service; these new edges61/30 precede last205/78 with141/46 pending.'
 packet['status']='sealed_selection_only_stopped_for_owner_review';dump(H/'review_packet.json',packet)
 l=read(H/'ledger.json');l['status']='sealed_selection_only_stopped_for_owner_review';dump(H/'ledger.json',l)
 qa=read(H/'figure_qa.json');qa['both_final_v02_figures_viewed']=True;dump(H/'figure_qa.json',qa)
 r=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'verify.py'),'--preseal'],capture_output=True,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
 receipt=json.loads(r.stdout);dump(H/'verify_receipt.json',receipt)
 prefix='''# 最新完成：覆盖阶段真实受阻选例核查封存（2026-10-23）

覆盖阶段受阻选例核查_v0.1_20261023 已按稿仅完成选例与核验，无PPCPP/P2、核心、R修复、候选覆盖路线、直达或性能批，未重跑旧108。先读00_通俗选例核查结论.md、01_全扫描分类账与索引.md、02_可用快照与阻断证书.md、usable_snapshots_v02/review_packet、ledger及final_receipt。

按ID考虑54来源标签/9基础几何，44个后缀详细分类、对应16物理切点；large_Z、medium_Z首次合格后按base冻结，后续10个同base标签跳过、不当负例，未判其余进度可选与否。取得2个不同base均为Z族，未凑6，不作跨形状复现。large_Z_corner_p30障碍[26,28]，原H前缀见证54，旧后缀失效边61/62、起点仍141个未完成，末次服务顶点205；medium_Z_corner_p30障碍[14,15]，原H见证29，边30/31、仍46个未完成，末次服务78（全0基）。二者各首个单格即合格、严格内部相交非贴角、S/基地合法、全部初始剩余责任和基地仍可达，是真覆盖阶段受阻，区别于上一批[0,1]末采后返航端。

42个不合格标签=I18/L18/small_Z6，共14物理切点：覆盖仍至少2未采时，旧单位格心边能穿内部的端点格均为初始未采任务或S，没有符合身份的已采/非目标阻断格，单格/相邻双格池均空；不是20次不够、不可达拒绝或算法表现结论。返航端和仅剩1目标的边单列，不用填充新清单。六个需放宽遮挡才可使用的未采格仅作文字身份注记，无E构造/几何/BFS，不自动放宽任务责任。

N追溯实际prep公开F/目标/完整原生路线及采用前缀，H不扩大，不拼旧扩展后任务。新障碍均为原已采目标格，P/H/未采U不变；按现有T=P∩F、D=P−F−H契约，E active T分别288→287、108→107，U201/75不变、D空，其余状态/资源不变。初次E仅改F导致active T未规范化，初版E.json及冻结原样保留，不可投入算法；另存E_contract_v02.json和新契约/冻结，正式可用索引以usable_snapshots_v02.json为准。自由域/U未变，未重跑几何/BFS或换障碍；不是删未采任务换短路线。

选例真实计账：独立合法性2163（N旧边2157+候选域复核6），闭禁飞盒2、严格内部相交4，连通BFS2（弹出4006/邻居16024）；2候选合格、不可达拒绝0、上限耗尽0、源缺口0。事前各状态≤20候选、全部≤54、至多6base上限及几何/BFS预算保留，不称零计算。两套快照/源hash/逐任务首次服务与逐边计数、两张旧后缀图和首图版、全分类/费用及冻结齐全。

只证明当前隔离条件下覆盖阶段受阻样本存在，未评价新路线资源/速度、未验证算法响应或顺序改进，更不证明需要重排。只有两尺度Z，I/L无候选不等于算法优秀或障碍方向失败。只读verify核120旧来源和所有冻结/契约/索引回执，新增核心/R/post/几何/BFS0；旧包不覆盖。封存停止交审，不自动B/R/P2比较，不扩图/放宽遮挡/追加预算或seed，无新闭环、留出或推送。

---

'''
 (H/'root_pre_finalize.md').write_bytes(root.read_bytes());root.write_bytes(prefix.encode('utf-8')+before);(H/'root_after.md').write_bytes(root.read_bytes())
 files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='final_receipt.json'}
 dump(H/'final_receipt.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed_selection_only_stopped_for_owner_review','files':files,'file_count':len(files),'root_path':str(root),'root_sha256':sha(root),'verify_receipt':receipt,'qualified_distinct_bases':2,'qualified_shape':'Z only','N_E_valid_input_index':'usable_snapshots_v02.json','new_algorithm_core_R_candidate_coverage_route_shortcut_performance_calls':0,'geometry_and_BFS_saved_counts':read(H/'scan_results.json')['counts'],'no_automatic_comparison_batch':True})
 print({'sealed':True,'files':len(files),'selected':2,'algorithm_R_post_performance':0,'root_updated':True,'stopped':True})
if __name__=='__main__':main()
