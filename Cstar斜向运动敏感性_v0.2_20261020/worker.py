import sys,json,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));c=json.loads(Path(job['input']).read_text(encoding='utf-8'))
    before=time.perf_counter();sys.path.insert(0,str(HERE/job['runtime']));from history_adapter import solve
    bootstrap=time.perf_counter()-before;begin=time.perf_counter()
    request={k:c[k] for k in ('free','targets','covered','current','base','published_targets','distance_budget') if k in c}
    if 'known_blocked' in c:request['known_blocked']=c['known_blocked']
    r=solve(request,job['budget'],job['seed'],max_iterations=20000);elapsed=time.perf_counter()-begin
    Path(sys.argv[2]).write_text(json.dumps(dict(job=job,result=r,entry_seconds=elapsed,bootstrap_seconds=bootstrap),ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
