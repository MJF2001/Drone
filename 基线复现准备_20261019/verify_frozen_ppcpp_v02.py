"""Read-only frozen comparison re-audit; never runs planners."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent/'独立版_v0.2';sys.path.insert(0,str(HERE))
import experiment as e
def main():
    for name,h in e.read(e.RUN/'sha256.json').items():assert e.sha(e.RUN/name)==h,name
    p=e.read(e.RUN/'protocol.json');assert all(e.sha(Path(n))==h for n,h in p['protected_hashes'].items())
    old=e.read(HERE.parent/'delivery_manifest.json');assert e.sha(e.ROOT/old['core_source'])==old['core_source_sha256']
    assert e.history()==[dict(x,predator=tuple(x['predator']),previous=tuple(x['previous']) if x['previous'] is not None else None) for x in e.read(e.RUN/'history_contracts.json')]
    checks=e.verify_rows(e.RUN/'runs',p['jobs']);assert checks==e.read(e.RUN/'route_decision_checks.json')
    print(json.dumps(dict(read_only=True,formal_calls=len(checks),valid=sum(c['valid'] for c in checks),timely=sum(c['timely'] for c in checks),PPCPP_decision_audits=sum(c['method']=='PPCPP' and c['valid'] for c in checks),protected=len(p['protected_hashes']),prior_core_helper_hash_match=True,history_contracts=10,holdout_used=False)))
if __name__=='__main__':main()
