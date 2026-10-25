"""One predeclared, truncated diagnostic. Not a benchmark or retry."""
import cProfile, hashlib, io, json, pstats, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE/'profile'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    assert (HERE/'road_summary.json').exists(), 'no competing benchmark'
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'protocol.json').exists(), 'no retries'
    protocol=json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
    for f,h in protocol['sources'].items():assert sha(HERE/f)==h
    source=HERE/'inputs/case12.json'
    save(OUT/'protocol.json',dict(calls=1,input=str(source),input_sha256=sha(source),
        seed=20261018,budget=5,max_iterations=20000,source_hashes=protocol['sources'],
        purpose='cProfile cumulative call attribution only; instrumentation changes timing; no ranking, retry or successful-road substitution'))
    sys.path.insert(0,str(HERE/'runtime'))
    from history_adapter import solve
    c=json.loads(source.read_text(encoding='utf-8'))
    c={k:c[k] for k in ('free','targets','covered','current','base','published_targets','distance_budget','known_blocked') if k in c}
    profiler=cProfile.Profile();profiler.enable()
    r=solve(c,5,20261018,max_iterations=20000)
    profiler.disable();profiler.dump_stats(str(OUT/'call.pstats'))
    save(OUT/'result.json',r)
    s=io.StringIO();pstats.Stats(profiler,stream=s).strip_dirs().sort_stats('cumulative').print_stats(55)
    (OUT/'cumulative.txt').write_text(s.getvalue(),encoding='utf-8')
    stats=pstats.Stats(profiler)
    rows=[dict(file=f,line=l,function=n,primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for (f,l,n),v in stats.stats.items()]
    save(OUT/'functions.json',sorted(rows,key=lambda x:-x['cumulative_seconds']))
    print(r['status'],r['graph_error'],r['seconds'])
if __name__=='__main__':main()
