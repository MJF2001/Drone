from pathlib import Path
import csv, hashlib, json, subprocess, collections

ROOT = Path(__file__).resolve().parents[4]
SUP = Path(__file__).resolve().parent
ALGO = ROOT / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
DIAG = ALGO / "continuous_history_diagnostics"
RUN = DIAG / "old_plan_warm_global_v0.1_20261017"
BEFORE = SUP / "source_manifest_before.json"
HANDOFF = ROOT / "交给主会话验收_补证与范围检查_20261017.md"
REPORT = SUP / "验收补证与范围规则检查报告_20261017.md"
FENCE = chr(96)*3

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def rel(path):
    return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()

def fmt_cell(x):
    if not x: return "—"
    return f"({x[0]}, {x[1]})"

def compressed(indices):
    if not indices: return "无"
    xs = sorted(set(int(x) for x in indices))
    spans=[]
    a=b=xs[0]
    for x in xs[1:]:
        if x==b+1: b=x
        else:
            spans.append(str(a) if a==b else f"{a}–{b}")
            a=b=x
    spans.append(str(a) if a==b else f"{a}–{b}")
    return ", ".join(spans)

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if HANDOFF.exists():
    raise SystemExit(f"Refusing to overwrite existing handoff: {HANDOFF}")

# Remove only the three temporary render-QA screenshots after visual inspection.
figdir = SUP / "figures"
for name in ("large_g1_render_check.png", "large_g1_development_render_check.png", "large_g3_development_render_check.png"):
    p = figdir / name
    if p.exists():
        p.unlink()

# Rehash the exact initial 424-path source manifest without changing it.
before = load_json(BEFORE)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
source_checks=[]
for path_text, expected in before["files"].items():
    path=ROOT / Path(path_text)
    actual=sha(path) if path.is_file() else None
    source_checks.append({"path":path_text,"expected_sha256":expected,"actual_sha256":actual,"matches":actual==expected})
source_mismatches=[r for r in source_checks if not r["matches"]]
source_after={
    "created_date":"2026-10-17",
    "baseline_manifest":rel(BEFORE),
    "baseline_HEAD":before["HEAD"],
    "current_HEAD":head,
    "head_unchanged":head==before["HEAD"],
    "checked_file_count":len(source_checks),
    "all_match":not source_mismatches,
    "files":source_checks,
    "mismatches":source_mismatches
}
write_json(SUP/"source_manifest_after.json",source_after)

# Independently verify the original run's 416-entry delivered-file manifest.
old_manifest_path=RUN/"deliverables_sha256.json"
old_manifest=load_json(old_manifest_path)
old_checks=[]
for path_text, expected in old_manifest.items():
    path=ROOT / Path(path_text)
    actual=sha(path) if path.is_file() else None
    old_checks.append({"path":path_text,"expected_sha256":expected,"actual_sha256":actual,"matches":actual==expected})
old_mismatches=[r for r in old_checks if not r["matches"]]
old_hash_record={
    "created_date":"2026-10-17",
    "source_manifest":rel(old_manifest_path),
    "expected_entry_count":len(old_manifest),
    "all_match":not old_mismatches,
    "files":old_checks,
    "mismatches":old_mismatches
}
write_json(SUP/"old_evidence_sha256_20261017.json",old_hash_record)

# Update the seven-point acceptance matrix's delivery row after final checks.
matrix_path=SUP/"acceptance_evidence_matrix_20261017.csv"
with matrix_path.open(encoding="utf-8-sig",newline="") as f:
    matrix=list(csv.DictReader(f))
for row in matrix:
    if row["item"]=="C delivery/hash/hand-off":
        row["status"]="pass"
        row["evidence"]="source_manifest_after.json: 424/424 initial paths match; old_evidence_sha256_20261017.json: 416/416 delivered paths match; new_evidence_sha256_20261017.json covers the supplement and handoff; handoff created at the reserved path."
with matrix_path.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(matrix[0]))
    w.writeheader()
    w.writerows(matrix)

