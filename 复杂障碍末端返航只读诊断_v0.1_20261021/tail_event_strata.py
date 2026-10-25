"""Explicit event-only denominators, keeping controls out of size/progress means."""
from tail_analysis import H,read,save,csvsave,summarize
def compute():
    a=read(H/'analysis.json');out={}
    for view,v in a['views'].items():
        pp=[p for p in v['pairs'] if p['kind']!='control'];ss=[s for s in v['states'] if s['kind']!='control'];strata={}
        for field in ('kind','size','progress','geometry_id'):
            strata[field]={str(value):summarize([p for p in pp if p[field]==value],[s for s in ss if s[field]==value]) for value in sorted({s[field] for s in ss})}
        out[view]=strata
    return out
if __name__=='__main__':
    x=compute();save(H/'events_only_strata.json',x)
    csvsave(H/'障碍主附分层.csv',[dict(view=view,dimension=field,value=value,**d) for view,vs in x.items() for field,groups in vs.items() for value,d in groups.items()])
