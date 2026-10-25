"""Read saved evidence only: route diagrams, plain report, final ledgers/manifest."""
from common import *
import sys,html,datetime
def diagram(st,a):
    c=read(H/st['input']);F=set(map(tuple,c['free']));T=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));A=set(map(tuple,st['A']));s=12;panel=(st['L']+8)*s+28;height=(st['w']+8)*s+110
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{3*panel}" height="{height}" viewBox="0 0 {3*panel} {height}"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Microsoft YaHei,Arial,sans-serif;font-size:11px}}</style>']
    for k,method in enumerate(('INPUT','PPCPP','P2_MULTI')):
        x0=k*panel+12;y0=42
        label=method;route=[]
        if method!='INPUT':
            jid=f'formal_{st["id"]}_20261020_{method}';r=next(r for r in a['rows'] if r['id']==jid)
            if (H/'outputs'/f'{jid}.json').exists():route=read(H/'outputs'/f'{jid}.json')['result']['raw'].get('route',[])
            label+=f' L={r["metrics"]["length"] if r["metrics"] else "NA"} valid={r["valid"]} timely={r["timely"]}'
        parts.append(f'<text x="{x0}" y="16">{html.escape(st["id"] if k==0 else label)}</text>')
        if k==0:parts.append(f'<text x="{x0}" y="31">H={len(hist)}/{st["T0_count"]}, new={len(A)}, seed=20261020</text>')
        for x,y in sorted(F):
            p=(x,y);fill='#ffb64d' if p in A else '#8bb7ec' if p in hist else '#ffeaaa' if p in T else '#f4f4f4'
            parts.append(f'<rect x="{x0+x*s}" y="{y0+y*s}" width="{s}" height="{s}" fill="{fill}" stroke="#ccc" stroke-width=".4"/>')
        if route:
            pts=' '.join(f'{x0+(p[0]+.5)*s},{y0+(p[1]+.5)*s}' for p in route)
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{"#206e31" if method=="PPCPP" else "#663db8"}" stroke-width="1.7" opacity=".82"/>')
        for p,color,radius in [(c['base'],'black',3),(c['current'],'#e50070',4)]:parts.append(f'<circle cx="{x0+(p[0]+.5)*s}" cy="{y0+(p[1]+.5)*s}" r="{radius}" fill="{color}"/>')
    parts.append(f'<text x="12" y="{height-14}">橙：新增A　蓝：历史H　黄：旧待检　灰：可飞非目标　黑：基地　红：当前位置。失败/迟到保留，固定首seed，不换例。</text></svg>')
    p=H/'figures'/f'{st["id"]}.svg'
    with p.open('x',encoding='utf8') as f:f.write(''.join(parts))
    return p.name
