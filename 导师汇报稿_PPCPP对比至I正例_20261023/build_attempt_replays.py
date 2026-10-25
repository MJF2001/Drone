"""Read-only extraction of historical paired improvement routes and actual shared prefixes."""
from pathlib import Path
import json,hashlib,html
METHODS=['PPCPP','LOCAL_P2']
def build_attempt_replays(H,ROOT):
 sources={};verified=0
 def read(p):
  p=Path(p);raw=p.read_bytes();sources[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw.decode('utf-8-sig'))
 def pts(x):return set(map(tuple,x))
 def label(x):
  words={'small':'小图','medium':'中图','large':'大图','I':'直路','L':'转角路','Z':'折线路','obstacle':'新增障碍','corner':'拐角扩展','straight':'直线扩展','p30':'约30%进度','p70':'约70%进度','event':'事件组','control':'无障碍对照'}
  return ' · '.join(words.get(w,w) for w in x.replace('__','_').split('_'))
 def check(s,r):
  nonlocal verified
  assert r and r[0]==s['current'] and r[-1]==s['base']
  assert pts(r)<=pts(s['free'])
  assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]))
  assert pts(s['targets'])<=pts(s['covered'])|pts(r) and len(r)-1<=s['distance_budget'];verified+=1
 def metric(r):
  v=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(r,r[1:])];d=[a[0]*b[0]+a[1]*b[1] for a,b in zip(v,v[1:])];return dict(steps=len(r)-1,turn90=d.count(0),turn180=d.count(-1))
 prep=ROOT/'PPCPP_LAST新开发地图验证_v0.1_20261020'
 def history(case,s):
  base='_'.join(case.split('_')[:2]);w=read(prep/'witnesses'/(case+'.json'));pr=read(prep/'prep/results'/(base+'.json'));initial=read(Path(pr['job']['input']));assert sources[str(Path(pr['job']['input']))]==pr['job']['input_sha256']
  hist=w['history'];assert hist==pr['raw']['route'][:w['cut']+1] and hist[-1]==s['current'] and hist[0]==s['base']
  assert not initial['covered'];assert pts(hist)&pts(initial['targets'])==pts(s['covered']);assert pts(hist)<=pts(initial['free'])
  assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(hist,hist[1:]));assert s['previous']==hist[-2]
  assert s['old_route']==pr['raw']['route'][w['cut']:]
  return initial,hist
 def panel(name,suffix,seconds,prefix,extra=None):return dict(name=name,route=prefix+suffix[1:],remaining=len(suffix)-1,seconds=seconds,**metric(prefix+suffix[1:]),**(extra or {}))
 mix=ROOT/'PPCPP局部P2混合开发诊断_v0.1_20261020';protocol=read(mix/'protocol.json');manifest={k.replace('\\','/'):v for k,v in read(mix/'manifest.json').items()};index={}
 for f in sorted((mix/'execution').glob('*.json')):
  d=read(f);j=d['job']
  assert sources[str(f)]==manifest[str(f.relative_to(mix)).replace('\\','/')]
  if j['repetition']==0 and j['method'] in METHODS:index[j['id'],j['method']]=d
 cases=[]
 for item in protocol['inputs']:
  cid=item['id'];s=read(Path(item['input']));assert sources[str(Path(item['input']))]==item['input_sha256'];initial,prefix=history(item['pair'],s)
  a=index[cid,'PPCPP'];b=index[cid,'LOCAL_P2']
  for d in [a,b]:
   j=d['job'];read(Path(j['input']));assert sources[str(Path(j['input']))]==j['input_sha256'];assert d['eligible'];check(s,d['raw']['route'])
  assert a['raw']['route']==b['raw']['P0']['route']==b['raw']['route']
  win=b['raw']['window'];local=b['raw']['local'];selected=b['raw']['selected'];extra=dict(selected=selected,window=win,local_steps=len(local['route'])-1 if local and local.get('route') else None,local_status=local.get('status') if local else 'not_called')
  cases.append(dict(id=cid,label=label(cid),initial=initial,snapshot=s,prefix=prefix,cut=len(prefix)-1,event='新增障碍' if item['kind']=='event' else '无障碍控制：同进度重规划',marker=item['marker'],panels=[panel('原PPCPP',a['raw']['route'],a['entry_seconds'],prefix),panel('局部P2混合',b['raw']['route'],b['entry_seconds'],prefix,extra)]))
 orient=ROOT/'PPCPP四方向共同预算正式比较_v0.1_20261020';ocases=[];manifest={k.replace('\\','/'):v for k,v in read(orient/'manifest.json').items()}
 for f in sorted((orient/'outputs').glob('*__0__PPCPP.json')):
  a=read(f);case=a['job']['case'];bf=orient/'outputs'/(case+'__0__ORIENT4.json');b=read(bf);s=read(orient/a['job']['input']);assert a['job']['input_sha256']==b['job']['input_sha256']==sources[str(orient/a['job']['input'])]
  for fp in [f,bf]:
   rel=str(fp.relative_to(orient)).replace('\\','/');assert sources[str(fp)]==manifest[rel]
  initial,prefix=history(case,s)
  for d in [a,b]:assert d['result']['eligible'];check(s,d['result']['raw']['route'])
  raw=b['result']['raw'];candidates=[]
  for c in raw['candidates']:
   route=c['inverse']['route'];check(s,route);candidates.append(dict(degree=c['degree'],route=route,steps=len(route)-1,seconds=c['seconds']))
  assert raw['route']==next(c['route'] for c in candidates if c['degree']==raw['selected_degree'])
  assert len(raw['route'])-1==min(c['steps'] for c in candidates)
  ocases.append(dict(id=case,label=label(case),initial=initial,snapshot=s,prefix=prefix,cut=len(prefix)-1,event='新增障碍' if '_obstacle_' in case else '拐角新增任务' if '_corner_' in case else '直线新增任务',marker=sorted(pts(initial['free'])-pts(s['free'])),candidates=candidates,selected_degree=raw['selected_degree'],panels=[panel('原PPCPP',a['result']['raw']['route'],a['result']['entry_seconds'],prefix),panel('四方向组合',raw['route'],b['result']['entry_seconds'],prefix)]))
 assert len(cases)==36 and len(ocases)==54
 # Default direction example: smallest-size first improving case in lexical order; all other cases remain available.
 default=min((i for i,c in enumerate(ocases) if c['panels'][1]['remaining']<c['panels'][0]['remaining']),key=lambda i:(len(ocases[i]['initial']['targets']),ocases[i]['id']))
 data=[dict(id='local-demo',kind='local',cases=cases,default=0),dict(id='direction-demo',kind='direction',cases=ocases,default=default)]
 from front_views import front_views
 data,_,_,_=front_views(H)
 payload=json.dumps(data,ensure_ascii=False,separators=(',',':'))
 (H/'改进方案历史回放数据.json').write_text(payload,encoding='utf8')
 (H/'改进方案历史回放核验.json').write_text(json.dumps(dict(passed=True,local_pairs=3,direction_pairs=3,historical_source_pairs_checked=90,seed=20261020,repetition=0,historical_routes_checked=verified,new_front_entries=24,render_solver_calls=0,selection='new front-block fixed I/L/Z order, all 3 retained',sources=sources,data_sha256=hashlib.sha256(payload.encode()).hexdigest()),ensure_ascii=False,indent=2),encoding='utf8')
 def markup(id,title,detail):
  return '<div class="replay attempt-demo" id="'+id+'"><h3>'+title+'</h3><p>'+detail+'</p><p class="small muted">事件前复用原始真实准备历史，事件后按新障碍重新求解；两边同一位置、历史、障碍。使用当时冻结版本，四邻接格心采集，无直达。旧的不合格回放已撤出本展示，原文件保留。</p><div class="replay-controls"><label>案例 <select class="ad-case"></select></label><button class="ad-play">同步起飞</button><button class="ad-reset">回到起点</button><button class="ad-event">跳到事件</button><button class="ad-end">查看完成</button><label>速度 <select class="ad-speed"><option>4</option><option selected>12</option><option>30</option></select>步/秒</label></div><input class="ad-range" type="range" min="0" value="0" step="0.1" aria-label="飞行进度"><p class="ad-clock"></p><p class="ad-explain"></p><p class="small muted">黄＝原待检；紫＝新增待检；绿＝已检；红框＝新增障碍；橙点＝无人机；蓝块＝基地。淡线是计划，实线是实际飞行。相同飞行速度，不模拟计算等待。</p><div class="ad-grid"></div><details class="ad-candidates"><summary>查看四条真实候选（未选中路线不是实际执行）</summary><p class="small muted">以下是候选全程预览：绿色表示已有历史加上该候选能够覆盖的任务，并不表示四条都已实际执行。</p><div class="ad-mini-grid"></div></details><p class="small muted">新验证固定种子20261020；卡片耗时是事件后完整入口，包含方案所需计算，不是动画速度。全程步数包含共同前缀；正文汇总使用原实验口径，不能与单例直接混算。</p></div>'
 h1=markup('local-demo','同步看：原路线与局部P2混合','这三例均是下一格此前未飞、旧覆盖计划真实受阻的新实验。橙线标出P2搜索窗口：直路、折线路仍同路；转角路接续83→79步。旧批无收益结论不套用到新批。')
 h2=markup('direction-demo','同步看：固定方向与四方向择优','三例共用“下一格未飞覆盖路段受阻”的新输入。右边比较四个方向的完整候选后只执行选中路线，可展开查看候选；不会把四条都飞一遍。默认直路，三例全部保留，不按收益挑例。')
 css='.ad-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.ad-grid canvas,.ad-mini-grid canvas{width:100%;height:auto;display:block}.ad-range{width:100%;margin-top:12px}.ad-grid .replay-card{padding:12px}.ad-grid p{white-space:pre-line}.ad-mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.ad-mini-grid p{font-size:12px}.ad-explain{background:#edf2f7;padding:10px;font-size:13px}@media(max-width:650px){.ad-grid,.ad-mini-grid{grid-template-columns:1fr}}'
 js='(()=>{const DATA='+payload.replace('<','\\u003c')+';'+(H/'attempt_replays.js').read_text(encoding='utf-8-sig')+'})();'
 return h1,h2,css,js
