"""Reports from saved endpoint-bound certificates only, no geometry."""
from pathlib import Path
from collections import Counter
import json,shutil
H=Path(__file__).resolve().parent;R=H.parent;A=R/'任意方向直达收益结构只读归因_v0.1_20261022';S=10**60
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def md(n,s):(H/n).write_text(s,encoding='utf8')
def show(v):return f'{(v[0]+v[1])/(2*S):.6f}'
def main():
    rs=read(H/'117路线固定顺序下界.json');ps=read(H/'57配对顺序限制证书.json');ms=read(H/'多段区间全量表.json');ss=read(H/'分批核验汇总.json');allparts=read(H/'全部锚点区间下界.json');prior=read(A/'57配对成本位置与等长证据.json')
    assert {(p['batch'],p['case']) for p in ps if p['sign']=='positive'}=={(p['batch'],p['case']) for p in prior if p['interval_sign']=='positive'}
    st='|批次|方法|路线数|锚点区间|单边/多边|保存L合计|下界B合计|L−B松上限量≈|固定顺序最优路线|\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for s in ss:st+=f"|{s['cohort']}|{s['method']}|{s['routes']}|{s['parts']}|{s['single_edge_parts']}/{s['multi_edge_parts']}|{show(s['L_ticks'])}|{show(s['B_ticks'])}|{show(s['improvement_cap_ticks'])}|{s['fixed_order_optimal_routes']}|\n"
    p0=next(s for s in ss if s['cohort']=='54_states' and s['method']=='PPCPP');p2=next(s for s in ss if s['cohort']=='54_states' and s['method']=='P2_MULTI');seq_count=Counter((p['batch'],p['actual_sequences_different']) for p in ps)
    md('00_通俗结论.md',f'''# 固定采集顺序连接下界核验

本轮零求解核验证明：本固定批中，继续强化连接并不能消除多数PPCPP相对现有P2参照的差距。117条路线、8098个锚点区间、57配对全部完成；两套独立算术复核通过，没有同顺序证据矛盾。

54批PPCPP共3462个锚点区间，仅6个输出多边段。固定原实际采集顺序后，进一步可改善量的合计上限不超过 **{p0['improvement_cap_interval'][1]}**（约6.586187）；这不是已找到的收益。48/54条已取得固定实际顺序最优证书，另6条未确认最优。P2相应49/54条已认证，上限约4.343146。六世界PPCPP六条全部已取得各自固定顺序最优证书；P2仅按认可三配对记录，2/3条已认证。

54配对中44组严格认证B_PPCPP>L_P2，且实际服务顺序不同；这正覆盖目前PPCPP严格长于参照的44组。六世界认可的三组也全部通过。故这些例子中任何保持该PPCPP实际首次采集顺序的合法路线都无法达到已保存P2路线的长度。其余10组判为非正，仅表示这一下界证书未排除追平，不代表一定能追平或已证明顺序最优。

'''+st+'''
这里B是“当前点→原实际首次服务序列→基地”的相邻端点欧氏距离和，仅作为下界，未生成路线。障碍和严格信用顺序可以使B不可取到；忽略这些限制只会使下界更松，不破坏B≤F≤L。F是相同顺序、任务/历史、端点、信用、几何及剩余距离额度下的最优下确界。若保存合法路线的每个区间均为共线同向，实际取得B，才给出固定顺序最优证书。

全量12个多边区间都在采集间；本批所有PPCPP返航区间已是单条保存合法边，固定末采集位置后没有进一步返航连接改善空间。这个结论不代表更换末采集位置能省去整个返航差，也没有测新顺序算法在共同预算内能否找到P2参照。

唯一后续建议：进入服务顺序（含末次位置）层面的机制设计前审查，先核对与旧尝试的具体差异，再决定是否值得另行实验。本轮不选LAST、不实现或运行新算法，不作全局覆盖最优或完整几何/顺序损失分解。冻结源、旧包及留出不变，封存停止，交负责人审核。
''')
    table='|ID|B≈|L≈|进一步改善上限量≈|区间/单边/多边|固定实际顺序最优|\n|---|---:|---:|---:|---|---|\n'
    for r in rs:table+=f"|{r['id']}|{show(r['B_ticks'])}|{show(r['L_ticks'])}|{show(r['improvement_cap_ticks'])}|{r['parts']}/{r['single_edge_parts']}/{r['multi_edge_parts']}|{'是' if r['fixed_actual_order_optimal_certificate'] else '未认证'}|\n"
    md('01_117路线与下界方法.md','''# 117路线与下界方法

全表原始锚点序列、实际首次服务序列、B与L的认证区间、L−B包络、原剩余距离额度E和精确等长证明见117路线固定顺序下界.json；CSV便于读取，以下小数仅为近似展示。实际改善量属于[0, L−B的认证上端]，并不以L−B区间的下端作为“保证能省的量”。非零包络均是松上限，不承诺可实施。

主分析采用10^60尺度整数平方根向外有理包络；独立verify采用80位Decimal平方根的向外区间求和，另以不同的逐边向量判定复核主分析的点投影共线单调证据。两者不相互导入；非等长的上下界由独立区间重新计算，不是仅读passed字段。几何合法性沿用哈希绑定的原独立回执，本轮不重做任何可视/碰撞或采集交点扫描。仅对已保存信用时刻作坐标算术核对。

原资源仍为输入剩余E，未重置；每条保存L≤E，所以该路线提供F≤L的可行证据，B下界仅放松几何连接，不放松指定任务、实际顺序或端点。相同顺序下起点即时信用、空任务返航、零长锚点均有定义；真实批没有起点新信用或空任务，未补造样本。

单边区间自动等于其端点距离；多边也逐点检查共线同向，不能凭“多边”就说可改善。所有8098区间均核对原索引和输出边范围；105条取得固定实际顺序最优证书，12条未认证。

'''+table)
    ptable='|批次|状态|B_PPCPP−L_P2≈|区间判定|实际序列不同|严格顺序限制证书|\n|---|---|---:|---|---|---|\n'
    for p in ps:ptable+=f"|{p['batch']}|{p['case']}|{show(p['B_PPCPP_minus_saved_L_P2_ticks'])}|{p['sign']}{'(精确等长补证)' if p['exact_equal_by_squared_multiset'] else ''}|{'是' if p['actual_sequences_different'] else '否'}|{'是' if p['strict_order_restriction_certificate'] else '无'}|\n"
    md('02_57配对顺序限制证书.md',f'''# 57配对顺序限制证书

54状态与六世界认可三配对分列；I_S、I_M、T_S仅单条描述，不与另一方法强配。逐对核对F/P/H/targets/D、current/previous/base及原剩余额度完全相同，并检查保存实际首次服务序列。

54组正/非正/未确定为44/10/0；六世界三组为3/0/0。54组实际序列不同{seq_count[('54_states',True)]}、相同{seq_count[('54_states',False)]}；六世界三组均不同。若同顺序出现正证书，程序会抛出证据矛盾而停止。本批没有该矛盾。

原large_I_obstacle_p70的严格端点下界与P2保存长度亦有相同平方值多重集合的等长证据，列入非正而非用显示浮点0判等；原跨零记录未改。逐对原始区间和等长依据在57配对顺序限制证书.json。

正证书的含义严格限定为：任何保留这条PPCPP实际首次服务顺序的合法路线，长度至少B_PPCPP，且严格大于已经保存的合法P2参照L_P2；若要达到该参照，必须改变实际服务顺序（包括可能改变末次位置），或改变本轮模型。这个必要条件不证明只调整末采集格就够，也不证明某种新顺序搜索能在预算内实现。

'''+ptable)
    mt='|ID|段号/类别|原锚点|保存多段顶点|L≈|B≈|L−B上限量≈|共线同向|\n|---|---|---|---|---:|---:|---:|---|\n'
    for p in ms:mt+=f"|{p['id']}|{p['part']}/{p['kind']}|{p['anchor_a']}→{p['anchor_b']}|{p['saved_output_vertices']}|{show(p['L_ticks'])}|{show(p['B_ticks'])}|{show(p['improvement_cap_ticks'])}|{'是' if p['exact_equal_by_collinear_forward'] else '否'}|\n"
    md('03_多段区间全量.md','''# 多段区间全量

共12个多边锚点区间：54批PPCPP6、P2五，六世界PPCPP六条合计0，认可P2三条合计1。54批每方法3462区间；六世界PPCPP六条共684（认可三条490、非配对三条194），P2三条490。与负责人探索性计数一致，松上限量的6位展示也分别为6.586187及4.343146。

这些区间的保存多段均不共线同向，故本轮未认证其取得端点下界；不进一步判定端点直线是否受障碍阻挡。表中的坐标仅是已有顶点和锚点定义，不是新增直线或替代输出。即使L−B较大，也只提供剩余可改善量的上限。

'''+mt)
    md('review_packet.md','''# 审核入口

00_通俗结论.md为结论与唯一后续建议；01_117路线与下界方法.md给全量路线及B≤F≤L的含义；02_57配对顺序限制证书.md逐对列示正/非正/未确定及序列核对；03_多段区间全量.md不遗漏全部12多段区间。

完整机器证据：117路线固定顺序下界.json/CSV（含锚点序列与资源）、全部锚点区间下界.json、多段区间全量表.json（含保存顶点）、57配对顺序限制证书.json、分批核验汇总.json、来源hash.json、零求解调用账.json。主分析输出采用整数平方包络；verify.py独立以80位向外Decimal区间和逐边向量证据重算。

只读核验.ps1只运行本包独立verify，核对来源及本包封存清单、全部117路线、8098区间、57对和证书；不导入生产或几何模块，不运行原后处理或旧verify，不产生路径。锚点欧氏量是算术下界，可不合法，不是执行的新直达路线。

新增规划/核心/图搜索/可视/后处理/候选/新路线/反事实均0。旧包、冻结算法及留出不改，未提交推送。资源保留原剩余E，未放宽；105固定顺序最优证书不是全局覆盖最优，也没有求完整几何/顺序损失分解。本轮完成封存停止，不自动选LAST或实现下一算法。
''')
    shutil.copyfile(R/'任意方向固定采集顺序连接下界核验执行稿_给sol_20261022.md',H/'执行稿原文快照.md')
    print(json.dumps({'reports_written':True,'owner_initial_counts_confirmed':True,'strict_order_certificates':sum(p['strict_order_restriction_certificate'] for p in ps),'new_queries':0},ensure_ascii=False))
if __name__=='__main__':main()
