"""Postprocessing only; fixed event/scale/progress/layout strata and timing repeats."""
import statistics
from common import H,read,save
from spec import METHODS,SEEDS
def summarize(states,rows):
    out=dict(n=len(states),pairs={},times={},methods={})
    for m in METHODS:
        own=[r for r in rows if r['job']['method']==m];valid=[x for x in states if x['methods'][m]['eligible']]
        out['methods'][m]=dict(calls=len(own),eligible=sum(r['eligible'] for r in own),complete_states=len(valid),total_steps=sum(x['methods'][m]['metrics']['length'] for x in valid))
    for ref in ('PPCPP','FIRST'):
        xs=[x for x in states if x['methods']['STRUCT']['eligible'] and x['methods'][ref]['eligible']];ds=[x['methods']['STRUCT']['metrics']['length']-x['methods'][ref]['metrics']['length'] for x in xs]
        out['pairs'][ref]=dict(common_states=len(xs),shorter=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),longer=sum(d>0 for d in ds),difference=sum(ds),mean_relative=statistics.mean(d/x['methods'][ref]['metrics']['length'] for x,d in zip(xs,ds)) if xs else None)
    pairs=[]
    for x in states:
        for seed in SEEDS:
            pairs.append({m:next(r['entry_seconds'] for r in rows if r['job']['case_id']==x['case_id'] and r['job']['seed']==seed and r['job']['method']==m) for m in ('FIRST','STRUCT')})
    out['times']=dict(struct_faster=sum(x['STRUCT']<x['FIRST'] for x in pairs),struct_slower=sum(x['STRUCT']>x['FIRST'] for x in pairs),paired_calls=len(pairs),seed_means={str(seed):{m:statistics.mean(r['entry_seconds'] for r in rows if r['job']['seed']==seed and r['job']['method']==m) for m in METHODS} for seed in SEEDS})
    return out
def main():
    a=read(H/'analysis.json');rows=read(H/'execution/checks.json');out={'overall':summarize(a['states'],rows)}
    for key in ('event','size','progress','layout'):
        out[key]={}
        for value in dict.fromkeys(x[key] for x in a['states']):
            states=[x for x in a['states'] if x[key]==value];ids={x['case_id'] for x in states};out[key][str(value)]=summarize(states,[r for r in rows if r['job']['case_id'] in ids])
    save(H/'strata.json',out);print(out['overall'])
if __name__=='__main__':main()
