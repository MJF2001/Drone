from pathlib import Path
import json,hashlib

def build_scaled_widgets(H):
 O=H/'分尺度严格受阻与综合展示_v0.3_20261024';b=(O/'results.json').read_bytes();d=json.loads(b);v=json.loads((O/'independent_verification.json').read_text(encoding='utf8'));assert v['passed'] and v['results_sha256']==hashlib.sha256(b).hexdigest()
 worlds=[]
 for w in d['worlds']:
  if w['kind']=='reuse_single':
   old=json.loads(Path(w['source']).read_text(encoding='utf8'));c=next(x for x in old['protocol']['cases'] if x['id']==w['case']);sessions=[]
   for r in old['records']:
    if r['case']!=c['id']:continue
    obj=json.loads(Path(r['source']).read_text(encoding='utf8'));raw=obj.get('result',obj)['raw'];route=c['prefix']+r['route'][1:]
    sessions.append(dict(method=r['method'],route=route,covered=c['snapshot']['targets'],deferred=c['snapshot']['deferred_targets'],steps=len(route)-1,events=[dict(step=c['cut'],name='前方未飞覆盖格受阻')],phases=[dict(start_step=0,free=c['initial']['free'],published=c['initial']['published_targets'],plan=c['old_plan'],seconds=0),dict(start_step=c['cut'],free=c['snapshot']['free'],published=c['snapshot']['published_targets'],plan=r['route'],seconds=r['seconds'],raw=raw)]))
   w=dict(id='medium_I_single',kind='single',size='medium',initial=c['initial'],events=[dict(name='前方未飞覆盖格受阻',remove=c['marker'])],sessions=sessions)
  if w['kind']=='mixed':
   w['events'][4]['name']='障碍3'
   for session in w['sessions']:session['events'][4]['name']='障碍3'
  for s in w['sessions']:
   vec=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(s['route'],s['route'][1:])];dots=[a[0]*b[0]+a[1]*b[1] for a,b in zip(vec,vec[1:])];s['turn90']=dots.count(0);s['turn180']=dots.count(-1);s['seconds']=sum(p['seconds'] for p in s['phases'][1:]);s['timely']=all(p['seconds']<=20.010 for p in s['phases'][1:])
   for p in s['phases']:
    raw=p.pop('raw',{})
    if s['method']=='LOCAL_P2' and raw.get('window'):
     p['window']=raw['window'];p['selected']=raw.get('selected');p['local_steps']=len(raw['local']['route'])-1 if (raw.get('local') or {}).get('route') else None
    if s['method']=='ORIENT4' and raw.get('candidates'):
     p['selected_degree']=raw['selected_degree'];p['candidates']=[dict(degree=c['degree'],steps=len(c['inverse']['route'])-1,route=c['inverse']['route']) for c in raw['candidates']]
    for key in ['source','sha256']:p.pop(key,None)
  w['label']={'small':'小图','medium':'中图','large':'大图'}[w['size']]+' · '+('综合：两次扩展＋三个障碍' if w['kind']=='mixed' else '单障碍真实阻断')+' · 初始'+str(len(w['initial']['targets']))+'格'
  worlds.append(w)
 worlds.sort(key=lambda w:({'small':0,'medium':1,'large':2}[w['size']],w['kind']=='mixed'))
 payload=json.dumps(worlds,ensure_ascii=False,separators=(',',':'));(H/'分尺度严格受阻回放数据.json').write_text(payload,encoding='utf8')
 progress_dir=H/'各自进度前方障碍展示_v0.1_20261024'
 progress_bytes=(progress_dir/'results.json').read_bytes();progress=json.loads(progress_bytes)['worlds'];receipt=json.loads((progress_dir/'independent_verify.json').read_text('utf-8'));assert receipt['passed'] and receipt['results_sha256']==hashlib.sha256(progress_bytes).hexdigest()
 for w in progress:
  w['label']={'small':'小图','medium':'中图','large':'大图'}[w['size']]+' · '+('综合：两次扩展＋20/50/75%三障碍' if w['kind']=='mixed' else '20/50/75%三次前方障碍')+' · 初始'+str(len(w['initial']['targets']))+'格'
  for ss in w['sessions']:
   vec=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(ss['route'],ss['route'][1:])];dots=[a[0]*b[0]+a[1]*b[1] for a,b in zip(vec,vec[1:])];ss['turn90']=dots.count(0);ss['turn180']=dots.count(-1);ss['seconds']=sum(p['seconds'] for p in ss['phases'][1:]);ss['timely']=all(p['seconds']<=20.010 for p in ss['phases'])
   for ph in ss['phases']:
    raw=ph.pop('raw',{})
    if ss['method']=='LOCAL_P2' and raw.get('window'):ph.update(window=raw['window'],selected=raw.get('selected'),local_steps=len(raw['local']['route'])-1 if (raw.get('local') or {}).get('route') else None)
    if ss['method']=='ORIENT4' and raw.get('candidates'):ph.update(selected_degree=raw['selected_degree'],candidates=[dict(degree=c['degree'],steps=len(c['inverse']['route'])-1,route=c['inverse']['route']) for c in raw['candidates']])
    for key in ['source','sha256']:ph.pop(key,None)
 progress_payload=json.dumps(progress,ensure_ascii=False,separators=(',',':'));(H/'各自进度回放数据.json').write_text(progress_payload,encoding='utf-8')
 def widget(id,title,methods,extra):
  return '<div class="replay scaled-widget" id="'+id+'" data-methods="'+','.join(methods)+'"><h3>'+title+'</h3><p>'+extra+'</p><p class="small muted">小／中／大图均有单障碍与综合案例；全部满足障碍格此前未飞过、在旧计划待执行覆盖路段上、阻断后任务与基地仍可达。使用原冻结算法、四邻接格心采集，不混入直达。初始共用真实PPCPP准备前缀，第一次事件后各方法独立执行与接续。</p><div class="replay-controls"><label>案例 <select class="sw-case"></select></label><button class="sw-play">同步起飞</button><button class="sw-reset">回到起点</button><label>跳到 <select class="sw-event-select"></select></label><button class="sw-event">事件出现</button><button class="sw-end">查看完成</button><label>速度 <select class="sw-speed"><option>4</option><option selected>12</option><option>30</option></select>步/秒</label></div><input class="sw-range" type="range" min="0" step="0.1" value="0" aria-label="实际飞行进度"><p class="sw-clock"></p><p class="sw-protocol"></p><div class="sw-timeline"></div><p class="small muted">黄＝原待检；紫＝新增待检；绿＝实际已检；红框＝新增障碍；橙点＝无人机；蓝块＝基地；实线＝实际飞过，淡线＝当前计划。动画按相同移动速度，不模拟规划等待。</p><div class="sw-grid"></div><details class="sw-candidates"><summary>当前四方向候选（仅选中者实际执行）</summary><div class="sw-mini"></div></details><h4>当前案例完整结果</h4><div class="table-scroll sw-table"></div><p class="small muted">路程与转弯按实际完整轨迹统计；接续耗时是各次事件后入口之和，共同初始准备不重复计入该列。综合阶段位置与历史可能分化，不能把最终差距解释成某一次相同输入选择的因果效果。单次种子开发演示，不代表普遍优越。</p></div>'
 main=widget('scaled-main','严格受阻回放：小、中、大图与综合事件',['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP'],'只展示通过真实阻断资格与独立回放核验的案例。综合案例包含直线扩展、拐角扩展和三个不同位置的真实阻断。')
 local=widget('scaled-local','原PPCPP vs 局部P2混合：分尺度同步回放',['PPCPP','LOCAL_P2'],'右侧橙色粗线标出当前被搜索的窗口，并显示是否采用局部结果。最终效果按真实输出展示，保留等长与更长情况；不预设混合一定有效。')
 direction=widget('scaled-direction','原PPCPP vs 四方向组合：分尺度同步回放',['PPCPP','ORIENT4'],'右侧每次事件后比较四条完整候选，只执行最终选中路线。可展开当前阶段的候选图；综合案例中，较早选择也会改变后续事件的实际输入。')
 css='.replay{margin:26px 0;border:1px solid #bccedc;border-radius:7px;padding:18px;background:#f8fafc}.replay h3{margin-top:0}.replay-controls{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;font-size:13px}.replay select,.replay button{font:inherit;color:var(--ink);background:white;border:1px solid #b5c5d3;border-radius:4px;padding:6px 8px;max-width:100%}.replay-controls label{display:flex;align-items:center;gap:5px;max-width:100%}.replay button{cursor:pointer}.replay-card{min-width:0;border:1px solid var(--line);border-radius:5px;background:white;padding:10px}.replay-card h4{margin:0;font-size:14px;line-height:1.5}.replay-card canvas{display:block;margin:8px 0}.replay-card p{margin:4px 0;line-height:1.6}.scaled-widget .sw-range{width:100%;margin-top:12px}.sw-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.sw-grid.pair{grid-template-columns:repeat(2,minmax(0,1fr))}.sw-grid canvas,.sw-mini canvas{width:100%;height:auto;aspect-ratio:auto}.sw-grid p{white-space:pre-line;font-size:12px}.sw-timeline{display:flex;flex-wrap:wrap;gap:6px}.sw-timeline span{padding:5px 7px;font-size:12px;background:#e5edf5;border-radius:3px}.sw-timeline span.active{background:#d5e8db}.sw-protocol{font-size:13px;background:#edf2f7;padding:10px}.sw-mini{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.sw-table table{min-width:650px;font-size:13px}@media(max-width:650px){.sw-grid,.sw-grid.pair,.sw-mini{grid-template-columns:1fr}}'
 js='(()=>{const BASE_WORLDS='+payload.replace('<','\\u003c')+';const PROGRESS_WORLDS='+progress_payload+';'+(H/'scaled_replays.js').read_text(encoding='utf-8-sig')+'})();'
 def revise_pair(markup):
  start=markup.index('<p class="small muted">');end=markup.index('</p>',start)+4
  markup=markup[:start]+'<p class="small muted">各自从零规划起飞，按自己的实际覆盖进度触发20%、50%、75%障碍；每次障碍都在当前旧计划的下一格、此前未飞过。小中大图均提供三障碍与综合情况。原四邻接格心模型，不混入直达。</p>'+markup[end:]
  markup=markup.replace('分尺度同步回放','分尺度各自进度回放').replace('共同初始准备不重复计入该列','各自初始规划另列，不计入接续列').replace('综合阶段位置与历史可能分化，不能把最终差距解释成某一次相同输入选择的因果效果','障碍由各自路线的下一格决定，坐标可不同；这是相同触发规则下的响应展示，不是同一障碍地图的严格配对').replace('同一次','同一次')
  return markup
 return main,revise_pair(local),revise_pair(direction),css,js