details=load_json(SUP/"range_details_final.json")
states=details["states"]
with (SUP/"literal_r_plus1_results.csv").open(encoding="utf-8-sig",newline="") as f:
    literals=list(csv.DictReader(f))

state_rows=[]
for s in states:
    e=s["event_analysis"]
    obs_sizes=[len(c["cells"]) for c in e["obstacle_components"]]
    explicit=len(e["explicit_deferred_targets"])
    removed=len(e["removed_initial_targets"])
    state_rows.append(
        f"| {s['map_id']} | {s['event']} | {fmt_cell(s['current'])} / {fmt_cell(s['base'])} | "
        f"{s['case_sha256'][:12]}… | {s['old_route_steps']} / {s['covered_history_count']} / {s['pending_target_count']} | "
        f"{e['active_added_target_count']} / {e['active_added_targets_requiring_new_route_visit_count']} | "
        f"{explicit} / {removed} | {', '.join(map(str,obs_sizes)) if obs_sizes else '无'} | {compressed(e['old_route_blocked_indices'])} |"
    )

# Compact display of the 40 saved R_PLUS1 results; seed and repeat remain separate in the CSV.
result_rows=[]
for map_id in [s["map_id"] for s in states]:
    chunks=[]
    for budget in ("1","20"):
        rows=[r for r in literals if r["map_id"]==map_id and r["budget_seconds"]==budget]
        counts=collections.Counter((r["core_steps"],r["final_steps"],r["final_source"]) for r in rows)
        parts=[]
        for (core,final,source),n in sorted(counts.items(), key=lambda x:(int(x[0][0]),x[0][2])):
            parts.append(f"{core}/{final}步×{n} {source}")
        chunks.append(f"{budget}s：{'; '.join(parts) if parts else '无'}")
    result_rows.append(f"| {map_id} | {'<br>'.join(chunks)} |")

range_summary=[]
for s in states:
    parts=[]
    for r in s["ranges"]:
        c=r["cfg"]
        alias=f"（= {r['alias_of']}）" if r["alias_of"]!=r["name"] else ""
        parts.append(f"{r['name']}{alias} [{c['left']},{c['right']}]")
    range_summary.append(f"| {s['map_id']} | {'；'.join(parts)} |")

explicit_by={s["map_id"]:len(s["event_analysis"]["explicit_deferred_targets"]) for s in states}
removed_by={s["map_id"]:len(s["event_analysis"]["removed_initial_targets"]) for s in states}
missing_explicit=sum(removed_by[k]-explicit_by[k] for k in removed_by)
explicit_total=sum(explicit_by.values())
removed_total=sum(removed_by.values())
new_total=sum(s["event_analysis"]["active_added_target_count"] for s in states)
need_total=sum(s["event_analysis"]["active_added_targets_requiring_new_route_visit_count"] for s in states)
assert len(states)==10 and len(literals)==40
assert explicit_total==27 and removed_total==33 and missing_explicit==6 and new_total==1925 and need_total==1925
assert all(not s["event_analysis"]["active_added_targets_on_old_remaining_route"] and s["event_analysis"]["active_added_at_current_count"]==0 for s in states)

cross=details["cross_batch_summary"]
timeline=load_json(SUP/"execution_timeline_20261017.json")
errata=load_json(SUP/"audit_summary_errata_20261017.json")
source_after=load_json(SUP/"source_manifest_after.json")
old_hash_record=load_json(SUP/"old_evidence_sha256_20261017.json")
literal_global_fallback=sum(r["global_common_fallback"]=="True" for r in literals)
literal_local_fallback=sum(r["scope_core_common_fallback_internal"]=="True" for r in literals)
literal_old_suffix=sum(r["final_source"]=="old_suffix" for r in literals)
assert literal_global_fallback==0 and literal_local_fallback==4 and literal_old_suffix==4
assert source_after["all_match"] and source_after["head_unchanged"] and old_hash_record["all_match"]
assert len(source_after["files"])==424 and len(old_hash_record["files"])==416

