"""Read-only saved-map inventory; no planner imports or new trajectory generation."""
from pathlib import Path
import json, hashlib, time, html
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'中心区OFF全量质量时间开发比较_v0.1_20261022'
ORIGIN=ROOT/'PPCPP_LAST新开发地图验证_v0.1_20261020'
GUARDS={}; COUNTS=Counter(); CACHE={}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p, expected=None):
    p=Path(p).resolve(); b=p.read_bytes(); h=hashlib.sha256(b).hexdigest()
    if expected is not None: assert h==expected, str(p)
    GUARDS[str(p)]=h; COUNTS['file_reads']+=1; COUNTS['bytes_read']+=len(b)
    return json.loads(b.decode('utf-8-sig'))
def write(name,o):
    p=HERE/name; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:
        f.write(json.dumps(o,ensure_ascii=False,indent=2) if not isinstance(o,str) else o)
def pts(x): return set(map(tuple,x))
def packed(x): return [list(p) for p in sorted(x)]
def components(s):
    COUNTS['component_traversals']+=1; todo=set(s); out=[]
    while todo:
        first=min(todo);todo.remove(first); stack=[first];part={first}
        while stack:
            x,y=stack.pop();COUNTS['component_cells']+=1
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                COUNTS['neighbor_checks']+=1
                if q in todo:todo.remove(q);part.add(q);stack.append(q)
        out.append(packed(part))
    return sorted(out,key=lambda c:(-len(c),c))
def layer(c,initial,w):
    P0=pts(initial['published_targets']);F0=pts(initial['free'])
    P=pts(c['published_targets']);F=pts(c['free']);H=pts(c['covered']);D=pts(c['deferred_targets']);T=pts(c['targets']);U=T-H
    assert T==P&F and D==(P-F)-H and U==P-H-D
    assert P0<=P and H<=P0 and H.isdisjoint(U|D) and U.isdisjoint(D)
    assert pts(w['blocked'])==F0-F and not F-F0
    return dict(P0=P0,P=P,F0=F0,F=F,H=H,D=D,T=T,U=U,added=P-P0,blocked=F0-F)
def picture(name,data,title):
    L={k:pts(v) for k,v in data['layers'].items()};width,height=1560,650
    im=Image.new('RGB',(width,height),'white');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    d.text((20,12),title,font=font,fill='#17314d')
    bounds=L['F0']|L['P'];xs=[p[0] for p in bounds];ys=[p[1] for p in bounds]
    xmin,xmax,ymin,ymax=min(xs),max(xs),min(ys),max(ys)
    step=min(470/(xmax-xmin+1),470/(ymax-ymin+1))
    labels=['① 事件前完整任务区域 P0','② 事件后：已检 / 未检 / 暂缓','③ 同一状态 + 保存的实际历史前缀']
    if name.startswith('G1_disconnected'):
        labels=['① 起始已发布任务区域','② 起始未检责任（尚无已检历史）','③ 相同起始状态：没有执行前缀']
    colors={'free':'#edf2f7','P0':'#6ea8dc','H':'#82c59c','U':'#f3bf69','D':'#e56767','block':'#444c56'}
    for j,label in enumerate(labels):
        bx=20+j*520;by=85;d.text((bx,51),label,font=font,fill='#17314d')
        def box(p):
            x,y=p;return (bx+(x-xmin)*step,by+(ymax-y)*step,bx+(x-xmin+1)*step,by+(ymax-y+1)*step)
        def center(p):
            a,b,c,e=box(p);return ((a+c)/2,(b+e)/2)
        for p in sorted(L['F0']|L['P']):
            col=colors['free']
            if j==0:
                if p in L['P0']:col=colors['P0']
            else:
                if p in L['H']:col=colors['H']
                if p in L['U']:col=colors['U']
                if p in L['D']:col=colors['D']
                if p in L['blocked'] and p not in L['P']:col=colors['block']
            d.rectangle(box(p),fill=col,outline='#d8dee6',width=1)
            if j and p in L['blocked']:
                a,b,c,e=box(p);d.line((a,b,c,e),fill='#a62024',width=2);d.line((a,e,c,b),fill='#a62024',width=2)
        region=L['P0'] if j==0 else L['P']
        for x,y in region:
            a,b,c,e=box((x,y))
            for q,line in [((x-1,y),(a,b,a,e)),((x+1,y),(c,b,c,e)),((x,y+1),(a,b,c,b)),((x,y-1),(a,e,c,e))]:
                if q not in region:d.line(line,fill='#254f78',width=2)
        if j==2 and len(data['prefix'])>1:d.line([center(p) for p in data['prefix']],fill='#974bc0',width=2)
        markers=[(data['base'],'B','#111111'),(data['current'],'X','#b52024')]
        if data['base']==data['current']:markers=[(data['base'],'B=X','#111111')]
        for p,txt,col in markers:
            x,y=center(p);d.ellipse((x-4,y-4,x+4,y+4),fill=col);d.text((x+5,y-15),txt,font=small,fill=col)
        d.text((bx,570),f"P0={len(L['P0'])}  P={len(L['P'])}  H={len(L['H'])}  U={len(L['U'])}  D={len(L['D'])}",font=small,fill='#17314d')
    d.text((20,602),'蓝：原任务  绿：已检  橙：未检  红：暂缓  红叉：新增障碍  灰白：原本无任务的可飞域',font=font,fill='#17314d')
    caption='紫线为旧格心模型实际前缀，不是新直达路线；当前图不代表真实道路外可以安全飞行。'
    if name.startswith('G1_disconnected'):caption='这里只展示冻结起始地图，无新增事件、无已检历史、无规划轨迹；三个任务块之间本来没有任务。'
    d.text((20,628),caption,font=small,fill='#425466')
    p=HERE/'figures'/f'{name}.png';p.parent.mkdir(exist_ok=True);assert not p.exists();im.save(p)

