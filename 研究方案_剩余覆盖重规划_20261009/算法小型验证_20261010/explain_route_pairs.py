"""Read-only diagnosis of saved 20s routes; never invokes a planner."""
from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib, statistics, sys
from PIL import Image, ImageDraw, ImageFont
from scenarios import deserialize
from audit import audit
from supplement_route_metrics import metrics, checks

D=Path(__file__).parent
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
O=D/'results/run_30_route_explanation_20261012'
INPUTS=[D/'results/run_29b_p2_search_audit_20261012/runs.json',D/'results/run_26_unified_new_maps/snapshots.json']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def points(a):return set(map(tuple,a))
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(FONT,n)

def diagnose(r,s,meta):
    route=list(map(tuple,r['route']));a=audit(s,route)
    assert a['valid'] and a==r['independent_audit']
    m=metrics(route,s.targets,s.covered)
    initial=points(meta['initial_targets']);seen=set(s.covered)|({route[0]}&s.targets)
    cells=[];spatial=Counter();phase=Counter();edges=Counter();zone_changes=0
    lastzone=None
    for i,(u,p) in enumerate(zip(route,route[1:]),1):
        cat=('non_target' if p not in s.targets else 'historical' if p in s.covered else 'repeat_new' if p in seen else 'fresh')
        zone='old_region' if p in initial else 'extension' if p in s.targets else 'outside_target'
        stage='return' if i>m['completion_step'] else 'inspection'
        spatial[zone+'|'+cat]+=1;phase[stage+'|'+cat]+=1
        cells.append(dict(step=i,position=p,category=cat,zone=zone,phase=stage))
        edges[tuple(sorted((u,p)))]+=1
        if lastzone is not None and lastzone!=zone:zone_changes+=1
        lastzone=zone;seen.add(p)
    assert sum(spatial.values())==m['length']==sum(phase.values())
    assert m['missing_targets']==0
    return dict(case=s.name,repeat=r['repeat'],method=r['variant'],source=r.get('source'),
        seconds=r['seconds'],status=r['status'],metrics=m,spatial=dict(spatial),phase=dict(phase),
        repeated_edge_steps=sum(v-1 for v in edges.values()),zone_changes=zone_changes,steps=cells)

def render(case,s,meta,rs,diags,path):
    im=Image.new('RGB',(1860,870),'white');dr=ImageDraw.Draw(im)
    dr.text((28,15),case,font=font(23),fill='#142d44')
    dr.text((28,52),'同一状态、同一20秒预算、重复0；线为实际飞行路线，不是原始MST树。',font=font(21),fill='#344054')
    domain=points(meta['domain']);obstacles=points(meta['obstacles']);initial=points(meta['initial_targets'])
    area=set(s.targets)|set(s.covered)|obstacles|{s.current,s.base}
    for r in rs:area|=points(r['route'])
    xmin=min(p[0] for p in area)-1;xmax=max(p[0] for p in area)+1
    ymin=min(p[1] for p in area)-1;ymax=max(p[1] for p in area)+1
    scale=min(560/(xmax-xmin+1),440/(ymax-ymin+1))
    info_y=int(150+(ymax-ymin+1)*scale+28)
    colors={'fresh':'#276ac6','historical':'#e37922','repeat_new':'#e37922','non_target':'#9a45ac'}
    for panel in range(3):
        left=25+panel*615;top=150
        dr.text((left,105),['事件发生后的地图','增强P2：访问顺序优化','MST初始化＋2-opt'][panel],font=font(24),fill='#142d44')
        def xy(p):return (left+(p[0]-xmin+.5)*scale,top+(ymax-p[1]+.5)*scale)
        for x in range(xmin,xmax+1):
            for y in range(ymin,ymax+1):
                p=(x,y);cx,cy=xy(p)
                fill='#f4f5f7' if p in domain else '#b5b8bd'
                if p in s.targets:fill='#d8eaf9' if p in initial else '#c9efd5'
                if p in s.covered and p in s.targets:fill='#c4c8cf'
                if p in obstacles:fill='#303840'
                dr.rectangle((cx-scale/2,cy-scale/2,cx+scale/2,cy+scale/2),fill=fill,outline='#e0e3e7',width=1)
        if panel:
            r=rs[panel-1];d=diags[panel-1];route=list(map(tuple,r['route']))
            for step,u,v in zip(d['steps'],route,route[1:]):
                a=xy(u);b=xy(v);color='#343b48' if step['phase']=='return' else colors[step['category']]
                dr.line((a,b),fill=color,width=3)
                if step['step']%15==0:
                    cx,cy=b;dr.ellipse((cx-8,cy-8,cx+8,cy+8),fill='white',outline=color,width=1)
                    dr.text((cx-6,cy-6),str(step['step']),font=font(10),fill=color)
            m=d['metrics'];y=info_y
            for t in [f"总步数 {m['length']}；重叠率 {m['overlap_ratio']:.1%}",
                      f"新覆盖 {m['fresh_target_steps']}；历史重复 {m['historical_target_steps']}",
                      f"本轮重复 {m['repeated_new_target_steps']}；非目标移动 {m['non_target_steps']}",
                      f"完成巡检前 {m['completion_step']} 步；返航尾段 {m['return_tail_steps']} 步"]:
                dr.text((left,y),t,font=font(21),fill='#344054');y+=32
        for p,label,col in [(s.current,'S','#e72746'),(s.base,'B','#111827')]:
            cx,cy=xy(p);dr.ellipse((cx-9,cy-9,cx+9,cy+9),fill=col)
            dr.text((cx-6,cy-9),label,font=font(14),fill='white')
    dr.text((28,info_y+155),'底色：蓝＝旧路段待检；绿＝新增待检；灰＝已检；黑＝障碍；浅灰＝可通行非目标。',font=font(21),fill='#344054')
    dr.text((28,info_y+190),'线色：蓝＝首次覆盖；橙＝重复到达目标；紫＝非目标移动；深灰＝巡检完成后的返航；数字＝步序。',font=font(21),fill='#344054')
    im.crop((0,0,1860,info_y+235)).save(path)

