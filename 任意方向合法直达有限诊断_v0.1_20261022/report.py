"""Read saved evidence only: summaries, accounting and coordinate drawings."""
from pathlib import Path
from decimal import Decimal
from collections import Counter,defaultdict
import json,csv,math,hashlib
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,v):(H/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def md(n,t):(H/n).write_text(t,encoding='utf8')
def diagram(job,r,dest,rejected=None):
    src=read(H/job['payload']);c=src['input'];F=set(map(tuple,c['free']));P=set(map(tuple,c['published_targets']));U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));old=src['raw']['route'];new=r['vertices'];xmin=min(x for x,y in F);xmax=max(x for x,y in F);ymin=min(y for x,y in F);ymax=max(y for x,y in F)
    im=Image.new('RGB',(1800,1060),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    d.text((30,16),job['id'],fill='black',font=font)
    for panel,path,title,color in ((0,old,'Saved four-neighbor route | L = '+str(r['L4']),'#c04444'),(1,new,'Shortcut polyline | L = %.6f'%r['Lshortcut_display'],'#1665b5')):
        left=panel*900+36;top=112;scale=min(820/(xmax-xmin+2),800/(ymax-ymin+2));cx=left+(820-scale*(xmax-xmin+1))/2;cy=top+(800-scale*(ymax-ymin+1))/2
        def xy(p):return (cx+(p[0]-xmin+.5)*scale,cy+(ymax-p[1]+.5)*scale)
        d.text((left,65),title,fill=color,font=font)
        for x in range(xmin,xmax+1):
            for y in range(ymin,ymax+1):
                a,b=xy((x-.5,y+.5)),xy((x+.5,y-.5));fill='#444444' if (x,y) not in F else ('#fff4cf' if (x,y) in P else '#f4f4f4');d.rectangle([a,b],fill=fill,outline='#c8c8c8',width=1)
        if len(path)>1:d.line([xy(p) for p in path],fill=color,width=2)
        for p in U:
            x,y=xy(p);rad=max(2,min(4,scale/6));d.ellipse((x-rad,y-rad,x+rad,y+rad),outline='#008340',width=1)
        for p,label,co in ((c['current'],'S','#8c168c'),(c['base'],'B','#111111')):
            x,y=xy(p);d.rectangle((x-4,y-4,x+4,y+4),outline=co,width=2);d.text((x+5,y+1),label,fill=co,font=small)
        if rejected is not None and panel==1:
            a,b=xy(old[rejected['i']]),xy(old[rejected['j']]);d.line([a,b],fill='#e87600',width=4);d.text((left,925),'Orange = rejected candidate, NOT an output edge.',fill='#b65c00',font=small)
    d.text((30,968),'Green rings: required cell centers / nominal service anchors; passing cell interior earns no credit.',fill='black',font=small)
    d.text((30,995),'Dark: outside F within displayed bounding box (not necessarily a physical construction obstacle).',fill='black',font=small)
    d.text((30,1022),'Coordinates: x right, y up; S current, B base. Both panels use the identical saved task and F.',fill='black',font=small)
    im.save(dest)
def main():
    jobs=read(H/'117固定清单.json');status=read(H/'batch_status.json');rows=[];groups=defaultdict(list);entries={x['id']:x['entry'] for x in map(json.loads,(H/'actual_entries.jsonl').read_text(encoding='utf8').splitlines())};counts=Counter();auditseconds=0;stage=Counter()
    for j in jobs:
        if j['id'] not in status['completed']:continue
        r=read(H/'outputs'/(j['id']+'.json'));a=read(H/'audits'/(j['id']+'.json'));e=entries[j['id']];groups[(j['batch'],j['method'])].append((j,r));counts.update(r['counts']);counts['independent_geometry']+=a['counts']['geometry'];counts['independent_service_intersections']+=a['counts']['service_intersections'];auditseconds+=a['seconds'];stage.update(r['timing']);parts=defaultdict(lambda:[0,0.])
        for p in r['parts']:parts[p['kind']][0]+=p['L4'];parts[p['kind']][1]+=(float(p['new_interval'][0])+float(p['new_interval'][1]))/2
        row={'batch':j['batch'],'case':j['case'],'method':j['method'],'id':j['id'],'original_discrete_steps':r['L4'],'original_euclidean_length':r['L4'],'new_euclidean_length':r['Lshortcut_display'],'saving':r['saving_display'],'saving_ratio':r['saving_ratio_display'],'new_length_lower':r['Lshortcut_interval'][0],'new_length_upper':r['Lshortcut_interval'][1],'distance_budget':r['distance_budget'],'same_actual_first_order':not r['actual_order_changed'],'main_entry_seconds':e['entry_seconds'],'independent_audit_seconds':a['seconds'],'late':e['late'],'fallback':e['fallback'],'candidate_queries':r['counts']['candidate'],'candidate_rejections':sum(not q['legal'] for q in r['query_log']),'source_geometry':r['counts']['source_validation'],'output_geometry':r['counts']['output_validation'],'independent_geometry':a['counts']['geometry'],'service_intersections_main':r['counts']['service_intersections'],'service_intersections_independent':a['counts']['service_intersections'],'old_direction_changes':r['turns_original']['nonzero_direction_changes'],'new_direction_changes':r['turns_new']['nonzero_direction_changes'],'old_turn_radians':r['turns_original']['total_turn_radians'],'new_turn_radians':r['turns_new']['total_turn_radians'],'source_generation_seconds_historical':j['saved_generation_seconds'],'source_generation_budget_historical':j['saved_generation_budget']}
        for kind in ('start_to_first','between_first_services','last_to_base','empty_task_to_base'):row[kind+'_old']=parts[kind][0];row[kind+'_new']=parts[kind][1]
        rows.append(row)
    dump('117全表.json',rows)
    with (H/'117全表.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    pairs=[];by={(x['batch'],x['case'],x['method']):x for x in rows}
    for x in rows:
        k=(x['batch'],x['case'],'P2_MULTI')
        if x['method']=='PPCPP' and k in by:
            y=by[k];pairs.append({'batch':x['batch'],'case':x['case'],'PPCPP_L4':x['original_discrete_steps'],'P2_L4':y['original_discrete_steps'],'original_PPCPP_minus_P2':x['original_discrete_steps']-y['original_discrete_steps'],'PPCPP_shortcut':x['new_euclidean_length'],'P2_shortcut':y['new_euclidean_length'],'PPCPP_saving':x['saving'],'P2_saving':y['saving'],'post_PPCPP_minus_P2':x['new_euclidean_length']-y['new_euclidean_length'],'both_first_order_preserved':x['same_actual_first_order'] and y['same_actual_first_order']})
    dump('57同物理输入配对.json',pairs)
    summary=[]
    for (batch,method),rs in groups.items():
        vals=[by[(batch,j['case'],method)] for j,r in rs];old=sum(x['original_discrete_steps'] for x in vals);new=sum(x['new_euclidean_length'] for x in vals)
        summary.append({'batch':batch,'method':method,'n':len(vals),'L4_sum':old,'new_sum':new,'saving_sum':old-new,'weighted_reduction':(old-new)/old,'equal_case_mean_reduction':sum(x['saving_ratio'] for x in vals)/len(vals),'positive':sum(x['saving']>0 for x in vals),'zero':sum(x['saving']==0 for x in vals),'order_changed':sum(not x['same_actual_first_order'] for x in vals),'part_savings':{k:sum(x[k+'_old']-x[k+'_new'] for x in vals) for k in ('start_to_first','between_first_services','last_to_base','empty_task_to_base')}})
    dump('分批汇总.json',summary)
    gate=read(H/'gate_attempt_1.json');gcounts=Counter();corrections=[]
    for x in gate['results']:
        gcounts['direct_main_geometry']+=x['counts']['direct_main'];gcounts['independent_geometry']+=x['counts']['direct_independent'];gcounts['independent_service_intersections']+=x['counts']['service_independent']
        if 'output' in x:
            gcounts['main_candidate']+=x['output']['counts']['candidate'];gcounts['main_source_geometry']+=x['output']['counts']['source_validation'];gcounts['main_output_geometry']+=x['output']['counts']['output_validation'];gcounts['main_service_intersections']+=x['output']['counts']['service_intersections']
        elif x['name'].startswith('12_') or x['name'].startswith('13_'):
            actual=2 if x['name'].startswith('12_') else 3;gcounts['main_service_intersections']+=actual;corrections.append({'fixture':x['name'],'raw_direct_service_counter':x['counts']['service_main'],'actual_calls_from_frozen_expression':actual,'reason':'Expected-value expression and cross-check repeat primary hit; retain raw counter and account every actual call here. No fixture rerun.'})
    dump('门槛服务调用计数补正.json',corrections)
    formal={'routes_planned':117,'postprocessor_entries':len(status['started']),'new_polylines':len(status['completed']),'failed':int(status['failure'] is not None),'unrun':len(status['unrun']),'candidate_rejections':sum(x['candidate_rejections'] for x in rows),'geometry_preprocessing_queries':0,**dict(counts),'main_entry_seconds_sum':sum(e['entry_seconds'] for e in entries.values()),'main_entry_seconds_max':max(e['entry_seconds'] for e in entries.values()),'independent_audit_seconds_sum':auditseconds,'independent_audit_seconds_max':max(x['independent_audit_seconds'] for x in rows),'late':sum(e['late'] for e in entries.values()),'fallback':sum(e['fallback'] is not None for e in entries.values()),'phase_seconds_sum':dict(stage),'encoding_and_return_seconds_sum':sum(e['entry_seconds'] for e in entries.values())-sum(stage.values())}
    ledger={'forbidden_calls':{'coverage_planning_entries':0,'core':0,'BFS':0,'Dijkstra':0,'Astar':0,'visibility_graph_search':0,'exact_coverage':0,'closed_loop':0,'new_worlds':0,'new_seeds':0,'production_modules_imported':0},'formal':formal,'technical_gate':{'attempts':1,'fixtures':24,'registered_cases':24,'passed':24,'postprocessor_entries':11,'new_polylines':10,**dict(gcounts)},'readonly_receipt_check_geometry':0,'counting_note':'Gate source-resource rejection is an expected technical case, excluded from formal denominator. Primary service-hit repetitions in fixtures12/13 corrected by frozen expression review. Main output geometry, independent geometry and services are outside candidate cap and all separately charged.'};dump('调用与耗时总账.json',ledger)
    sm='|批次|方法|条数|原长度合计|新长度合计|减少|减少比例|正/零|实际顺序改变|\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for s in summary:sm+='|%s|%s|%d|%d|%.6f|%.6f|%.3f%%|%d/%d|%d|\n'%(s['batch'],s['method'],s['n'],s['L4_sum'],s['new_sum'],s['saving_sum'],100*s['weighted_reduction'],s['positive'],s['zero'],s['order_changed'])
    md('00_通俗报告.md','''# 任意方向合法直达：有限诊断结果

24项技术门槛第一轮全部通过，随后按冻结清单一次处理117条保存路线，全部完成并通过独立几何、信用及长度审核。失败、迟到、回退和未运行均为0。每条均有正收益，真实批零收益例为0，未补造或增加样本；零收益仅由独立标示的技术控制展示。

'''+sm+'''
这是预登记远端优先捷径规则实现的距离减少，不是最优几何差距，也未测采集顺序优化收益。本批117条实际首次服务顺序均保持；固定名义锚点后顺带信用能改变实际顺序的技术夹具也通过，故不能把“本批未改变”推广为机制永不改变。

54状态和六世界分列；六世界只在L_S、L_M、T_M有同物理输入P2。I_S、I_M、T_S只描述各自PPCPP，不拼配。54批各状态等权的减少比例另见分批汇总.json，表中比例为总长度加权，不把两者混称。三个重复seed没有作为独立样本加入。

结论支持“这些保存路线存在可实现的合法直达收益”，不支持“已经解决剩余覆盖顺序问题”或论文创新。旧四邻接排名不与新欧氏模型混合；剩余PPCPP/P2路线差不是全部顺序损失。后处理用了历史保存初始路线，历史生成耗时逐条单列，不是端到端共同20秒比较。转向次数及角度是新折线描述，不直接替代旧90度转弯指标。

模型采用单位格心、严格开放自由域、精确有理几何、即时真实中心信用及剩余距离R=E。所有输出保留原名义锚点与暂缓责任，完整边保存所替代原索引区间，欧氏长度用向外包络区间审核。几何及资源审核无未确定项；来源额度未被重置或放宽。处理后双方长度差有1组区间跨零，单列未确定，不以显示值约等于0就判相等。只构造有限可行折线，未求连续最短路径或最优证书。

完成封存停止，不进入顺序优化、新规划算法或新场景实验。完整证据见review_packet.md。
''')
    ptext='|批次|状态|原PPCPP−P2|PPCPP收益|P2收益|处理后PPCPP−P2|\n|---|---|---:|---:|---:|---:|\n'
    for p in pairs:ptext+='|%s|%s|%d|%.6f|%.6f|%.6f|\n'%(p['batch'],p['case'],p['original_PPCPP_minus_P2'],p['PPCPP_saving'],p['P2_saving'],p['post_PPCPP_minus_P2'])
    # Store outward pair differences, avoiding classification from display floats.
    for p in pairs:
        x=by[(p['batch'],p['case'],'PPCPP')];y=by[(p['batch'],p['case'],'P2_MULTI')]
        with __import__('decimal').localcontext() as cx:
            cx.prec=60;cx.rounding=__import__('decimal').ROUND_FLOOR;low=Decimal(x['new_length_lower'])-Decimal(y['new_length_upper']);cx.rounding=__import__('decimal').ROUND_CEILING;high=Decimal(x['new_length_upper'])-Decimal(y['new_length_lower'])
        p['post_difference_interval']=[str(low),str(high)];p['certified_sign']='positive' if low>0 else ('negative' if high<0 else ('zero' if low==high==0 else 'uncertain'))
    dump('57同物理输入配对.json',pairs)
    pp=''
    for b in ('54_states','6_last_responses'):
        a=[p for p in pairs if p['batch']==b];signs=Counter(p['certified_sign'] for p in a)
        pp+=f"{b}：同输入配对{len(a)}组；区间认证PPCPP较长/相等/较短/未确定为{signs['positive']}/{signs['zero']}/{signs['negative']}/{signs['uncertain']}。差值区间见57同物理输入配对.json，不用展示浮点或容差判输赢。\n\n"
    uncertain=[p['case'] for p in pairs if p['certified_sign']=='uncertain']
    md('01_全量与配对结果.md','# 全量与配对\n\n117全表.json/CSV逐条提供三类段账、长度区间、信用顺序、源生成耗时、入口与独立审计耗时、候选及审计计数、回退和方向变化。完整原trace交叉及每条新边原索引证据保存在outputs。原trace交叉按原移动计数；跨trace的新线段不按比例虚构一种“真实local长度”。\n\n'+pp+'未确定组：'+','.join(uncertain)+'。以下数值仅为近似展示，胜负以区间结论为准。\n\n'+ptext+'\nI_S、I_M、T_S没有同输入P2输出，未配对。57组是54状态及3六世界分批记录，不作为57个独立测试场景推断普遍优势。\n')
    md('02_合同门槛预算与独立审核.md',f'''# 合同、门槛与预算

执行稿D1—D5逐字原文保存在执行稿原文快照.md；模型不另选间隙或容差。主几何法在精确穿格事件参数和其间开区间内作全域判定；这是线段在有限轴对齐边界间归属恒定的完备分段，不是固定步长采样。独立法检查线段与包围盒内全部相关禁止格闭方形的精确slab相交，另排除包围盒外边界。障碍角/边重合均拒绝；四自由象限交点允许。两法没有相互导入或共享谓词。

24门槛在运行前保存每项唯一案例与手算预期，不超过每项4案例；第一轮24/24通过，没有改预期、改模型或调候选。包括2变√2正控制、相同路径的中间必检保护、空任务/零长/跨原索引闭环、起点信用、顺带顺序改变、资源恰好/超限及次数/软截止回退。所有内部主源验收/候选/输出审核、独立审核、中心信用次数另记，并非把24或96冒充全部计算上限。门槛12/13检查表达式重复调用主信用谓词，原局部计数未覆盖重复；已根据冻结源码在门槛服务调用计数补正.json和总账中完整补记，未补跑。

冻结117清单及源码后只运行一批。候选总上限479232，实际{counts['candidate']}；原路线验收上限11262实际{counts['source_validation']}，输出主几何上限11262实际{counts['output_validation']}，独立几何上限11262实际{counts['independent_geometry']}。主/独立服务交点各自上限1369618，实际分别{counts['service_intersections']}/{counts['independent_service_intersections']}。几何预处理没有可视图或额外LOS查询；F构建、原索引/锚点构建时间包含主入口。候选拒绝{formal['candidate_rejections']}次，均计入候选账，没有因拒绝而补路线。

主入口从JSON解析前到完整输出编码后计时，含源几何检查、候选、输出审核、信用、区间长度、段账及方向指标；最大{formal['main_entry_seconds_max']:.6f}秒，总{formal['main_entry_seconds_sum']:.6f}秒，均在20秒内。18秒软截止和次数回退没有在真实批触发；仅技术控制验证了回退，不能称硬实时保证。输入载荷从原包抽取及来源哈希冻结是事前只读准备，历史规划生成未重跑，成本逐条保留。

独立审核总{auditseconds:.6f}秒，计时外另计，每输出只审一次；主/独立几何及服务计数上限在正式批前冻结。独立信用按每任务最早(edge,t)求首次到达，长度以60位精度的独立向外区间复核主50位区间。资源使用L4≤E、各新边对应不重不漏原区间的三角不等式及整体长度区间双重核对；没有给临界容差。

verify.py的audit_one仅读保存输入及新折线，不生成候选，已逐条执行并写audits。命令行默认再验封存哈希和独立审计回执，不重复几何调用；其新增几何计数为0。需要重新执行几何审核属于另一次有计费的复核，不能把重复调用隐去。来源哈希冲突/生产异常/最终非法原定立即停余批，本批未发生。

技术准备曾在正式前假定旧54包具有completion_manifest而停止，失败日志保留；修复为沿用上一封存来源哈希，新六世界来源核对其原封存清单。只读schema检查另有一次错误后修正，均不是正式后处理失败，也未消耗正式路线槽。不改变旧包。无新规划/核心/图搜索/覆盖精确搜索/闭环/地图/seed。
''')
    (H/'figures').mkdir(exist_ok=True);examples=[]
    pos=next((j,r) for j,r in groups[('54_states','PPCPP')] if r['saving_display']>0);rej=next((j,r) for j,r in groups[('54_states','PPCPP')] if any(not q['legal'] for q in r['query_log']))
    diagram(*pos,H/'figures'/'01_actual_positive.png');rejected=next(q for q in rej[1]['query_log'] if not q['legal']);diagram(*rej,H/'figures'/'02_actual_rejection.png',rejected=rejected)
    examples=[{'kind':'actual_positive','id':pos[0]['id'],'figure':'figures/01_actual_positive.png'},{'kind':'actual_rejected_candidate','id':rej[0]['id'],'query':rejected,'figure':'figures/02_actual_rejection.png'},{'kind':'actual_zero','count':0,'note':'No zero saving route among fixed117; do not manufacture one.'},{'kind':'technical_zero_control_only','fixture':'21_中间中心必检','source':'gate_attempt_1.json','L4':2,'new_length':2}];dump('可复核实例.json',examples)
    md('03_实例与结论边界.md','''# 可复核实例

示例选择规则为固定清单中首条正收益、首条含拒绝查询的PPCPP路线，仅用于解释，不代替全量统计。

![真实正收益](figures/01_actual_positive.png)

![真实候选拒绝](figures/02_actual_rejection.png)

橙色线是实际被拒绝的候选，绝非可飞输出。所有绿色圈为原未完成任务的指定中心及名义锚点；新折线保留中心责任。暗格仅表示显示包围盒中F外禁止域，不把所有暗格都说成新增施工障碍。原起点、基地、任务与通行域均来自该次输入。

真实117条均有正收益，因此无真实零收益图。零收益机制控制见门槛21：同一自由2×2格，原(0,0)→(1,0)→(1,1)，中间(1,0)必检，锁住该锚点，输出仍为2；门槛20中间无任务才可直接缩至√2。两者是技术夹具，未冒充真实样本。

结论仅适用于本固定开发保存批与预登记规则；没有留出、新地图或新seed证据。名义顺序固定不构成严格顺序最优；即使本批真实首次服务均相同，也只证明这些输出满足该顺序，不证明几何最优。剩余差不能全部叫顺序损失。停止，交负责人审核。
''')
    md('review_packet.md','''# 审核入口

先读00_通俗报告.md，配对及完整证据见01_全量与配对结果.md、117全表.json/CSV、57同物理输入配对.json；合同/门槛/实际成本见02_合同门槛预算与独立审核.md；图示见03_实例与结论边界.md。

24门槛预登记.json→gate_attempt_1.json证明先门槛；frozen_manifest.json绑定通过门槛后的脚本、固定清单、成本上限及来源；117固定清单.json→inputs/outputs/audits绑定每条完整原载荷、新折线每边原索引、全任务实际首次信用及独立审核。actual_entries.jsonl为逐入口计时，batch_status.json保留固定分母和停止状态；调用与耗时总账.json合并实际主/独立/门槛费用，门槛服务调用计数补正.json保留局部计数补记原因。

只读核验.ps1默认复核封存哈希、来源及已保存独立审核回执，新几何调用0；不是重新运行后处理。独立几何审核已通过verify.py/audit_one逐条执行一次，保存于audits，其几何和中心交点次数全部计费。正式后处理不允许重复执行。

正式117/117合法完成，24/24门槛通过；原规划/核心/图搜索/精确覆盖/闭环全0。实际几何查询、后处理与新折线非0。无端到端算法排名、无最优分解、无创新证明。旧包/冻结源/留出未变，未提交推送；完成封存后停止，不自动继续。
''')
    print(json.dumps({'formal_completed':len(rows),'pairs':len(pairs),'candidate':counts['candidate'],'independent_geometry':counts['independent_geometry'],'main_geometry':counts['candidate']+counts['source_validation']+counts['output_validation'],'status':'reports_generated_no_new_geometry'},ensure_ascii=False))
if __name__=='__main__':main()