def main():
    start=time.perf_counter();root_before=(ROOT/'当前进度与下一步.md').read_bytes()
    assert not (HERE/'inventory.json').exists()
    (HERE/'root_before.md').write_bytes(root_before)
    manifest=read(SOURCE/'manifest.json'); mf=manifest['files']
    def src(n): return read(SOURCE/n,mf[n.replace('/','\\')])
    plan=src('plan.json');evidence={x['id']:x for x in src('history_evidence.json')}
    ids=sorted({j['case'] for j in plan['formal']}); assert len(ids)==54 and set(ids)==set(evidence)
    origin_manifest=read(ORIGIN/'manifest.json'); om=origin_manifest.get('files',origin_manifest)
    initial_audit=read(ORIGIN/'input_audit.json',om['input_audit.json']); meta={x['id']:x for x in initial_audit}
    rows=[]; packs={}
    for ident in ids:
        c=src('inputs/'+ident+'.json');ev=evidence[ident]; refs={}
        for p,h in ev['source_files'].items():refs[str(Path(p).resolve())]=read(p,h)
        wp=next(p for p in refs if '\\witnesses\\' in p);rp=next(p for p in refs if '\\prep\\results\\' in p);ip=next(p for p in refs if '\\prep\\inputs\\' in p)
        w,r,initial=refs[wp],refs[rp],refs[ip]
        assert r['raw']['status']=='core_complete' and r['eligible'] and r['method']=='PPCPP'
        assert r['job']['input_sha256']==sha(ip)
        prefix=w['history'];assert prefix==r['raw']['route'][:w['cut']+1]
        assert prefix[0]==initial['current'] and prefix[-1]==c['current'] and prefix[-2]==c['previous']
        assert c['old_route']==r['raw']['route'][w['cut']:]
        L=layer(c,initial,w);assert not initial['covered'];assert pts(prefix)<=L['F0']
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(prefix,prefix[1:]))
        assert L['H']==pts(prefix)&pts(initial['targets'])
        assert {tuple(z['cell']) for z in ev['evidence']}==L['H']
        for z in ev['evidence']:
            assert prefix[z['prefix_index']]==z['cell']==z['point'] and z['published_before_event'] and z['center_in_new_open_region']
        cs={k:components(L[k]) for k in ('P0','P','T','U','F')}
        # U components are descriptive only. Their immediate separator neighbors are not inferred paths.
        sep=[]
        for cc in cs['U']:
            neighbors={(x+dx,y+dy) for x,y in cc for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))}-L['U']
            sep.append(dict(task_count=len(cc),adjacent_completed=len(neighbors&L['H']),adjacent_deferred=len(neighbors&L['D']),adjacent_blocked=len(neighbors&L['blocked']),adjacent_free_nontask=len((neighbors&L['F'])-L['P'])))
        m=meta[ident]
        row=dict(id=ident,base_id=m['base_id'],family=m['family'],size=m['size'],event=m['event'],progress=m['progress'],counts={k:len(v) for k,v in L.items()},components={k:len(v) for k,v in cs.items()},U_sizes=[len(v) for v in cs['U']],history_steps=len(prefix)-1,history_verified=True,history_contract='原生格心四邻接执行前缀；当前接口固定H，未扩大重放信用',road_geometry_separate=False,source_input=str(SOURCE/'inputs'/f'{ident}.json'),source_initial=ip,source_preparation=rp,source_witness=wp,separator_contacts=sep)
        rows.append(row);packs[ident]=dict(id=ident,layers={k:packed(v) for k,v in L.items()},components=cs,prefix=prefix,current=c['current'],base=c['base'],previous=c['previous'],input_sha256=sha(SOURCE/'inputs'/f'{ident}.json'))
    write('inventory.json',rows);write('layers_and_components.json',packs)
    summary=dict(states=54,base_geometries=len({r['base_id'] for r in rows}),P0_connected=sum(r['components']['P0']==1 for r in rows),P_connected=sum(r['components']['P']==1 for r in rows),T_connected=sum(r['components']['T']==1 for r in rows),U_fragmented=sum(r['components']['U']>1 for r in rows),history_verified=sum(r['history_verified'] for r in rows),events={k:dict(states=len(v),U_fragmented=sum(r['components']['U']>1 for r in v),U_components_histogram=dict(Counter(r['components']['U'] for r in v))) for k in sorted({r['event'] for r in rows}) for v in [[r for r in rows if r['event']==k]]},no_new_solver_calls=True)
    write('summary.json',summary)
    selected=[]
    for family in ('I','L','Z'):
        group=[r for r in rows if r['family']==family]; base=min(r['base_id'] for r in group);group=[r for r in group if r['base_id']==base]
        for progress in (min(r['progress'] for r in group),max(r['progress'] for r in group)):
            row=min((r for r in group if r['progress']==progress),key=lambda r:r['id']);selected.append(row['id']);picture(row['id'],packs[row['id']],row['id']+'：连续任务区域与真实巡检历史')
    # Frozen G1 contrast: same plotting semantics, no invented connecting road or history.
    gpath=ROOT/'障碍后片区两阶段规则有限验证_v0.1_20261023/inputs/G1-A__history.json';g=read(gpath)
    gf=ROOT/'障碍后片区两阶段规则有限验证_v0.1_20261023/final_receipt.json';gfdata=read(gf);assert sha(gpath)==gfdata['files']['inputs\\G1-A__history.json'] if 'inputs\\G1-A__history.json' in gfdata['files'] else sha(gpath)==gfdata['files']['inputs/G1-A__history.json']
    gp=pts(g['published_targets']);gl={k:set() for k in ('H','D','added','blocked')};gl.update(P0=gp,P=gp,T=gp,U=gp,F=pts(g['free']),F0=pts(g['free']))
    gdata=dict(layers={k:packed(v) for k,v in gl.items()},prefix=[],base=g['base'],current=g['current'])
    gc=components(gp);picture('G1_disconnected_control',gdata,'对照：G1起始任务本来就是孤立小块，中间不是已检道路')
    write('selection.json',dict(policy='I/L/Z各字典序最小基底，最小/最大既有进度，状态ID平局；不按结果选择',selected=selected,G1_task_components=len(gc),G1_P=len(gp),G1_F=len(gl['F'])))
    header='|状态|事件|P0/P/T/U分量|H/U/D格数|U各片格数|历史来源|\n|---|---|---|---|---|---|\n'
    table=header+'\n'.join(f"|{r['id']}|{r['event']}|"+'/'.join(str(r['components'][k]) for k in ('P0','P','T','U'))+'|'+ '/'.join(str(r['counts'][k]) for k in ('H','U','D'))+f"|{r['U_sizes']}|已核旧原生前缀|" for r in rows)
    text=(f"# 连续道路地图盘点\n\n54状态来自{summary['base_geometries']}个基底，不是54张独立地图。"
          f"原始任务区域P0连通{summary['P0_connected']}/54，事件后发布区域P连通{summary['P_connected']}/54；剩余U分离{summary['U_fragmented']}/54。\n\n"
          "这与最新G1等孤立任务块不同：项目原有道路形任务区域并未全部断开，不能把局部简化实验说成整个项目地图不连续。\n\n"
          "54份H均可追溯到9次旧PPCPP准备路线的实际截断前缀；逐格集合及保存中心见证一致。但它们是原生四邻接/格心历史，后来的中心区接口把H固定输入，没有重新执行斜向历史或扩大信用。不能据此声称已有连续斜向事件实验。\n\n"
          "没有单独的工程道路边界字段，P是任务区域模型，F通常包含宽的道路外可飞空间；这不是现场安全许可，也未验证真实道路尺度。\n\n"
          "straight/corner是新增区域事件，obstacle才是障碍事件，必须分别报告，不能把54状态统称54个障碍场景。\n\n"
          + '\n'.join(f"- {k}：{v['states']}状态，U分离{v['U_fragmented']}；分量分布{v['U_components_histogram']}。" for k,v in summary['events'].items())+
          "\n\n## 下一步边界\n\n先看地图是否符合研究场景。U分量只是描述，不自动等于规则片区；旧规则要求原标签不相接，与连续P不能直接套用。完整真实输入可复用作快照研究，障碍输入还需另证旧实际直达路线是否受阻，不能以存在障碍代替阻断证据。本轮没有判定规则触发、没有跑候选、没有按收益选图。\n\n[地图对照](地图对照.html) · [全54状态](01_完整地图层与历史来源表.md) · [结构细表](02_连续性与剩余分片结构.md)\n")
    write('00_通俗结论与地图入口.md',text)
    write('01_完整地图层与历史来源表.md','# 地图层与来源\n\nP0=prep输入published_targets，P=事件published_targets，T=targets=P∩F，H=covered，D=(P−F)−H，U=T−H=P−H−D。已采格后被封堵仍保留H，不重复计入D。无单独道路边界字段。\n\n'+table+'\n\n逐状态绝对来源路径与完整成员见inventory.json及layers_and_components.json。')
    write('02_连续性与剩余分片结构.md','# 四邻接结构描述，不是片区算法\n\n'+table+'\n\nseparator_contacts只统计各U分量边界邻接的已检/暂缓/障碍/可飞非任务格，类别可重合（已检格后来被封堵）。它不是片间最短路或独立因果归因。细节见inventory.json。连通性由栈遍历计算，verify用独立并查集复核。')
    gallery=''.join(f'<section id="{i}"><h2>{html.escape(i)}</h2><img src="figures/{i}.png" alt="{i}三层地图"><p>保存输入，不生成新轨迹。</p></section>' for i in selected)
    trs=''.join('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in (r['id'],r['event'],r['components']['P0'],r['components']['P'],r['components']['U'],r['U_sizes'],'旧格心前缀已核'))+'</tr>' for r in rows)
    page='<!doctype html><html lang="zh"><meta charset="utf-8"><title>连续道路与剩余任务地图</title><style>body{font:16px Microsoft YaHei,sans-serif;max-width:1560px;margin:24px auto;padding:0 20px;background:#f4f7fa;color:#19344e}section{background:white;padding:18px;margin:24px 0;border-radius:8px}img{width:100%;height:auto}table{border-collapse:collapse;background:white;width:100%}td,th{padding:8px;border:1px solid #ccd5df}h1{font-size:28px}.note{padding:16px;background:#fff3d8}</style><h1>道路连续，不代表剩余任务始终连续</h1>'
    page+=f'<div class="note">54状态：P0连通{summary["P0_connected"]}，P连通{summary["P_connected"]}，U分离{summary["U_fragmented"]}。不是54个独立几何；非新算法实验。原历史为四邻接格心轨迹，不能冒充斜向实际执行。</div>'+gallery
    page+='<section><h2>对照：近期G1诊断地图不是连续道路</h2><img src="figures/G1_disconnected_control.png" alt="G1孤立任务块"><p>任务20格、可飞域759格，三个分离任务块；空白原本没有采集责任。</p></section><h2>54状态完整索引</h2><table><tr><th>状态</th><th>事件</th><th>P0分量</th><th>P分量</th><th>U分量</th><th>U大小</th><th>历史</th></tr>'+trs+'</table></html>'
    write('地图对照.html',page)
    write('source_guards.json',GUARDS)
    write('workload.json',dict(counts=dict(COUNTS),seconds=time.perf_counter()-start,new_core=0,new_post=0,new_shortest_paths=0,new_visibility=0,new_routes=0,component_traversals_are_new=True))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
