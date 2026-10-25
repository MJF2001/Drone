import json,hashlib,importlib.util,csv
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;S=R/'PPCPP四方向共同预算正式比较_v0.1_20261020'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=load('metric',M/'metrics.py').metrics;cross=load('cross',M/'crosscheck.py').calculate
manifest=read(S/'manifest.json');hashes={};rows=[];groups={}
def checked(rel):
 p=S/rel;assert sha(p)==manifest[rel],rel;hashes[str(p.relative_to(R))]=sha(p);return read(p)
order=checked('order.json')
for j in order:
 if j['method']!='ORIENT4':continue
 x=checked('outputs/'+j['id']+'.json');c=checked(j['input']);raw=x['result']['raw'];assert x['result']['eligible']
 ms=[]
 for rec in raw['candidates']:
  m=metric(c,rec['inverse']['route']);assert m==cross(c,rec['inverse']['route']) and m['complete_legal'];ms.append(m)
 assert [r['degree'] for r in raw['candidates']]==[0,90,180,270]
 base=ms[0];best=min(range(4),key=lambda k:(ms[k]['length'],k));assert raw['selected_degree']==best*90
 allowed=[k for k in range(4) if ms[k]['turns90']<=base['turns90'] and ms[k]['turns180']<=base['turns180']]
 safe=min(allowed,key=lambda k:(ms[k]['length'],k))
 d=dict(case=j['case'],rep=j['rep'],original=base,shortest=ms[best],constrained=ms[safe],best_degree=best*90,constrained_degree=safe*90,candidates=ms)
 groups.setdefault(j['case'],[]).append(d)
 for k,m in enumerate(ms):rows.append(dict(case=j['case'],rep=j['rep'],degree=k*90,**m))
assert len(rows)==648 and len(groups)==54
states=[]
for name,ds in sorted(groups.items()):
 assert len(ds)==3
 for d in ds[1:]:assert {k:v for k,v in d.items() if k!='rep'}=={k:v for k,v in ds[0].items() if k!='rep'}
 states.append(ds[0])
fields=['length','turns90','turns180','completion_step','return_tail_steps','non_target_steps','historical_target_steps','repeated_new_target_steps']
totals={v:{f:sum(s[v][f] for s in states) for f in fields} for v in ('original','shortest','constrained')}
counts=dict(states=54,replicates=3,candidate_routes=648,shortest_improves=sum(s['shortest']['length']<s['original']['length'] for s in states),constrained_improves=sum(s['constrained']['length']<s['original']['length'] for s in states),no_tradeoff_candidate=sum(s['shortest']['length']<s['original']['length'] and s['constrained']['length']==s['original']['length'] for s in states))
a=dict(totals=totals,counts=counts,states=states,source_hashes=hashes,new_solver_calls=0)
(H/'analysis.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf8')
with (H/'648候选完整指标.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(head,rr):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])
lines=['# 四方向长度—转弯只读诊断','2026-10-21。新增求解0；162组合输出中的648条候选逐格双指标复算通过，54状态三重复全部指标/选择一致。下表每状态只计一次，不累加重复。',table(['指标','原方向','长度优先','转弯不增约束'],[[f]+[totals[v][f] for v in totals] for f in fields]),'## 计数',str(counts),'## 全54状态',table(['状态','原步数','最短步数','约束步数','原90/180','最短90/180','约束90/180','约束方向'],[[s['case'],s['original']['length'],s['shortest']['length'],s['constrained']['length'],*[str(s[v]['turns90'])+'/'+str(s[v]['turns180']) for v in totals],s['constrained_degree']] for s in states]),'## 分层',table(['层','N','原步数','最短步数','约束步数','约束获益状态'],[[v,len(ss),*[sum(s[k]['length'] for s in ss) for k in totals],sum(s['constrained']['length']<s['original']['length'] for s in ss)] for pos,vs in ((0,['small','medium','large']),(1,['I','L','Z']),(2,['straight','corner','obstacle'])) for v in vs for ss in [[s for s in states if s['case'].split('_')[pos]==v]]]),'## 边界','转弯不增约束是逐状态分别比较90/180次数，不是合计互相抵消，也不加入能耗权重。结果只是在已生成四候选中做离线选择，没有实测新选择器的入口开销/截止，不能称新算法正式成绩。所有转弯随实际单位格路线重算，不把图角度代替执行角度。原方向包含在候选内，不更差是构造属性；未用留出，无普遍性或全局最优结论。']
(H/'完整诊断表.md').write_text('\n\n'.join(lines),encoding='utf8')
print(json.dumps(dict(totals=totals,counts=counts),ensure_ascii=False))
