import json,hashlib,importlib.util,statistics,html
from collections import defaultdict,Counter
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;S=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=module('diag_metric',M/'metrics.py').metrics;cross=module('diag_cross',M/'crosscheck.py').calculate
saved=read(S/'analysis.json');manifest=read(S/'manifest.json');hashes={};groups=defaultdict(dict);allrows=[]
fields=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps','turns90','turns180']
for call in saved['calls']:
 if call['budget']!=20:continue
 p=S/call['output'];assert sha(p)==manifest[call['output']];hashes[str(p.relative_to(R))]=sha(p)
 x=read(p);c=read(Path(x['job']['input']));assert sha(Path(x['job']['input']))==x['job']['input_sha256']
 m=metric(c,x['raw']['route']);assert m==cross(c,x['raw']['route'])==call['metrics'];assert call['timely_valid']
 groups[call['case_id'],call['repetition']][call['method']]=dict(raw=x['raw'],metrics=m,input=c,output=call['output'])
assert len(groups)==162
diag=[]
for (name,rep),g in sorted(groups.items()):
 a=g['LAST_V2']['metrics'];p=g['P2_MULTI']['raw'];b=g['P2_MULTI']['metrics'];im=p['improvements']
 assert im[-1]['steps']==b['length'];assert all(x['steps']>y['steps'] for x,y in zip(im,im[1:]))
 raw=[v for v in im if v['source'] in ('old_suffix','common_fallback') or v['source'].endswith('_raw')]
 core=next(e['end'] for e in p['events'] if e['stage']=='core_finished');early=[v for v in im if v['seconds']<=core]
 gains=Counter()
 for x,y in zip(im,im[1:]):gains['optimized_accept' if y['source'].endswith(('_opt','_deep')) else 'other_accept']+=x['steps']-y['steps']
 d={k:a[k]-b[k] for k in fields};assert d['length']==sum(d[k] for k in fields[1:5])==d['completion_step']+d['return_tail_steps']
 diag.append(dict(id=name,rep=rep,LAST=a['length'],P2=b['length'],delta=d,source=p['source'],first=im[0],recorded_raw_best=min((v['steps'] for v in raw),default=None),core_best=early[-1]['steps'],improvements=im,accepted_gains=dict(gains)))
states=[]
for name in sorted({k[0] for k in groups}):
 ds=[d for d in diag if d['id']==name];g=groups[name,0];parts=name.split('_')
 states.append(dict(id=name,family=parts[1],size=parts[0],delta={k:statistics.mean(d['delta'][k] for d in ds) for k in fields},LAST=[d['LAST'] for d in ds],P2=[d['P2'] for d in ds],sources=[d['source'] for d in ds],recorded_raw_best=[d['recorded_raw_best'] for d in ds],core_best=[d['core_best'] for d in ds]))
