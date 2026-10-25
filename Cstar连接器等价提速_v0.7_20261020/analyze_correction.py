"""Version diagnostics, no new solves and no other-algorithm ranking."""
import csv,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    folders={'v05':ROOT/'Cstar任务域修正_v0.5_20261020','v06':ROOT/'Cstar等价效率修正_v0.6_20261020','v07':HERE}
    index={k:{(r['name'],r['seed']):r for r in read(p/'road_checks.json')} for k,p in folders.items()}
    original={(r['case_id'],int(r['seed'])):r for r in csv.DictReader((ROOT/'七算法共同预算比较_v0.2_20261020/all_runs.csv').open(encoding='utf-8-sig')) if r['method']=='CSTAR'}
    rows=[];prefix=[]
    for key,r in index['v07'].items():
        row=dict(case=key[0],seed=key[1],name=original[key]['name'],scale=original[key]['scale'],state=original[key]['state'])
        for version in folders:
            q=index[version][key]
            for field in ('status','timely','steps','entry_seconds'):row[version+'_'+field]=q[field]
        rows.append(row)
        previous=index['v06'][key]
        if not previous['accepted'] and r['accepted']:
            old=read(folders['v06']/'evidence/results'/(previous['run_id']+'.json'))['result']
            new=read(HERE/'evidence/results'/(r['run_id']+'.json'))['result']
            assert old['diagnostic_route']==new['route'][:len(old['diagnostic_route'])]
            assert old['iterations']==new['iterations'][:len(old['iterations'])]
            strip=lambda e:{k:v for k,v in e.items() if k!='moved_steps'}
            assert list(map(strip,old['events']))==list(map(strip,new['events'][:len(old['events'])]))
            prefix.append(dict(case=key[0],seed=key[1],prefix_steps=len(old['diagnostic_route'])-1,prepared_tsp_events=sum(e['type']=='tsp' for e in old['events']),match=True))
    with (HERE/'versions_road40.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={}
    for version in folders:
        rs=list(index[version].values());ok=[r for r in rs if r['timely']]
        summary[version]=dict(calls=len(rs),timely=len(ok),strict20=sum(r['accepted'] and r['entry_seconds']<=20 for r in rs),mean_entry=statistics.mean(r['entry_seconds'] for r in rs),max_entry=max(r['entry_seconds'] for r in rs),mean_success_entry=statistics.mean(r['entry_seconds'] for r in ok),max_success_entry=max(r['entry_seconds'] for r in ok),complete_steps=sum(r['steps'] for r in ok),note='complete-step totals have different success subsets; do not compare as full-batch route gain')
    byscale={s:dict(calls=sum(r['scale']==s for r in rows),timely=sum(r['v07_timely'] for r in rows if r['scale']==s)) for s in ('small','medium','large')}
    save(HERE/'correction_analysis.json',dict(versions=summary,v07_scales=byscale,v06_failed_prefix_checks=prefix,ranking=False,new_solves=0))
    print(json.dumps(dict(versions=summary,scales=byscale,prefix_equal=len(prefix)),ensure_ascii=False))
if __name__=='__main__':main()
