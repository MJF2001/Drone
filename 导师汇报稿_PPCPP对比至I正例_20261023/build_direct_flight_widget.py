from pathlib import Path
import json,math,hashlib

def build_direct_flight_widget(H):
 O=H/'直达区域入口起飞展示_v0.2_20261024'
 W=json.loads((O/'worlds.json').read_text('utf-8'));audit=json.loads((O/'independent_verify.json').read_text('utf-8'))
 assert audit['passed'] and audit['worlds_sha256']==hashlib.sha256((O/'worlds.json').read_bytes()).hexdigest()
 worlds=[]
 for w in W:
  if w['status']!='complete':continue
  cards=[];ini=w['initial']
  for a in w['agents']:
   cum=[0.]
   for x,y in zip(a['full_path'],a['full_path'][1:]):cum.append(cum[-1]+math.dist(x,y))
   out=json.loads((O/'outputs'/(a['response']+'.json')).read_text('utf-8'))
   cards.append(dict(view=a['view'],path=a['full_path'],cum=cum,length=a['length'],seconds=a['seconds'],credits=a['credits'],expected=len(a['final_H']),event_distance=a['cut_distance'],prefix=a['path'],old=a['old'],response=out['views'][a['view']]['path'],return_length=a['return_length'],inspection_length=a['inspection_length']))
  worlds.append(dict(name=w['name'],size=w['size'],free=ini['free'],targets=ini['published_targets'],history=[],deferred=[w['obstacle']],base=ini['base'],current=ini['base'],cards=cards))
 data=json.dumps(worlds,ensure_ascii=False,separators=(',',':'));(H/'直达完整飞行回放数据.json').write_text(data,encoding='utf-8')
 markup='<div id="direct-replay" class="replay"><h4>从待检区入口起飞：前方出现障碍后，直飞省在哪里？</h4><p>所有任务初始化为待检，直接从区域入口格起飞（起点当场完成采集），最后返回同一入口；达到约30%采集进度后公开同一个前方未飞障碍，再完成可检任务并返航。横向看直达前后，纵向看两种算法。</p><div class="dr-controls"><label>完整飞行案例 <select id="dr-case"></select></label><button id="dr-play">▶ 同步播放</button><button id="dr-reset">重置</button><button id="dr-return">看障碍出现</button><button id="dr-end">看完整路线</button><label>速度 <select id="dr-speed"><option value="4">4 米/秒</option><option value="12" selected>12 米/秒</option><option value="30">30 米/秒</option></select></label></div><input id="dr-slider" aria-label="同步已飞距离" type="range" min="0" max="1000" value="0"><p id="dr-info"></p><div id="dr-grid"></div><div id="dr-result" class="note"></div><p class="small muted">绿格：已采集；黄格：待采集；红格：障碍遮挡暂缓；蓝点：基地；橙点：当前位置。格内小框为中心有效采集区。灰色虚线是未公开障碍前的计划参照（公开后可能受阻），彩色为已飞轨迹，直达版绿色斜线凸显直飞。</p><details><summary>真实运行、事件与计时口径</summary><p>三张原始I形小/中/大图，固定seed20261020；12个完整飞行会话，18次核心＋18次直达调用。初始规划每算法一次，原生/直达共享；事件后各自按真实位置、历史独立重算。不是预置30%历史；起点格在零距离时完成采集，之后全部实际路径都会播放。</p><p>各会话在首次达到至少30%采集、且自然到达轴向入射格心时公开障碍；不强迫补飞，不模拟非格心停止。因为飞行距离不同，障碍公开不是相同物理时刻。障碍格四个前缀均未穿过，四条未执行覆盖计划均受阻，之后仍有待检任务且可达；事件后不再公开新事件。</p><p>障碍坐标在重规划前按共同资格选定，不按收益筛选；这些是受控演示，不是随机场景或总体排名。冻结原核心和直达规则未改，仅包装允许从任务入口基地、空历史起飞，并按规则采集起点。时间为起飞规划＋事件后响应的共同端到端累计；原生分支不计离线诊断用的未采用直达输出，独立审核和文件读写等不计入。</p><p>完成遮挡外全部任务即达到可检覆盖100%；障碍格暂缓，不冒充完成。信用按保存的内部见证点染色。巡检阶段/末次采集后返航亦按该见证划分，不能据阶段差宣称独立因果贡献。</p></details></div>'
 css='#direct-replay{margin:24px 0;padding:20px;border:1px solid #c9d9e6;background:#f6f9fc;border-radius:10px}#direct-replay h4{font-size:20px;margin:0 0 10px}.dr-controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.dr-controls select,.dr-controls button{max-width:100%;padding:8px;border:1px solid #bdcddd;border-radius:5px;background:white;color:#203047}#dr-slider{width:100%;margin:16px 0 0}#dr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.dr-card{background:white;border:1px solid #cedce7;border-radius:8px;padding:12px;min-width:0}.dr-card h5{font-size:17px;margin:0 0 8px}.dr-card canvas{display:block;width:100%;aspect-ratio:1.35;background:#fff}.dr-card .dr-stat{font-size:13px;line-height:1.8}.dr-card b{color:#245c96}.dr-bar{height:5px;background:#e5edf4;margin:6px 0}.dr-bar i{display:block;height:100%;background:#5391bc}#dr-result{font-size:14px}#dr-info{font-size:13px}@media(max-width:650px){#direct-replay{padding:10px}#dr-grid{grid-template-columns:1fr}.dr-controls label{max-width:100%}.dr-controls select{width:100%}}'
 js='(()=>{const W='+data+';'+(H/'direct_flight_replay.js').read_text(encoding='utf-8')+'})();'
 return markup,css,js
