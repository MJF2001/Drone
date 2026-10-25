"""Development comparison report export from saved evidence only; no solver calls."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,math,html
from PIL import Image,ImageDraw,ImageFont
from center_bench_v01_20261022.bench import H as HERE,R as ROOT,read,dump,sha
from datetime import datetime,timezone
def now():return datetime.now(timezone.utc).isoformat()

FONT='C:/Windows/Fonts/msyh.ttc'
def fnt(size):
    return ImageFont.truetype(FONT,size)
def value(r):
    return Fraction(r['n'],r['d'])
def point(raw):
    return tuple(value(v) for v in raw)
def ptext(raw):
    return '('+', '.join(str(v) for v in point(raw))+')'
def exact_text(expr):
    terms=[]
    for row in expr['terms']:
        c=value(row['c']);r=row['r']
        terms.append(str(c) if r==1 else ('' if c==1 else str(c)+'·')+'√'+str(r))
    return ' + '.join(terms) or '0'
def approx(expr):
    return sum(float(value(t['c']))*math.sqrt(t['r']) for t in expr['terms'])
def sumc(rows):
    c=Counter()
    for row in rows:
        c.update(row)
    return c

class Canvas:
    def __init__(self,w,h):
        self.image=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.image)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(self,xy,text,size=20,fill='#17263c'):
        self.d.text(xy,text,font=fnt(size),fill=fill)
        self.svg.append(f'<text x="{xy[0]}" y="{xy[1]+size}" fill="{fill}" font-family="Microsoft YaHei,sans-serif" font-size="{size}">{html.escape(text)}</text>')
    def line(self,pts,fill,width=3,dash=False,arrow=False):
        pts=[(float(x),float(y)) for x,y in pts]
        if dash:
            for a,b in zip(pts,pts[1:]):
                length=math.dist(a,b)
                for j in range(0,int(length),12):
                    self.d.line([tuple(a[k]+(b[k]-a[k])*t/max(length,1) for k in (0,1)) for t in (j,min(j+6,length))],fill=fill,width=width)
        else:
            self.d.line(pts,fill=fill,width=width)
        dashed=' stroke-dasharray="6 6"' if dash else ''
        self.svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{fill}" stroke-width="{width}"{dashed}/>')
        if arrow and len(pts)==2:
            a,b=pts;dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length>15:
                mid=((a[0]+b[0])/2,(a[1]+b[1])/2);u=(dx/length,dy/length)
                wings=[(mid[0]-8*u[0]+4*u[1],mid[1]-8*u[1]-4*u[0]),mid,
                       (mid[0]-8*u[0]-4*u[1],mid[1]-8*u[1]+4*u[0])]
                self.line(wings,fill,width=2)
    def rect(self,box,fill,outline='#b7c2d0',width=1,dash=False):
        if dash:
            x0,y0,x1,y1=box
            self.line([(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)],outline,width,True)
        else:
            self.d.rectangle(box,fill=fill,outline=outline,width=width)
            self.svg.append(f'<rect x="{box[0]}" y="{box[1]}" width="{box[2]-box[0]}" height="{box[3]-box[1]}" fill="{fill or "none"}" stroke="{outline}" stroke-width="{width}"/>')
    def circle(self,xy,r,fill,outline='#fff',width=1):
        x,y=xy;self.d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=outline,width=width)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')
    def save(self,path):
        self.image.save(path.with_suffix('.png'))
        path.with_suffix('.svg').write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')

def stats(values):
    import statistics
    vals=sorted(values)
    return {'N':len(vals),'mean':statistics.mean(vals) if vals else None,'median':statistics.median(vals) if vals else None,
            'P95':vals[math.ceil(.95*len(vals))-1] if vals else None,'max':max(vals) if vals else None}
def avg(values):return sum(values)/len(values) if values else None
def pct(v):return '未定义' if v is None else f'{100*v:.3f}%'
def num(v):return '未定义' if v is None else f'{v:.6f}'
def write_csv(path,rows):
    import csv
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def compare_cert(a,b):
    from center_bench_v01_20261022.exact import Expr
    return (Expr.load(a['length_certificate']['exact'])-Expr.load(b['length_certificate']['exact'])).sign()

def route_figure(pair,loaded,title,path,credit_example=False):
    c=Canvas(1500,970);c.text((35,20),title,28);c.text((35,66),pair['case']+' / seed '+str(pair['seed'])+'；共同公开快照完整虚拟执行',21)
    for panel,view in enumerate(('B','C')):
        x=loaded[(pair['case'],pair['seed'],view)];inp=x['input'];pathpoints=x['record']['path'];F=inp['free'];P=inp['published_targets'];initial=inp['covered']
        xs=[p[0] for p in F];ys=[p[1] for p in F];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        scale=min(620/(xmax-xmin+1),560/(ymax-ymin+1));offset=panel*740
        def xy(p):return offset+70+(float(p[0])-xmin+.5)*scale,730-(float(p[1])-ymin+.5)*scale
        c.text((offset+35,110),view+(' PPCPP＋直达' if view=='B' else ' P2＋同版直达')+' / '+x['termination'],24)
        for q in F:
            a=xy((q[0]-.5,q[1]+.5));b=xy((q[0]+.5,q[1]-.5));c.rect((*a,*b),'#edf2f7','#e5ebf3',1)
        for q in P:
            sx,sy=xy(q);radius=max(2,min(4,scale*.17));c.circle((sx,sy),radius,'#7191bd')
        for q in initial:c.circle(xy(q),max(2,min(4,scale*.18)),'#9aa2aa')
        c.line([xy(q) for q in pathpoints],'#087f6b' if view=='C' else '#1168bd',2)
        evs=x['record']['metrics']['diagonal_offcenter_witnesses']
        if credit_example and evs:
            ev=evs[0];a,b=pathpoints[ev['edge']:ev['edge']+2];c.line([xy(a),xy(b)],'#c641ab',5)
            t=ev['cell'];sx,sy=xy(t);c.rect((*xy((t[0]-.2,t[1]+.2)),*xy((t[0]+.2,t[1]-.2))),'#f6dfaa','#ac791c',2)
            w=ev['evidence']['witness']['point'];c.circle(xy(point(w)),6,'#e79a25')
        c.circle(xy(inp['current']),7,'#bb3434');c.circle(xy(inp['base']),7,'#17263c')
        c.text((offset+35,771),'距离 '+num(x['record']['metrics']['length'])+' m；共同端到端 '+num(x['time'])+' s',20)
        c.text((offset+35,811),'未过格心斜段首次信用任务 '+str(x['record']['metrics']['diagonal_offcenter_first_credit_tasks']),20)
    c.text((35,870),'灰：给定历史；蓝点：公开任务；红：当前点；黑：基地。完整虚拟执行，不是新连续事件历史。',20)
    c.text((35,910),'原格心锚点保留；有首次斜段信用也不代表全历史从未经过格心，更不等于算法创新。',20)
    c.save(path)

def scatter(states,path):
    c=Canvas(1320,850);c.text((35,20),'54状态等权：B相对C的距离与计算时间（含预算参照）',27)
    c.text((35,67),'横轴：B比C多走比例；纵轴：C/B共同端到端时间倍率（对数刻度）。不构造综合优越分数。',19)
    xs=[100*s['B_C_distance_extra'] for s in states];ys=[math.log10(s['C_B_time_ratio']) for s in states]
    xmin,xmax=min(min(xs)-2,-2),max(xs)+2;ymin,ymax=min(min(ys)-.1,0),max(ys)+.15
    def xy(x,y):return 140+(x-xmin)/(xmax-xmin)*1040,700-(y-ymin)/(ymax-ymin)*550
    c.line([(140,150),(140,700),(1180,700)],'#4a596e',2)
    for k in range(6):
        x=xmin+(xmax-xmin)*k/5;sx,sy=xy(x,ymin);c.line([(sx,150),(sx,700)],'#dce4ed',1);c.text((sx-20,715),f'{x:.1f}%',17)
    for k in range(5):
        y=ymin+(ymax-ymin)*k/4;sx,sy=xy(xmin,y);c.line([(140,sy),(1180,sy)],'#dce4ed',1);c.text((35,sy-12),f'{10**y:.2f}×',17)
    if xmin<=0<=xmax:c.line([xy(0,ymin),xy(0,ymax)],'#b13f3f',2,True)
    colors={'small':'#2a7d9f','medium':'#8c61b0','large':'#c87935'}
    for s in states:c.circle(xy(100*s['B_C_distance_extra'],math.log10(s['C_B_time_ratio'])),5,colors[s['size']])
    c.text((160,780),'蓝：small  紫：medium  橙：large；54状态共享9基础地图与历史，不能当54独立实地图。',19)
    c.save(path)

def strata_figure(strata,path):
    c=Canvas(1320,750);c.text((35,20),'预定尺寸/事件分层：直达距离增量与B/C差距',27)
    c.text((35,66),'每状态先平均三个seed，再层内状态等权；正直达收益为A→B缩短，正B/C差距为B更长。',19)
    c.text((35,120),'层（状态数）',21);c.text((410,120),'A→B平均缩短',21);c.text((850,120),'B相对C平均多走',21)
    for i,s in enumerate(strata):
        y=180+75*i;c.text((35,y),s['factor']+' / '+s['value']+' ('+str(s['states'])+')',21)
        for x,key,col in ((420,'A_B_saving','#2c7b9d'),(870,'B_C_distance_extra','#b96e39')):
            v=s[key];c.rect((x,y+4,x+max(1,abs(v)*600),y+30),col,col,1);c.text((x+205,y),pct(v),20)
    c.save(path)

def main(seal=False):
    import statistics
    assert not (HERE/'final_receipt.json').exists()
    plan=read(HERE/'plan.json');status=read(HERE/'status.json')
    assert status['failure'] is None and len(status['formal_completed'])==324 and len(status['technical_completed'])==12
    assert read(HERE/'verify_receipt.json')['passed']
    metadata={x['id']:x for x in read(HERE/'history_evidence.json')}
    rows=[];loaded={};native_counts=Counter();main_counts=Counter();audit_counts=Counter();cold=[];walls=[];postscope=Counter();attempts=[]
    for job in plan['formal']:
        file=HERE/'outputs'/(job['id']+'.json');x=read(file);assert x['passed']
        native_counts.update(x['native_counts_actual']);audit_counts.update(x['independent']['counts']);cold.append(x['cold_import_seconds']);walls.append(x['worker_wall_seconds']);postscope.update(x['query_scope_schema'])
        attempts.append({'job':job,'output_sha256':sha(file),'termination':x['timing']['termination'],'timing':x['timing'],'worker_wall_seconds':x['worker_wall_seconds'],
            'cold_import_seconds':x['cold_import_seconds'],'independent_seconds':x['independent_wall_seconds'],'native_counts':x['native_counts_actual']})
        for view,record in x['views'].items():
            m=record['metrics'];t=x['timing'];tm=t['raw_common_end_to_end'] if view in ('A','C0') else t['combined_end_to_end']
            row={'case':job['case'],'size':metadata[job['case']]['size'],'event':metadata[job['case']]['event'],'seed':job['seed'],'view':view,
                'method':job['method'],'termination':t['termination'],'native_status':t['native_status'],'passed':x['passed'],
                'time_seconds':tm,'native_entry_seconds':t['native_entry_seconds'],'post_increment_seconds':t['post_increment'] if view in ('B','C') else 0,
                'native_late':t['native_late'],'raw_stage_late':t['raw_stage_late'],'post_late':t['post_late'] if view in ('B','C') else False,
                'combined_late':t['combined_late'] if view in ('B','C') else t['raw_stage_late'],**m}
            row.update({f'turns_{k}':m['turns'].get(k,0) for k in ('total','90','180','other')})
            if m['stages']:
                for k in ('to_first_witness','between_first_last_witness','after_last_witness_return'):
                    cert=m['stages'][k];row[k+'_meters']=(float(value(cert['low']))+float(value(cert['high'])))/2
            rows.append(row);main_counts.update(record['counts'])
            loaded[(job['case'],job['seed'],view)]={'record':record,'input':x['input'],'termination':t['termination'],'time':tm,'row':row}
    write_csv(HERE/'正式648视图完整指标.csv',rows);dump(HERE/'正式逐入口来源与阶段.json',attempts)
    pairs=[]
    for case in sorted(metadata):
        for seed in (20261020,20261021,20261022):
            data={v:loaded[(case,seed,v)]['row'] for v in ('A','B','C0','C')};a,b,c0,c=[data[v] for v in ('A','B','C0','C')]
            natural=all(data[v]['termination']=='natural' for v in ('B','C'))
            timely=natural and all(not data[v][k] for v in ('B','C') for k in ('native_late','raw_stage_late','post_late','combined_late'))
            pairs.append({'case':case,'size':metadata[case]['size'],'event':metadata[case]['event'],'seed':seed,'natural_pair':natural,'timely_natural_pair':timely,
                'A_B_saving':(a['length']-b['length'])/a['length'],'B_C_distance_extra':(b['length']-c['length'])/c['length'],
                'B_C_time_saving':(c['time_seconds']-b['time_seconds'])/c['time_seconds'],'C_B_time_ratio':c['time_seconds']/b['time_seconds'],
                'B_C_extra_meters':b['length']-c['length'],'B_C_saved_seconds':c['time_seconds']-b['time_seconds'],
                'A_B_exact_sign':compare_cert(a,b),'B_C_exact_sign':compare_cert(b,c),'A':a['length'],'B':b['length'],'C0':c0['length'],'C':c['length'],
                'time_B':b['time_seconds'],'time_C':c['time_seconds']})
    dump(HERE/'同状态同seed配对.json',pairs)
    keys=('A_B_saving','B_C_distance_extra','B_C_time_saving','C_B_time_ratio','B_C_extra_meters','B_C_saved_seconds')
    def states_of(selection):
        out=[]
        for case in sorted({p['case'] for p in selection}):
            pp=[p for p in selection if p['case']==case];out.append({'case':case,'size':metadata[case]['size'],'event':metadata[case]['event'],'seed_count':len(pp),**{k:avg([p[k] for p in pp]) for k in keys}})
        return out
    states=states_of(pairs);dump(HERE/'54状态等权结果.json',states)
    def summary(selection):
        ss=states_of(selection)
        return {'pairs':len(selection),'states':len(ss),'excluded_pairs':162-len(selection),'state_equal_means':{k:avg([s[k] for s in ss]) for k in keys},
            'total_distance_B_C_extra':sum(p['B'] for p in selection)/sum(p['C'] for p in selection)-1 if selection else None,
            'total_distance_A_B_saving':1-sum(p['B'] for p in selection)/sum(p['A'] for p in selection) if selection else None,
            'quality_B_longer_equal_shorter':[sum(p['B_C_exact_sign']==sign for p in selection) for sign in (1,0,-1)],
            'A_B_shorter_equal_longer':[sum(p['A_B_exact_sign']==sign for p in selection) for sign in (1,0,-1)],
            'B_slower_pairs':sum(p['B_C_saved_seconds']<0 for p in selection)}
    subsets={name:summary(ss) for name,ss in [('all',pairs),('natural',[p for p in pairs if p['natural_pair']]),('timely_natural',[p for p in pairs if p['timely_natural_pair']])]}
    dump(HERE/'自然完成子集与排除.json',{'summaries':subsets,'excluded_from_natural':[p for p in pairs if not p['natural_pair']],
        'excluded_from_timely_natural':[p for p in pairs if not p['timely_natural_pair']],
        'denominator_rule':'full162 pairs vs conditional subset; average available seeds per state, count retained states, never substitute subset for full batch'})
    strata=[]
    for factor in ('size','event'):
        for v in sorted({s[factor] for s in states}):
            ss=[s for s in states if s[factor]==v];strata.append({'factor':factor,'value':v,'states':len(ss),**{k:avg([s[k] for s in ss]) for k in keys}})
    dump(HERE/'预定分层.json',strata)
    timing={v:{'common_end_to_end':stats([r['time_seconds'] for r in rows if r['view']==v]),'native':stats([r['native_entry_seconds'] for r in rows if r['view']==v]),
       'post_increment':stats([r['post_increment_seconds'] for r in rows if r['view']==v]),'budget':sum(r['termination']=='budget' for r in rows if r['view']==v),
       'native_late':sum(r['native_late'] for r in rows if r['view']==v),'raw_stage_late':sum(r['raw_stage_late'] for r in rows if r['view']==v),
       'post_late':sum(r['post_late'] for r in rows if r['view']==v),'combined_late':sum(r['combined_late'] for r in rows if r['view']==v)} for v in ('A','B','C0','C')}
    credit={v:{'task_occurrences':sum(r['diagonal_offcenter_first_credit_tasks'] for r in rows if r['view']==v),
        'state_count':len({r['case'] for r in rows if r['view']==v and r['diagonal_offcenter_first_credit_tasks']}),
        'state_seed_count':sum(r['diagonal_offcenter_first_credit_tasks']>0 for r in rows if r['view']==v),
        'never_center_occurrences':sum(r['never_center_in_whole_actual_history_tasks'] for r in rows if r['view']==v)} for v in ('A','B','C0','C')}
    totals={v:{'total_length':sum(r['length'] for r in rows if r['view']==v),'new_credit':sum(r['new_credit'] for r in rows if r['view']==v),
        'missing':sum(r['missing'] for r in rows if r['view']==v),'returned':sum(r['return_success'] for r in rows if r['view']==v),
        'turns':sum(r['turns_total'] for r in rows if r['view']==v),'touches':sum(r['center_region_touch_events'] for r in rows if r['view']==v),
        'repeated_touches':sum(r['repeated_touch_events'] for r in rows if r['view']==v),'no_new_credit_routes':sum(r['no_new_credit_route'] for r in rows if r['view']==v)} for v in ('A','B','C0','C')}
    tech=Counter();technical_native=Counter();technical_main=Counter();technical_scopes=Counter();technical_walls=[]
    for j in plan['technical']:
        x=read(HERE/'outputs'/(j['id']+'.json'));technical_native.update(x['native_counts_actual']);tech.update(x['independent']['counts'])
        technical_scopes.update(x['query_scope_schema']);technical_walls.append(x['worker_wall_seconds'])
        for record in x['views'].values():technical_main.update(record['counts'])
    replay=sumc(c['audit']['counts'] for c in read(HERE/'technical_saved_replay.json')['checks'])
    accounts={'formal_core':dict(native_counts),'formal_main_virtual_execution':dict(main_counts),'formal_independent':dict(audit_counts),
        'formal_service_scopes':dict(postscope),'technical_core':dict(technical_native),'technical_independent':dict(tech),
        'technical_main_virtual_execution':dict(technical_main),'technical_service_scopes':dict(technical_scopes),
        'technical_worker_wall_seconds':stats(technical_walls),'technical_worker_wall_total':sum(technical_walls),
        'technical_saved_replay_new_queries':dict(replay),'pure_prechecks':read(HERE/'prechecks.json'),'final_binding_verify':read(HERE/'verify_receipt.json'),
        'cold_import_seconds':stats(cold),'worker_wall_seconds':stats(walls),'unique_entry_worker_wall_total':sum(walls),
        'attempt_wall_total':sum(json.loads(line)['wall'] for line in (HERE/'attempts.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(line)['event']=='ended'),
        'formal_calls':324,'technical_calls':12,'total_core_calls':336,'formal_post_calls':324,'technical_post_calls':12}
    dump(HERE/'调用与几何总账.json',accounts)
    assert len(rows)==648 and len(pairs)==162 and len(states)==54 and all(s['seed_count']==3 for s in states)
    assert all(totals[v]['missing']==0 and totals[v]['returned']==162 for v in ('A','B','C0','C'))
    assert all(r['passed'] and r['active_coverage']==1 for r in rows)
    result={'full':subsets['all'],'subsets':subsets,'timing':timing,'credit':credit,'view_totals':totals,'strata':strata,'formal_calls':324,'technical_calls':12}
    dump(HERE/'summary.json',result)
    figdir=HERE/'figures';figdir.mkdir(exist_ok=True);scatter(states,figdir/'54状态质量时间');strata_figure(strata,figdir/'尺寸事件分层')
    worst=max(pairs,key=lambda p:p['B_C_distance_extra']);route_figure(worst,loaded,'质量负例：按全批最大B/C距离差选取（仅展示，不改统计）',figdir/'质量负例路线')
    positive=next((p for p in pairs if loaded[(p['case'],p['seed'],'B')]['record']['metrics']['diagonal_offcenter_first_credit_tasks']),None)
    if positive:route_figure(positive,loaded,'新信用例：第一条符合关键斜段条件的B记录',figdir/'新信用例路线',True)
    allsum=subsets['all'];natural=subsets['natural'];sv=allsum['state_equal_means'];nv=natural['state_equal_means']
    tt='\n'.join('|'+ '|'.join([v,str(timing[v]['common_end_to_end']['N']),num(timing[v]['common_end_to_end']['mean']),num(timing[v]['common_end_to_end']['median']),num(timing[v]['common_end_to_end']['P95']),num(timing[v]['common_end_to_end']['max']),str(timing[v]['budget']),str(timing[v]['native_late']),str(timing[v]['post_late'])])+'|' for v in ('A','B','C0','C'))
    ct='\n'.join('|'+ '|'.join([v,str(credit[v]['task_occurrences']),str(credit[v]['state_count']),str(credit[v]['state_seed_count']),str(credit[v]['never_center_occurrences'])])+'|' for v in ('A','B','C0','C'))
    report=f'''# 中心区新条件：PPCPP直达质量—时间开发比较

本轮完整执行12技术入口＋324正式入口，共336新核心调用，到上限即停。正式PPCPP162、P2 162；A/B及C0/C各共享同一次核心，直达各162。648个视图均合法、全部当前可检责任完成并返航，失败/未运行0。正式结果不混技术输入、纯桩或历史批。

这是一组**给定相同初始历史的事件后快照比较**：54状态共享9基础地图和旧准备历史、每状态原3seed；不是54独立真实地图，也不是新连续事件收益实验。H逐格在原事件前合法中心前缀找到证据，格心严格属于新中心区；随后遮挡的已完成历史保留，暂缓未完成不计H。没有以新服务规则回放旧前缀扩大H，各视图显式初始采集一致且因当前已在H而幂等。

## 三个问题

1. **直达相对原PPCPP改善多少？** 正式总距离缩短 {pct(allsum['total_distance_A_B_saving'])}；先同状态同seed配对再状态等权平均缩短 {pct(sv['A_B_saving'])}。A→B缩短/相等/变长为 {allsum['A_B_shorter_equal_longer']}（162配对），保留零收益和负收益，不据结果改锚点。
2. **相对P2付出多少距离换多少计算时间？** 全批B/C总距离比差为 {pct(allsum['total_distance_B_C_extra'])}，状态等权平均多走 {pct(sv['B_C_distance_extra'])}，平均每状态配对多走 {num(sv['B_C_extra_meters'])}米、共同端到端少用 {num(sv['B_C_saved_seconds'])}秒。状态等权时间节省比例 {pct(sv['B_C_time_saving'])}；B更长/等长/更短 {allsum['quality_B_longer_equal_shorter']}，B更慢 {allsum['B_slower_pairs']}例。距离与时间是不同指标，不能用两个百分比大小证明综合优越。
3. **新覆盖规则实际利用到什么程度？** 下表给严格关键指标。只有实际执行斜段取得首次信用且整段不含目标格心才算；偏离格心的证明点不足。任一视图为0也是有效结果，不改图追正例。格心锚点保留，所有可检未采任务仍在后续折线经过其格心，因此“整个已执行历史从未经过格心”的任务为0；即使信用可能提前取得，也没有新增释放锚点优化。

|视图|斜段首次信用任务格次（含seed重复）|涉及状态数/54|涉及状态seed数/162|全历史未过格心任务格次|
|---|---:|---:|---:|---:|
{ct}

{('已保存新信用例路线及严格交区间/内部见证。' if positive else '本批B中没有符合关键指标的新信用例，图中明确不伪造正例；纯预检的斜段差异不替代实际返回路线。')}

## 预算与时间口径

P2保留原有限流程和20秒保护，不强行与PPCPP同短预算，也不空等20秒；直达另20秒总保护、18秒软候选截止和4096候选。全批有预算触顶时C只是“预算参照”，不能全称充分自然完成。

双方成功自然完成子集保留 {natural['pairs']}/162 配对、{natural['states']}/54状态，排除 {natural['excluded_pairs']} 配对；其B/C状态等权距离差 {pct(nv['B_C_distance_extra'])}，总距离差 {pct(natural['total_distance_B_C_extra'])}，平均节省 {num(nv['B_C_saved_seconds'])}秒。该条件子集只在各状态剩余seed内平均，再状态等权，不能冒充完整开发集。自然完成且全部阶段及时的更严格子集另列在自然完成子集与排除.json，所有被排除ID、原状态和原因保留。

|视图|N|共同端到端均值s|中位数s|P95s|最大s|预算触顶（共享核心）|原生迟到|直达阶段迟到|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{tt}

原生时间、直达增量和各自均值/中位数/P95/最大值见summary.json/正式648视图完整指标.csv。A/C0计一次原生、必要新信用执行和编码；B/C计同一原生及已有必要包装再加直达/对应执行/编码，不能将A/B共享核心求和当两次计算。原生观察器profile在两方法内计时，其开销并非保证可忽略，尤其可能影响P2在20秒内完成程度，不能把本次插桩时间与旧批无插桩时间作因果比较。

计时细节补充：开始前冻结来源hash检查/冷导入在外；代码在原生返回后还核对实际加载的核心来源，该项必要来源身份包装实际含在A/C0和B/C共同端到端内，未单独隔离。预登记文字“来源hash在外”仅准确描述开始前冻结检查，不能扩展成所有来源校验均未计时。两次原始证据落盘已按实测artifact_flush_excluded_seconds扣除；主流水线必要编码保留。独立审核/完整落盘/进程冷启动不在主时间内，worker及父进程墙钟、冷导入、审核费用另存逐入口来源与阶段及调用总账。统计P95采用nearest-rank，不做事后阈值。

## 覆盖、距离阶段和事件行为

全部视图可检覆盖率100%、返航162/162；公开完成率把暂缓目标保留在分母，具体每入口目标/历史/剩余/暂缓/新增/未完成及覆盖分母见CSV。新信用仅由完整返回折线虚拟执行提交，预测与实际副本分开，原输入c在执行前后相等。没有把未完成短路线当优势。

起点至首次新增信用、采集间和末次信用后返航距离使用**固定可复核内部见证约定**：取首次相交实际段的严格区间中点，按这些见证顺序分段，保存精确根式和认证范围；不是唯一的物理首次进入时刻或因果分解。全程无新增采集单列。中心区触达/重复触达按“每段每任务相交＋显式初态动作”事件记，受返回折线分段影响，不表示额外飞行成本。“无新增信用段长度”是整段分类，不是逐点非采集距离。90°/180°/其他非零转弯统一计算，共线正向分段、采集与等待不制造转弯。

## 公平接入与证据范围

生产service/exact、直达路线选择和独立解析region复用中心区v0.3源码。规模边界明确为旧快照F<=10000、公开目标<=1500，观察最大3036/336，不套微型25格/12目标限制；source/output审核<=原n边、服务<=n×责任、候选4096。独立审核在解析服务前使用整数严格必要盒排除并单列测试数，只减少不可能相交的计算，不更改责任或路线。单位格原路线由四邻接/自由端点独立证明合法，直达由独立禁飞闭格相交检验。没有LAST、四方向、混合、跳过格心锚点、区域位置优化或精确最优搜索。

技术六状态按尺寸各取字典序首个corner和obstacle，旧清单不存在无事件层，三条缺层事前登记，未伪造无事件。12项零核心预检及12技术真实/保存回放分开记账。每入口独立进程、四个线程变量为1，无跨输入缓存，轮换两方法先后；设备和CPU说明见environment.json，其他操作系统负载不保证完全消除。

## 分层、负例和新信用图

![54状态质量时间]({(figdir/'54状态质量时间.png').as_posix()})

![预定分层]({(figdir/'尺寸事件分层.png').as_posix()})

![质量负例]({(figdir/'质量负例路线.png').as_posix()})

'''+(f"![新信用例]({(figdir/'新信用例路线.png').as_posix()})\n\n" if positive else '')+'''
尺寸/事件层在预定分层.json，状态/seed配对与等权结果均保留，不事后挑最佳层。负例图按全批最大B/C距离差确定，仅展示、不改变样本。旧9.562%等仅为不同格心模型历史背景，不据本次差异归因于中心区模型；道路尺度/事件/历史相互关联，不作独立因果解释。

独立审核在每返回后实际执行，生产与独立服务是不同解析代码；完整事件/信用见证和几何回执、原返回/后处理、所有attempt及规模上界保存。技术保存回放又产生独立查询，单列计费；最终verify只核绑定及保存独立回执，新增几何/规划/后处理/搜索0。全部计数原文在调用与几何总账.json。无连续事件新实验、留出、额外seed、识别/飞控或实机验证；不称中心区或直达为创新，不宣称3毫米识别或现场安全。封存更新根进度后停止交审，不推送。
'''
    (HERE/'00_通俗开发比较报告.md').write_text(report,encoding='utf-8')
    packet='''# 开发比较 review packet

先读00_通俗开发比较报告.md、summary.json和final_receipt.json。正式324核心形成648视图；12技术核心、12纯案例及技术保存回放单列，不能并入正式162×各视图的分母。

01_完整预登记与计时口径.md/plan.json记录尺度、预算、顺序、缺少无事件层、统计和停止边界；history_evidence.json逐H格引用旧中心前缀及来源hash，给定历史不扩张。bindings/规模适配.diff/additional_core_source_bindings说明谓词、审核和原核心来源，active_freeze/formal_freeze保护代码、输入/配置/依赖。

每正式入口outputs包含唯一native_raw、唯一post_raw和两视图路径/完整虚拟执行事件、信用见证、分阶段时间、实际核心/图查询、独立主/后处理回执。A/B与C0/C不重复求解。正式648视图完整指标.csv、同状态同seed配对、54状态等权结果、预定分层、自然完成子集与排除逐层保持分母和负例，区别预算参照与自然完成。

计时解释以报告中的实际代码边界补充为准：开始前冻结hash/cold在外，返回后的实际加载来源校验在共同包装内；原始证据flush扣除，必要编码保留。profile开销计时且可能使P2触顶，不能声称与旧无插桩运行等价时间。独立审核及新进程/落盘墙钟另外记录，不把共享核心时间跨视图相加。

最终verify_receipt是只读绑定/保存回执核验，新核心/选择器/后处理/几何0。技术保存回放收据包含新独立几何查询，运行时独立审核每入口均已完成且计费。调用与几何总账.json区分正式、技术、纯桩、保存复核。再次查看可按manifest核对源/输入/返回hash；本轮不追加算法或额外验证批。

关键区域指标必须检查整条已执行斜段不含格心，另看整条历史是否从未到格心；证明点偏离格心不是正例。若该指标为0，报告如实保留，不造图追触发。旧模型成绩不作变化因果，当前结果仅开发基准，非论文创新或实机安全。
'''
    (HERE/'review_packet.md').write_text(packet,encoding='utf-8')
    print(json.dumps({'exported':True,'full':allsum,'natural':natural,'credit':credit,'budget_C':timing['C']['budget']},ensure_ascii=False))
    if not seal:return
    for name,digest in read(HERE/'formal_freeze.json').items():assert sha(HERE/name)==digest
    for name,digest in read(HERE/'old_source_guards.json').items():assert sha(name)==digest
    root=ROOT/'当前进度与下一步.md';current=root.read_text(encoding='utf-8-sig');(HERE/'root_pre_finalize.md').write_text(current,encoding='utf-8')
    header=f'''# 最新完成：中心区54快照质量—时间开发比较封存（2026-10-22）

中心区PPCPP直达质量时间开发比较_v0.1_20261022 已按稿完成12纯案例、12技术核心及保存回放、324正式核心（PPCPP/P2各162），总336到上限停止。先看00_通俗开发比较报告.md、summary.json、review_packet.md及final_receipt.json。54状态×原3seed，共同外部历史逐格前缀证据通过，当前显式采集幂等，不扩大H；9基础地图，不称连续事件收益。无事件层缺失事前登记，技术各尺寸选首corner/obstacle，不补图。

A/B共一次原PPCPP、C0/C共一次P2核心，中心区/直达共同适配，格心锚点/搜索/预算不改；648视图合法完成可检任务返航，失败/未运行0。A→B总距离省{pct(allsum['total_distance_A_B_saving'])}、状态等权省{pct(sv['A_B_saving'])}。B/C总距离差{pct(allsum['total_distance_B_C_extra'])}、状态等权多走{pct(sv['B_C_distance_extra'])}，平均少用{num(sv['B_C_saved_seconds'])}秒共同端到端；不以时间百分比压过距离百分比证明优越。

P2正式预算触顶{timing['C']['budget']}/162，触顶保留预算参照；双方自然完成子集{natural['pairs']}/162配对、{natural['states']}/54状态，排除{natural['excluded_pairs']}另列，不能代全批。原生20秒、直达另20/18软截止。profile开销计入，可能影响20秒内P2完成程度；主包装内含返回后来源校验，开始前hash/cold和独立审核在外，flush扣除，旧批时间不作因果比较。

关键新信用：B斜段不经格心首次信用任务格次{credit['B']['task_occurrences']}（含seed重复）、涉及{credit['B']['state_count']}状态；C为{credit['C']['task_occurrences']}格次/{credit['C']['state_count']}状态。全历史从未经过格心数均0（名义锚点保留）。证明点偏离格心不算正例，不追触发。阶段距离采用严格内部见证约定，非唯一物理首次时刻；重复触达为分段事件，非飞行成本。

完整attempt/输入/源码hash、原返回/新折线/虚拟执行见证、逐视图指标、同seed配对/状态等权/预定分层及自然子集排除、负例图、调用账/独立回执已存。技术和正式单列，最终verify核绑定回执新增核心/几何0。当前是新条件开发基准，不是创新、识别或实机安全证据；未改留出、追加seed/连续事件/优化批或推送。封存更新后停止交审。

---
'''
    root.write_text(header+'\n'+current,encoding='utf-8');(HERE/'root_after.md').write_bytes(root.read_bytes())
    files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.name not in ('manifest.json','final_receipt.json')}
    dump(HERE/'manifest.json',{'files':files})
    receipt={'status':'COMPLETE_FIXED_CENTER_CREDIT_DEVELOPMENT_COMPARISON_SEALED_STOP','passed':True,'formal_core_calls':324,'technical_core_calls':12,'total_new_core_calls':336,
       'formal_PPCPP':162,'formal_P2':162,'formal_post_calls':324,'views':648,'pure_cases':12,'failed':0,'unrun':0,'all_returned_and_serviceable_covered':True,
       'P2_budget_cases':timing['C']['budget'],'natural_pairs':natural['pairs'],'B_diagonal_offcenter_task_occurrences':credit['B']['task_occurrences'],
       'old_models_not_mixed':True,'future_or_holdout_used':False,'formal_freeze_unchanged':True,'saved_verify_sha256':sha(HERE/'verify_receipt.json'),
       'manifest_sha256':sha(HERE/'manifest.json'),'sealed_files':len(files),'stopped_for_owner_review':True,'no_additional_batches':True,'seal_new_algorithm_calls':0}
    dump(HERE/'final_receipt.json',receipt)
    for name,digest in files.items():assert sha(HERE/name)==digest
    print({'sealed':True,'files':len(files)})

if __name__=='__main__':
    import sys
    main('--seal' in sys.argv)

