import csv,statistics
from collections import Counter
from common_orient import *
from audit_orient import check,semantics
def stats(xs):
 a=sorted(xs);z=(len(a)-1)*.95;i=int(z)
 return dict(N=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i),max=max(a))
def compute():
 complete=read(H/'completion.json');assert complete['completed'] and complete['entries']==285;rows=[];calls=[];outs={};audits={};protocol=read(H/'protocol.json');seal=read(H/'environment_seal.json')
 for info in complete['records']:
  x=read(H/info['output']);j=x['job'];assert sha(j['input'])==j['input_sha256'] and sha(H/'environment_seal.json')==j['seal_sha256'];assert x['runtime_reads']==[str(Path(j['input']).resolve())]
  for p,h in x['production_hashes'].items():assert seal['files'][p]==h
  assert x['status']==j['expected'];c=read(j['input']);audit=check(c,x);audits[j['id'],j['mode'],j['degree']]=audit;outs[j['id'],j['mode'],j['degree']]=x
  calls.append(dict(sequence=j['sequence'],id=j['id'],stage=j['stage'],mode=j['mode'],degree=j['degree'],status=x['status'],exception=x['exception'],eligible=x['eligible'],entry_seconds=x['entry_seconds'],core_calls=x['core_calls'],output=info['output'],audit=audit))
 for item in protocol['inputs']:
  ident=item['id'];old=outs[ident,'OLD',0]['raw']['candidates'][0]['raw'];new0=outs[ident,'NEW',0]['raw']['candidates'][0]['raw'];golden=read(item['golden'])['raw']['branches']['P0'];assert semantics(old)==semantics(new0)==semantics(golden)
  directions=[]
  for deg in (0,90,180,270):
   x=outs[ident,'NEW',deg];directions.append(dict(degree=deg,metrics=audits[ident,'NEW',deg][0]['metrics'],entry_seconds=x['entry_seconds'],route=x['raw']['route'],trace=x['raw']['trace']))
  winner=min(directions,key=lambda d:(d['metrics']['length'],d['degree']));base=directions[0]['metrics'];m=winner['metrics'];rows.append(dict(**{k:item[k] for k in ('id','family','size','event','progress')},directions=directions,selected_degree=winner['degree'],baseline=base,selected=m,saved=base['length']-m['length']))
 for r in complete['records']:
  if r['stage']=='B3':
   x=read(H/r['output'])
   for cand in x['raw']['candidates']:assert semantics(cand['raw'])==semantics(outs[r['id'],'NEW',cand['degree']]['raw']['candidates'][0]['raw'])
 for stem in ('left','right'):assert semantics(outs[stem+'_old','OLD',0]['raw']['candidates'][0]['raw'])==semantics(outs[stem+'_new','NEW',0]['raw']['candidates'][0]['raw'])
 keys=('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active')
 total={m:{k:sum(r[m][k] for r in rows) for k in keys} for m in ('baseline','selected')}
 strata=[]
 for factor in ('family','size','event','progress'):
  for v in sorted({r[factor] for r in rows}):
   rr=[r for r in rows if r[factor]==v];strata.append(dict(factor=factor,value=v,N=len(rr),short=sum(r['saved']>0 for r in rr),equal=sum(r['saved']==0 for r in rr),baseline=sum(r['baseline']['length'] for r in rr),selected=sum(r['selected']['length'] for r in rr),saved=sum(r['saved'] for r in rr)))
 return norm(dict(states=rows,calls=calls,totals=total,strata=strata,short=sum(r['saved']>0 for r in rows),equal=sum(r['saved']==0 for r in rows),selected_counts=dict(Counter(r['selected_degree'] for r in rows)),B1_zero_pairs=54,golden_pairs=54,B3_candidate_pairs=12,entry_calls=285,core_calls=complete['real_core_calls'],timing={mode:stats([c['entry_seconds'] for c in calls if c['mode']==mode and c['eligible'] and c['stage']==('B3' if mode=='COMBO' else 'B1')]) for mode in ('OLD','NEW','COMBO')}))
def main():
 d=compute();save(H/'analysis.json',d)
 for filename,rows in [('54四方向完整指标.csv',[dict(id=s['id'],family=s['family'],size=s['size'],event=s['event'],progress=s['progress'],degree=r['degree'],selected_degree=s['selected_degree'],entry_seconds=r['entry_seconds'],**r['metrics']) for s in d['states'] for r in s['directions']]),('285门槛调用.csv',[{k:v for k,v in c.items() if k!='audit'} for c in d['calls']]),('分层收益.csv',d['strata'])]:
  with (H/filename).open('x',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps({k:d[k] for k in ('totals','short','equal','selected_counts','entry_calls','core_calls','timing')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
