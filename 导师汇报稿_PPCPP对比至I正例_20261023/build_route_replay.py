"""Replay saved 2026-10-20 CORE4 results; never import or run a planner."""
from pathlib import Path
import csv, hashlib, html, json, math


def build_replay(folder, root):
    source = root / '七算法共同预算比较_v0.3_Cstar07_20261020'
    provenance = []

    def read(path):
        data = path.read_bytes()
        provenance.append(dict(path=str(path), sha256=hashlib.sha256(data).hexdigest()))
        return data.decode('utf-8-sig')

    protocol = json.loads(read(source / 'protocol.json'))
    rows = list(csv.DictReader(read(source / 'all_runs.csv').splitlines()))
    methods = ['PPCPP', 'P2_MULTI', 'OARP_CORE2', 'TREE_MST', 'CSTAR', 'TRACE', 'CAP']
    cases = []
    runs = {}
    seen = set()
    for case in protocol['cases']:
        path = source / 'inputs' / (case['case_id'] + '.json')
        snapshot = json.loads(read(path))
        assert provenance[-1]['sha256'] == case['input_sha256']
        cases.append(dict(id=case['case_id'], name=case['original_name'], scale=case['scale'],
                          event=case['event'], snapshot={k: snapshot[k] for k in
                          ['free', 'targets', 'covered', 'current', 'base', 'published_targets',
                           'deferred_targets', 'distance_budget']}))
    by_case = {c['id']: c for c in cases}
    for row in rows:
        result = json.loads(read(source / 'execution/results' / (row['run_id'] + '.json')))
        snapshot = by_case[row['case_id']]['snapshot']
        route = [tuple(p) for p in result['route']]
        free = set(map(tuple, snapshot['free']))
        targets = set(map(tuple, snapshot['targets']))
        history = set(map(tuple, snapshot['covered']))
        assert route[0] == tuple(snapshot['current']) and route[-1] == tuple(snapshot['base'])
        assert set(route) <= free
        assert all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1 for a, b in zip(route, route[1:]))
        assert targets <= history | set(route)
        assert len(route)-1 == int(row['steps']) <= snapshot['distance_budget']
        assert row['valid'] == 'True'
        assert math.isclose(result['entry_seconds'], float(row['entry_seconds']), abs_tol=1e-12)
        job = result['job']
        assert job['method'] == row['method'] and str(job['seed']) == row['seed']
        assert job['case_id'] == row['case_id']
        assert job['input_sha256'] == next(c['input_sha256'] for c in protocol['cases'] if c['case_id'] == row['case_id'])
        key = row['case_id'] + ':' + row['seed'] + ':' + row['method']
        assert key not in seen
        seen.add(key)
        runs[key] = dict(route=result['route'], steps=int(row['steps']), seconds=float(row['entry_seconds']),
                         timely=row['timely'] == 'True', status=row['status'], run_id=row['run_id'])
    seeds = sorted({row['seed'] for row in rows})
    assert len(cases) == 20 and len(rows) == 280 and len(seeds) == 2
    assert all(f"{c['id']}:{seed}:{method}" in runs for c in cases for seed in seeds for method in methods)
    data = dict(cases=cases, runs=runs, methods=methods, seeds=seeds)
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    (folder / '七算法真实路线回放数据.json').write_text(payload, encoding='utf-8')
    receipt = dict(source_batch=source.name, snapshots=20, methods=7, seeds=seeds, routes=280,
                   failures=0, model='four-neighbor, cell-center collection', new_planner_calls=0,
                   default_selection='first obstacle-only case in original protocol order; first original seed',
                   checks=['input SHA256', 'run identities', 'correct start and base', 'all cells free',
                           'unit cardinal moves', 'all current tasks covered', 'distance resource',
                           'saved CSV steps and entry time'],
                   replay_data_sha256=hashlib.sha256(payload.encode()).hexdigest(), sources=provenance)
    (folder / '七算法真实路线回放_数据核对.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    options = ''.join(f'<option value="{c["id"]}">{html.escape(c["id"]+" · "+c["name"])}</option>' for c in cases)
    markup = '''<div id="route-replay" class="replay"><h3>同图同步回放：七种方法实际怎样飞？</h3>
<p class="small muted">使用当时保存的真实输出：四邻接移动，到任务格心才计完成；没有使用后来的斜向直达或中心区规则。动画从该输入快照起点开始，障碍已经公开，不虚构发现前的飞行过程。</p>
<div class="replay-controls"><label>地图 <select id="replay-case">'''+options+'''</select></label><label>种子 <select id="replay-seed"></select></label>
<button id="replay-play" type="button">▶ 同步播放</button><button id="replay-reset" type="button">↺ 重播</button>
<label>回放速度 <select id="replay-speed"><option value="4">4步/秒</option><option value="12" selected>12步/秒</option><option value="32">32步/秒</option><option value="80">80步/秒</option></select></label>
<label><input id="replay-plan" type="checkbox" checked> 显示完整计划</label></div>
<div class="replay-scrub"><input id="replay-progress" type="range" min="0" max="1" step="0.05" value="0" aria-label="同步飞行进度"><output id="replay-counter"></output></div>
<p id="replay-info" class="small muted"></p>
<div class="replay-legend"><span><i style="background:#e9eef3"></i>可飞非目标</span><span><i style="background:#efc86e"></i>待检</span><span><i style="background:#a5cdb0"></i>已有完成历史</span><span><i style="background:#46a39c"></i>本次新完成</span><span><i style="background:#263746"></i>不可飞 / 障碍</span><span>◆ 蓝色：基地　▲ 橙色：无人机</span></div>
<div id="replay-grid" class="replay-grid"></div>
<p class="small muted">所有无人机按同样步速同时出发，完成后停在基地；快慢只反映飞行路线长短，不是计算速度。计算耗时另列，迟到结果保留标记。线段内的位置插值仅用于动画，抵达格心才更新覆盖。默认展示原协议排序中首个“纯新增障碍”状态，不按胜负挑例；可切换全部20状态和2个原种子。画面为七方法共同视窗，可能裁去无关的远处可飞空白。</p>
<p class="small muted">280条保存路线已逐条核对起终点、四邻接、通行、覆盖、资源及统计一致性；本次新增算法求解0次。<span class="refs"><a href="#ref-R35">R35</a></span></p></div>'''
    css = '''
.replay{margin:26px 0;border:1px solid #bccedc;border-radius:7px;padding:18px;background:#f8fafc}.replay h3{margin-top:0}.replay-controls{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;font-size:13px}.replay select,.replay button{font:inherit;color:var(--ink);background:white;border:1px solid #b5c5d3;border-radius:4px;padding:6px 8px;max-width:100%}.replay-controls label{display:flex;align-items:center;gap:5px;max-width:100%}.replay-controls select#replay-case{max-width:365px}.replay button{cursor:pointer}.replay #replay-play{background:#245c96;color:white}.replay-scrub{display:flex;align-items:center;gap:12px;margin:15px 0}.replay-scrub input{flex:1;min-width:60px;accent-color:#245c96}.replay-scrub output{min-width:115px;text-align:right;font-size:12px}.replay-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.replay-card{min-width:0;border:1px solid var(--line);border-radius:5px;background:white;padding:9px}.replay-card.primary{border:2px solid #245c96;padding:8px}.replay-card h4{margin:0;font-size:14px;line-height:1.5}.replay-card canvas{display:block;width:100%;height:auto;background:#263746;margin:8px 0;aspect-ratio:4/3}.replay-card p{font-size:12px;margin:4px 0;line-height:1.6}.replay-card .replay-time{min-height:38px;color:var(--muted)}.replay-card .late{color:#a14330;font-weight:bold}.replay-legend{display:flex;gap:7px 12px;flex-wrap:wrap;font-size:11px;margin:12px 0}.replay-legend span{display:inline-flex;align-items:center;gap:4px}.replay-legend i{width:11px;height:11px;border:1px solid #9bacb9}.replay-card .done{color:#24754f;font-weight:bold}
@media(max-width:800px){.replay{padding:12px}.replay-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.replay-controls select#replay-case{max-width:270px}}
@media(max-width:480px){.replay-grid{grid-template-columns:1fr}.replay-controls label{flex-wrap:wrap}.replay-controls select#replay-case{max-width:260px}}
@media print{.replay-controls,.replay-scrub{display:none}.replay-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.replay-card{break-inside:avoid}.replay{padding:9px}.replay-card h4{font-size:9pt}}
'''
    js = '(()=>{const D='+payload.replace('<', '\\u003c')+';'+r'''
const $=id=>document.getElementById(id),key=p=>p[0]+','+p[1],names={CSTAR:'C*'};
const select=$('replay-case'),seed=$('replay-seed'),slider=$('replay-progress'),play=$('replay-play');
D.seeds.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;seed.append(o)});
select.value=(D.cases.find(c=>c.event==='obstacle')||D.cases[0]).id;
let position=0,maxSteps=0,playing=false,last=0,cards=[],currentCase;
function pause(){playing=false;play.textContent='▶ 同步播放'}
function load(){pause();position=0;currentCase=D.cases.find(c=>c.id===select.value);const s=currentCase.snapshot;
const all=D.methods.map(m=>({method:m,...D.runs[currentCase.id+':'+seed.value+':'+m]}));
maxSteps=Math.max(...all.map(r=>r.steps));slider.max=maxSteps;slider.value=0;
const points=[...s.targets,...s.deferred_targets,s.base,s.current,...all.flatMap(r=>r.route)];
let minX=Math.min(...points.map(p=>p[0]))-1,maxX=Math.max(...points.map(p=>p[0]))+1,minY=Math.min(...points.map(p=>p[1]))-1,maxY=Math.max(...points.map(p=>p[1]))+1;
const cell=Math.min(600/(maxX-minX+1),420/(maxY-minY+1)),ox=(640-cell*(maxX-minX+1))/2,oy=(480-cell*(maxY-minY+1))/2;
const xy=p=>[ox+(p[0]-minX+.5)*cell,480-oy-(p[1]-minY+.5)*cell];
const target=new Set(s.targets.map(key)),hist=new Set(s.covered.map(key)),pending=new Set([...target].filter(k=>!hist.has(k)));
const bg=document.createElement('canvas');bg.width=640;bg.height=480;const bc=bg.getContext('2d');bc.fillStyle='#263746';bc.fillRect(0,0,640,480);
function fill(ctx,p,color){const [x,y]=xy(p);ctx.fillStyle=color;ctx.fillRect(x-cell/2+.25,y-cell/2+.25,Math.max(.5,cell-.5),Math.max(.5,cell-.5))}
s.free.forEach(p=>fill(bc,p,'#e9eef3'));s.targets.forEach(p=>fill(bc,p,hist.has(key(p))?'#a5cdb0':'#efc86e'));
bc.fillStyle='#f8c8c1';s.deferred_targets.forEach(p=>{const [x,y]=xy(p);bc.font=Math.max(8,cell*.8)+'px sans-serif';bc.textAlign='center';bc.fillText('×',x,y+cell*.25)});
$('replay-grid').replaceChildren();cards=all.map(r=>{const card=document.createElement('article');card.className='replay-card'+(r.method==='PPCPP'?' primary':'');
const label=names[r.method]||r.method;card.innerHTML='<h4>'+label+'</h4><p class="replay-time">计算 '+r.seconds.toFixed(4)+' 秒 · <span class="'+(r.timely?'':'late')+'">'+(r.timely?'及时返回':'合法但迟到')+'</span><br>完整路线 '+r.steps+' 步</p><canvas width="640" height="480" aria-label="'+label+'真实路线回放"></canvas><p class="replay-stat"></p><p class="replay-state"></p>';
$('replay-grid').append(card);let first=new Map();r.route.forEach((p,i)=>{const k=key(p);if(pending.has(k)&&!first.has(k))first.set(k,i)});
return {...r,canvas:card.querySelector('canvas'),stat:card.querySelector('.replay-stat'),state:card.querySelector('.replay-state'),xy,cell,bg,first,fill,total:pending.size,historyCount:s.targets.filter(p=>hist.has(key(p))).length,targetCount:s.targets.length,base:s.base};});
const ev={none:'无事件控制',straight:'直线扩展',corner:'拐角扩展',obstacle:'新增障碍',straight_obstacle:'直线扩展＋障碍',corner_obstacle:'拐角扩展＋障碍'};
$('replay-info').textContent=currentCase.id+' · '+(ev[currentCase.event]||currentCase.event)+' · 当前可检 '+s.targets.length+' 格 · 初始剩余 '+pending.size+' 格 · 遮挡暂缓 '+s.deferred_targets.length+' 格。七图使用同一比例、同一视窗。';draw();}
function path(ctx,r,end,color,width){ctx.beginPath();r.route.slice(0,Math.floor(end)+1).forEach((p,i)=>{const [x,y]=r.xy(p);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});if(end<r.steps&&end%1){const a=r.route[Math.floor(end)],b=r.route[Math.floor(end)+1],t=end%1;const [x,y]=r.xy([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]);ctx.lineTo(x,y)}ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin='round';ctx.stroke()}
function draw(){cards.forEach(r=>{const ctx=r.canvas.getContext('2d'),p=Math.min(position,r.steps),i=Math.floor(p);ctx.drawImage(r.bg,0,0);let count=0;
r.first.forEach((index,k)=>{if(index<=i){count++;r.fill(ctx,k.split(',').map(Number),'#46a39c')}});
if($('replay-plan').checked)path(ctx,r,r.steps,'#7485bb66',Math.max(1,r.cell*.09));
path(ctx,r,p,'#205bb5',Math.max(1.6,r.cell*.16));const [bx,by]=r.xy(r.base);ctx.fillStyle='#174d85';ctx.beginPath();ctx.moveTo(bx,by-5);ctx.lineTo(bx+5,by);ctx.lineTo(bx,by+5);ctx.lineTo(bx-5,by);ctx.closePath();ctx.fill();
const a=r.route[i],b=r.route[Math.min(i+1,r.steps)],t=p-i,[x,y]=r.xy([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]);
const prev=r.route[Math.max(0,i-1)],dx=b[0]-a[0]||a[0]-prev[0],dy=b[1]-a[1]||a[1]-prev[1];ctx.save();ctx.translate(x,y);ctx.rotate(Math.atan2(-dy,dx));ctx.fillStyle='#eb712a';ctx.strokeStyle='white';ctx.lineWidth=1.8;ctx.beginPath();ctx.moveTo(9,0);ctx.lineTo(-6,-6);ctx.lineTo(-3,0);ctx.lineTo(-6,6);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
const coverage=r.targetCount?(100*(r.historyCount+count)/r.targetCount).toFixed(1):'100.0';r.stat.textContent='已飞 '+p.toFixed(1)+' / '+r.steps+' 步 · 本次完成 '+count+'/'+r.total+' 格';
r.state.className='replay-state'+(p>=r.steps?' done':'');r.state.textContent='可检覆盖 '+coverage+'% · '+(p>=r.steps?'已完成并返航':count===r.total?'覆盖完成，返航中':'执行剩余巡检');});
slider.value=position;$('replay-counter').textContent=position.toFixed(1)+' / '+maxSteps+' 同步步';}
play.addEventListener('click',()=>{if(playing){pause();return}if(position>=maxSteps)position=0;playing=true;last=performance.now();play.textContent='❚❚ 暂停'});
$('replay-reset').addEventListener('click',()=>{pause();position=0;draw()});slider.addEventListener('input',()=>{pause();position=Number(slider.value);draw()});
select.addEventListener('change',load);seed.addEventListener('change',load);$('replay-plan').addEventListener('change',draw);
function frame(now){if(playing){position=Math.min(maxSteps,position+Math.min(.1,(now-last)/1000)*Number($('replay-speed').value));last=now;draw();if(position>=maxSteps)pause()}requestAnimationFrame(frame)}
document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
window.routeReplayAudit={caseCount:D.cases.length,routeCount:Object.keys(D.runs).length,methods:D.methods,model:'CORE4 cell-center',seek(value){pause();position=Math.max(0,Math.min(maxSteps,value));draw()},snapshot(){return {caseId:currentCase.id,seed:seed.value,maxSteps,position,playing,cards:cards.map(r=>({method:r.method,steps:r.steps,state:r.state.textContent,stat:r.stat.textContent}))}}};
load();requestAnimationFrame(frame);
})();'''
    return markup, css, js
