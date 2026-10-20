"""Stage a separate 1s/20s continuation, never alter sealed 120s evidence."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'OARP新版道路复验_汇报用_20261018'
def main():
    assert not (ROOT/'run.py').exists()
    s=(OLD/'run.py').read_text(encoding='utf-8')
    def change(a,b):
        nonlocal s
        assert a in s,a;s=s.replace(a,b)
    change("for seed in (20261018,20261019):jobs.append({'plan_id':p.stem+'_'+str(seed),'case':p.stem,'seed':seed})",
        "for seed in (20261018,20261019):\n            for budget in (1,20):jobs.append({'plan_id':p.stem+'_'+str(seed)+'_B'+str(budget),'case':p.stem,'seed':seed,'budget':budget})")
    change('assert len(jobs)==20','assert len(jobs)==40')
    change("'full_call_limit':20,'SCIP_limit':40,'GLNS_limit':20,'soft_seconds':120,'hard_seconds':135",
           "'full_call_limit':40,'SCIP_limit':80,'GLNS_limit':40,'soft_seconds':[1,20],'hard_seconds':'job budget + 15'")
    change('FROZEN:20 OARP-only calls,120s soft/135s hard; zero new calls in preparation',
           'FROZEN:40 OARP-only calls,1s/20s soft and +15s hard; zero calls in preparation')
    change("k.entry(req,'RANK0',None,[],attempt,seconds=120)","k.entry(req,'RANK0',None,[],attempt,seconds=job['budget'])")
    change("bootstrap_seconds=bootstrap,imports=", "soft_seconds=job['budget'],bootstrap_seconds=bootstrap,imports=")
    change('timeout=135','timeout=j[\'budget\']+15')
    (ROOT/'run.py').write_text(s,encoding='utf-8')
    v=(OLD/'verify.py').read_text(encoding='utf-8')
    def vc(a,b):
        nonlocal v
        assert a in v,a;v=v.replace(a,b)
    vc("counts['response']==20 and counts['SCIP']<=40 and counts['GLNS']<=20", "counts['response']==40 and counts['SCIP']<=80 and counts['GLNS']<=40")
    vc('len(set(actual))==20','len(set(actual))==40')
    vc("r['public_seconds']<120", "r['public_seconds']<j['budget']")
    vc("c['audited']<120", "c['audited']<j['budget']")
    vc("'full_calls':20", "'full_calls':40")
    (ROOT/'verify.py').write_text(v,encoding='utf-8')
    (ROOT/'continuation.json').write_text(json.dumps({'source':str(OLD),'old_run_sha256':hashlib.sha256((OLD/'run.py').read_bytes()).hexdigest(),
        'change':'budget and planned call count only; identical kernel, inputs, GLNS config, candidate handling and warm import convention',
        'Cstar':'not run, still restart diagnostic without core coverage history'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('STAGED; no planning calls')
if __name__=='__main__':main()
