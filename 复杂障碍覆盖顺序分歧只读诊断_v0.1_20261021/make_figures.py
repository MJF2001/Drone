"""Draw only saved paths and saved subsets; no graph search."""
from order_common import *
from html import escape

def draw(p,a,c):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="1270" viewBox="0 0 1240 1270">','<rect width="1240" height="1270" fill="#fff"/>','<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#152238} .small{font-size:14px}</style>']
    def text(x,y,s,size=16):out.append(f'<text x="{x}" y="{y}" font-size="{size}">{escape(str(s))}</text>')
    text(30,34,p['id']+' | 原轨迹只读观测',24);text(30,63,'蓝=采集前段；橙=返航；绿=共同轨迹前缀；紫菱=轨迹分叉；青圈=首次不同采集目标',16)
    text(30,86,'下两行是等新增采集比例，非同一时间、同一位置或同一任务；经过次数以表格为准。',16)
    free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));history=set(map(tuple,c['covered']));w=max(x for x,y in free)+1;h=max(y for x,y in free)+1
    for col,(method,key) in enumerate([('PPCPP','PPCPP_id'),('P2_MULTI','P2_id')]):
        r=next(r for r in a['routes'] if r['id']==p[key]);raw=read(S/'outputs'/f'{r["id"]}.json');path=list(map(tuple,raw['result']['raw']['route']));x0=48+col*610;unit=17;gx=x0+58;gy0=129
        def panel(y,title,remain=None,pos=None):
            text(x0,y-12,title,18)
            for yy in range(h):
                for xx in range(w):
                    q=(xx,yy);color='#374151' if q not in free else '#dce9ee' if q in history else '#f1f5f9'
                    if remain is not None and q in remain:color='#f59e0b'
                    out.append(f'<rect x="{gx+xx*unit}" y="{y+yy*unit}" width="{unit}" height="{unit}" fill="{color}" stroke="white" stroke-width=".5"/>')
            return lambda q:(gx+(q[0]+.5)*unit,y+(q[1]+.5)*unit)
        def poly(seq,xy,color,width=2,dash=''):
            if len(seq)>1:out.append(f'<polyline points="{" ".join(f"{xy(q)[0]},{xy(q)[1]}" for q in seq)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" opacity=".8" '+(f'stroke-dasharray="{dash}"' if dash else '')+'/>')
        def circle(q,xy,color,radius=6,label=None):
            xx,yy=xy(q);out.append(f'<circle cx="{xx}" cy="{yy}" r="{radius}" fill="white" fill-opacity=".6" stroke="{color}" stroke-width="2"/>')
            if label:text(xx+8,yy-6,label,12)
        xy=panel(gy0,f'{method}  L={r["L"]}  C={r["C"]}  R={r["R"]}')
        poly(path[:r['C']+1],xy,'#2563eb');poly(path[r['C']:],xy,'#ef7f18',3);poly(path[:p['common_vertex_count']],xy,'#10986a',3,'4 3')
        circle(c['base'],xy,'#111827',6,'B');circle(path[0],xy,'#10986a',5,'S');circle(r['completion_position'],xy,'#dc2626',7,'E')
        if p['route_status']=='common_state_fork':
            xx,yy=xy(p['common_state']['current']);out.append(f'<path d="M {xx} {yy-7} L {xx+7} {yy} L {xx} {yy+7} L {xx-7} {yy} Z" fill="#a855f7"/>');poly([p['common_state']['current'],p['PPCPP_next' if col==0 else 'P2_next']],xy,'#a855f7',4)
        ac=p['acquisition_divergence']['next_PPCPP' if col==0 else 'next_P2_MULTI']
        if ac:circle(ac['next_target'],xy,'#0891b2',8,'a')
        m=r['metrics'];text(x0,409,f'历史到达={m["historical_target_steps"]}，新目标重复={m["repeated_new_target_steps"]}，90°/180°={m["turns90"]}/{m["turns180"]}',14)
        for row,percent in enumerate((75,90)):
            ss=next(s for s in p['slice_pairs'] if s['percent']==percent)[method];y=467+row*337;xy=panel(y,f'{percent}%：步 {ss["step"]}，剩余 {ss["remaining_count"]} 格，碎片 {ss["fragmentation"]["components"]}',set(map(tuple,ss['remaining'])))
            circle(c['base'],xy,'#111827',5,'B');circle(ss['position'],xy,'#9333ea',7,'P')
            ds=ss['remaining_base_distance'];text(x0,y+h*unit+23,f'目标基地图距 min/med/max={ds["min"]}/{ds["median"]}/{ds["max"]}；后缀={ss["full_suffix_length"]}',14)
    d=p['decision_evidence'];b=p['acquisition_divergence'];text(30,1134,f'ΔL/ΔC/ΔR = {p["delta"]["L"]}/{p["delta"]["C"]}/{p["delta"]["R"]}；共同顶点末端步 {p["common_state"]["step"]}；共同采集目标数 {b["common_target_count"]}',18)
    text(30,1160,f'分叉模式：{d["owner_kind"]}；trace事件索引：{d.get("owner_event_index","NA")}；最高分同分数：{d.get("recorded_max_tie_count","NA")}',16)
    text(30,1186,'P2无在线逐步决策trace。图仅展示其最终保存路线；更短完整后缀不证明仅改下一步可取得全部收益。',16)
    text(30,1212,'恢复段未保存候选距离/评分；不得补算。相同采集顺序前缀不保证到达前的状态相同。',16)
    text(30,1238,f'固定选例：{p["kind"]} / seed={p["seed"]}；原始输入与输出hash见 analysis.json 和 deep_reads。',15)
    out.append('</svg>');return '\n'.join(out)

if __name__=='__main__':
    a=read(H/'analysis.json');(H/'figures').mkdir()
    for ex in a['examples']:
        p=next(p for p in a['pairs'] if p['id']==ex['pair_id']);c=read(S/'inputs'/f'{p["case"]}.json')
        with (H/'figures'/f'{p["id"]}.svg').open('x',encoding='utf8') as f:f.write(draw(p,a,c))
    save(H/'figure_index.json',dict(examples=a['examples'],missing=a['missing_example_categories']))
    print('Saved',len(a['examples']),'fixed SVG pages; distance/planner searches=0')
