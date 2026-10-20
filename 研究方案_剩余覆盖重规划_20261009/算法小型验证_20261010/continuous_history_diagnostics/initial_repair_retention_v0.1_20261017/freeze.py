from pathlib import Path
import json,hashlib,sys,platform,os,subprocess,datetime
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';OLD=D.parent/'fixed_scope_true_history_v0.1_20261017'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
mode=sys.argv[1];dest=D/('preflight_protocol.json' if mode=='preflight' else 'protocol.json');assert not dest.exists()
env=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,executable=sys.executable,platform=platform.platform(),processor=platform.processor(),cpu_count=os.cpu_count(),thread_env={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']},head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),worktree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),hardware=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json'],capture_output=True,text=True).stdout)
(D/('environment_'+mode+'.json')).write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
old=json.loads((OLD/'protocol.json').read_text(encoding='utf-8'));protected=dict(old['protected_hashes'])
paths=list((D/'source_snapshot').rglob('*'))+list((ALGO/'.deps').rglob('*'))+list(D.glob('*.py'))+list(D.glob('synthetic*'))+[D/'tasks_draft.json',D/'preflight_tasks.json',D/('environment_'+mode+'.json')]
for p in paths:
 if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':protected[str(p.resolve())]=sha(p)
for p,h in protected.items():assert sha(p)==h,('protected mismatch',p)
jobs=json.loads((D/('preflight_tasks.json' if mode=='preflight' else 'tasks_draft.json')).read_text(encoding='utf-8'))
protocol=dict(version='initial_repair_retention_v0.1',mode=mode,jobs=jobs,protected_hashes=protected,synthetic_cap=60,synthetic_used=len((D/'synthetic_calls.jsonl').read_text().splitlines()),preflight_cap=10,formal_cap=200,construction_order=['public','R_PLUS1','R_SEED'],tie='keep earlier',continuation='original full PLUS1 with absolute public deadline; no cache transfer; no seed injection',initial_preparation=0,holdout=False,clock='perf_counter public origin; offer-point validation and actual continuation entry',watchdog='B+30s',freeze_utc=env['utc'])
dest.write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8');print(mode,'FROZEN',len(protected),'hashes',len(jobs),'jobs')
