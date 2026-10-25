"""Post-analysis explanatory reports and fixed figures; performs no searches."""
import html
from tail_analysis import H,S,read,save,csvsave
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(str(x) for x in row)+'|' for row in rows])
def fmt(x):return f'{x:.4f}' if isinstance(x,float) else str(x)
def figure(ex,a):
    name=ex['case'];c=read(S/'inputs'/f'{name}.json');st=next(s for s in read(S/'states.json') if s['name']==name)
    unit=20;pw=st['w']*unit+65;ph=st['h']*unit+135
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{2*pw}" height="{ph}" viewBox="0 0 {2*pw} {ph}"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Arial,sans-serif;font-size:12px}}</style>',f'<text x="15" y="17">{html.escape(name)} / {ex["view"]} / rep={ex["rep"]} / post-hoc fixed selection</text>', '<text x="15" y="35">blue: before completion; red: return tail; light blue: initial H; dark gray: obstacle; gray+blue edge: covered then blocked</text>']
    data=dict(selection=ex,input_sha256=__import__('tail_analysis').sha(S/'inputs'/f'{name}.json'),methods={})
    for panel,method in enumerate(('PPCPP','P2_MULTI')):
        r=next(r for r in a['routes'] if r['case']==name and r['method']==method and r['rep']==ex['rep']);raw=read(S/'outputs'/f'{name}__{ex["rep"]}__{method}.json')['result']['raw'];route=raw['route'];data['methods'][method]=r
        ox=panel*pw+25;oy=105
        def xy(p):return ox+(p[0]+.5)*unit,oy+(st['h']-p[1]-.5)*unit
        parts.append(f'<text x="{ox}" y="56">{method}; L={r["L"]}, C={r["C"]}, R={r["R"]}, dF={r["dF"]}, X={r["X"]}</text>')
        parts.append(f'<text x="{ox}" y="74">E={r["E"]}, base={c["base"]}; {r["seconds"]:.6f}s; {"TIMELY" if r["timely"] else "LATE"}</text>')
        f=set(map(tuple,c['free']));h=set(map(tuple,c['covered']))
        for p in map(tuple,c['published_targets']):
            x,y=xy(p);color='#555' if p not in f else '#b7d3ea' if p in h else '#e8efdb';stroke='#3399df' if p in h and p not in f else 'white'
            parts.append(f'<rect x="{x-unit/2}" y="{y-unit/2}" width="{unit}" height="{unit}" fill="{color}" stroke="{stroke}" stroke-width="1"/>')
        for segment,color,width in ((route[:r['C']+1],'#2259bd',1.5),(route[r['C']:],'#d52224',2.5)):
            pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,segment));parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" opacity="0.85"/>')
        for label,p,color,offset in [('B',c['base'],'#000',(-12,0)),('S',c['current'],'#a500bf',(4,-5)),('E',r['E'],'#f18a00',(4,12))]:
            x,y=xy(p);parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="white" stroke-width="0.5"/><text x="{x+offset[0]}" y="{y+offset[1]}" font-weight="bold" fill="{color}">{label}</text>')
    parts+=['</svg>'];(H/'figures'/f'{name}.svg').write_text('\n'.join(parts),encoding='utf8');save(H/'figures'/f'{name}.json',data)
