"""Single read-only entry for raw results, matrix, sources and final delivery."""
from pathlib import Path
import json,csv,hashlib,itertools,re
import verify
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 verify.main('preflight');verify.main('formal')
 protocol=read(D/'protocol.json');jobs=protocol['jobs'];maps={j['map_id'] for j in jobs}
 expected=set(itertools.product(maps,('RANGE_SEED','RANGE_PLUS1','RANGE_PLUS2','RANGE_ALL','P2_MULTI'),(1,20),(0,1)))
 assert len(maps)==10 and len(jobs)==200 and {(j['map_id'],j['method'],j['budget'],j['repeat']) for j in jobs}==expected
 original=read(D.parent/'old_plan_warm_global_v0.1_20261017/protocol.json')
 seeds={(j['map_id'],j['repeat']):j['seed'] for j in original['jobs']}
 assert all(j['seed']==seeds[j['map_id'],j['repeat']] for j in jobs)
 with (D/'all_results.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==200 and len({x['run_id'] for x in rows})==200
 lookup={j['run_id']:j for j in jobs}
 for row in rows:
  rid=row['run_id'];j=lookup[rid];x=read(D/'formal'/(rid+'.json'));raw=x['raw'];rc=x['independent_route_check']
  assert row['valid']==str(bool(rc['valid']))
  if rc['valid']:assert int(row['steps'])==rc['steps']
  assert abs(float(row['seconds'])-raw['seconds'])<1e-9
  assert row['source']==(raw.get('source') or '')
  assert j==x['job']
  accepts=raw.get('improvements',[]) if j['method']=='P2_MULTI' else raw['detail']['acceptances']
  assert all(0<=e['seconds']<=j['budget'] for e in accepts)
  assert all(a['seconds']<=b['seconds'] and a['steps']>=b['steps'] for a,b in zip(accepts,accepts[1:]))
  if raw.get('route'):assert accepts and accepts[-1]['steps']==len(raw['route'])-1
  if (raw.get('source') or '').startswith('scope_core:'):assert raw['route']==raw['core_route']
 assert len(read(D/'fixture_calls.json'))==34
 assert read(D/'deadline_injection_results.json')['fixture_calls']==4
 assert len(read(D/'checker_fixture_results.json')['checks'])==6
 assert 'Ran 25 tests' in (D/'related_regressions.log').read_text(encoding='utf-8')
 manifest=read(D/'delivery_sha256.json')
 for e in manifest['files']:
  p=Path(e['absolute_path']);assert p.is_file() and p.stat().st_size==e['size_bytes'] and sha(p)==e['sha256'],str(p)
 print(json.dumps({'status':'PASS','formal_matrix':200,'preflight_matrix':10,'raw_table_rows':200,'same_original_seeds':True,'delivery_files':len(manifest['files']),'read_only':True,'optimizer_calls':0},indent=2))
if __name__=='__main__':main()
