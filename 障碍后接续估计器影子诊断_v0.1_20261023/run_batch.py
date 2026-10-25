"""Serial bounded controller. Predictions sealed before truth joining."""
from common import *
import sys,subprocess,os,traceback
from collections import Counter
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
from policy import decide
from frozen_shadow_center_20261023.exact import Expr,certificate,Uncertain
def bounds(expr):
 lo,hi=expr.interval(128)
 with localcontext() as c:
  c.prec=80;c.rounding=ROUND_FLOOR;a=Decimal(lo.numerator)/Decimal(lo.denominator);c.rounding=ROUND_CEILING;b=Decimal(hi.numerator)/Decimal(hi.denominator)
 return [str(a),str(b)]
def predictions():
 start=time.perf_counter();rows=[];slots=read(H/'manifest.json')['slots'];keys=list(dict.fromkeys(x['key'] for x in slots))
 for key in keys:
  arms={arm:read(H/'outputs'/(key+'__'+arm+'.json')) for arm in ('OFF','ALT1')};available=all(o['passed'] and o['eligible'] and read(H/'audits'/(key+'__'+arm+'.json'))['passed'] for arm,o in arms.items());row=dict(key=key,available=available,arms={arm:dict(status=o['status'],eligible=o['eligible'],Jhat_raw=o.get('Jhat_raw'),Jhat_post=o.get('Jhat_post'),prefix_summary=o.get('prefix_summary'),counts=o.get('counts'),timing=o.get('timing')) for arm,o in arms.items()})
  if available:
   d=Expr.load(arms['ALT1']['Jhat_certificate']['exact'])-Expr.load(arms['OFF']['Jhat_certificate']['exact']);interval=bounds(d);pred=decide(True,interval,not d.terms);row.update(delta_hat_certificate=certificate(d),delta_hat_interval=interval,delta_hat_display=float(sum(d.interval())/2),prediction=pred)
   try:assert (pred['choice']=='ALT1')==((d+Expr.number(Fraction(1,100000000))).sign()<0)
   except Uncertain:assert pred['choice']=='OFF'
  else:row['prediction']=decide(False,['0','0'])
  rows.append(row)
 dump(H/'predictions.json',rows)
 output_hashes={str(p.relative_to(H)):sha(p) for folder in ('crops','outputs','audits','crop_audits') for p in sorted((H/folder).glob('*.json'))}
 dump(H/'predictions_seal.json',dict(sealed_utc=time.time(),predictions_sha256=sha(H/'predictions.json'),manifest_sha256=sha(H/'manifest.json'),policy_sha256=read(H/'manifest.json')['policy_sha256'],freeze_sha256=sha(H/'freeze.json'),controller_sha256=sha(Path(__file__)),files=output_hashes,truth_loaded_by_prediction_program=False,source_data_access='estimator guard allows one crop only; controller predictions use substitute estimates and saved independent receipts only',seconds=time.perf_counter()-start))
 print(dict(predictions_sealed=True,pairs=len(rows),suggest_ALT1=sum(r['prediction']['choice']=='ALT1' for r in rows)),flush=True)
def main():
 start=time.perf_counter();guard();assert read(H/'technical/round1.json')['passed'] and read(H/'crop_audit_receipt.json')['passed'];manifest=read(H/'manifest.json');assert len(manifest['slots'])==38;completed=[];failure=None;attempted=[];env=dict(os.environ)
 for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
 from audit import replacement
 for slot in manifest['slots']:
  t=time.perf_counter();attempted.append(slot['id']);log(H/'attempts.jsonl',dict(id=slot['id'],event='started',utc=time.time()))
  try:
   assert len(list((H/'logs').glob('*.post_started')))<38
   r=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'estimator.py'),str(H/slot['crop'])],capture_output=True,text=True,encoding='utf-8',env=env,timeout=150)
   (H/'logs'/(slot['id']+'.stdout')).write_text(r.stdout,encoding='utf-8');(H/'logs'/(slot['id']+'.stderr')).write_text(r.stderr,encoding='utf-8');assert r.returncode==0,(r.returncode,r.stderr)
   o=read(H/'outputs'/(slot['id']+'.json'));assert o['passed'],o.get('failure');assert o['new_core_calls']==0
   if o['eligible']:
    audit=replacement(slot,read(H/slot['crop']),o);dump(H/'audits'/(slot['id']+'.json'),audit);assert audit['passed']
   else:dump(H/'audits'/(slot['id']+'.json'),dict(passed=True,unavailable=True,reason=o['status'],scope='no incomplete trajectory in quality comparison'))
   completed.append(dict(id=slot['id'],status=o['status'],eligible=o['eligible'],parent_wall_seconds=time.perf_counter()-t));log(H/'attempts.jsonl',dict(id=slot['id'],event='completed',utc=time.time(),status=o['status'],eligible=o['eligible']));print(r.stdout.strip(),flush=True)
  except BaseException as ex:
   failure=dict(id=slot['id'],failure=repr(ex),traceback=traceback.format_exc());log(H/'attempts.jsonl',dict(id=slot['id'],event='failed_stopped',utc=time.time(),failure=failure));print(json.dumps(failure,ensure_ascii=False),flush=True);break
 notrun=[s['id'] for s in manifest['slots'] if s['id'] not in attempted];dump(H/'status.json',dict(completed=completed,failure=failure,attempted=attempted,not_run=notrun,wall_seconds=time.perf_counter()-start,core_calls=0,new_tails=len(attempted),post_calls=len(list((H/'logs').glob('*.post_started')))))
 if failure is None:predictions()
 else:print('STOPPED: no automatic repair or rerun',flush=True)
if __name__=='__main__':main()