selected={}
for fam in ('I','L','Z'):
 rr=[s for s in states if s['family']==fam];pos=sorted([s for s in rr if s['delta']['length']>0],key=lambda s:(s['delta']['length'],s['id']));zero=sorted([s for s in rr if s['delta']['length']==0],key=lambda s:s['id'])
 selected[fam]=dict(maximum=min(pos,key=lambda s:(-s['delta']['length'],s['id']))['id'] if pos else None,typical=pos[(len(pos)-1)//2]['id'] if pos else None,equal=zero[0]['id'] if zero else None)
totals={method:{k:sum(g[method]['metrics'][k] for g in groups.values())/3 for k in fields} for method in ('LAST_V2','P2_MULTI','PPCPP')}
logstats=dict(final_sources=dict(Counter(d['source'] for d in diag)),recorded_raw_beats_LAST=sum(d['recorded_raw_best'] is not None and d['recorded_raw_best']<d['LAST'] for d in diag),core_beats_LAST=sum(d['core_best']<d['LAST'] for d in diag),later_than_core_improves=sum(d['P2']<d['core_best'] for d in diag),later_than_core_saved=sum(d['core_best']-d['P2'] for d in diag)/3)
result=dict(states=states,queries=diag,selected=selected,totals=totals,logstats=logstats,new_solver_calls=0,source_hashes=hashes)
(H/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
def table(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(str(x) for x in r)+'|' for r in rows])
# Plain SVG scientific route diagrams; original and optimized routes, no generated imagery.
(H/'figures').mkdir(exist_ok=True)
for name in sorted({v for x in selected.values() for v in x.values() if v}):
 g=groups[name,0];c=g['P2_MULTI']['input'];f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));pub=set(map(tuple,c['published_targets']));W=max(x for x,y in f)+1;Y=max(y for x,y in f)+1;unit=min(650/W,560/Y);width=2*(W*unit+50);height=Y*unit+110
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="15" y="20" font-size="15">{html.escape(name)} | repetition 0 (not best seed)</text>']
 for panel,method in enumerate(('LAST_V2','P2_MULTI')):
  ox=25+panel*(W*unit+50);oy=75
  def xy(p):return (ox+(p[0]+.5)*unit,oy+(Y-p[1]-.5)*unit)
  svg.append(f'<text x="{ox}" y="48" font-size="15">{method}: {g[method]["metrics"]["length"]} steps</text>')
  for p in f|pub:
   x,y=xy(p);color='#444444' if p not in f else '#99c7ed' if p in hist else '#cfe8bd' if p in t else '#f6f6f6';svg.append(f'<rect x="{x-unit/2}" y="{y-unit/2}" width="{unit}" height="{unit}" fill="{color}" stroke="#dddddd" stroke-width="0.3"/>')
  route=g[method]['raw']['route'];end=g[method]['metrics']['completion_step']
  for segment,color in ((route[:end+1],'#2453a6'),(route[end:],'#d34c23')):
   coords=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,segment));svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.7" opacity="0.85"/>')
  for p,label in ((c['current'],'S'),(c['base'],'B'),(route[end],'E')):
   x,y=xy(p);svg.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/><text x="{x+4}" y="{y-4}" font-size="12">{label}</text>')
 svg.append(f'<text x="15" y="{height-10}" font-size="12">Green targets; light blue history; dark obstacle; blue coverage; orange return. Overlaps do not encode repeat counts.</text></svg>')
 (H/'figures'/f'{name}.svg').write_text('\n'.join(svg),encoding='utf-8')
lines=['# PPCPP/LAST与P2差距只读诊断','2026-10-20。仅已有数据；新增求解0，留出未用。主分析20秒全部及时配对，54状态每项三种子均值求和。',table(['指标','LAST','P2','LAST−P2'],[[k,totals['LAST_V2'][k],totals['P2_MULTI'][k],totals['LAST_V2'][k]-totals['P2_MULTI'][k]] for k in fields]),'## 日志证据',json.dumps(logstats,ensure_ascii=False,indent=2),'## 全54状态（差值均为LAST−P2）',table(['状态','LAST三种子','P2三种子','总差','历史重复差','本轮重复差','非目标差','覆盖前差','返航差','P2最终来源'],[[s['id'],s['LAST'],s['P2'],*[s['delta'][k] for k in ('length','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps')],s['sources']] for s in states]),'## 固定案例']
for fam,choice in selected.items():
 for role,name in choice.items():
  if name is None:continue
  ds=[d for d in diag if d['id']==name];lines += [f'### {fam} / {role} / {name}',f'![路线](figures/{name}.svg)',table(['重复','LAST','P2','已记录raw最短','core结束在手','最终来源','接受改进链'],[[d['rep'],d['LAST'],d['P2'],d['recorded_raw_best'],d['core_best'],d['source'],' → '.join(str(v['steps'])+':'+v['source'] for v in d['improvements'])] for d in ds])]
lines+=['## 证据边界','improvements仅记录严格变短的接受候选，不包含所有未接受候选的长度或中间路线。raw最短比LAST短是存在该候选的证据；未记录raw优势不是不存在优势。core_finished包含横纵扫描、最近邻及每初值8轮2-opt，不能叫纯扫描。接受下降属于按实际顺序更新的账目，不是独立机制因果贡献。图仅展示最终路线，重叠线不能直接看出经过次数，次数以逐格指标为准。']
(H/'诊断数据与案例.md').write_text('\n\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(totals=totals,logstats=logstats,selected=selected),ensure_ascii=False))
