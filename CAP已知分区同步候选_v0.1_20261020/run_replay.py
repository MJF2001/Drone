import json,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
sys.path.insert(0,str(H/'runtime'))
from known_sync import restore
from primitives import Metric
from checks import audit
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    protocol=read(H/'protocol.json')
    for p,h in protocol['files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    records=[]
    for job in protocol['jobs']:
        c=read(Path(job['input']));raw=read(Path(job['result']))['raw'];path=list(map(tuple,raw['diagnostic_route']))
        pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))
        for k,plan in enumerate(raw['plans']):
            end=plan['path_end'];pending-=set(path[:end+1]);before=plan['structure_before']
            g=restore(before,Metric(set(map(tuple,c['free']))),tuple(plan['start']))
            g.sync(pending,path[end]);after=g.snapshot();check=audit(before,after,pending)
            records.append(dict(run_id=job['run_id'],case_id=job['case_id'],plan_index=k,before=before,after=after,
                pending=sorted(pending),events=g.events,check=check))
    assert len(records)==60
    for item in records:
        if item['case_id']=='case10' and item['plan_index']==0:
            assert sorted(len(n['R']) for n in item['after']['nodes'] if n['R'])==[2,137]
    (H/'replay.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(saved_jobs=40,saved_boundaries=len(records),split_boundaries=sum(any(e['type']=='known_residual_split_batch' for e in x['events']) for x in records),full_CAP_calls=0,performance_calls=0)))
if __name__=='__main__':main()
