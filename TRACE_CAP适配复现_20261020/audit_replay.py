import sys,json
from pathlib import Path
from audit import audit
job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
c=json.loads(Path(job['input']).read_text(encoding='utf-8'))
r=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
result=audit(c,r)
assert r['status']=='complete' and r['seconds']<job['budget']
print(json.dumps(result,ensure_ascii=False))