obstacle_state_lines=[]
for s in states:
    e=s["event_analysis"]
    if e["obstacle_components"]:
        blocked=e["old_route_blocked_indices"]
        roles=sorted({role for idx_roles in e["blocked_route_index_roles"] for role in idx_roles.get("roles",[])}) if e["blocked_route_index_roles"] else []
        split=e["same_component_separated_route_effects"]
        split_text="；".join(
            f"{x['left_route_span']['start']}→{x['right_route_span']['start']}：索引差{x['route_index_gap']}，中间首检任务{x['intervening_first_hit_task_count']}，曼哈顿/事件前BFS={x['minimum_manhattan_map_distance']}/{x['minimum_pre_event_free_graph_distance']}"
            for x in split
        ) or "同一组件未产生多个分离的旧路线接触段"
        obstacle_state_lines.append(
            f"- {s['map_id']}：障碍组件格数{[len(c['cells']) for c in e['obstacle_components']]}；"
            f"旧路线受阻索引 {compressed(blocked)}；作用标签 {', '.join(roles) if roles else '见JSON逐索引记录'}；{split_text}。"
        )
    else:
        obstacle_state_lines.append(f"- {s['map_id']}：无新增障碍格，旧剩余路线未被障碍阻断。")

results_table="\n".join(result_rows)
state_table="\n".join(state_rows)
range_table="\n".join(range_summary)
obstacle_lines="\n".join(obstacle_state_lines)
matrix_rel=rel(matrix_path)
head=source_after["current_HEAD"]