def main():
    a=read(H/'analysis.json');verifylog=(H/'verify_execution.log').read_text(encoding='utf8');assert 'ALL PASS' in verifylog
    states=read(H/'states.json');links=[]
    for st in states:
        name=diagram(st,a);links.append(f'<h3>{html.escape(st["id"])}</h3><a href="figures/{name}"><img style="max-width:100%" src="figures/{name}"/></a>')
    with (H/'48状态路线图.html').open('x',encoding='utf8') as f:f.write('<!doctype html><meta charset="utf-8"><title>固定48状态：输入与两路线</title><h1>开发固定批，seed20261020</h1>'+''.join(links))
    order=[json.loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];receipts=[read(p) for p in (H/'logs').glob('*.receipt.json')]
    synthetic=[]
    for p in (H/'technical_rounds').rglob('outputs/*.json'):
        try:x=read(p)
        except (json.JSONDecodeError,UnicodeDecodeError):continue
        if 'actual_core_calls' in x:synthetic.append(dict(path=str(p.relative_to(H)),stub_cores=len(x['actual_core_calls'])))
    ledger=dict(real_cap=306,attempted_processes=len(order),real_entries=sum(r['markers']['entry_starts'] for r in receipts),real_cores=sum(r['markers']['core_starts'] for r in receipts),phase_processes=dict(collections.Counter(j['phase'] for j in order)),generation_BFS=read(H/'generation_ledger.json')['ordinary_BFS'],pre_event_input_audit_BFS=read(H/'input_audit.json')['ordinary_BFS'],final_verify_BFS=24,ordinary_BFS_total=read(H/'generation_ledger.json')['ordinary_BFS']+read(H/'input_audit.json')['ordinary_BFS']+24,coverage_exact_searches=0,synthetic_output_records=len(synthetic),synthetic_core_calls_in_saved_outputs=sum(x['stub_cores'] for x in synthetic),synthetic_records=synthetic,cold_real_dependency_import_checks=len(list((H/'technical_rounds').glob('*/B1.json'))),cold_production_inventory_imports=1,no_retry=True,holdout_used=False)
    save(H/'call_ledger_final.json',ledger)
    groups=a['views']['timely']['groups'];table='\n'.join(f'|{g["group"]}|{g["three_seed_H_U_complete"]}|{g["mean_DH_minus_DU"]}|{g["classification"]}|' for g in groups)
    examples='\n'.join(f'- {g["selection"]}：{g["group"]}，均值{g["mean_DH_minus_DU"]}；四条件见48图入口。' for g in a['detailed_examples'])
    report=f'''# 侧向拓宽固定开发批结果

真实入口{ledger['real_entries']}/306，核心{ledger['real_cores']}，未补跑。完整技术门槛第三轮通过；前两轮错误、修复与回归保留。技术通过与研究支持分别判断。

主及时配对：{json.dumps(a['views']['timely']['all'],ensure_ascii=False)}。
事件：{json.dumps(a['views']['timely']['events'],ensure_ascii=False)}；控制：{json.dumps(a['views']['timely']['controls'],ensure_ascii=False)}。
包含迟到的全部合法附录：{json.dumps(a['views']['legal']['all'],ensure_ascii=False)}。缺失与失败见144配对账；未将失败记0。

原有限继续判据：{json.dumps(a['signal'],ensure_ascii=False)}。此结论仅针对固定开发数据；P2是可行参照，不是oracle。三seed不当独立地图，同一几何两个历史切点不重复计为两张图。

|匹配组|三seed H/U完整|平均D_H−D_U|分类|
|---|---|---|---|
{table}

D=L_PPCPP−L_P2。比较位置时当前/基地距离和任务布局也变化，D_H−D_U及事件减CONTROL均为描述性，不能当纯历史因果损失或可直接删除步数。各seed C+R、四移动类型和转弯见完整指标，访问/实际trace见嵌套原始字段。

详细组按预登记最大、最小、绝对值最小顺序去重：
{examples}

耗时、完整/及时/迟到/失败：{json.dumps(a['time_summary'],ensure_ascii=False)}。

48状态路线图.html固定首seed20261020，输入/两方法并列；失败不换seed。真实6历史、12前缀、候选全表和48输入均保留；独立输入审计与最终只读verify通过。普通BFS总{ledger['ordinary_BFS_total']}次单列，无覆盖精确、LAST、四方向、混合、留出或新地图。冻结源码不改，Git未提交推送。完成后停止，交负责人审核，不启动下一研究轮次。
'''
    with (H/'实验报告.md').open('x',encoding='utf8') as f:f.write(report)
    with (H/'review_packet.md').open('x',encoding='utf8') as f:f.write('# 审核入口\n\n先读实验报告.md、technical_repairs.md、call_ledger_final.json；再看48状态路线图.html、144全部配对与不可用原因.csv、signal.json及verify_execution.log。两阶段seal与最终manifest保留。技术总PASS来自第三轮实际检查，历史失败不覆盖。\n')
    root=R/'当前进度与下一步.md';old=root.read_bytes()
    with (H/'root_progress_before_completion.md').open('xb') as f:f.write(old)
    addition=f'# 最新完成：侧向拓宽v0.4固定批封存（2026-10-21）\n\n真实入口{ledger["real_entries"]}/306、核心{ledger["real_cores"]}，技术第三轮通过，原6准备＋12门槛＋288正式按序完成，全部原始失败与技术修复保留。原有限继续信号registered_pass={a["signal"]["registered_pass"]}，支持几何{a["signal"]["support_geometries"]}；仅开发诊断，不是普遍因果或主算法确认。双指标、48输入及候选历史、严格及时/含迟到配对、全部48固定seed路线图和只读verify保留。详见PPCPP侧向拓宽开发诊断_v0.4_20261021/实验报告.md。冻结原件及旧版本不改，留出不用，Git不提交推送，完成停止待审核。\n\n---\n\n'
    with root.open('wb') as f:f.write(addition.encode('utf8')+old)
    with (H/'root_progress_after_completion.md').open('xb') as f:f.write(root.read_bytes())
    save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','delivery_execution.log')})
    print(json.dumps(dict(status='SEALED_COMPLETE',ledger=ledger,signal=a['signal']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
