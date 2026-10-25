from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
H=Path(__file__).resolve().parent
urls={
 'LS_MCPP_aaai_commit':'https://api.github.com/repos/reso1/LS-MCPP/commits?sha=aaai&until=2026-10-23T23:59:59Z&per_page=1',
 'LS_MCPP_aaai_README':'https://raw.githubusercontent.com/reso1/LS-MCPP/c7dec715d764d35593b40f32d49e70b7eb352455/README.md'
}
def get(kv):
 k,u=kv
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'ResearchEvidenceAudit/1.0'}),timeout=30) as r:b=r.read()
  p=H/'sources'/(k+('.txt' if 'README' in k else '.json'));p.write_bytes(b)
  return dict(id=k,url=u,path=str(p.relative_to(H)),sha256=hashlib.sha256(b).hexdigest(),ok=True)
 except Exception as e:return dict(id=k,url=u,ok=False,error=str(e))
rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(get,urls.items()))
(H/'sources'/'aaai_fetches.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(rows)