report=f"""# 第70份验收补证与10状态范围规则检查

日期：2026-10-17  
审查基线 HEAD：{head}

本报告完成执行稿 A1–A5 补证及 B1–B4 离线检查。B 阶段只读取既有输入、旧路线和保存结果；**规划器调用 0 次**。本报告是交付给主会话评审的证据，不替代主会话最终验收，也不据此选择后续机制。

## A. 验收补证

| 执行稿项目 | 状态 | 证据与结论 |
|---|---|---|
| A1 既有独立验收 | 通过 | 新只读检查复核 120/120 路线、40/40 热启动序列、40/40 LITERAL 核心，并重算 120 项矩阵；416 项旧交付清单复核通过。 |
| A2 独立只读入口 | 通过 | verify_acceptance_range_20261017.py --check 输出 PASS；5 个篡改夹具测试通过，能检出序列遗漏、核心前后缀改变、重复成功和哈希损坏。 |
| A3 回归与预检证据 | 部分闭合 | 25 项回归事后重跑通过，实际调用范围规划引擎 7 次；另 5 次合成微型 warm/P2 调用覆盖关闭 warm 对照、空任务返航、非法/不可行输入、截止中断和已接受候选保留。共 12 次合成规划器调用，0 次正式地图调用。6 次正式预检仅在 completion_final.json 留有总数，缺少逐次输入、结果和日志；原多地图关闭 warm 日志未找到，因此不声称历史证据已恢复或完整对照已证明。 |
| A4 勘误与执行偏离 | 通过（有限制） | 原 audit_summary.json 保留不改；勘误只替换其 protocol_deviations 计数：初批异常 13 次、恢复1异常 64 次（原文 10/60 不再采用）。197 次尝试中有 120 个唯一有效结果，无重复成功；恢复2完成全部40条 LITERAL，预定方法轮换曾中断。17 项保护哈希中仅运行器 run_p2_warm_global_20261017.py 不匹配，事后哈希不能证明进程启动时加载的字节。 |
| A5 进入 B 的门槛 | 通过并披露 | 未发现冻结输入损坏、保存路线非法或 LITERAL 核心/责任分配与独立重建不符；A3 缺口和运行器哈希例外已披露，故继续 B。 |
| B1–B4 十状态检查 | 通过 | 10 个状态、40 个范围行和40条 R_PLUS1 记录独立重建；详细事件、边界、责任、拼接、路线结果见机器数据。 |
| C 交付与哈希 | 通过 | 初始源清单424/424匹配，旧交付文件416/416匹配；新证据清单覆盖本补充目录和本交接稿。 |

warm 计算路径的源代码在每轮 pass 和候选交换前检查截止时间；接受交换后再计算整条服务序列的 sequence_cost。计算消耗预算，且可能触发截止；日志中40次 warm 调用共记录76次交换，每次都有完成的序列成本记录。预算1秒组有10次无改进结束、10次截止；预算20秒组有16次无改进结束、4次截止。后续 warm expand 分别有10次和4次因截止跳过。没有 profiler 隔离这些操作的耗时，不能给出开销百分比。

69/70 相同输入的80个配对全部有耗时差异；14个配对路线步数、路线内容、来源/阶段状态发生变化，另有8个配对仅阶段日志变化。large_g1、20秒：69号 P2/LITERAL 为941/939步，70号为1073/941步，warm为1243步；70号 P2 在 H_scan_opt 截止、warm 在 warm_optimize 截止。P2 和 LITERAL 同样跨批变化，因此该差值不能归因于 warm，也没有证据归因于特定 CPU 或负载。

## B. 十个事件后状态

来源为第70号协议复用的 preparation_verification_v0.1_20261016/cases 和对应 preflight_v0.1_20261016/initial_cases；完整路径、协议路径及 SHA256 见 range_details_final.json 与 state_overview.csv。每个状态共用两预算、两种子的历史状态，不计作40张不同地图。

| map_id | 事件 | 当前 / 基地 | 事件后输入 SHA256 | 旧路线步 / 已检历史格 / 当前待检格 | 新增活动目标 / 必须新安排访问 | 显式暂缓 / 初始目标移除 | 障碍组件格数 | 旧路线受阻索引 |
|---|---|---|---|---:|---:|---:|---:|---|
{state_table}

合计新增活动目标1,925格，全部需要新路线访问；没有新增目标落在旧剩余路线或当前位置。已检历史保留，新增目标不按事件前经过位置追溯记为已检。初始目标中有33格因事件障碍移除，27格也在输入 deferred_targets 中明确列出；另6格未显式标记（large_g4 5格、small_g4 1格），均保留为“已移除初始目标/障碍格”，不冒称显式暂缓。新目标、遮挡/暂缓和历史覆盖分账见机器细节。

### 障碍对旧路线的直接影响

{obstacle_lines}

上述受阻路线访问均被独立标为 connection；没有首检服务格或末服务后的返航格被强行归入受阻服务。large_g3 和 large_g4 的多个受阻片段分别来自同一个9格障碍组件，并非多个障碍组件合并；片段间事件前自由图最短距离与曼哈顿距离均为1，夹有已计划首检任务。全部逐段路线索引、夹入任务坐标及图距离见 range_details_final.json 的 same_component_separated_route_effects。

### 范围形成规则与保留代价

| map_id | 四种路线索引范围（闭区间） |
|---|---|
{range_table}

范围边界按旧路线序号表达，range_boundaries.csv 另列起点/接回格、前缀/后缀步数、窗口负责目标数、可改旧服务块数/比例，以及每个纳入服务块的实现规则来源。空间地图图和路线序列图区分呈现于 figures/index.html 的10张 SVG。

独立重建所得规则为：R_SEED 把受阻接触包络及新增连通块的最近可达旧路线接入锚点纳入一个区间；接入距离并列时按旧路线索引较小者打破平局；多个片段/组件取单区间包络。R_PLUS1/R_PLUS2 向外扩一/两个服务块边界，并按合法端点向外闭合；R_ALL 为完整旧路线 [0,N]。这描述实现规则的纳入原因，不证明范围在数学上最小或最优。

R_SEED 的单区间连带纳入在 large_g2 为1块/13项旧任务、medium_g1 为27块/108项、medium_g2 为14块/112项；这些没有直接障碍接触的服务块属于包络连带。只有 large_g1 和 medium_g2 的 R_PLUS2 与 R_ALL 完全重合；其余状态仍保留部分旧路线前后缀或旧服务块。medium_g4、small_g2、small_g3 的 R_SEED 可改旧服务块为0，但窗口仍分别负责132、25、30个新增目标，不能称为零重排任务。没有搜索多窗口、替代锚点或最优范围。

### 保存的 R_PLUS1 局部结果

40/40 记录都有合法核心、有效 patch 结构、有效最终拼接；核心范围与独立重建一致，责任分配一致；每一条最终步数等于其核心路线步数。全局 common fallback 为0条；其中4条来源名称是 scope_core:common_fallback（这是局部核心内部初始化），4条来自 old_suffix（均为 small_g4）。来源和种子/重复的逐行结果如下；其他三个范围没有本批求解成绩。

| map_id | 保存的 R_PLUS1 核心/最终步数与来源（按预算、重复压缩显示） |
|---|---|
{results_table}

## 仍未证实的事项与可供主会话决定的问题

- 原多地图 warm-off 对照、6次正式 smoke preflight 的逐次记录仍无法恢复；本次微型事后回归不替代原始证据。
- 没有同一进程开跑时源码快照；运行器协议哈希差异的具体生效时点不确定。没有剖析数据，不能量化额外时间检查/整序列成本占比。
- 当前范围只按实现规则诊断；“哪些任务最少必须重排”、单区间是否优于多窗口、哪种范围能缩短完整路线都未被此检查证明。

可供后续单因素验证、由主会话决定是否开展的问题（本轮未启动）：

1. 在两个同一障碍组件造成分离接触段的状态中，只把单区间包络改为多窗口，比较合法完整路线和用时，检验连带范围是否必要。
2. 固定状态、目标、预算与求解器，只改变等距离锚点平局规则，测量接口/完整路线变化。
3. 固定状态与求解器，只改变 R_SEED/R_PLUS1/R_PLUS2/R_ALL 的范围宽度，观察完整路线质量与计算时间；不以本轮结果预设最优范围。

## 交付索引

- [验收矩阵](acceptance_evidence_matrix_20261017.csv)
- [只读复核器](verify_acceptance_range_20261017.py) 与 [夹具测试日志](audit_fixture_tests_final_20261017.log)
- [只读复核日志](acceptance_check_20261017.log)
- [10状态总览 CSV](state_overview.csv)、[40范围边界 CSV](range_boundaries.csv)、[40条核心结果 CSV](literal_r_plus1_results.csv)
- [完整机器细节 JSON](range_details_final.json)
- [执行时间线 JSON](execution_timeline_20261017.json)、[197次尝试 CSV](execution_attempt_timeline.csv)、[勘误 JSON](audit_summary_errata_20261017.json)、[warm 额外成本分析 JSON](warm_overhead_analysis_20261017.json)
- [69/70全部80配对](cross_batch_69_70_all_pairs.csv)、[22个变化配对](cross_batch_69_70_changed_pairs.csv)
- [旧证据哈希清单](old_evidence_sha256_20261017.json)、[源清单复核](source_manifest_after.json)、新证据哈希清单将在所有交付文件完成后生成。
"""
REPORT.write_text(report,encoding="utf-8")