def main():
    checks();O.mkdir(parents=True,exist_ok='--refresh-derived' in sys.argv)
    hashes={str(p):sha(p) for p in INPUTS}
    raw=read(INPUTS[1]);snaps={r['snapshot']['name']:(deserialize(r['snapshot']),r['metadata']) for r in raw}
    rows=[r for r in read(INPUTS[0]) if r['batch']=='new' and r['budget']==20 and r['variant'] in ('multi','TREE')]
    lookup={(r['case'],r['repeat'],r['variant']):r for r in rows};ds={}
    for r in rows:
        s,meta=snaps[r['case']];ds[r['case'],r['repeat'],r['variant']]=diagnose(r,s,meta)
    pairs=[]
    for case,(s,meta) in sorted(snaps.items()):
        for rep in (0,1):
            a=ds[case,rep,'multi'];b=ds[case,rep,'TREE'];ma=a['metrics'];mb=b['metrics']
            diff={k:ma[k]-mb[k] for k in ('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps','turns90','turns180')}
            assert diff['fresh_target_steps']==0
            assert diff['length']==sum(diff[k] for k in ('historical_target_steps','repeated_new_target_steps','non_target_steps'))
            assert diff['length']==diff['completion_step']+diff['return_tail_steps']
            pairs.append(dict(case=case,repeat=rep,family=meta['family'],domain=meta['domain_kind'],delta=diff))
    # Fixed selection: largest advantage stable in both repeats; tie prefers obstacle then largest route.
    bycase={case:[p for p in pairs if p['case']==case] for case in snaps}
    stable_p=[c for c,ps in bycase.items() if all(p['delta']['length']<0 for p in ps)]
    stable_t=[c for c,ps in bycase.items() if all(p['delta']['length']>0 for p in ps)]
    ties=[c for c,ps in bycase.items() if all(p['delta']['length']==0 for p in ps)]
    avg=lambda c:statistics.mean(p['delta']['length'] for p in bycase[c])
    sel=[('增强P2优势最大且两次方向一致',min(stable_p,key=lambda c:(avg(c),c))),
         ('MST优势最大且两次方向一致',max(stable_t,key=lambda c:(avg(c),c))),
         ('两次均持平的纯障碍例',max([c for c in ties if snaps[c][1]['family']=='obstacle'],key=lambda c:(ds[c,0,'multi']['metrics']['length'],c)))]
    for title,candidates,choose in [('纯障碍中P2较短',[c for c in stable_p if snaps[c][1]['family']=='obstacle'],min),('纯障碍中MST较短',[c for c in stable_t if snaps[c][1]['family']=='obstacle'],max),('直线扩展中MST较短',[c for c in stable_t if snaps[c][1]['family']=='straight'],max)]:
        if candidates:sel.append((title,choose(candidates,key=lambda c:(avg(c),c))))
    selected=[]
    for i,(title,case) in enumerate(sel,1):
        s,meta=snaps[case];rs=[lookup[case,0,v] for v in ('multi','TREE')];diags=[ds[case,0,v] for v in ('multi','TREE')]
        name=f'case_{i:02d}.png';render(case,s,meta,rs,diags,O/name)
        selected.append(dict(title=title,case=case,image=name,repeat_shown=0))
    groups=[]
    for fam in sorted({p['family'] for p in pairs}):
        ps=[p for p in pairs if p['family']==fam];deltas={k:sum(p['delta'][k] for p in ps) for k in ps[0]['delta']}
        groups.append(dict(family=fam,n=len(ps),p2_win=sum(p['delta']['length']<0 for p in ps),tie=sum(p['delta']['length']==0 for p in ps),tree_win=sum(p['delta']['length']>0 for p in ps),delta=deltas))
    for name,obj in [('diagnostics.json',list(ds.values())),('pairs.json',pairs),('event_summary.json',groups),('selected.json',selected)]:
        (O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    assert hashes=={str(p):sha(p) for p in INPUTS}
    (O/'protocol.json').write_text(json.dumps(dict(no_solver_called=True,input_sha256=hashes,script_sha256=sha(Path(__file__)),audited_routes=len(rows),selection='20s, both repeats agree; largest mean advantage; tie is largest pure-obstacle route; supplementary pure-event cases',hashes_unchanged=True),ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 增强P2与MST路线差异图解（2026-10-12）','',
      '## 最值得关注的发现','',
      '1. 不能据此认定树结构最好：同类事件内部双方都有胜负。','2. 全部48次配对中，增强P2的本轮重复少96步、历史重复多53步，合计重复目标到达少43步；但非目标移动多79步，最终多36步。更少重复覆盖不自动等于更短总路线。','3. 总长度差36步可另拆成巡检阶段多17步、返航尾段多19步。区域间连接、覆盖结束位置与返航的共同安排值得检查。','4. 这些是成本定位，尚不是创新点或机制因果证明。','',
      '## 本轮回答什么','',
      '读取已保存的同预算20秒结果，不新增求解。逐条独立复核96条路线（24状态×2次×2方法），全部合法、完成可检目标并返航；原始输入哈希未改变。图示重复0，同时检查重复1，未挑选对结论有利的一次重复。','',
      '当前MST是生成访问顺序后做2-opt，不是区域分解树，也不是TRACE或C*完整算法。以下是路线成本定位，不是算法机制的因果证明。','',
      '## 全部状态的结果','',
      '差值统一为增强P2减MST：负值表示P2较短。每类16次配对来自8状态×2重复，不是16个独立地图。','',
      '|事件|P2胜/平/MST胜|总步数差|历史重复差|本轮重复差|非目标移动差|巡检阶段差|返航尾段差|',
      '|---|---|---:|---:|---:|---:|---:|---:|']
    for g in groups:
        d=g['delta'];lines.append(f"|{g['family']}|{g['p2_win']}/{g['tie']}/{g['tree_win']}|"+'|'.join(str(d[k]) for k in ('length','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps'))+'|')
    lines+=['','总步数差＝历史重复差＋本轮重复差＋非目标移动差。两者首次完成的新覆盖量相同。另一种独立划分是总步数＝巡检完成前步数＋完成后返航尾段；这两套划分不能相加。返航尾段短不代表整条路线更好，也可能只是最后一个目标离基地近。','',
      '## 怎样读图','',
      'S是事件后的无人机当前位置，B是基地。绿色仅表示已发布的新增待检路面；黑色障碍遮挡的目标不计入当前可检集合。图裁剪到道路与实际路线附近，外围深灰表示不在允许飞行域。数字每15步标注一次；重走同一边的线可能互相覆盖，精确次数以表格和JSON为准。','',
      '主案例按两次重复平均步数差选择优势最大的双方案例；持平案例选择两次均相同的最大纯障碍路线；另补双方纯障碍与直线扩展案例。它们用于解释已知结果，不能用于估计现场发生概率。']
    for i,item in enumerate(selected,1):
        case=item['case'];a=ds[case,0,'multi'];b=ds[case,0,'TREE'];ma=a['metrics'];mb=b['metrics'];p=next(p for p in pairs if p['case']==case and p['repeat']==0);d=p['delta']
        lines+=['',f"## 例{i}：{item['title']}",'',f'`{case}`','',f"![例{i}]({(O/item['image']).as_posix()})",'',
          '|指标|增强P2|MST＋2-opt|','|---|---:|---:|']
        for label,key in [('总步数','length'),('历史重复','historical_target_steps'),('本轮重复','repeated_new_target_steps'),('非目标移动','non_target_steps'),('巡检完成前步数','completion_step'),('返航尾段','return_tail_steps'),('90°转弯','turns90')]:lines.append(f'|{label}|{ma[key]}|{mb[key]}|')
        explanations=[
          '通俗解释：这例MST重复经过本轮刚检过的格子16步，P2只有3步。P2虽然在非目标区域多走3步，仍净省10步。图中的MST长条扫描转弯少，但总长度更长；少转弯与少走路并不等价。',
          '通俗解释：P2从S往右出发时，沿灰色已检路面移动了一段，历史重复20步；MST没有这项历史重复。P2虽在其他新检区域少重复9步，仍净多12步。两者返航尾段都是9步，这例差异发生在完成巡检之前。',
          '通俗解释：MST提前2步完成最后一个目标，但后面返航多2步，最终打平。只看巡检结束时刻或只看返航，都会遗漏另一半。',
          '通俗解释：P2没有重复到达目标；MST有4步本轮重复。不过P2的非目标移动多2步，最终只省2步。不是把重复消掉多少就能等量节省多少总路程。',
          '通俗解释：P2无重复覆盖、且提前2步完成巡检，仍比MST总路程多2步，因为返航尾段多4步。这是覆盖结束位置值得纳入共同考虑的直接例子，但并不证明某种新的返航方法有效。',
          '通俗解释：MST没有重复覆盖，P2有2步历史重复，另外非目标移动也多2步，共差4步。两者90°转弯同为22次，不能用转弯次数解释这例长度差。']
        lines+=['',explanations[i-1],'',f"该例步数差 {d['length']}＝历史重复差 {d['historical_target_steps']}＋本轮重复差 {d['repeated_new_target_steps']}＋非目标移动差 {d['non_target_steps']}。巡检阶段差 {d['completion_step']}，返航尾段差 {d['return_tail_steps']}。",'',
          f"增强P2最终采用的候选来源为 `{a['source']}`。重复1的P2减MST差为 {bycase[case][1]['delta']['length']} 步；不能把图中的单次差额当成普遍收益。"]
        # Record the actual redundant cell locations for an independently checkable spatial explanation.
        for title,z in [('增强P2',a),('MST',b)]:
            counts=Counter(tuple(e['position']) for e in z['steps'] if e['category'] in ('historical','repeat_new'))
            hot=sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))[:6]
            lines.append(f"{title}重复目标到达较集中的坐标及冗余次数："+('；'.join(f'{pos}：{n}' for pos,n in hot) or '无')+'。')
    lines+=['','## 判断与下一步','',
      '可以确定：双方胜负都能在具体的重复目标到达和非目标转移中核对，而不是检查工作量不同；同类事件内仍出现相反胜负，事件标签不足以选择算法。','',
      '尚不能确定：某种分块结构、树本身或旧路线保留机制导致优势。本轮观察最终路线，没有控制初始序列、搜索过程及几何因素，不能从图形外观推导因果。覆盖阶段与返航也相互影响，不能将返航差额全部解释为返航算法优劣。','',
      '建议下一轮聚焦“覆盖方向、入口出口与返航位置的联合选择”：先冻结一组待检小块，比较固定方向/端点与允许改变方向/端点的结果，保持地图、任务与连接规则一致；在小规模下精确求解，用于确认额外往返是否确实可以消除。两种设置都应计入从当前位置出发以及最终返航的成本。','',
      '如果这一机制确有收益，再单独改变扩展接入位置或障碍位置，检查收益是否稳定；之后才考虑如何在限时内实现。方向/端点优化已是已有文献的常见思想，不把这一验证本身称为创新。当前尚未执行该实验，也未选定论文主算法。','',
      '本轮属于开发数据事后诊断；图中某条路线看起来不整齐并不构成可改进性的证明。具体改动需经同预算对照与独立地图验证。逐步分类、区域分类及所有48对数据见本轮结果目录。']
    report=B/'40_增强P2与MST路线差异图解_20261012.md'
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(groups=groups,selected=selected,report=str(report)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
