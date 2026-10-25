"""Export-only successor: fix duplicate dict keywords; saved analysis unchanged."""
from support import *
from analyze import csvout
if __name__=='__main__':
 d=read(H/'analysis.json')
 csvout('324状态预算方法三种子.csv',[{**r,'lengths':json.dumps(r['lengths']),'entry_times':json.dumps(r['entry_times'])} for r in d['states']])
 csvout('双视图配对.csv',[dict(budget=b,**{k:v for k,v in c.items() if k!='pairs'}) for b,s in d['summary'].items() for c in s['comparisons']])
 save(H/'failures.json',dict(technical_failures=0,gate_failures=0,formal_calls=972,gate_calls=49,analysis_export_failure=dict(original='analyze.py',log='analysis.log',reason='dict duplicate lengths/entry_times keys in CSV export, after complete successful independent compute and first972 CSV; original source/output retained',successor='export_v02.py',scope='export only from unchanged saved analysis.json',formal_invalidated=0,formal_reruns=0),environment_scope_correction='Discovery v01 completed with audit/input/config and resealed before any gate calls; no post-run environment supplementation.',invalid=[x for x in d['calls'] if x['has_returned_route'] and not x['route_valid']]))
 print('Export v02 completed; saved analysis/raw unchanged;0 formal reruns')