# Write the root handoff without cleaning or attributing existing cache changes.
status_bytes=subprocess.check_output(["git","status","--porcelain=v1","-z","--untracked-files=all"],cwd=ROOT)
status_rows=[x for x in status_bytes.decode("utf-8","surrogateescape").split("\0") if x]
tracked=[x for x in status_rows if not x.startswith("?? ")]
untracked=[x for x in status_rows if x.startswith("?? ")]
tracked_pyc=sum(x.lower().endswith(".pyc") for x in tracked)
tracked_nonpyc=[x[3:] for x in tracked if not x.lower().endswith(".pyc")]
supp_untracked=sum("/acceptance_and_range_rules_v0.1_20261017/" in x.replace("\\","/") for x in untracked)

handoff=f"""# 交给主会话验收：补证与范围检查

日期：2026-10-17

本轮执行稿已完成可完成的 A、B、C 工作并交付。**B 阶段覆盖规划调用为 0。** 本文供主会话验收，不作最终研究结论或自动批准后续机制。

- 工作根目录：{ROOT.as_posix()}
- 补充目录：{SUP.resolve().as_posix()}
- 仓库 HEAD：{head}（与起始源清单记录 {before['HEAD']} 一致）
- 起始源清单：424个路径；结束重哈希：{'全部匹配' if source_after['all_match'] else '存在差异'}（见 source_manifest_after.json）。
- 原70号交付清单：416项；结束重哈希：{'全部匹配' if old_hash_record['all_match'] else '存在差异'}（见 old_evidence_sha256_20261017.json）。
- 17项协议保护哈希中1项不匹配：run_p2_warm_global_20261017.py；期望 {errata['protocol_hash_mismatch']['expected_sha256']}，当前 {errata['protocol_hash_mismatch']['actual_sha256']}。其余16项匹配。事后哈希不证明进程开跑时加载版本。
- 运行计数：B离线分析规划器调用0；25项回归的事后计数调用7次；warm/P2边界微型回归5次；新合成回归规划器调用合计12次；正式地图调用0次；没有重跑120项性能矩阵。
- 当前 Git 状态快照：{len(tracked)}个 tracked 修改（其中{tracked_pyc}个 .pyc，其余{len(tracked_nonpyc)}个非缓存文件）、{len(untracked)}个 untracked 项（其中补充目录下{supp_untracked}个）。这些状态已记录但未清理；未改写缓存或原始哈希清单。source_manifest_before.json 没有保存起始 Git 状态，故不把当前状态逐项归因为本补充任务。
- 根目录此前已有的字节码同步审计记录30个运行时 .pyc 缓存偏差、对应源码与其余清单匹配：_backup_before_sync_20261017/snapshot_audit_20261017.json；缓存未被本轮覆盖或清除。

## 复核命令

从 .remote_Drone 根目录运行以下只读检查（非零退出表示失败）：

{FENCE}powershell
.\\运行环境\\python\\python.exe -B .\\研究方案_剩余覆盖重规划_20261009\\算法小型验证_20261010\\continuous_history_diagnostics\\acceptance_and_range_rules_v0.1_20261017\\verify_acceptance_range_20261017.py --check
{FENCE}

篡改夹具测试命令：

{FENCE}powershell
Push-Location .\\研究方案_剩余覆盖重规划_20261009\\算法小型验证_20261010\\continuous_history_diagnostics\\acceptance_and_range_rules_v0.1_20261017
..\\..\\..\\..\\运行环境\\python\\python.exe -B -m unittest -v test_acceptance_audit_fixtures_20261017
Pop-Location
{FENCE}

## 核心结果与未闭合项

120个唯一正式结果复核有效，40条热启动序列和40条 LITERAL 核心审计通过；新10状态检查新增目标共1,925格，全部需后续新路线访问。障碍受阻索引、范围边界来源、路线保留代价、40条 R_PLUS1 输出和图件目录见下方报告与 CSV/JSON。没有证明 R_SEED 最小必要，也没有替代范围的性能成绩。

仍需评审时正视的限制：

1. 6次正式 smoke preflight 只有汇总计数，没有逐次输入/结果/日志。
2. 历史多地图关闭 warm 与冻结 P2 的对照日志无法恢复；本轮仅做了5次合成微型回归。
3. 17项协议哈希中的运行器例外无法从事后文件哈希确定其对正式进程的具体影响时间。
4. warm 额外成本分析无 profiler，不能报告耗时占比；69/70批差不能归因到 CPU/负载。
5. 初始目标移除33格，其中27格在输入 deferred_targets 显式记录；另6格仅能确认被移除且落于障碍，未显式标记。

## 文件链接

- [补证与范围规则短报告]({rel(REPORT)})
- [验收矩阵]({rel(matrix_path)})
- [10状态总览 CSV]({rel(SUP/'state_overview.csv')})、[范围边界 CSV]({rel(SUP/'range_boundaries.csv')})、[R_PLUS1逐结果 CSV]({rel(SUP/'literal_r_plus1_results.csv')})
- [完整机器可读细节 JSON]({rel(SUP/'range_details_final.json')})、[10张图件索引]({rel(SUP/'figures'/'index.html')})
- [只读复核器]({rel(SUP/'verify_acceptance_range_20261017.py')})、[复核日志]({rel(SUP/'acceptance_check_20261017.log')})、[夹具测试日志]({rel(SUP/'audit_fixture_tests_final_20261017.log')})
- [勘误、时间线与warm分析]({rel(SUP/'audit_summary_errata_20261017.json')})、[执行时间线 JSON]({rel(SUP/'execution_timeline_20261017.json')})、[warm额外成本 JSON]({rel(SUP/'warm_overhead_analysis_20261017.json')})
- [69/70完整配对 CSV]({rel(SUP/'cross_batch_69_70_all_pairs.csv')})、[变化配对 CSV]({rel(SUP/'cross_batch_69_70_changed_pairs.csv')})
- [起始源清单]({rel(BEFORE)})、[结束源清单复核]({rel(SUP/'source_manifest_after.json')})、[旧证据416项哈希]({rel(SUP/'old_evidence_sha256_20261017.json')})；新证据哈希清单由最后一步生成。
- [完整执行稿](Luna执行稿_验收补证与范围规则检查_20261017.md)

## 实际调用与运行事实

- 25项回归复跑：25 passed；带计数运行器统计7次范围引擎规划调用，0次正式开发地图调用。
- warm/P2事后微型套件：5次规划器调用，其中4次 warm 候选、1次冻结 P2；全为合成夹具。
- B阶段范围重建、碰撞/图距离与路线责任检查：0次规划器调用。
- 原执行尝试：197次，120个唯一有效结果；首次38次（25有效、13次LITERAL入口异常），恢复1共64次路径类型异常，恢复2共95次有效结果；无重复有效成功。
- 当前空间范围结果不填补58号历史范围性能，不启动任何新性能任务。

## 交付审阅

请主会话按上述证据审阅 A3 未闭合、运行器哈希例外及范围规则事实，再决定是否验收和是否提出单因素后续问题。此处不自动启动后续实验。
"""
HANDOFF.write_text(handoff,encoding="utf-8")

