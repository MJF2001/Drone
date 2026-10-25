"""Independent PPCPP ratio/stratum and version recheck; zero solver calls."""
import csv,json,statistics,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(summary,pairs):
    assert summary['n']==len(pairs)
    assert summary['shorter']==sum(a<b for a,b in pairs)
    assert summary['equal']==sum(a==b for a,b in pairs)
    assert summary['longer']==sum(a>b for a,b in pairs)
    assert summary['ppcpp_sum']==sum(a for a,b in pairs) and summary['other_sum']==sum(b for a,b in pairs)
    if pairs:assert abs(summary['mean_relative']-statistics.mean(a/b-1 for a,b in pairs))<1e-12
    else:assert summary['mean_relative'] is None
def main():
    p=read(HERE/'protocol.json');old=read(ROOT/'七算法共同预算比较_v0.2_20261020/protocol.json')
    for a,b in zip(p['cases'],old['cases']):assert a['input_sha256']==b['input_sha256']
    for name,h in p['sources'].items():
        if name in old['sources']:assert h==old['sources'][name]
    rows=read(HERE/'execution/checks.json');assert len(rows)==280
    by={(r['case_id'],r['seed'],r['method']):r for r in rows};c={x['case_id']:x for x in p['cases']}
    center=read(HERE/'PPCPP中心统计.json');assert center['versions']==p['versions']
    count=0
    for x in center['comparisons']:
        pairs=[];strata={'state':{'control':[],'event':[]},'scale':{'small':[],'medium':[],'large':[]}}
        for case in p['cases']:
            for seed in p['seeds']:
                a=by[case['case_id'],seed,'PPCPP'];b=by[case['case_id'],seed,x['method']]
                if a['timely'] and b['timely']:
                    ab=a['steps'],b['steps'];pairs.append(ab)
                    strata['state'][case['state']].append(ab);strata['scale'][case['scale']].append(ab)
        check(x,pairs);assert x['unpaired']==40-len(pairs);count+=len(pairs)
        for kind,groups in strata.items():
            for label,ps in groups.items():check(x['by_'+kind][label],ps)
    details=list(csv.DictReader((HERE/'PPCPP及时配对明细.csv').open(encoding='utf-8-sig')))
    assert len(details)==count==center['paired_rows']
    for row in details:
        key=row['case_id'],int(row['seed']);a=by[*key,'PPCPP'];b=by[*key,row['method']]
        assert a['timely'] and b['timely']
        assert int(row['ppcpp_steps'])==a['steps'] and int(row['other_steps'])==b['steps']
        assert abs(float(row['relative'])-(a['steps']/b['steps']-1))<1e-12
    cstar_complete_equal=0
    for r in rows:
        if r['method']!='CSTAR' or r['technical_failure']:continue
        z=read(HERE/'execution/results'/(r['run_id']+'.json'))['raw'];assert z['version']=='CSTAR_EQUIVALENT_v0.7'
        if r['valid']:
            ref=read(ROOT/'Cstar连接器等价提速_v0.7_20261020/evidence/results'/f"road__{r['case_id']}__{r['seed']}.json")['result']
            strip=lambda q:{k:v for k,v in q.items() if k!='seconds'}
            assert strip(z)==strip(ref);cstar_complete_equal+=1
    if (HERE/'delivery_manifest.json').exists():
        manifest=read(HERE/'delivery_manifest.json')
        assert set(manifest)=={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='delivery_manifest.json'}
        for name,h in manifest.items():assert sha(HERE/name)==h
    print(json.dumps(dict(all_pass=True,new_solver_calls=0,PPCPP_pair_rows=count,comparisons=6,CSTAR_complete_equal_to_frozen_validation=cstar_complete_equal,sealed=(HERE/'delivery_manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
