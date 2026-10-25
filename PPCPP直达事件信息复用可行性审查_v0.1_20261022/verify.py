"""Saved source/phase arithmetic only. Does not certify novelty or geometry."""
from pathlib import Path
import json,hashlib,statistics,math
H=Path(__file__).resolve().parent;B=H.parent/'PPCPP直达质量时间开发比较_v0.1_20261022'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert abs(a-b)<1e-10*max(1,abs(a),abs(b))
def main():
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    rows=read(H/'162同批PPCPP阶段时序.json');assert len(rows)==162 and len({r['id'] for r in rows})==162
    for r in rows:
        x=read(B/'outputs'/(r['id']+'.json'));assert x['job']['phase']=='formal' and x['job']['method']=='PPCPP';assert x['job']['case']==r['case'] and x['job']['seed']==r['seed'];assert r['counts']==x['post']['counts'];assert r['core_p0_seconds']==x['native']['phase_seconds'].get('p0')
        for k,v in x['post']['timing'].items():assert r[k]==v
        for k in ('original_seconds','post_increment_seconds','pipeline_seconds'):assert r[k]==x['timing'][k]
        close(r['candidate_phase_zero_cost_optimistic_time'],r['pipeline_seconds']-r['candidate']);close(r['candidate_phase_optimistic_saving_ratio'],r['candidate']/r['pipeline_seconds']);assert r['candidate_phase_zero_cost_optimistic_time']>=0
    for k,s in read(H/'同批成本位置汇总.json').items():
        v=[r[k] for r in rows if r[k] is not None];assert len(v)==s['n'];close(sum(v),s['sum']);close(statistics.mean(v),s['mean']);close(statistics.median(v),s['median']);close(sorted(v)[math.ceil(.95*len(v))-1],s['p95_nearest_rank']);close(max(v),s['max'])
    for p in read(H/'逐行源码证据.json'):
        lines=Path(p['path']).read_text(encoding='utf8').splitlines();assert p['sha256']==sha(Path(p['path']));assert p['lines']==[{'line':i,'text':line} for i,line in enumerate(lines,1)]
    assert len(read(H/'文献核查记录.json')['additional'])<=3;assert all(x==0 for x in read(H/'零调用账.json').values())
    print(json.dumps({'passed':True,'saved_PPCPP_pipelines':162,'source_files_with_line_evidence':len(read(H/'逐行源码证据.json')),'new_planning_geometry_candidates_inputs_closed_loop':0,'scope':'source hashes, exact line snapshots and saved timing statistics; mathematical validity/novelty remain human review'},ensure_ascii=False))
if __name__=='__main__':main()
