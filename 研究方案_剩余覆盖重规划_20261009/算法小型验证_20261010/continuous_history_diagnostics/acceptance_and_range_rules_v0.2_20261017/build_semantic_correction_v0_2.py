"""Offline, no-solver build of the 10-state range-rule supplement."""
from pathlib import Path
from collections import deque, defaultdict
import csv, hashlib, html, json, sys

ROOT = Path(__file__).resolve().parents[4]
ALGO = ROOT / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
SUP = ALGO / "continuous_history_diagnostics" / "acceptance_and_range_rules_v0.2_20261017"
BASE_SUP = ALGO / "continuous_history_diagnostics" / "acceptance_and_range_rules_v0.1_20261017"
RUN = ALGO / "continuous_history_diagnostics" / "old_plan_warm_global_v0.1_20261017"
PREP = ALGO / "continuous_history_diagnostics" / "preparation_verification_v0.1_20261016"
INITIAL = ALGO / "continuous_history_diagnostics" / "preflight_v0.1_20261016" / "initial_cases"
OLD69 = ALGO / "continuous_history_diagnostics" / "comparison_v0.1_20261016"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BASE_SUP))
sys.path.insert(0, str(ALGO / "frozen_baselines" / "v2_20261012" / "source"))
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
from verify_acceptance_range_20261017 import check_core
from audit import audit


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_obj(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def norm(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


def connected_components(cells):
    todo = set(map(tuple, cells)); comps = []
    while todo:
        seed = min(todo); todo.remove(seed); comp = {seed}; q = deque([seed])
        while q:
            x, y = q.popleft()
            for z in ((x-1,y),(x,y-1),(x,y+1),(x+1,y)):
                if z in todo:
                    todo.remove(z); comp.add(z); q.append(z)
        comps.append(sorted(comp))
    return sorted(comps, key=lambda c: c[0])


def spans(indices):
    out = []
    for i in sorted(indices):
        if not out or i > out[-1]["end"] + 1:
            out.append({"start": i, "end": i})
        else:
            out[-1]["end"] = i
    return out


def bfs_distance(start, goals, free):
    start = tuple(start); goals = set(map(tuple, goals))
    if start in goals: return 0
    q = deque([(start, 0)]); seen = {start}
    while q:
        (x,y), d = q.popleft()
        for z in ((x-1,y),(x,y-1),(x,y+1),(x+1,y)):
            if z in goals: return d+1
            if z in free and z not in seen:
                seen.add(z); q.append((z,d+1))
    return None


def first_hits(route, goals):
    goals = set(map(tuple, goals)); found = {}
    for i,p in enumerate(map(tuple,route)):
        if p in goals and p not in found: found[p] = i
    return found


def deferred_goal_set(published_targets, covered, free):
    return (set(map(tuple,published_targets))-set(map(tuple,covered)))-set(map(tuple,free))


def pre_event_service_hits(old_route, initial_targets, covered, current):
    remaining=set(map(tuple,initial_targets))-set(map(tuple,covered))-{tuple(current)}
    return first_hits(old_route,remaining)


def old_route_role_at_index(old_route, index, first_service_hits):
    last_service=max(first_service_hits.values(),default=-1)
    cell=tuple(old_route[index])
    if first_service_hits.get(cell)==index:return "first_service"
    if index>last_service:return "return"
    return "connection"


def event_envelopes(case, plan):
    route = list(map(tuple, case["old_route"])); free = set(map(tuple, case["free"]))
    bounds = plan["boundaries"]; legal = [i for i in bounds if route[i] in free]
    bad = plan["old_collision_indices"]; records = []
    contact_spans = spans(bad); contacts = []
    for cid, contact in enumerate(contact_spans, 1):
        left_raw = max(i for i in bounds if i < contact["start"])
        right_raw = min(i for i in bounds if i > contact["end"])
        closed = [max(i for i in legal if i <= left_raw),
                  min(i for i in legal if i >= right_raw)]
        contacts.append({"contact_id": cid, "blocked_indices": list(range(contact["start"], contact["end"] + 1)),
                         "raw_contact_span": [contact["start"], contact["end"]],
                         "service_boundary_span": [left_raw, right_raw], "legal_closed_span": closed,
                         "legal_endpoint_expansion": [left_raw - closed[0], closed[1] - right_raw]})
    if contacts:
        overall = [max(i for i in legal if i < min(bad)), min(i for i in legal if i > max(bad))]
        records.append({"type": "collision_contacts", "contacts": contacts,
                        "overall_closed_span": overall, "blocked_indices": bad})
    for ci, comp in enumerate(plan["new_components"], 1):
        anchor = comp["anchor_index"]; at = bounds.index(anchor)
        raw = [bounds[max(0,at-1)], bounds[min(len(bounds)-1,at+1)]]
        closed = [max(i for i in legal if i <= raw[0]),
                  min(i for i in legal if i >= raw[1])]
        records.append({"type": "new_component_anchor", "component_id": ci,
                        "cells": comp["cells"], "anchor_index": anchor,
                        "anchor_cell": route[anchor], "distance": comp["distance"],
                        "tie_rule": "minimum (graph_distance, old_route_index)",
                        "adjacent_boundary_span": raw, "endpoint_legal_span": closed,
                        "legal_endpoint_expansion": [raw[0]-closed[0], closed[1]-raw[1]]})
    return records


def included_block_reasons(block, event_records, range_name, seed):
    """Describe mechanical inclusion paths without inferring necessity or a unique cause."""
    a, b = block["start"], block["end"]
    start = a
    reasons = []
    supports = []
    contact_count = 0
    anchor_count = 0
    direct = False
    for e in event_records:
        if e["type"] == "collision_contacts":
            for contact in e["contacts"]:
                contact_count += 1
                if any(a <= i <= b for i in contact["blocked_indices"]):
                    direct = True
                    reasons.append("direct_obstacle_collision_overlap")
                l, r = contact["legal_closed_span"]
                if l <= start < r:
                    supports.append((l, r, f"collision_contact_{contact['contact_id']}"))
                    if not any(a <= i <= b for i in contact["blocked_indices"]):
                        reasons.append("collision_contact_to_service_boundary_or_legal_endpoint_closure")
        elif e["type"] == "new_component_anchor":
            anchor_count += 1
            raw_l, raw_r = e["adjacent_boundary_span"]
            close_l, close_r = e["endpoint_legal_span"]
            if raw_l <= start < raw_r:
                supports.append((close_l, close_r, f"new_component_anchor_{e['component_id']}"))
                reasons.append("new_component_anchor_to_service_boundary_closure")
            elif close_l <= start < close_r:
                supports.append((close_l, close_r, f"new_component_anchor_{e['component_id']}"))
                reasons.append("legal_endpoint_closure")
    support_n = len(supports)
    if range_name == "R_SEED" and not direct and support_n == 0:
        if contact_count + anchor_count >= 2:
            reasons.append("multi_contact_or_anchor_enclosing_hull_gap")
        else:
            reasons.append("included_by_rule_reason_non_unique")
    if range_name in ("R_PLUS1", "R_PLUS2") and not (seed[0] <= start < seed[1]):
        reasons.append("PLUS1_boundary_expansion" if range_name == "R_PLUS1" else "PLUS2_boundary_expansion")
    if range_name == "R_ALL" and not (seed[0] <= start < seed[1]):
        reasons.append("full_old_route_interval_inclusion")
    if not reasons:
        reasons.append("included_by_rule_reason_non_unique")
    reasons = list(dict.fromkeys(reasons))
    nonunique = (len(reasons) > 1 or "included_by_rule_reason_non_unique" in reasons or
                 "multi_contact_or_anchor_enclosing_hull_gap" in reasons or
                 (support_n > 1))
    return {"inclusion_reasons": reasons,
            "attribution_status": "rule_included_reason_non_unique" if nonunique else "mechanical_rule_path_identified_not_a_necessity_claim",
            "supporting_local_envelopes": [z[2] for z in supports],
            "supporting_local_envelope_count": support_n,
            "primitive_contact_count": contact_count,
            "primitive_anchor_count": anchor_count,
            "direct_collision_overlap": direct,
            "necessity_or_unnecessary_claim": False}


def draw_svg(state, path):
    case=state["_case"]; route=list(map(tuple,case["old_route"])); free=set(map(tuple,case["free"]))
    initial=set(map(tuple,case["metadata"]["initial_targets"])); targets=set(map(tuple,case["targets"]))
    covered=set(map(tuple,case["covered"])); current=tuple(case["current"]); base=tuple(case["base"])
    deferred=set(map(tuple,case["metadata"].get("deferred_targets",[])))
    obstacle_cells=set(map(tuple,state["event_analysis"]["obstacle_cells"]))
    new=targets-initial
    remain=(targets&initial)-covered-{current}
    xvals=[p[0] for p in free|set(route)|{current,base}]; yvals=[p[1] for p in free|set(route)|{current,base}]
    xmin,xmax=min(xvals)-1,max(xvals)+1; ymin,ymax=min(yvals)-1,max(yvals)+1
    W,H=2000,1050; mx,my,mw,mh=70,155,875,610; rx,ry,rw=1010,210,920
    scale=min(mw/max(1,xmax-xmin),mh/max(1,ymax-ymin));ox=mx+(mw-(xmax-xmin)*scale)/2;oy=my+(mh-(ymax-ymin)*scale)/2
    X=lambda x:ox+(x-xmin)*scale
    Y=lambda y:oy+(ymax-y)*scale
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#334155"/></marker></defs>',
         '<rect width="100%" height="100%" fill="#ffffff"/>']
    def txt(x,y,s,size=17,color="#172033",weight="normal",anchor="start"):
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="Microsoft YaHei, SimHei, Noto Sans CJK SC, sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(s))}</text>')
    txt(70,54,f"{state['map_id']}  ·  事件后执行状态",27,"#111827","bold")
    txt(70,88,f"事件：{state['event_cn']}    当前 {current}    基地 {base}    历史已检 {len(covered)} 格    当前发布目标 {len(targets)} 格    新增 {len(new)} 格",18)
    txt(70,123,f"输入 SHA256 {state['case_sha256']}",14,"#475569")
    txt(mx,145,"地图空间视图（全图范围；线表示旧剩余路线方向）",17,"#111827","bold")
    # Grid and coordinate labels.
    xstep=max(1,round((xmax-xmin)/7));ystep=max(1,round((ymax-ymin)/6))
    for xv in range((xmin//xstep)*xstep,xmax+1,xstep):
        out.append(f'<line x1="{X(xv):.1f}" y1="{my}" x2="{X(xv):.1f}" y2="{my+mh}" stroke="#e8edf2" stroke-width="1"/>')
        txt(X(xv),my+mh+22,xv,12,"#64748b","normal","middle")
    for yv in range((ymin//ystep)*ystep,ymax+1,ystep):
        out.append(f'<line x1="{mx}" y1="{Y(yv):.1f}" x2="{mx+mw}" y2="{Y(yv):.1f}" stroke="#e8edf2" stroke-width="1"/>')
        txt(mx-10,Y(yv)+4,yv,12,"#64748b","normal","end")
    out.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" fill="none" stroke="#94a3b8"/>')
    # Walkable cells supply map context; tiny dots keep large maps legible.
    free_path=[]
    for x,y in sorted(free): free_path.append(f'M{X(x):.2f},{Y(y):.2f}h0.01')
    out.append('<path d="'+''.join(free_path)+'" stroke="#cbd5df" stroke-width="1.6" opacity="0.55"/>')
    # Historical route, arrows, and visited/target classes.
    pts=" ".join(f'{X(x):.2f},{Y(y):.2f}' for x,y in route)
    out.append(f'<polyline points="{pts}" fill="none" stroke="#334155" stroke-width="2.1" opacity="0.72" marker-end="url(#arrow)"/>')
    cell_r=max(2.5,min(5.5,scale*0.34))
    for p in covered:
        out.append(f'<circle cx="{X(p[0]):.2f}" cy="{Y(p[1]):.2f}" r="{cell_r:.2f}" fill="#cbd5e1" opacity="0.75"/>')
    for p in remain:
        out.append(f'<rect x="{X(p[0])-cell_r:.2f}" y="{Y(p[1])-cell_r:.2f}" width="{2*cell_r:.2f}" height="{2*cell_r:.2f}" fill="#3b82f6" opacity="0.83"/>')
    for p in new:
        out.append(f'<path d="M{X(p[0]):.2f},{Y(p[1])-cell_r:.2f} L{X(p[0])+cell_r:.2f},{Y(p[1]):.2f} L{X(p[0]):.2f},{Y(p[1])+cell_r:.2f} L{X(p[0])-cell_r:.2f},{Y(p[1]):.2f} Z" fill="#f59e0b"/>')
    for p in deferred:
        out.append(f'<path d="M{X(p[0])-cell_r:.2f},{Y(p[1])-cell_r:.2f} l{2*cell_r:.2f},{2*cell_r:.2f} m0,-{2*cell_r:.2f} l-{2*cell_r:.2f},{2*cell_r:.2f}" stroke="#dc2626" stroke-width="2.2"/>')
    for p in obstacle_cells:
        out.append(f'<rect x="{X(p[0])-cell_r:.2f}" y="{Y(p[1])-cell_r:.2f}" width="{2*cell_r:.2f}" height="{2*cell_r:.2f}" fill="#7f1d1d" stroke="#fff" stroke-width="0.7"/>')
    for p in covered & obstacle_cells:
        out.append(f'<circle cx="{X(p[0]):.2f}" cy="{Y(p[1]):.2f}" r="{max(1.4,cell_r*0.42):.2f}" fill="#fff" stroke="#0f172a" stroke-width="0.7"/>')
    # Range starts/joins as nested spatial endpoint rings. The exact route index is printed in the sequence panel.
    colors={"R_SEED":"#0f766e","R_PLUS1":"#ea580c","R_PLUS2":"#7c3aed","R_ALL":"#be123c"}
    for j,r in enumerate(state["ranges"]):
        cfg=r["cfg"];rad=4+2*j
        for idx,shape in ((cfg["left"],"circle"),(cfg["right"],"rect")):
            q=route[idx]
            if shape=="circle":
                out.append(f'<circle cx="{X(q[0]):.2f}" cy="{Y(q[1]):.2f}" r="{rad}" fill="none" stroke="{colors[r["name"]]}" stroke-width="2"/>')
            else:
                out.append(f'<rect x="{X(q[0])-rad:.2f}" y="{Y(q[1])-rad:.2f}" width="{2*rad}" height="{2*rad}" fill="none" stroke="{colors[r["name"]]}" stroke-width="1.5" stroke-dasharray="3 2"/>')
    # Current/base overlays are last so their markers remain visible.
    out.append(f'<path d="M{X(current[0]):.2f},{Y(current[1])-9:.2f} L{X(current[0])+8:.2f},{Y(current[1])+7:.2f} L{X(current[0])-8:.2f},{Y(current[1])+7:.2f} Z" fill="#16a34a" stroke="#064e3b" stroke-width="1.4"/>')
    out.append(f'<rect x="{X(base[0])-7:.2f}" y="{Y(base[1])-7:.2f}" width="14" height="14" fill="#ef4444" stroke="#7f1d1d" stroke-width="1.4"/>')
    # Legend.
    legend=[("#cbd5e1","●","事件前已检历史"),("#3b82f6","■","当前可检且未检目标"),("#f59e0b","◆","事件新增目标"),("#7f1d1d","■","事件新增障碍"),("#334155","━","旧剩余路线方向"),("#16a34a","▲","当前位置"),("#ef4444","■","基地"),("#dc2626","×","未检且受阻的暂缓目标"),("#ffffff","○","障碍上的已检历史（双重标签）")]
    lx,ly=80,my+mh+60
    for k,(c,sym,label) in enumerate(legend):
        xx=lx+(k%2)*420; yy=ly+(k//2)*26
        txt(xx,yy,sym,17,c,"bold");txt(xx+24,yy,label,14,"#334155")
    txt(70,1018,"说明：空间图只显示地图格与路线轨迹；范围以右侧旧路线索引区间表达，不把路线窗口画成空间矩形。",13,"#475569")
    # Route sequence panel.
    txt(rx,145,"路线序列视图（索引是 old_route 的序号）",17,"#111827","bold")
    n=len(route)-1;axis_y=ry+455
    for tick in range(0,n+1,max(1,round(max(1,n)/8))):
        xx=rx+tick/max(1,n)*rw
        out.append(f'<line x1="{xx:.1f}" y1="{ry-8}" x2="{xx:.1f}" y2="{axis_y+5}" stroke="#e2e8f0" stroke-width="1"/>')
        txt(xx,axis_y+27,tick,12,"#64748b","normal","middle")
    txt(rx+rw/2,axis_y+52,"旧路线索引 i（相邻点之间为一步）",13,"#475569","normal","middle")
    for j,r in enumerate(state["ranges"]):
        cfg=r["cfg"];yy=ry+j*103;color=colors[r["name"]]
        txt(rx,yy+24,r["name"],18,color,"bold")
        txt(rx+105,yy+24,f"[{cfg['left']}, {cfg['right']}]  {cfg['start']} → {cfg['join']}",15,"#334155")
        pct=100*cfg['required_count']/cfg['pending_count'] if cfg['pending_count'] else 0
        txt(rx+105,yy+48,f"前缀 {cfg['prefix_steps']} 步  ·  可改旧块 {cfg['modifiable_blocks']}/{cfg['block_count']}  ·  窗口目标 {cfg['required_count']}/{cfg['pending_count']} ({pct:.1f}%)  ·  后缀 {cfg['suffix_steps']} 步",14,"#475569")
        x0=rx+cfg["left"]/max(1,n)*rw;x1=rx+cfg["right"]/max(1,n)*rw
        out.append(f'<line x1="{rx}" y1="{yy+69}" x2="{rx+rw}" y2="{yy+69}" stroke="#cbd5e1" stroke-width="6" stroke-linecap="round"/>')
        out.append(f'<line x1="{x0:.2f}" y1="{yy+69}" x2="{x1:.2f}" y2="{yy+69}" stroke="{color}" stroke-width="9" stroke-linecap="round"/>')
        out.append(f'<circle cx="{x0:.2f}" cy="{yy+69}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>')
        out.append(f'<rect x="{x1-6:.2f}" y="{yy+63}" width="12" height="12" fill="#fff" stroke="{color}" stroke-width="3"/>')
        txt(x0,yy+91,f"L={cfg['left']}",12,color,"normal","middle")
        txt(x1,yy+91,f"R={cfg['right']}",12,color,"normal","middle")
    txt(rx,axis_y+90,"○ 左边界 / □ 右边界；彩色部分为允许替换的旧路线索引区间。",14,"#334155")
    txt(rx,axis_y+119,"R_ALL 覆盖全旧尾段；其余范围仍可能保留固定前缀/后缀。区间只限制任务/路线修改，不裁剪寻路地图。",14,"#334155")
    # Legend of range colors.
    for j,name in enumerate(("R_SEED","R_PLUS1","R_PLUS2","R_ALL")):
        xx=rx+j*210;yy=ry-32
        out.append(f'<line x1="{xx}" y1="{yy}" x2="{xx+34}" y2="{yy}" stroke="{colors[name]}" stroke-width="5"/>')
        txt(xx+43,yy+5,name,13,colors[name],"bold")
    out.append('</svg>')
    Path(path).write_text("\n".join(out),encoding="utf-8")


def protocol_runid_audit():
    protocol=read(RUN/"protocol.json")
    jobs=protocol["jobs"]
    by_id={j["run_id"]:j for j in jobs}
    assert len(jobs)==120 and len(by_id)==120
    ledger_files=["execution_ledger.jsonl","recovery/recovery_ledger.jsonl","recovery2/recovery_ledger.jsonl"]
    attempts=[]
    for rel in ledger_files:
        for line in (RUN/rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row=json.loads(line);row["source_ledger"]=rel;attempts.append(row)
    successful=[r for r in attempts if r.get("worker_status")=="returned" and r.get("valid") is True
                and r.get("returncode")==0 and not r.get("watchdog_timeout")]
    successes_by_id=defaultdict(list)
    for row in successful:successes_by_id[row["run_id"]].append(row)
    assert set(successes_by_id)==set(by_id), "successful run_id set differs from protocol"
    assert all(len(v)==1 for v in successes_by_id.values()), "duplicate successful attempt for a run_id"
    final_rows=[json.loads(x) for x in (RUN/"final_120.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    final_by_id={x["job"]["run_id"]:x for x in final_rows}
    assert len(final_rows)==120 and len(final_by_id)==120 and set(final_by_id)==set(by_id)
    job_fields=("run_id","case","map_id","repeat","budget","seed","method")
    join_rows=[]
    for rid in sorted(by_id):
        job=by_id[rid];success=successes_by_id[rid][0];final=final_by_id[rid]
        assert all(success.get(k)==job.get(k) for k in job_fields), f"ledger/protocol job mismatch: {rid}"
        assert all(final["job"].get(k)==job.get(k) for k in job_fields), f"final/protocol job mismatch: {rid}"
        result=final["result"]
        assert result.get("worker_status")=="returned" and result.get("method")==job["method"]
        assert result.get("budget")==job["budget"] and result.get("seed")==job["seed"]
        join_rows.append({"run_id":rid,"map_id":job["map_id"],"budget":job["budget"],
            "repeat":job["repeat"],"method":job["method"],"seed":job["seed"],
            "protocol_job_match":True,"success_ledger":success["source_ledger"],
            "unique_success_for_run_id":True,"final_120_match":True,
            "final_result_path":final.get("result_path")})
    runner_matches=[(k,v) for k,v in protocol["protected_hashes"].items() if k.endswith("run_p2_warm_global_20261017.py")]
    assert len(runner_matches)==1
    runner_key,runner_expected=runner_matches[0]
    runner_actual=sha(ROOT/"run_p2_warm_global_20261017.py")
    assert runner_expected=="f7168fe617b62c27d7db51fb885b922d6baaf7edd7604c4a2e199f02c396d68f"
    assert runner_actual=="e8ff1d405546e0d01976a7a9cb803569092717d198fda7b22367fc4f24cbc72c"
    protected_bad=[]
    for name,expected in protocol["protected_hashes"].items():
        if name.endswith("run_p2_warm_global_20261017.py"):continue
        candidate=Path(name)
        if not candidate.is_absolute():candidate=ROOT/candidate
        if not candidate.is_file() or sha(candidate)!=expected:protected_bad.append(name)
    assert not protected_bad, f"unexpected protocol protected hash differences: {protected_bad}"
    return {"protocol_jobs":len(jobs),"final_120_rows":len(final_rows),"attempt_rows":len(attempts),
        "successful_attempt_rows":len(successful),"unique_success_run_ids":len(successes_by_id),
        "job_id_sets_match":True,"every_final_job_matches_protocol":True,
        "each_run_id_has_one_successful_original_attempt":True,
        "source_ledgers":ledger_files,"protected_hash_mismatches_other_than_runner":[],
        "runner_hash_exception":{"path_key":runner_key,"exact_protocol_expected_sha256":runner_expected,
                                  "exact_disclosed_current_sha256":runner_actual},
        "join_rows":join_rows}


def main():
    existing=read(BASE_SUP/"range_details.json")
    final=[];state_csv=[];goal_partition_csv=[];blocked_role_csv=[];range_reason_csv=[]
    range_csv=[];obstacle_csv=[];literal_csv=[]
    results={}
    for line in (RUN/"final_120.jsonl").read_text(encoding="utf-8").splitlines():
        item=json.loads(line);job=item["job"]
        if job["method"]=="LITERAL": results[(job["map_id"],job["budget"],job["repeat"])]=item
    assert len(results)==40
    for old in existing:
        map_id=old["map_id"];p=PREP/"cases"/(map_id+".json");case=read(p);meta=case["metadata"]
        raw_initial=INITIAL/(map_id+".json");initial_case=read(raw_initial)
        cursha=sha(p);initialsha=sha(raw_initial)
        assert cursha==old["case_sha256"]
        free=set(map(tuple,case["free"]));initial_free=set(map(tuple,initial_case["free"]))
        obstacle_cells=initial_free-free;new_free=free-initial_free
        initial=set(map(tuple,meta["initial_targets"]));published=set(map(tuple,meta["published_targets"]))
        targets=set(map(tuple,case["targets"]))
        covered=set(map(tuple,case["covered"]));current=tuple(case["current"]);old_route=list(map(tuple,case["old_route"]))
        explicit_deferred=set(map(tuple,meta.get("deferred_targets",[])))
        deferred=deferred_goal_set(published,covered,free)
        assert deferred==explicit_deferred, f"deferred formula mismatch {map_id}"
        assert targets==published&free, f"current inspectable target set mismatch {map_id}"
        initial_not_published=initial-published
        newly_published=published-initial
        initial_not_current=initial-targets
        removed=initial-targets;new_active=targets-initial
        assert covered<=initial and not (covered & new_active), f"event history retroactively covers new goal: {map_id}"
        assert not (targets-free), f"published goal blocked: {map_id}"
        plan=independent_plan(case);assert plan==old["range_plan"], f"range reconstruction mismatch {map_id}"
        pending=targets-covered-{current}
        pre_event_remaining=initial-covered-{current}
        hits=pre_event_service_hits(old_route,initial,covered,current);last_hit=max(hits.values(),default=-1)
        assert set(hits)==pre_event_remaining, f"pre-event route misses initial remaining task(s): {map_id}"
        return_start=last_hit+1
        remaining_after_last=[q for q,i in hits.items() if i>last_hit]
        blocked_return_before_service=[i for i,pnt in enumerate(old_route)
                                       if pnt not in free and i>last_hit
                                       and any(j>i for j in hits.values())]
        assert not remaining_after_last and not blocked_return_before_service
        assert old_route[-1]==tuple(case["base"]), f"old route does not terminate at base: {map_id}"
        obstacle_comps=connected_components(obstacle_cells)
        comp_records=[];route_blocked=[i for i,pnt in enumerate(old_route) if pnt not in free]
        hit_by_comp={}
        for cid,comp in enumerate(obstacle_comps,1):
            cells=set(comp);indices=[i for i,pnt in enumerate(old_route) if pnt in cells]
            spans_for_comp=spans(indices);hit_by_comp[cid]=indices
            comp_records.append({"component_id":cid,"cells":comp,"cell_count":len(comp),
                                 "route_indices":indices,"route_spans":spans_for_comp,
                                 "intersects_old_route":bool(indices)})
        cell_to_component={p:c["component_id"] for c in comp_records for p in c["cells"]}
        event_rows=[]
        role_by_index={}
        for i in route_blocked:
            q=old_route[i];first=hits.get(q)==i;is_pending=q in pending;after_last=(i>last_hit)
            old_role=old_route_role_at_index(old_route,i,hits)
            if q in deferred: post_status="uncompleted_deferred_target"
            elif q in covered: post_status="covered_history_obstructed"
            elif q in published: post_status="published_but_not_currently_inspectable"
            else: post_status="not_a_published_target"
            tags=[old_role]
            role_by_index[i]=old_role
            event_rows.append({"route_index":i,"cell":q,"obstacle_component_id":cell_to_component.get(q),
                               "old_plan_role":old_role,"old_plan_first_service":first,
                               "event_post_target_status":post_status,
                               "event_post_pending_target_cell":is_pending,
                               "pre_event_remaining_target_cell":q in pre_event_remaining,
                               "initial_target_cell":q in initial,"metadata_published_target_cell":q in published,
                               "current_inspectable_target_cell":q in targets,"covered_history_cell":q in covered,
                               "uncompleted_deferred_target_cell":q in deferred,"roles":tags})
        blocked_spans=spans(route_blocked)
        for sp in blocked_spans:
            ii=list(range(sp["start"],sp["end"]+1));sp["indices"]=ii
            sp["cells"]=[old_route[i] for i in ii]
            sp["obstacle_component_ids"]=sorted({cell_to_component[old_route[i]] for i in ii if old_route[i] in cell_to_component})
            sp["roles"]=[role_by_index[i] for i in ii]
        separated=[]
        for comp in comp_records:
            for left_span,right_span in zip(comp["route_spans"],comp["route_spans"][1:]):
                a=left_span["end"];b=right_span["start"]
                left_cells=[old_route[i] for i in range(left_span["start"],left_span["end"]+1)]
                right_cells=[old_route[i] for i in range(right_span["start"],right_span["end"]+1)]
                inter=[(q,i) for q,i in hits.items() if a<i<b]
                manhattan=min((abs(x-u)+abs(y-v) for x,y in left_cells for u,v in right_cells),default=None)
                dists=[bfs_distance(q, right_cells, initial_free) for q in left_cells]
                separated.append({"component_id":comp["component_id"],"left_route_span":left_span,
                                  "right_route_span":right_span,"route_index_gap":b-a,
                                  "intervening_first_hit_tasks":[{"cell":q,"route_index":i} for q,i in sorted(inter,key=lambda x:x[1])],
                                  "intervening_first_hit_task_count":len(inter),
                                  "minimum_manhattan_map_distance":manhattan,
                                  "minimum_pre_event_free_graph_distance":min((d for d in dists if d is not None),default=None)})
        added_on_old=set(new_active)&set(old_route)
        added_at_current=new_active & {current}
        added_needing_new_visit=new_active-set(old_route)-{current}
        initial_not_current_covered=initial_not_current&covered
        initial_not_current_deferred=initial_not_current&deferred
        initial_not_current_other=initial_not_current-initial_not_current_covered-initial_not_current_deferred
        event_analysis={"event":meta.get("event"),"obstacle_cells":sorted(obstacle_cells),
            "obstacle_components":comp_records,"old_route_blocked_indices":route_blocked,
            "old_route_blocked_spans":blocked_spans,"blocked_route_index_roles":event_rows,
            "same_component_separated_route_effects":separated,
            "initial_target_count":len(initial),"metadata_published_target_count":len(published),
            "current_inspectable_target_count":len(targets),
            "active_added_target_count":len(new_active),"active_added_targets_on_old_remaining_route_count":len(added_on_old),
            "active_added_targets_on_old_remaining_route":sorted(added_on_old),
            "active_added_at_current_count":len(added_at_current),
            "active_added_targets_requiring_new_route_visit_count":len(added_needing_new_visit),
            "active_added_targets_requiring_new_route_visit":sorted(added_needing_new_visit),
            "covered_history_count":len(covered),"covered_history_intersects_new_targets":bool(covered&new_active),
            "initial_targets_not_published":sorted(initial_not_published),
            "initial_targets_not_published_count":len(initial_not_published),
            "newly_published_targets":sorted(newly_published),"newly_published_target_count":len(newly_published),
            "initial_targets_not_currently_inspectable":sorted(initial_not_current),
            "initial_targets_not_currently_inspectable_count":len(initial_not_current),
            "not_currently_inspectable_initial_targets_already_covered":sorted(initial_not_current_covered),
            "not_currently_inspectable_initial_targets_uncompleted_deferred":sorted(initial_not_current_deferred),
            "not_currently_inspectable_initial_targets_other":sorted(initial_not_current_other),
            "metadata_published_targets":sorted(published),
            "current_inspectable_targets":sorted(targets),
            "covered_history_targets":sorted(covered),
            "event_deferred_uncompleted_targets":sorted(deferred),
            "event_deferred_target_count":len(deferred),
            "deferred_formula":"(metadata.published_targets - covered) - free",
            "deferred_formula_matches_metadata":deferred==explicit_deferred,
            "initial_targets_all_present_in_published_targets":initial<=published,
            "initial_published_overlap_count":len(initial&published),
            "initial_published_overlap":sorted(initial&published),
            "current_targets_equal_published_intersect_free":targets==published&free,
            "pre_event_remaining_service_targets":sorted(pre_event_remaining),
            "pre_event_remaining_service_target_count":len(pre_event_remaining),
            "old_route_first_service_positions":{f"{q[0]},{q[1]}":i for q,i in sorted(hits.items(),key=lambda x:x[1])},
            "last_pre_event_service_route_index":last_hit,
            "pre_event_return_segment_start_index":return_start,
            "pre_event_return_segment_route_indices":list(range(return_start,len(old_route))),
            "pre_event_route_ends_at_base":old_route[-1]==tuple(case["base"]),
            "pre_event_remaining_targets_after_last_service_count":len(remaining_after_last),
            "blocked_return_indices_before_unfinished_service":blocked_return_before_service,
            "blocked_first_service_index_count":sum(r["old_plan_role"]=="first_service" for r in event_rows),
            "blocked_connection_index_count":sum(r["old_plan_role"]=="connection" for r in event_rows),
            "blocked_return_index_count":sum(r["old_plan_role"]=="return" for r in event_rows),
            "first_service_targets_after_last_service_index":[q for q,i in hits.items() if i>last_hit],
            "blocked_return_before_remaining_service_count":len(blocked_return_before_service),
            "free_cells_before":len(initial_free),"free_cells_after":len(free),
            "event_blocked_cells_count":len(obstacle_cells),"free_cells_added":len(new_free),
            "service_hit_definition":"first appearance in old_route of initial_targets - covered - {current}, reconstructed before applying event obstacles; event-post status is recorded separately"}
        goal_partition_csv.append({"map_id":map_id,"initial_targets_count":len(initial),
            "metadata_published_targets_count":len(published),"current_inspectable_targets_count":len(targets),
            "covered_history_count":len(covered),"event_deferred_uncompleted_count":len(deferred),
            "initial_targets_not_published_count":len(initial_not_published),
            "newly_published_count":len(newly_published),
            "initial_targets_not_currently_inspectable_count":len(initial_not_current),
            "not_current_initial_already_covered_count":len(initial_not_current_covered),
            "not_current_initial_uncompleted_deferred_count":len(initial_not_current_deferred),
            "not_current_initial_other_count":len(initial_not_current_other),
            "deferred_formula_matches_metadata":deferred==explicit_deferred,
            "current_targets_equal_published_intersect_free":targets==published&free,
            "initial_target_cells_json":json.dumps(sorted(initial),ensure_ascii=False),
            "metadata_published_target_cells_json":json.dumps(sorted(published),ensure_ascii=False),
            "current_inspectable_target_cells_json":json.dumps(sorted(targets),ensure_ascii=False),
            "covered_history_cells_json":json.dumps(sorted(covered),ensure_ascii=False),
            "event_deferred_uncompleted_cells_json":json.dumps(sorted(deferred),ensure_ascii=False)})
        blocked_role_csv.extend({"map_id":map_id,**r,"cell_json":json.dumps(r["cell"],ensure_ascii=False),
            "roles_json":json.dumps(r["roles"],ensure_ascii=False)} for r in event_rows)
        event_records=event_envelopes(case,plan);seed=plan["seed_span"]
        aliases={};seen={}
        range_rows=[]
        for name in ("R_SEED","R_PLUS1","R_PLUS2","R_ALL"):
            cfg=plan["plans"][name];key=(cfg["left"],cfg["right"]);alias=seen.setdefault(key,name)
            ass=assignment(case,cfg)
            pfx=set(map(tuple,ass["prefix_required"]));local=set(map(tuple,cfg["required"]));sfx=set(map(tuple,ass["suffix_required"]))
            assert pfx|local|sfx==pending and not (pfx&local or pfx&sfx or local&sfx)
            block_rows=[]
            for bi,b in enumerate(plan["blocks"],1):
                if b["start"]>=cfg["left"] and b["start"]<cfg["right"]:
                    reason_detail=included_block_reasons(b,event_records,name,seed)
                    block_rows.append({"block_id":bi,"start":b["start"],"end":b["end"],"cells":b["cells"],
                                       "pending_target_count":len(set(map(tuple,b["cells"]))&pending),**reason_detail})
                    range_reason_csv.append({"map_id":map_id,"range":name,"block_id":bi,
                        "route_start":b["start"],"route_end":b["end"],
                        "pending_target_count":len(set(map(tuple,b["cells"]))&pending),
                        "inclusion_reasons_json":json.dumps(reason_detail["inclusion_reasons"],ensure_ascii=False),
                        "attribution_status":reason_detail["attribution_status"],
                        "supporting_local_envelopes_json":json.dumps(reason_detail["supporting_local_envelopes"],ensure_ascii=False),
                        "direct_collision_overlap":reason_detail["direct_collision_overlap"],
                        "necessity_or_unnecessary_claim":reason_detail["necessity_or_unnecessary_claim"]})
            aliases[name]=alias
            rr={"name":name,"alias_of":alias,"is_alias":alias!=name,"cfg":cfg,
                "start_cell":cfg["start"],"join_cell":cfg["join"],"prefix_steps":cfg["prefix_steps"],
                "suffix_steps":cfg["suffix_steps"],"window_steps":cfg["right"]-cfg["left"],
                "pending_target_count":cfg["pending_count"],"local_required_target_count":cfg["required_count"],
                "local_required_target_pct":cfg["required_count"]/cfg["pending_count"]*100 if cfg["pending_count"] else 0,
                "prefix_required_target_count":len(pfx),"suffix_required_target_count":len(sfx),
                "modifiable_old_service_blocks":cfg["modifiable_blocks"],"total_old_service_blocks":cfg["block_count"],
                "old_service_blocks":block_rows,"outside_prefix_preserved":cfg["left"]>0,
                "outside_suffix_preserved":cfg["right"]<len(old_route)-1,
                "required_target_cells":cfg["required"]}
            range_rows.append(rr)
            range_csv.append({"map_id":map_id,"event":meta.get("event"),"range":name,"alias_of":alias,
                "left_index":cfg["left"],"right_index":cfg["right"],"start_cell":json.dumps(cfg["start"]),
                "join_cell":json.dumps(cfg["join"]),"prefix_steps":cfg["prefix_steps"],
                "window_steps":cfg["right"]-cfg["left"],"suffix_steps":cfg["suffix_steps"],
                "pending_targets":cfg["pending_count"],"prefix_target_count":len(pfx),
                "local_target_count":cfg["required_count"],"local_target_pct":round(rr["local_required_target_pct"],3),
                "suffix_target_count":len(sfx),"modifiable_blocks":cfg["modifiable_blocks"],
                "service_blocks_total":cfg["block_count"],"preserves_prefix":cfg["left"]>0,
                "preserves_suffix":cfg["right"]<len(old_route)-1,
                "local_event_inclusion_reasons":json.dumps(sorted({z for b in block_rows for z in b["inclusion_reasons"]}),ensure_ascii=False),
                "reason_attribution_statuses":json.dumps(sorted({b["attribution_status"] for b in block_rows}),ensure_ascii=False)})
        # Report rule-inclusion categories without converting the geometry into a necessity claim.
        seed_row=range_rows[0]
        seed_reason_blocks=[b for b in seed_row["old_service_blocks"] if b["attribution_status"]=="rule_included_reason_non_unique"]
        merge_gap_blocks=[b for b in seed_row["old_service_blocks"] if "multi_contact_or_anchor_enclosing_hull_gap" in b["inclusion_reasons"]]
        event_analysis["R_SEED_non_unique_reason_service_blocks"]=len(seed_reason_blocks)
        event_analysis["R_SEED_non_unique_reason_pending_tasks"]=sum(b["pending_target_count"] for b in seed_reason_blocks)
        event_analysis["R_SEED_multi_contact_or_anchor_hull_gap_blocks"]=len(merge_gap_blocks)
        event_analysis["R_SEED_multi_contact_or_anchor_hull_gap_tasks"]=sum(b["pending_target_count"] for b in merge_gap_blocks)
        # Literal R_PLUS1 saved results: verify all states/seeds/budgets against independent assignment.
        literal_rows=[]
        for budget in (1,20):
            for repeat in (0,1):
                item=results[(map_id,budget,repeat)];job=item["job"];raw=item["result"]["raw"]
                cfg=plan["plans"]["R_PLUS1"];assigned=assignment(case,cfg);detail=raw["detail"]
                responsibilities_match=norm(detail.get("responsibilities"))==norm(assigned)
                core=raw.get("core_route") or ();patch=raw.get("core_patch") or ()
                core_exists=bool(core);core_valid=bool(core_exists and audit(case_to_snapshot(case),tuple(map(tuple,core)))["valid"])
                patch_valid=bool(core_exists and check_core(old_route,cfg["left"],cfg["right"],cfg["required"],core,patch))
                plan_match=detail.get("range_plan")==plan
                final_valid=bool(raw.get("route") and audit(case_to_snapshot(case),tuple(map(tuple,raw["route"])))["valid"])
                assert responsibilities_match and plan_match
                assert (not core_exists) or (core_valid and patch_valid)
                out={"budget_seconds":budget,"repeat":repeat,"seed":job["seed"],"core_exists":core_exists,
                     "core_steps":len(core)-1 if core_exists else None,"core_valid":core_valid if core_exists else None,
                     "core_patch_structure_valid":patch_valid if core_exists else None,
                     "final_steps":len(raw["route"])-1 if raw.get("route") else None,
                     "final_source":raw.get("source"),"final_valid":final_valid,
                     "global_common_fallback":raw.get("source")=="common_fallback",
                     "scope_core_common_fallback_internal":raw.get("source")=="scope_core:common_fallback",
                     "range_plan_matches_independent":plan_match,
                     "responsibilities_match_independent":responsibilities_match,
                     "saved_result_path":item.get("result_path")}
                literal_rows.append(out);literal_csv.append({"map_id":map_id,**out})
        state={"map_id":map_id,"event":meta.get("event"),"event_cn":{"straight":"直线扩展","corner":"拐角扩展","obstacle":"障碍","straight_obstacle":"直线扩展+障碍","corner_obstacle":"拐角扩展+障碍"}.get(meta.get("event"),meta.get("event")),
            "case_path":str(p.resolve()),"case_sha256":cursha,"initial_map_path":str(raw_initial.resolve()),
            "initial_map_sha256":initialsha,"source_protocols":[str((RUN/"protocol.json").resolve()),str((PREP.parent/"preparation_v0.1_20261016"/"protocol.json").resolve())],
            "current":case["current"],"base":case["base"],"old_route_steps":len(old_route)-1,
            "old_route_index_count":len(old_route),"covered_history_target_count":len(covered),
            "initial_target_count":len(initial),"metadata_published_target_count":len(published),
            "current_inspectable_target_count":len(targets),
            "current_pending_target_count":len(pending),"event_analysis":event_analysis,
            "range_boundary_source_records":event_records,"range_aliases":aliases,
            "ranges":range_rows,"literal_r_plus1_results":literal_rows,
            "saved_scope_performance_results":{"available_range":"R_PLUS1","rows":len(literal_rows),"other_ranges":"structure only; no saved performance results"},
            "_case":case}
        final.append(state)
        state_csv.append({"map_id":map_id,"event":meta.get("event"),"event_cn":state["event_cn"],
            "case_path":str(p.resolve()),"case_sha256":cursha,"initial_map_sha256":initialsha,
            "current":json.dumps(case["current"]),"base":json.dumps(case["base"]),
            "old_route_steps":len(old_route)-1,"covered_history_targets_count":len(covered),
            "initial_targets_count":len(initial),"current_inspectable_targets_count":len(targets),
            "current_pending_targets_count":len(pending),"added_active_targets":len(new_active),
            "added_on_old_route":len(added_on_old),"added_requiring_new_route_visit":len(added_needing_new_visit),
            "metadata_published_targets":len(published),"current_inspectable_targets":len(targets),
            "covered_history_targets":len(covered),"event_deferred_uncompleted_targets":len(deferred),
            "initial_targets_not_published":len(initial_not_published),
            "initial_targets_not_currently_inspectable":len(initial_not_current),
            "initial_not_current_but_already_covered":len(initial_not_current_covered),
            "initial_not_current_and_deferred":len(initial_not_current_deferred),
            "initial_not_current_other":len(initial_not_current_other),"blocked_cells":len(obstacle_cells),
            "obstacle_components":len(obstacle_comps),"old_route_blocked_indices":json.dumps(route_blocked),
            "old_route_blocked_spans":json.dumps(blocked_spans,ensure_ascii=False),
            "same_component_split_effects":len(separated),
            "blocked_first_service_indices":sum(r["old_plan_role"]=="first_service" for r in event_rows),
            "blocked_connection_indices":sum(r["old_plan_role"]=="connection" for r in event_rows),
            "blocked_return_indices":sum(r["old_plan_role"]=="return" for r in event_rows),
            "last_pre_event_service_route_index":last_hit,
            "pre_event_return_segment_start_index":return_start,
            "pre_event_remaining_targets_after_last_service_count":len(remaining_after_last),
            "blocked_return_before_remaining_service_count":len(blocked_return_before_service),
            "deferred_formula_matches_metadata":deferred==explicit_deferred,
            "R_SEED_non_unique_reason_blocks":len(seed_reason_blocks),
            "R_SEED_non_unique_reason_tasks":sum(b["pending_target_count"] for b in seed_reason_blocks),
            "R_SEED_multi_contact_or_anchor_hull_gap_blocks":len(merge_gap_blocks),
            "R_SEED_multi_contact_or_anchor_hull_gap_tasks":sum(b["pending_target_count"] for b in merge_gap_blocks),
            "R_PLUS1_literal_cores":sum(bool(z["core_exists"]) for z in literal_rows),
            "R_PLUS1_final_sources":json.dumps([z["final_source"] for z in literal_rows],ensure_ascii=False)})
        for c in comp_records:
            obstacle_csv.append({"map_id":map_id,"component_id":c["component_id"],"cells":json.dumps(c["cells"]),
                "cell_count":c["cell_count"],"route_indices":json.dumps(c["route_indices"]),
                "route_spans":json.dumps(c["route_spans"]),"intersects_old_route":c["intersects_old_route"]})
        draw_state={k:v for k,v in state.items() if k!="_case"};draw_state["_case"]=case
        fig=SUP/"figures"/(map_id+".svg");fig.parent.mkdir(exist_ok=True)
        draw_svg(draw_state,fig)
    # Cross-batch exact paired diagnostics: join 69/70 by map, budget, repeat, seed, method.
    oldrows=[json.loads(l) for l in (OLD69/"execution_ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    oldlookup={(r["map_id"],r["budget"],r["repeat"],r["seed"],r["method"]):r for r in oldrows if r["method"] in ("P2_MULTI","LITERAL")}
    newlookup={}
    for ln in (RUN/"final_120.jsonl").read_text(encoding="utf-8").splitlines():
        z=json.loads(ln);j=z["job"]
        if j["method"] in ("P2_MULTI","LITERAL"):newlookup[(j["map_id"],j["budget"],j["repeat"],j["seed"],j["method"])]=z
    cross=[]
    assert len(oldlookup)==len(newlookup)==80
    for key in sorted(oldlookup):
        a=oldlookup[key];z=newlookup[key];raw_old=read(OLD69/"runs"/(a["run_id"]+".json"))["raw"];raw_new=z["result"]["raw"]
        new_result=z["result"];new_steps=new_result["independent_route_check"].get("steps")
        route_old=raw_old.get("route",[]);route_new=raw_new.get("route",[])
        h_old=digest_obj(route_old);h_new=digest_obj(route_new)
        oldstage=raw_old.get("active_stage");newstage=raw_new.get("active_stage")
        def stage_status(raw):
            ev=raw.get("events",[])
            return {e.get("stage"):e.get("status",e.get("termination")) for e in ev if e.get("stage")}
        os=stage_status(raw_old);ns=stage_status(raw_new)
        changed=[name for name in sorted(set(os)|set(ns)) if os.get(name)!=ns.get(name)]
        row={"map_id":key[0],"budget":key[1],"repeat":key[2],"seed":key[3],"method":key[4],
            "69_steps":a["steps"],"70_steps":new_steps,
            "step_delta_70_minus_69":(new_steps-a["steps"]) if new_steps is not None else None,
            "69_source":a["source"],"70_source":raw_new.get("source"),
            "source_changed":a["source"]!=raw_new.get("source"),
            "69_seconds":a["seconds"],"70_seconds":raw_new.get("seconds"),
            "seconds_delta_70_minus_69":(raw_new.get("seconds")-a["seconds"]) if raw_new.get("seconds") is not None else None,
            "69_active_stage":oldstage,"70_active_stage":newstage,"active_stage_changed":oldstage!=newstage,
            "route_sha256_69":h_old,"route_sha256_70":h_new,"route_same":route_old==route_new,
            "route_length_changed":a["steps"]!=new_steps,
            "stage_status_changes":changed,"69_stage_status":os,"70_stage_status":ns,
            "69_run_id":a["run_id"],"70_run_id":z["job"]["run_id"]}
        cross.append(row)
    cross_changes=[r for r in cross if r["route_length_changed"] or r["source_changed"] or r["active_stage_changed"] or not r["route_same"] or r["stage_status_changes"]]
    # Remove private case objects before JSON serialization.
    clean=[]
    for s in final:
        clean.append({k:v for k,v in s.items() if k!="_case"})
    protocol_audit=protocol_runid_audit()
    protocol_join_rows=protocol_audit.pop("join_rows")
    doc={"created_date":"2026-10-17","revision":"v0.2_semantic_correction","mode":"offline_read_only_no_planner_calls",
         "states":clean,"methodology":{"state_input":"70 protocol-reused preparation_verification cases plus corresponding pre-event initial_cases",
           "obstacle_cells":"initial free cells minus event free cells; four-neighbour components",
           "deferred_interpretation":"deferred = (metadata.published_targets - covered) - free; the resulting set is checked against metadata.deferred_targets for every state; metadata published goals, current inspectable goals, covered history, and deferred goals are listed separately",
           "old_route_role_interpretation":"first service positions are reconstructed from initial_targets - covered - {current} before applying the event obstacle map; event-post target status is a separate field",
           "range_inclusion_attribution":"direct collision, local contact/anchor boundary closure, endpoint closure, multi-contact/anchor hull gaps, and PLUS extensions are separate mechanical labels; attribution is marked non-unique where the input geometry does not identify one cause; no label asserts unnecessary work",
           "new_target_categories":"active newly published cells split by old remaining route overlap, current location, and cells requiring a new route visit",
           "range_rules":"independently reconstructed via saved independent_plan/assignment audit adapters; graph distance in current free map, ties by lowest old_route index; R_PLUS1/R_PLUS2 add one/two service-boundary steps around R_SEED; endpoint legality closes outward",
           "map_distance":"Manhattan distance and pre-event free-grid BFS edge distance between separated blocked route contact spans",
           "figure":"SVG vector map view and distinct route-index sequence view; no spatial rectangle used as a route window",
           "cross_batch":"69/70 joined on map_id,budget,repeat,seed,method; outputs compare route bytes, steps, source, timing, active stage, and per-stage terminal status",
           "protocol_run_id_audit":"final_120 is joined to protocol and the three original attempt ledgers by run_id; each protocol ID must have one successful returned attempt and a matching final row; one runner hash exception is accepted only for the exact expected and exact disclosed current hashes"},
         "protocol_runid_audit":protocol_audit,
         "cross_batch_summary":{"paired_rows":len(cross),"rows_with_any_recorded_change":len(cross_changes),
           "route_length_changed":sum(r["route_length_changed"] for r in cross),"route_content_changed":sum(not r["route_same"] for r in cross),
           "source_changed":sum(r["source_changed"] for r in cross),"active_stage_changed":sum(r["active_stage_changed"] for r in cross),
           "stage_status_changed":sum(bool(r["stage_status_changes"]) for r in cross)},
         "planner_calls_in_this_analysis":0}
    (SUP/"range_details_final.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    def write_csv(name,rows):
        if not rows:return
        with (SUP/name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write_csv("state_overview.csv",state_csv);write_csv("range_boundaries.csv",range_csv)
    write_csv("goal_partition_v0.2.csv",goal_partition_csv)
    write_csv("blocked_route_roles_v0.2.csv",blocked_role_csv)
    write_csv("range_inclusion_reasons_v0.2.csv",range_reason_csv)
    write_csv("obstacle_route_effects.csv",obstacle_csv);write_csv("literal_r_plus1_results.csv",literal_csv)
    write_csv("cross_batch_69_70_all_pairs.csv",cross);write_csv("cross_batch_69_70_changed_pairs.csv",cross_changes)
    write_csv("protocol_runid_join_v0.2.csv",protocol_join_rows)
    correction_rows=[
        {"finding":"target_partition","v0.1_statement":"33 initial targets removed; 27 explicit deferred; six not explicit","v0.2_correction":"All ten states are recomputed as metadata published, current inspectable, covered history, and uncompleted deferred using deferred=(published-covered)-free. The six extra removed cells are covered history.","affected_outputs":"range_details_final.json; goal_partition_v0.2.csv; state_overview.csv; figures/*.svg"},
        {"finding":"blocked_route_roles","v0.1_statement":"Blocked indices classified from event-post pending targets; reported as connection-only","v0.2_correction":"Recomputed first-service positions from initial_targets-covered-{current} and old_route first appearances before event filtering. All 27 blocked indices are first-service positions; event-post deferred status is stored separately.","affected_outputs":"range_details_final.json; blocked_route_roles_v0.2.csv; obstacle_route_effects.csv"},
        {"finding":"return_order","v0.1_statement":"No independent event-pre return-boundary audit field","v0.2_correction":"Return segment starts after the last pre-event remaining service; all old routes terminate at base and no pre-event service remains beyond that point.","affected_outputs":"range_details_final.json; state_overview.csv"},
        {"finding":"range_inclusion_reason","v0.1_statement":"single_interval_enclosure_only treated no direct overlap/no anchor adjacency as a unique collateral cause","v0.2_correction":"Separate direct contact, local boundary/legal endpoint closure, multi-contact/anchor hull gaps, and PLUS extension. Mark non-unique causes explicitly; no unnecessary-work claim.","affected_outputs":"range_details_final.json; range_inclusion_reasons_v0.2.csv; range_boundaries.csv; figures/index.html"},
        {"finding":"run_id_provenance","v0.1_statement":"Semantic checker did not self-join final_120 to protocol and all original attempt ledgers","v0.2_correction":"All 120 final jobs join by run_id to protocol and one unique successful attempt across the three original ledgers. Runner mismatch accepted only for exact protocol and disclosed-current SHA256 values.","affected_outputs":"range_details_final.json; protocol_runid_join_v0.2.csv"},
        {"finding":"historical_scope","v0.1_statement":"Execution history may be read as complete preregistered traceability","v0.2_correction":"The six individual preflight logs and original multi-map warm-off logs remain unrecoverable historical gaps; label data as limited development diagnosis, not strict full preregistered execution.","affected_outputs":"correction_report_v0.2.md"}
    ]
    write_csv("correction_mapping_v0.2.csv",correction_rows)
    (SUP/"cross_batch_summary.json").write_text(json.dumps(doc["cross_batch_summary"],ensure_ascii=False,indent=2),encoding="utf-8")
    # A small HTML index lets reviewers open each vector figure without tooling.
    links="\n".join(f'<li><a href="{html.escape(Path(s["map_id"]+".svg").as_posix())}">{html.escape(s["map_id"])} — {html.escape(s["event_cn"])}</a></li>' for s in clean)
    (SUP/"figures"/"index.html").write_text('<!doctype html><meta charset="utf-8"><title>10-state range maps</title><h1>10 状态范围检查图</h1><ol>'+links+'</ol>',encoding="utf-8")
    print(json.dumps({"status":"PASS","states":len(clean),"range_rows":len(range_csv),
        "obstacle_components":len(obstacle_csv),"literal_rows":len(literal_csv),
        "cross_batch_pairs":len(cross),"cross_batch_changed_rows":len(cross_changes),
        "cross_batch_summary":doc["cross_batch_summary"],"planner_calls":0,
        "protocol_runid_successes":protocol_audit["unique_success_run_ids"],
        "files":["range_details_final.json","state_overview.csv","goal_partition_v0.2.csv","blocked_route_roles_v0.2.csv","range_inclusion_reasons_v0.2.csv","correction_mapping_v0.2.csv","range_boundaries.csv","obstacle_route_effects.csv","literal_r_plus1_results.csv","cross_batch_69_70_all_pairs.csv","cross_batch_69_70_changed_pairs.csv","protocol_runid_join_v0.2.csv","figures/index.html"]},ensure_ascii=False,indent=2))


def case_to_snapshot(c):
    from prepare_road_range_diagnostic_20261015 import snapshot
    return snapshot(c)


if __name__=="__main__": main()
