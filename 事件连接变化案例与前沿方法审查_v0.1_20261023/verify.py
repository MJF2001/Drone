"""Read-only receipt/hash audit. No planner, geometry, search, network or file writes."""
from pathlib import Path
import sys,json,hashlib,datetime
H=Path(__file__).resolve().parent
def read(p):return json.loads((H/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(ok,msg):
 if not ok:raise AssertionError(msg)
checks=[]
for name in ('A_registration_freeze.json','A_conclusion_freeze.json'):
 f=read(name)
 for p,s in f['files'].items():check(sha(H/p)==s,name+': '+p)
 checks.append(name+': unchanged '+str(len(f['files']))+' files')
guards=read('source_guards_A.json')
for p,s in guards.items():check(sha(p)==s,'old source changed: '+p)
checks.append('old source guards: '+str(len(guards)))
reg=read('case_registry.json');g=read('geometry_receipt.json');a=read('stageA_summary.json')
check(len(read('all54_state_equal_source.json'))==54,'state count')
check(len(reg['cases'])==6 and len(reg['geometry_segments'])==12,'registration caps')
check(len(g['records'])==12 and g['counts']['legal_calls']==24,'geometry stored count')
check(g['counts']['closed_forbidden_rectangle_tests']==0,'stored box count')
check(all(r['legal']=={'before':True,'after':True} and not r['visibility_changed'] for r in g['records']),'stored geometry labels')
check(len({r['id'] for r in g['records']})==12,'duplicate segments')
check(sum(x['label']=='仅事件后关联' for x in a['cases'])==4,'association count')
check(sum(x['label']=='无支持/反例' for x in a['cases'])==2,'counterexample count')
method_sources=set()
for c in reg['cases']:
 x=read('case_records/'+c['case']+'.json')
 check(c['plot_seed']==20261020,'plot seed')
 check(len(c['all_three_seed_pairs'])==3,'seed count')
 check(x['claim_event_caused_order_mismatch'] is False,'causal overclaim')
 check(x['knowledge_source_verified_actual_prep_input'] is True,'before source not verified')
 check([p['seed'] for p in x['all_seed_saved_evidence']]==[20261020,20261021,20261022],'seed identities')
 for p in x['all_seed_saved_evidence']:
  for m,d in p['methods'].items():
   check(sha(d['source'])==d['sha256'],'saved seed source changed')
   method_sources.add(d['source'])
  check(p['methods']['C']['internal_P2_final_visit_sequence'] is None,'invented P2 internal order')
checks.append('6 fixed cases, 18 saved pairs, '+str(len(method_sources))+' original method files; 12/24 geometry receipts only, no replay')
papers=read('sources/pdf_downloads.json')
check(len(papers)==4,'PDF count')
for p in papers:
 f=H/'papers'/(p['id']+'.pdf');check(f.stat().st_size==p['bytes'] and sha(f)==p['sha256'],'PDF source hash')
for f in ('sources/metadata_fetches.json','sources/aaai_fetches.json'):
 for r in read(f):
  if r['ok']:check(sha(H/r['path'])==r['sha256'],'metadata hash')
for r in read('papers/render_receipt.json'):check(sha(H/r['path'])==r['sha256'],'render hash')
v=read('sources/version_status_final.json')
for name in ('FALCON','LS_MCPP'):
 r=read('sources/'+('FALCON_commit.json' if name=='FALCON' else 'LS_MCPP_aaai_commit.json'))[0]
 check(r['sha']==v[name]['commit'],'commit mismatch')
 check(r['commit']['committer']['date'][:10]<='2026-10-23','future source commit')
check(v['paper_code_executed'] is False,'paper execution')
c=read('candidate_ledger.json')
check(len(c['candidates'])==c['admitted_candidates']==10,'candidate cap')
check(sum(x['deep_read'] for x in c['candidates'])==4,'deep cap')
check(len(list((H/'文献笔记').glob('*.md')))==4,'note count')
for x in c['candidates']:
 for k in ('first_public','version_date','preprint_first','arxiv_version_date'):
  if k in x:check(x[k]<='2026-10-23','future paper version')
checks.append('10 candidates / 4 deep notes / 4 primary PDFs and source versions verified')
l=read('ledger.json')
check(all(x==0 for x in l['algorithm_counts'].values()),'new algorithm work')
check(l['geometry']==g['counts'] and l['geometry_replay_in_verify']==0,'ledger geometry')
check(l['recommended_implementation_mechanisms']==0 and l['holdout_used'] is False,'scope')
check(len(list((H/'sources').glob('web_*.json')))==l['web_tool_batches_saved']==9,'web receipt count')
root=H.parent/'当前进度与下一步.md';before=(H/'root_before.md').read_bytes();now=root.read_bytes()
check(now.endswith(before),'old root progress not fully retained')
checks.append('algorithm/core/search/candidate/new route/closed loop all zero; old progress retained')
f=H/'final_receipt.json'
if f.exists():
 final=read('final_receipt.json')
 for p,s in final['files'].items():check(sha(H/p)==s,'sealed file changed: '+p)
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'}
 check(actual==set(final['files']),'unsealed or missing file')
 check(sha(root)==final['root_progress_sha256'],'root progress changed after seal')
 check(now.startswith('# 最新完成：事件连接变化正反例与前沿方法审查封存'.encode('utf-8')),'root entry')
 checks.append('final seal: '+str(len(final['files']))+' files and root hash verified')
else:check('--preseal' in sys.argv,'not sealed; use --preseal only during preparation')
print(json.dumps({'ok':True,'mode':'sealed' if f.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'new_core_calls':0,'new_geometry_calls':0,'new_path_or_coverage_searches':0,'writes':0,'network_calls':0},ensure_ascii=False,indent=2))
