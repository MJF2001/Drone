from pathlib import Path
import json,sys,hashlib,subprocess,csv,statistics,math
D=Path(__file__).resolve().parent;OLD=D.parent/'fixed_scope_true_history_v0.1_20261017'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 manifest=read(D/'delivery_sha256.json')
 for e in manifest['files']:
  p=Path(e['absolute_path']);assert p.stat().st_size==e['size_bytes'] and sha(p)==e['sha256'],('delivery mismatch',str(p))
 old=read(OLD/'delivery_sha256.json')
 for e in old['files']:assert sha(e['absolute_path'])==e['sha256'],('old delivery changed',e['absolute_path'])
 audits=[]
 for mode in ('preflight','formal'):
  p=subprocess.run([sys.executable,'-B','-X','utf8',str(D/'verify.py'),mode],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0,p.stderr;audits.append(read(D/(mode+'_audit.json')));assert json.loads(p.stdout)==audits[-1]
 jobs=read(D/'protocol.json')['jobs'];assert len(jobs)==200
 oldjobs=read(OLD/'protocol.json')['jobs'];oldkeys={(j['map_id'],j['repeat'],j['budget'],j['seed'],j['case'],j['case_sha256']) for j in oldjobs}
 assert {(j['map_id'],j['repeat'],j['budget'],j['seed'],j['case'],j['case_sha256']) for j in jobs}==oldkeys
 assert len({(j['map_id'],j['repeat'],j['budget'],j['method']) for j in jobs})==200
 assert {j['method'] for j in jobs}=={'FIX_SEED','FIX_PLUS1','FIX_ALL','POOL_INIT','POOL_PLUS1'}
 rows=list(csv.DictReader((D/'all_results.csv').open(encoding='utf-8-sig')));assert len(rows)==200
 idx={(r['map_id'],int(r['repeat']),int(r['budget']),r['method']):r for r in rows};maps=sorted({r['map_id'] for r in rows});summary=read(D/'analysis_summary.json')
 for comp in summary['comparisons']:
  deltas=[];ratios=[]
  for m in maps:
   if comp['exclude_large_g4'] and m.startswith('large_g4'):continue
   aa=[];bb=[]
   for rep in (0,1):
    a=idx[m,rep,comp['budget'],comp['a']];b=idx[m,rep,comp['budget'],comp['b']]
    if a['valid']=='True' and b['valid']=='True':
     av=int(a['steps']);bv=int(b['steps']);deltas.append(av-bv);aa.append(av);bb.append(bv)
   if aa:ratios.append(100*(statistics.mean(aa)/statistics.mean(bb)-1))
  assert comp['quality_pairs']==len(deltas) and comp['maps']==len(ratios)
  assert math.isclose(comp['mean_map_relative_pct'],statistics.mean(ratios),abs_tol=1e-10)
  assert comp['sum_delta']==sum(deltas) and comp['shorter']==sum(v<0 for v in deltas) and comp['longer']==sum(v>0 for v in deltas)
 calls=[json.loads(l) for l in (D/'synthetic_calls.jsonl').read_text().splitlines()];assert len(calls)==50<=60 and len({x['call_index'] for x in calls})==50
 print(json.dumps(dict(status='PASS',delivery_files=len(manifest['files']),old_delivery_files=len(old['files']),preflight=audits[0]['tasks'],formal=audits[1]['tasks'],valid_final_routes=audits[1]['valid_routes'],candidate_events=audits[1]['all_candidate_count'],synthetic_top_level_calls=len(calls),read_only=True,solver_calls=0),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
