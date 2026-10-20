from pathlib import Path
import sys,json,hashlib,subprocess,statistics,math
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 for e in read(D/'delivery_sha256.json')['files']:assert sha(e['path'])==e['sha256']
 from stage_checks import check
 audits=[];rawrows=[]
 for mode in ('preflight','formal'):
  p=subprocess.run([sys.executable,'-B','-X','utf8',str(D/'verify.py'),mode],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0,p.stderr;audits.append(json.loads(p.stdout))
  for j in read(D/('preflight_protocol.json' if mode=='preflight' else 'protocol.json'))['jobs']:
   x=read(D/mode/(j['run_id']+'.json'));r=x['raw']
   if j['method']=='LOCAL_THEN_ALL':check(r,j['budget'])
   if mode=='formal':rawrows.append((j,r))
 jobs=read(D/'protocol.json')['jobs'];assert len(jobs)==120 and len({(j['map_id'],j['repeat'],j['budget'],j['method']) for j in jobs})==120
 old=read(D.parent/'fixed_scope_true_history_v0.1_20261017/protocol.json')['jobs'];key=lambda j:(j['map_id'],j['repeat'],j['budget'],j['seed'],j['case'],j['case_sha256']);assert set(map(key,jobs))==set(map(key,old))
 index={(j['map_id'],j['repeat'],j['budget'],j['method']):r for j,r in rawrows};summary=read(D/'analysis_summary.json');maps=sorted({j['map_id'] for j in jobs})
 for comp in summary['comparisons']:
  differences=[];ratios=[]
  for m in maps:
   aa=[];bb=[]
   for rep in (0,1):
    a=index[m,rep,comp['budget'],'LOCAL_THEN_ALL']['route'];b=index[m,rep,comp['budget'],comp['baseline']]['route']
    if a and b:aa.append(len(a)-1);bb.append(len(b)-1);differences.append(len(a)-len(b))
   if aa:ratios.append(100*(statistics.mean(aa)/statistics.mean(bb)-1))
  assert comp['pairs']==len(differences) and math.isclose(comp['mean_map_relative_pct'],statistics.mean(ratios),abs_tol=1e-10)
  assert comp['sum_delta']==sum(differences) and comp['shorter']==sum(d<0 for d in differences) and comp['longer']==sum(d>0 for d in differences)
 for m in summary['methods']:
  rs=[r for j,r in rawrows if j['method']==m['method'] and j['budget']==m['budget']];assert m['failed']==sum(not r['route'] for r in rs)
  assert m['overrun_gt10ms']==sum(r['seconds']>m['budget']+.01 for r in rs) and math.isclose(m['max_overrun'],max(0,max(r['seconds']-m['budget'] for r in rs)),abs_tol=1e-8)
  if m['method']=='LOCAL_THEN_ALL':
   assert m['first_overrun_gt10ms']==sum(r['switch_public_elapsed']>m['budget']/2+.01 for r in rs)
   assert m['second_overrun_gt10ms']==sum(r['stages'][1]['seconds']>r['stages'][1]['available_seconds']+.01 for r in rs)
 assert len((D/'synthetic_calls.jsonl').read_text().splitlines())==31<=40
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(D.parent/'constraint_release_offline_v0.1_20261017/verify.py')],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0,p.stderr
 print(json.dumps(dict(status='PASS',files=len(read(D/'delivery_sha256.json')['files']),formal=audits[1]['tasks'],valid_routes=audits[1]['valid_routes'],candidate_events=audits[1]['candidate_events'],preflight=6,synthetic_calls=31,solver_calls=0,read_only=True),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
