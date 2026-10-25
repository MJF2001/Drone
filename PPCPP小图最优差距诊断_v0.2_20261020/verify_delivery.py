from common import *
from verify import verify
from analyze import summarize
def main():
 v=verify();a=read(H/'analysis.json');assert summarize(v['states'])==a['summary']
 for relative,item in read(H/'reuse.json').items():assert sha(H/relative)==sha(R/item['source'])==item['sha256']
 # Verify unchanged exact/model implementations across runner-only revision.
 old=R/'PPCPP小图最优差距诊断_v0.1_20261020'
 for name in ('common.py','geometry.py','exact.py','independent.py','tests.py','run.py','verify.py'):assert sha(old/name)==sha(H/name)
 report=(H/'小图最优差距诊断结果.md').read_text(encoding='utf-8');count=0
 for r in a['states']:
  expected='|'+ '|'.join(map(str,[r['id'],r['Lp'],r['Lstar'],r['G']]))+'|';assert expected in report;count+=1
 positive=sorted([r for r in a['states'] if r['G']>0],key=lambda r:(-r['G'],r['id']));zeros=sorted([r for r in a['states'] if r['G']==0],key=lambda r:r['id']);prefix=sorted([r for r in a['states'] if r['checkpoints'][0].get('D',0)>0],key=lambda r:r['id'])
 assert a['selected']==dict(max_gap=positive[0]['id'] if positive else None,zero_first=zeros[0]['id'] if zeros else None,positive_prefix_first=prefix[0]['id'] if prefix else None)
 for name in set(x for x in a['selected'].values() if x):assert (H/'figures'/f'{name}.png').exists() and (H/'figures'/f'{name}.svg').exists()
 assert len(list((H/'prep').glob('*.json')))==4 and len(list((H/'execution').glob('*.json')))==24
 assert a['query_count']==v['exact_queries']==64 and a['query_statuses']=={'optimal':64}
 assert a['summary']['positive']==2 and a['summary']['zero']==22 and a['summary']['G']==4
 tests=read(H/'tests/results.json');assert tests['count']==len(tests['tests'])==271 and tests['passed']
 for t in tests['tests']:
  if t['name'] in ('state_cap','time_cap'):assert t['result']['status']=='unresolved' and t['result']['length'] is None
 v.pop('states');v.update(report_rows=count,reuse_verified=True,exact_source_unchanged=True,review_status='待研究负责人审核');print(json.dumps(v,ensure_ascii=False))
if __name__=='__main__':main()
