"""Saved-result tables, layered SVGs and seal; no graph computation."""
from run import H,R,OLD,read,write,sha
from collections import Counter
import time,html
def picture(r):
 c=r['input'];F=set(map(tuple,c['free']));T=set(map(tuple,c['targets']));P=set(map(tuple,c['published_targets']));HH=set(map(tuple,c['covered']));D=set(map(tuple,c['deferred_targets']));U=T-HH;Q=set(map(tuple,r['extraction']['Q'] or []));pred=set(map(tuple,r['extraction'].get('predicted_new',[])))
 xmin=min(x for x,y in F);xmax=max(x for x,y in F);ymin=min(y for x,y in F);ymax=max(y for x,y in F);step=min(430/(xmax-xmin+1),440/(ymax-ymin+1));svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="650"><rect width="1500" height="650" fill="white"/>',f'<text x="20" y="25" font-size="19">{r["id"]} — event U vs first-recovery Q</text>'];colors=['#e3a447','#ca69a4','#59a6c5','#aa9e45']
 for j,title in enumerate(('Event: supplied physical H / U','Same event + ACTUAL pre-event history','First recovery: PREDICTED prefix / Q')):
  bx=25+490*j;by=90;svg.append(f'<text x="{bx}" y="65" font-size="15">{title}</text>')
  def box(p):return (bx+(p[0]-xmin)*step,by+(ymax-p[1])*step)
  def center(p):
   a,b=box(p);return (a+step/2,b+step/2)
  for p in F|P:
   color='#eff2f5'
   if p in HH:color='#72b792'
   if p in U:color='#edc169'
   if p in D:color='#d96363'
   if j==2:
    if p in pred:color='#b0a0dd'
    for i,part in enumerate(r['Q_components'] or []):
     if list(p) in part:color=colors[i%len(colors)]
   a,b=box(p);svg.append(f'<rect x="{a:.2f}" y="{b:.2f}" width="{step:.2f}" height="{step:.2f}" fill="{color}" stroke="white" stroke-width=".4"/>')
  path=r['actual_pre_event_history'] if j==1 else r['extraction']['prefix'] if j==2 else []
  if path:
   pts=' '.join(f'{center(p)[0]:.2f},{center(p)[1]:.2f}' for p in path);color='#16784b' if j==1 else '#7250b0';svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
  for p,label in ((c['base'],'B'),(c['current'],'Xevent'))+(((r['extraction']['X'],'Xdecision'),) if j==2 and r['extraction']['has_recovery'] else ()):
   a,b=center(p);svg.append(f'<circle cx="{a:.2f}" cy="{b:.2f}" r="3" fill="#111"/><text x="{a+4:.2f}" y="{b-5:.2f}" font-size="11">{label}</text>')
  text=f"H={len(HH)} U={len(U)} D={len(D)}" if j<2 else f"Q={len(Q)} components={r['decision'].get('component_sizes')}"
  svg.append(f'<text x="{bx}" y="565" font-size="14">{html.escape(text)}</text>')
 svg.extend(['<text x="20" y="602" font-size="15">Green = actually completed before event. Purple = event-response native PREDICTION only.</text>','<text x="20" y="628" font-size="15">No new execution, alternative goal, connector path or benefit simulation. Colored Q components are not no-fly zones.</text></svg>']);write('figures/'+r['id']+'.svg','\n'.join(svg))
