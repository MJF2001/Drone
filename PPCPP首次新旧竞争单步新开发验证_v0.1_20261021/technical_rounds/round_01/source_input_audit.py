"""Independent old geometry/history block and direct-duplicate checks."""
from common import *
import ast
def signature(c):
    f=c['free'];dx=min(p[0] for p in f);dy=min(p[1] for p in f)
    def pt(p):return [p[0]-dx,p[1]-dy]
    x={k:[pt(p) for p in c[k]] for k in ('free','targets','covered','published_targets','deferred_targets','initial_targets','old_route')}
    x.update({k:None if c[k] is None else pt(c[k]) for k in ('current','previous','base','predator')});x['distance_budget']=c['distance_budget']
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def geometry_check(use_BFS):
    text=(H/'independent_input_block.py.txt').read_text(encoding='utf8');ns=dict(globals())
    if not use_BFS:
        def exact_rect_distance(f,s):
            assert f==rect(min(p[0] for p in f),min(p[1] for p in f),max(p[0] for p in f)-min(p[0] for p in f)+1,max(p[1] for p in f)-min(p[1] for p in f)+1)
            return {p:abs(p[0]-s[0])+abs(p[1]-s[1]) for p in f}
        ns['bfs']=exact_rect_distance
    exec(compile(ast.parse(text),'<frozen independent input block>','exec'),ns);assert ns['BFS']==24
    assert [(m['L'],m['w']) for m in read(H/'maps.json')]==[(l,w) for l in (24,36,48) for w in (4,6)]
    for m in read(H/'maps.json'):
        gg=[g for g in read(H/'groups.json') if g['geometry']==m['id']];assert [g['boundary_count'] for g in gg]==[m['L']//2,2*m['L']//3]
    old=read(B/'states.json');new=read(H/'states.json');oldsha={sha(B/s['input']) for s in old};oldsig={signature(read(B/s['input'])) for s in old}
    assert not {(m['L'],m['w']) for m in read(H/'maps.json')} & {(s['L'],s['w']) for s in old}
    rows=[dict(state=s['id'],sha256=sha(H/s['input']),translation_normalized_signature=signature(read(H/s['input']))) for s in new]
    assert all(r['sha256'] not in oldsha and r['translation_normalized_signature'] not in oldsig for r in rows)
    assert len({r['sha256'] for r in rows})==len(rows)==48
    return dict(passed=True,ordinary_BFS=24 if use_BFS else 0,groups=12,states=48,real_histories=6,planner_calls=0,direct_duplicate_with_old=False,statistical_independence_claim=False,signatures=rows)
def main():
    require('technical');require('prep');require('generated');x=geometry_check(True);save(H/'input_audit.json',x)
    receipt('inputs_audited',[H/'input_audit.json',H/'groups.json',H/'states.json',H/'states_metadata.json',H/'gate_order.json',H/'order.json',*sorted((H/'inputs').glob('*.json')),*sorted((H/'jobs').glob('*.json')),*sorted((H/'history').glob('*.json')),*sorted((H/'witnesses').glob('*.json'))]);print('PASS48 true-history inputs; independent BFS24; no old direct/translated duplicates',flush=True)
if __name__=='__main__':main()
