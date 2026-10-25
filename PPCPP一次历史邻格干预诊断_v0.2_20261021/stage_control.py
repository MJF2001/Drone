"""Hash-bound PASS receipts, shared by actual production stages."""
from probe_common import *
def binding():
    return {name:sha(H/name) for name in read(H/'binding_files.json')}
def receipt(stage,paths):
    save(H/'receipts'/f'{stage}.json',dict(stage=stage,status='PASS',binding=binding(),artifacts={str(Path(p).relative_to(H)):sha(p) for p in paths}))
def require(stage):
    r=read(H/'receipts'/f'{stage}.json');assert r['status']=='PASS' and r['stage']==stage and r['binding']==binding(),('invalid_stage_receipt',stage)
    for name,h in r['artifacts'].items():assert sha(H/name)==h,('changed_stage_artifact',stage,name)
    return r
def require_preseal():
    require('preseal');s=read(H/'preseal.json');assert s['complete'] and s['binding']==binding()
    for name,h in s['critical_source_hashes'].items():assert sha(name)==h,name
    return s