def report():
    a=read(H/'analysis.json');(H/'figures').mkdir()
    for ex in a['examples']:figure(ex,a)
    main=a['views']['timely'];legal=a['views']['legal'];me=main['summary']['events'];le=legal['summary']['events'];sig=main['signal']
    rows=[]
    for s in main['states']:
        means=s['mean'];rows.append([s['case'],s['n'],*[fmt(means[k]) if means else '不可用' for k in ('dL','dC','dR','ddF','dX')],s['labels']['return_major'] if s['labels'] else '不可用'])
    lines=['# 复杂障碍末端返航只读归因报告','', '2026-10-21。已封存，待负责人审核。','',
      '## 结论与边界','',
      f'主及时视图达到预登记有限重复信号：{len(sig["states"])}个完整三种子障碍状态，覆盖{len(sig["families"])}布局族、{len(sig["geometries"])}个尺寸×布局几何ID，均为ΔL>0且返航差≥完整差50%。所有入选状态三种子均同向并满足该标签。只说明成本现象重复，不证明贪心、捕食者、恢复目标等是原因，不证明新机制有收益。','',
      f'全部{len(a["routes"])}条完整路线的X值集合为{sorted({r["X"] for r in a["routes"]})}：两方法从各自完成位置均走图最短返航。差异在于末端到基地的图距离，不是返航寻路本身绕远。换末端会改变覆盖顺序和前段代价，不能把ΔdF直接许诺为可省步数，也不重新批准LAST规则。','',
      '## 分母与两种视图','',
      table(['视图','障碍配对','障碍状态/完整3种子','控制配对/状态','ΔL>0配对','返航主要正项','返航超过总差','前段主要正项'],[[label,v['summary']['events']['pairs'],f'{v["summary"]["events"]["states"]}/{v["summary"]["events"]["full_three_seed_states"]}',f'{v["summary"]["control"]["pairs"]}/{v["summary"]["control"]["states"]}',v['summary']['events']['positive_pairs'],v['summary']['events']['return_major'],v['summary']['events']['return_over_total'],v['summary']['events']['pre_major']] for label,v in [('主:严格<20s',main),('附:全部合法含迟到',legal)]]),'',
      f'P2迟到{len(a["late_returns"])}次，最大{max(r["milliseconds_over"] for r in a["late_returns"]):.5f}ms，超过10ms的{sum(r["milliseconds_over"]>10 for r in a["late_returns"])}次。毫秒级超出仍严格排除，不修改20秒阈值；也不称为大幅失控。没有种子部分可用的状态：主视图各状态n为0或3。主视图缺失的大尺寸room等状态保留不可用行，不能据主视图推断全12障碍状态的无偏表现。','',
      '### 逐状态主表（PPCPP−P2，n为有效seed数）','',table(['状态','n','ΔL','ΔC','ΔR','ΔdF','ΔX','返航主要正项'],rows),'',
      '### 主视图全部状态（含控制）的布局/尺寸/进度可用分母','']
    for field in ('kind','size','progress'):
        lines+=[table([field,'配对','状态','完整3种子状态','几何ID'],[[key,v['pairs'],v['states'],v['full_three_seed_states'],v['geometries']] for key,v in main['strata'][field].items()]),'']
    lines+=['完整交叉分层及原始符号在timely_分层.csv/JSON、timely_状态.csv；legal文件独立呈现含迟到视图。进度不增加几何ID，3seed不是3张地图。同一迷宫模板的进度共享几何。','',
      '## 有符号差与分布','',
      table(['视图','ΣΔL','ΣΔC','ΣΔR','ΣΔdF','ΣΔX','状态ΔL中位[最小,最大]','状态ΔR中位[最小,最大]'],[[label,*[v['summary']['events']['signed_pair_sums'][k] for k in ('dL','dC','dR','ddF','dX')],str(v['summary']['events']['state_distribution']['dL']),str(v['summary']['events']['state_distribution']['dR'])] for label,v in [('主',main),('附',legal)]]),'',
      f'主视图24个障碍配对：ΣΔL={me["signed_pair_sums"]["dL"]}=ΣΔC({me["signed_pair_sums"]["dC"]})+ΣΔR({me["signed_pair_sums"]["dR"]})。返航差合计超过总差，是采集前段存在抵消；不把负值截成0，不把1599/798当作唯一结论或因果贡献率。按8状态等权平均ΔL={me["state_distribution"]["dL"]["equal_state_mean"]}、ΔR={me["state_distribution"]["dR"]["equal_state_mean"]}；按5几何ID等权则ΔL={me["geometry_equal_mean"]["dL"]}、ΔR={me["geometry_equal_mean"]["dR"]}，两种单位不可混用。','',
      f'四类移动的独立互斥分解（主视图障碍配对求和）：首次目标差{me["signed_pair_sums"]["dFresh"]}、历史目标差{me["signed_pair_sums"]["dHistorical"]}、本轮重复目标差{me["signed_pair_sums"]["dRepeated"]}、非目标差{me["signed_pair_sums"]["dNonTarget"]}，合计同为{me["signed_pair_sums"]["dL"]}。阶段分解与此不能叠加。本批当前T=F，所有合法落点都是目标格，所以非目标移动为0；不意味着没有连接成本。','',
      f'主视图障碍(ΔC,ΔR)符号九分类：{me["phase_sign_counts"]}。return_major与pre_major可以重叠：例如21x15_rooms_p30各占50%，不是互斥归类。返航差超过总差的2个状态：31x21_maze_p30为ΔC=-125、ΔR=133、ΔL=8；31x21_serpentine_p30为-185、255、70，不能忽略前段补偿。','',
      '## 重复信号与例外','',f'主视图满足状态：{sig["states"]}。几何ID：{sig["geometries"]}。三种子符号一致性、完整原值和阈值标签见analysis.json/views/timely/signal与timely_状态.csv。附视图单独也通过：{legal["signal"] ["passed"]}，含8个正标签状态；不借附表替主表过关。','']
    for view,v in [('主及时',main),('附含迟到',legal)]:
        lines.append(f'{view}全部反例检索：'+str({k:len(ids) for k,ids in v['counterexamples'].items()})+'。缺失类别明确为0，不制造反例；same_tail_different_total给出所有ΔR=0且ΔL!=0，不临时调整“差很多”的阈值。')
    lines+=['', '主视图有2个障碍状态同长：21x15_maze_p10、21x15_serpentine_p30，各3种子；不能说复杂障碍总导致PPCPP明显更长。附视图两个31x21_rooms状态以前段差为主要正项、返航不到50%，是返航主导解释的边界，且两状态P2均迟到。','',
      '无障碍控制主视图为2状态/6配对，ΔL总和24、ΔC=-9、ΔR=33，也呈现末端距离现象。不能据此宣称障碍独有原因；控制和事件任务量不同，不比较其绝对长度当事件效应。','',
      '## 固定事后图例','', '每族最大差/最小正差/字典序首个同长，选状态最小及时rep，已讨论迷宫p30保留去重；本批全部选rep0。采集前蓝、尾段红，重叠线不表示次数。','']
    for ex in a['examples']:lines.append(f'- [{ex["case"]}](figures/{ex["case"]}.svg)：{ex["reasons"]}，视图{ex["view"]}。')
    lines+=['',f'缺失类别：{a["missing_example_categories"]}，没有用其他族补位。各图JSON保存真实尾段、末端、基地、距离和全部指标；CSV保留原顶点索引。','',
      '## 来源、运算与停止','',f'96正式路线逐格双指标与上游analysis一致，上游verify实际通过。首次分析距离运算账：{a["distance_execution"]}。独立Dijkstra只对29个唯一(state,E)搜索，跨seed缓存67次；16次base全图BFS提供96次逻辑查询。绘图不搜索；只读verify会再执行同样次数，其实际运算账在call_ledger.json单列，不将验证次数伪称首次分析次数。普通点对图距离不是覆盖最优次序搜索。','',
      '全部原始输入、输出、states/analysis/report_data、两个seal及manifest和指标源hash在presources.json，统计脚本/规则在分析前preseal封存。新报告、绘图及verify是后续产物，由最终manifest覆盖，未冒充提前存在。原数据不改，失败清单保留为空；未修算法、加图、加seed、加预算、使用留出。','',
      '**建议仅进一步提出“完成位置与覆盖顺序联合考虑”的受控问题，交负责人审核。** 该问题有跨布局的成本依据，但没有证明固定最近基地一格、终点奖励、区域图或新增候选会奏效。当前不实现LAST升级或其他新算法。','', '已封存，待负责人审核。']
    with (H/'通俗结论与归因报告.md').open('x',encoding='utf8') as f:f.write('\n'.join(lines))
    save(H/'figure_index.json',dict(examples=a['examples'],missing=a['missing_example_categories']))
    (H/'review_packet.md').write_text('# 审核入口\n\n先读通俗结论与归因报告.md，再读protocol.md、主/附状态与分层CSV、48全部配对.csv、96路线指标与末端.csv、distance_ledger.json及analysis.json。figures有固定选例SVG/PNG和原值JSON。presources.json为全部原始来源hash，preseal.json为分析前代码/规则封存；manifest为最终全交付。\n\n只读核验：运行环境/python/python.exe -B -X utf8 本目录/tail_verify.py；不调用规划器或覆盖最优搜索，只重算普通图距离和指标。verify.log及call_ledger.json为实际执行账，按声明不自指manifest。\n\n已封存，待负责人审核，不自动开始算法开发。\n',encoding='utf8')
    print('REPORT and',len(a['examples']),'fixed SVG figures written. No new distance searches.',flush=True)
if __name__=='__main__':report()
