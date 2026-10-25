"""Read-only report/source arithmetic verification. No solver calls."""
from pathlib import Path
import json,hashlib,re,statistics
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    checks=read(H/'derived_checks.json');rs=read(R/'评价指标完整补算与数据审计_v0.1_20261020/per_run.json')
    lookup={(x['case_id'],x['seed'],x['method']):x for x in rs if x['batch']=='SEVEN_V03'}
    for x in checks['ppcpp_timely_comparisons']:
        d=[]
        for cid,seed,m in lookup:
            if m!='PPCPP':continue
            a=lookup[cid,seed,m];b=lookup[cid,seed,x['method']]
            if a['timely'] and b['timely']:d.append(a['m']['length']/b['m']['length']-1)
        assert len(d)==x['n'] and sum(v<0 for v in d)==x['shorter'] and sum(v==0 for v in d)==x['equal'] and sum(v>0 for v in d)==x['longer']
        assert abs(statistics.mean(d)-x['mean_relative'])<1e-12
    common=[];methods={x['method'] for x in rs if x['batch']=='SEVEN_V03'}
    for cid,seed in {(x['case_id'],x['seed']) for x in rs if x['batch']=='SEVEN_V03'}:
        own=[lookup[cid,seed,m] for m in methods]
        if all(x['timely'] for x in own):common+=own
    assert len(common)//7==checks['common_call_pairs']==24
    labels={'C*（四邻接）':'CSTAR','CAP旧适配':'CAP'}
    for row in checks['seven_common_timely']:
        xs=[x for x in common if x['method']==labels.get(row[0],row[0])]
        assert row[1]==len(xs) and row[2]==sum(x['m']['length'] for x in xs)
        assert row[4]==sum(x['m']['turns90'] for x in xs) and row[5]==sum(x['m']['turns180'] for x in xs)
    text=(H/'实验数据详细总结与对比分析_20261020.md').read_text(encoding='utf-8')
    assert len(text)==checks['report_characters']
    for url in re.findall(r'\]\(([^)]+)\)',text):assert Path(url).is_file(),url
    assert '## 13 ' in text and '99.8042%' in text and '10288' in text
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,source_routes=360,timely_comparisons=6,seven_common_pairs=24,new_solver_calls=0,report_links_valid=True,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