def finish():
 rows=read(H/'results.json');plan=read(H/'plan.json');W=read(H/'workload.json');reasons=Counter(r['decision']['reason'] for r in rows)
 for sid in plan['figures']:picture(next(r for r in rows if r['id']==sid))
 table=['|状态|基底/族/尺度/进度|事件U大小|首次恢复Q大小|q0|唯一最小片|机会/第一拒绝|旧原生阻断|旧实际post阻断|','|---|---|---|---|---|---|---|---|---|']
 for r in rows:
  e=r['extraction'];d=r['decision'];table.append(f'|{r["id"]}|{r["base_id"]}/{r["family"]}/{r["size"]}/{r["progress"]}|{r["U_sizes"]}|{d.get("component_sizes") if e["has_recovery"] else "无恢复/null"}|{e.get("q0")}|{d["S"]}|{d["reason"]}|{r["blockage"]["old_native_suffix_blocked"]}|未知|')
 write('18状态全表.md','# 18状态全表\n\n'+'\n'.join(table)+'\n\n分量按最小坐标排序，而非按大小排序；C编号不用于优选。每状态input/actual_pre_event_history/extraction及全部集合、代表距离、首拒绝后null见states/*.json。没有恢复的Q不填0。距离表在distance_rows，不含父指针或回溯路径。')
 summary=dict(states=18,base_geometries=len({r['base_id'] for r in rows}),event_U_fragmented=sum(len(r['U_sizes'])>1 for r in rows),has_first_recovery=sum(r['extraction']['has_recovery'] for r in rows),trigger_opportunities=sum(r['decision']['trigger'] for r in rows),first_reasons=dict(reasons),old_native_blocked=sum(r['blockage']['old_native_suffix_blocked'] for r in rows),old_actual_post_confirmed=0,old_actual_post_unknown=18,primary_rows=W['primary']['distance_rows'],independent_rows=W['independent']['distance_rows'],core=0,post=0,coverage_or_visibility_queries=0,controller_implemented=False,benefit_compared=False)
 write('summary.json',summary)
 write('00_通俗机会检查结论.md',f'''# 连续道路剩余连通片：固定机会检查

固定18个障碍快照、9个基底，各取旧OFF批rep=0/seed=20261020/PPCPP保存P0返回。新定义RESIDUAL_CC_TRIGGER_V1只将首次原生恢复时完整Q的四邻接分量称为“剩余连通片”，没有改持续控制器或旧矩形标签版规则。

结果：**触发机会0/18**。9例无恢复机会，8例恢复处只剩一个连通片，large_L_obstacle_p70有10格/2格两个片，原目标属于唯一2格最小片，但两个位置条件都不成立。不存在通过本次固定判据的状态；这不证明激活后无收益，也不是规则一般无效结论。

事件U分离5例，到首次恢复时这5例的Q全部只剩一片。反而large_L_obstacle_p70的事件U原为1片，在原生预测前缀后分为10+2。事件U与决策Q不能混用，预测采集不是新增实际执行H。

large_L_obstacle_p70的代表：R=(4,5)、S=(19,4)。返航等式要求9=16+23，实际不成立；严格条件要求19<3+16，实际为等号。这不是计数/默认目标门槛失败，不能移动基地或改不等号追触发。它是本批唯一到位置条件的状态。本批决策分量最多2片，未见3片以上碎裂；工程片区合理性仍未验证。

全部18个旧原生后缀经过新增阻塞格的数量为{summary['old_native_blocked']}；**旧实际直达计划受阻证据仍18例未知**。绑定的事件前prep只保存native raw，witness未给实际post阻断证书；事件后的post不用于反推。没有据此获得下一轮“真正受阻”收益比较资格。

主分析与独立审核各27次分量计算（U18、Q9）、各11个单源距离行，均在54行上限内；每侧访问16514格、邻接检查66056次。它们是新增图计算，不能写成图搜索全0。真实核心、公共post、新历史、新候选路线、覆盖搜索和几何可视查询均0；6个纯技术夹具通过。

图和全量证据：[18状态全表](18状态全表.md)、[分层图](地图入口.html)、[定义与证据边界](定义与证据边界.md)、[审核入口](review_packet.md)。固定政策不改，结果交负责人作研究取舍；不自动启动控制器、收益/速度比较或新图实验。未确认主算法或创新。
''')
 write('定义与证据边界.md','''# 定义和证据边界

旧版用事件前登记、原任务互不相接的矩形标签；新版只在首次原生恢复决策处，对完整尚未采Q做四邻接分量，ID按最小坐标。连续P不变，已采H/规划预测前缀不在Q；分量不是F的通行障碍，不合并/膨胀/八邻接，不把绝对少量假设说成已实现。

判定仍依次为至少两片、唯一最小片、q0属于S、各片B最近坐标平局代表、对所有R的精确返航等式与严格绕行不等式。X行单独核完整Q原最近目标；前置条件失败时未计算的S/代表/条件保持null。没有生成替代q_R、没有连接路径/父指针、没有完整路线评分。未来若做持续控制器，应在首次恢复冻结片标签和S而非每步重分；本轮没有实施它。

输入来自旧OFF批完整18个obstacle，不挑事件U分离5例。原native raw mode=PPCPP、selected=P0且只含P0；前缀与P0一致，initial_collect_here、完整Q、current/previous/pending_count逐条核。首次恢复及之前进入判据，之后的响应路线/末采/总距离/post均未用于判定。源输出整文件hash仅作来源绑定。

事件前H另核witness.history等于旧准备raw真实截断前缀，H逐格来自原目标与该前缀交集；图中实际历史和预测前缀分层。独立审核用另一套前缀扣除、并查集和分层波前距离，不使用主返回距离充作证明。距离字段只保存格到源的整数距离。

旧原生阻断只核输入old_route与新增阻塞格交集；不等价于旧实际post受阻。绑定prep无post字段，见证只给native障碍选择/可行性，不能将可行路线当实际直达路线。未知不记false，不放宽资格或补做线段查询。
''')
 gallery=''.join(f'<section><h2>{sid}</h2><img src="figures/{sid}.svg" style="width:100%"></section>' for sid in plan['figures'])
 write('地图入口.html','<!doctype html><meta charset="utf-8"><title>U与首次恢复Q</title><style>body{font:16px Microsoft YaHei,sans-serif;margin:24px;background:#eef2f6}section{background:white;padding:15px;margin:20px 0}</style><h1>实际历史与预测前缀分层</h1><p>绿：事件前实际H及历史线；紫：事件后原生预测采集及前缀线；Q彩色片不是禁飞区。按判定前固定的4例制图，未按触发结果挑选。</p>'+gallery)
 write('review_packet.md','''# 审核入口

先读[通俗结论](00_通俗机会检查结论.md)、[18状态全表](18状态全表.md)、[地图入口](地图入口.html)、[定义与边界](定义与证据边界.md)。plan/index在任何判断前固定18输入、政策、源hash、预算与4图选择；tests.py为最多6个预定夹具，无真实核心。states内保存输入、实际历史、只到首次恢复的预测前缀与trace、Q/分量/全部条件及未知阻断证据；distance_rows保存两套独立距离行，不含路径。

workload分主分析/独立分量和距离计算次数、访问量、邻接检查、时间；核心/post/候选路线/几何可视为0，不掩盖新图计算。纯夹具图集合另算不纳正式18，固定关系测试没有图距离行。

verify.py为只读hash/根链/保存两套距离结果一致/行预算与条件算术核验，不新做分量、距离或几何查询；真正语义独立审核在本轮运行中完成并保存。无触发意味着本固定定义+判据的适用性证据不足，不回答激活收益、速度、创新。完成即止，后续由负责人裁决。
''')
 before=(H/'root_before.md').read_bytes();assert (R/'当前进度与下一步.md').read_bytes()==before
 progress='''# 最新进度：连续道路剩余连通片固定触发机会检查封存（2026-10-23）

连续道路剩余连通片触发机会检查_v0.1_20261023 已按稿完成并停止。RESIDUAL_CC_TRIGGER_V1定义为首次原生恢复处完整预测剩余Q的四邻接分量，独立于旧原始矩形标签，不改持续控制器。全部18个obstacle固定OFF/PPCPP/rep0/seed20261020保存P0返回纳入，来源与真实H、initial_collect_here、前缀和每条trace语义核验通过，无效果选例。

机会0/18：9例无恢复、8例首次恢复只剩一片、large_L_obstacle_p70两片10+2但位置条件失败（9≠16+23、19=3+16而非严格小于）。事件U分离5例在首次恢复Q均只一片；large_L_obstacle_p70则由事件U一片变为预测Q两片，不能混用时刻/把预测采集算实际H。未临时合并碎片或放宽条件。不能据零触发推激活后无收益、一般无效或创新成立。

主与独立各27次分量、11单源距离行/16514访问格/66056邻接检查，低于各54行上限；独立采用并查集与波前距离，6纯夹具通过。真实核心/post/新历史/候选路线/覆盖搜索/几何可视查询全部0，但新增格图计算非0。旧原生后缀阻断与旧实际post阻断分栏，后者18例未知，未用事件后post反推、未加可视查询补证，因此不自动取得真正受阻收益比较资格。

入口00_通俗机会检查结论.md、18状态全表.md、地图入口.html、定义与证据边界.md、review_packet；18状态输入/实际历史/预测截断、条件和两套无父指针距离行、计账/hash/verify封存。旧来源/final不改，根仅追加，交负责人决定固定定义取舍；不启动控制器、收益比较或新地图，不追触发。

---

'''
 after=progress.encode()+before;(R/'当前进度与下一步.md').write_bytes(after);(H/'root_after.md').write_bytes(after)
 from verify import verify
 write('preseal_verify.json',verify(False));files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('final_receipt.json','verify_receipt.json')}
 write('final_receipt.json',dict(status='fixed_definition_opportunity_check_complete_stopped',files=files,root_sha256=sha(R/'当前进度与下一步.md'),summary=summary,utc=time.time(),auto_next=False));v=verify();v['final_receipt_sha256']=sha(H/'final_receipt.json');write('verify_receipt.json',v);print(json.dumps(v,ensure_ascii=False,indent=2))
if __name__=='__main__':finish()
