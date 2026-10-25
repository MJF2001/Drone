"""Independent union-find and raw-source history/set verification. No planner imports."""
from pathlib import Path
import json,hashlib,time
from collections import Counter
H=Path(__file__).resolve().parent; ROOT=H.parent; C=Counter()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ps(x):return set(map(tuple,x))
def components(s):
    C['union_find_runs']+=1;par={p:p for p in s}
    def root(p):
        while par[p]!=p:par[p]=par[par[p]];p=par[p]
        return p
    for x,y in sorted(s):
        C['cells']+=1
        for q in ((x+1,y),(x,y+1)):
            C['edge_tests']+=1
            if q in par:
                a,b=root((x,y)),root(q)
                if a!=b:par[a]=b;C['unions']+=1
    groups={}
    for p in s:groups.setdefault(root(p),[]).append(list(p))
    return sorted((sorted(v) for v in groups.values()),key=lambda v:(-len(v),v))
def verify():
    start=time.perf_counter();guards=read(H/'source_guards.json')
    for p,h in guards.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    rows=read(H/'inventory.json');packs=read(H/'layers_and_components.json');assert len(rows)==len(packs)==54
    prepost=[]
    for r in rows:
        c=read(r['source_input']);a=read(r['source_initial']);w=read(r['source_witness']);prep=read(r['source_preparation']);p=packs[r['id']]
        P0=ps(a['published_targets']);P=ps(c['published_targets']);F=ps(c['free']);F0=ps(a['free']);hist=ps(c['covered']);D=ps(c['deferred_targets']);T=ps(c['targets']);U=T-hist
        assert w['history']==prep['raw']['route'][:w['cut']+1]==p['prefix']
        assert w['history'][-1]==c['current']==p['current'] and w['history'][-2]==c['previous']
        assert not a['covered'] and P0==ps(c['initial_targets'])==ps(a['targets'])
        assert hist==ps(w['history'])&P0 and T==P&F and D==P-F-hist and U==P-hist-D
        assert c['old_route']==prep['raw']['route'][w['cut']:]
        assert prep['raw']['status']=='core_complete' and prep['method']=='PPCPP' and prep['eligible']
        assert all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(w['history'],w['history'][1:]))
        layers=dict(P0=P0,P=P,F0=F0,F=F,H=hist,D=D,T=T,U=U,added=P-P0,blocked=F0-F)
        assert {k:ps(v) for k,v in p['layers'].items()}==layers
        for k in ('P0','P','T','U','F'):
            out=components(layers[k]);assert out==p['components'][k] and len(out)==r['components'][k]
        assert all(r['counts'][k]==len(v) for k,v in layers.items())
        # Additional fixed-set structural comparison; not path search or causal route comparison.
        before=components(P0-hist)
        prepost.append(dict(id=r['id'],event=r['event'],U_before_event_components=len(before),U_after_event_components=r['components']['U'],before_sizes=[len(v) for v in before],after_sizes=r['U_sizes']))
    summary=read(H/'summary.json')
    assert summary['P0_connected']==sum(r['components']['P0']==1 for r in rows)==54
    assert summary['P_connected']==sum(r['components']['P']==1 for r in rows)==54
    assert summary['U_fragmented']==sum(r['components']['U']>1 for r in rows)==30
    for kind,v in summary['events'].items():
        rr=[r for r in rows if r['event']==kind];assert len(rr)==v['states'] and sum(r['components']['U']>1 for r in rr)==v['U_fragmented']
    for i in read(H/'selection.json')['selected']:assert (H/'figures'/f'{i}.png').is_file()
    before=(H/'root_before.md').read_bytes();current=(ROOT/'当前进度与下一步.md').read_bytes()
    assert current==before or ((H/'root_after.md').exists() and current==(H/'root_after.md').read_bytes() and current.endswith(before))
    if (H/'manifest.json').exists():
        for p,h in read(H/'manifest.json')['files'].items():assert hashlib.sha256((H/p).read_bytes()).hexdigest()==h,p
    return dict(passed=True,states=54,source_guards=len(guards),independent_components=dict(C),pre_post_structure=prepost,seconds=time.perf_counter()-start,new_core=0,new_post=0,new_shortest_paths=0,new_visibility=0,new_route_generation=0,scope='raw saved input/history equality; independent union-find components; no recomputation of continuous credit geometry, no new solver calls')
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
