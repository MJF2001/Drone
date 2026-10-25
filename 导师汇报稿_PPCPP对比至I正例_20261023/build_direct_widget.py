from pathlib import Path
import json,csv,math,hashlib

def build_direct_widget(H):
 S=H.parent/'中心区OFF全量质量时间开发比较_v0.1_20261022'
 files={}; worlds=[]
 def read(p):
  b=p.read_bytes();files[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
 def val(x):return x['n']/x['d'] if isinstance(x,dict) else x
 with (S/'正式648视图完整指标.csv').open(encoding='utf-8-sig',newline='') as f:rows={(r['case'],r['view'],r['seed']):r for r in csv.DictReader(f)}
 files[str(S/'正式648视图完整指标.csv')]=hashlib.sha256((S/'正式648视图完整指标.csv').read_bytes()).hexdigest()
 for size in ['small','medium','large']:
  for p in sorted((S/'inputs').glob(size+'*.json')):
   inp=read(p);name=inp['name'];cards=[]
   for method,views in [('PPCPP',['A','B']),('P2_MULTI',['C0','C'])]:
    d=read(S/'outputs'/f'formal__{name}__0__{method}.json')
    assert d['passed'] and d['independent']['passed'] and d['input']==inp
    for v in views:
     z=d['views'][v];m=z['metrics'];path=[[val(x),val(y)] for x,y in z['path']];cum=[0.0]
     for a,b in zip(path,path[1:]):cum.append(cum[-1]+math.dist(a,b))
     row=rows[name,v,'20261020'];assert row['passed']=='True'
     assert abs(cum[-1]-m['length'])<1e-8 and abs(cum[-1]-float(row['length']))<1e-8
     assert path[0]==inp['current'] and path[-1]==inp['base'] and m['missing']==0
     credits=[]
     for e in z['events']:
      if not e.get('new'):continue
      if e['kind']=='collect_here':dist=0.0
      else:
       i=e['edge'];t=val(e['evidence']['witness']['t']);assert 0<=t<=1
       dist=cum[i]+t*(cum[i+1]-cum[i])
      credits.append([e['cell'],dist])
     final=set(map(tuple,inp['covered']))|{tuple(c) for c,t in credits}
     assert final==set(map(tuple,m['final_H'])) and len(credits)==m['new_credit']
     timing=d['timing']['raw_common_end_to_end' if v in ('A','C0') else 'combined_end_to_end']
     assert abs(timing-float(row['time_seconds']))<1e-10
     cards.append(dict(view=v,path=path,cum=cum,length=cum[-1],seconds=timing,credits=credits,expected=m['covered_final'],turns=m['turns'],post_increment=float(row['post_increment_seconds'])))
   assert all(c['expected']==cards[0]['expected'] for c in cards)
   worlds.append(dict(name=name,size=size,free=inp['free'],targets=inp['published_targets'],history=inp['covered'],deferred=inp['deferred_targets'],base=inp['base'],current=inp['current'],cards=cards))
 assert len(worlds)==54
 data=json.dumps(worlds,ensure_ascii=False,separators=(',',':'))
 (H/'直达四图回放数据.json').write_text(data,encoding='utf-8')
 (H/'直达四图来源核对.json').write_text(json.dumps(dict(passed=True,states=54,views=216,seed=20261020,new_solver_calls=0,new_post_calls=0,source_hashes=files,data_sha256=hashlib.sha256(data.encode()).hexdigest(),checks=['保存路径距离与CSV逐一相符','原始与直达共同物理输入','保存见证信用和最终集合一致','共同端到端时间与CSV一致'],credit_display='在保存的区间内部见证点染色，不声称为首次入区瞬间'),ensure_ascii=False,indent=2),encoding='utf-8')
 markup="""<div id="direct-replay" class="replay"><h4>同一个任务，直飞省在哪里？</h4><p>横向看直达前后；纵向看两种算法。四架无人机以相同模拟速度前进，短路线会先回到基地。</p><div class="dr-controls"><label>事件后快照 <select id="dr-case"></select></label><button id="dr-play">▶ 同步播放</button><button id="dr-reset">重置</button><button id="dr-return">看返航段</button><button id="dr-end">看完整路线</button><label>速度 <select id="dr-speed"><option value="4">4 米/秒</option><option value="12" selected>12 米/秒</option><option value="30">30 米/秒</option></select></label></div><input id="dr-slider" aria-label="同步已飞距离" type="range" min="0" max="1000" value="0"><p id="dr-info"></p><div id="dr-grid"></div><div id="dr-result" class="note"></div><p class="small muted">绿格：已采集；黄格：待采集；红格：障碍遮挡暂缓；蓝点：基地；橙点：当前位置。格内小框为中心有效采集区。灰色虚线是该算法原四邻接路线，彩色为已飞轨迹，直达版绿色斜线凸显直飞。</p><details><summary>数据与播放口径</summary><p>完整开放54个保存快照，每个固定展示seed=20261020；上方总体结论仍来自54状态×3种子。不是从零起飞，也不模拟飞行中再发生事件；初始绿色为事件前真实已检历史。新障碍、直线扩展与拐角扩展分别可选，不冒充综合连续事件。</p><p>采用中心区OFF全量批，时间为保存的共同端到端实测，直达版包括后处理增量；原版与直达版共享同次核心，不重复计费。动画不模拟计算等待，不用当前电脑重新计时。信用按原记录的区间内部见证点变绿，不声称首次入区瞬间；仅穿过格子边缘不计完成。折线转直线仍须合法且保留采集责任。</p></details></div>"""
 css="""#direct-replay{margin:24px 0;padding:20px;border:1px solid #c9d9e6;background:#f6f9fc;border-radius:10px}#direct-replay h4{font-size:20px;margin:0 0 10px}.dr-controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.dr-controls select,.dr-controls button{max-width:100%;padding:8px;border:1px solid #bdcddd;border-radius:5px;background:white;color:#203047}#dr-slider{width:100%;margin:16px 0 0}#dr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.dr-card{background:white;border:1px solid #cedce7;border-radius:8px;padding:12px;min-width:0}.dr-card h5{font-size:17px;margin:0 0 8px}.dr-card canvas{display:block;width:100%;aspect-ratio:1.35;background:#fff}.dr-card .dr-stat{font-size:13px;line-height:1.8}.dr-card b{color:#245c96}.dr-bar{height:5px;background:#e5edf4;margin:6px 0}.dr-bar i{display:block;height:100%;background:#5391bc}#dr-result{font-size:14px}#dr-info{font-size:13px}@media(max-width:650px){#direct-replay{padding:10px}#dr-grid{grid-template-columns:1fr}.dr-controls label{max-width:100%}.dr-controls select{width:100%}}"""
 js='(()=>{const W='+data+';'+(H/'direct_replay.js').read_text(encoding='utf-8')+'})();'
 return markup,css,js