# Hash all supplement files and the root handoff; exclude this manifest itself.
new_files=[]
for path in sorted(SUP.rglob("*")):
    if path.is_file() and path.name!="new_evidence_sha256_20261017.json":
        new_files.append({"path":rel(path),"size_bytes":path.stat().st_size,"sha256":sha(path)})
new_files.append({"path":rel(HANDOFF),"size_bytes":HANDOFF.stat().st_size,"sha256":sha(HANDOFF)})
new_hash={
    "created_date":"2026-10-17",
    "scope":"All files under the new acceptance/range supplement directory plus the root handoff document; the manifest excludes itself.",
    "entry_count":len(new_files),
    "all_files_exist":True,
    "files":new_files
}
write_json(SUP/"new_evidence_sha256_20261017.json",new_hash)

print(json.dumps({
    "status":"PASS" if source_after["all_match"] and old_hash_record["all_match"] else "FAIL",
    "head":head,
    "source_manifest_count":len(source_after["files"]),
    "source_manifest_all_match":source_after["all_match"],
    "old_deliverables_count":len(old_hash_record["files"]),
    "old_deliverables_all_match":old_hash_record["all_match"],
    "states":len(states),
    "range_rows":sum(len(s["ranges"]) for s in states),
    "literal_rows":len(literals),
    "explicit_deferred":explicit_total,
    "removed_initial_targets":removed_total,
    "removed_not_explicit":missing_explicit,
    "new_active_targets":new_total,
    "global_fallback_rows":literal_global_fallback,
    "local_scope_core_fallback_rows":literal_local_fallback,
    "old_suffix_rows":literal_old_suffix,
    "new_evidence_entries":len(new_files),
    "report":str(REPORT),
    "handoff":str(HANDOFF)
},ensure_ascii=False,indent=2))
