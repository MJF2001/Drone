"""Fetch four fixed primary documents; extract text/render only, execute no paper code."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,time
H=Path(__file__).resolve().parent
PAPERS=[('TRACE','https://arxiv.org/pdf/2609.21777v1'),('OARP_Replan','https://arxiv.org/pdf/2311.17837v2'),('FALCON','https://arxiv.org/pdf/2407.00577v2'),('LS_MCPP','https://ojs.aaai.org/index.php/AAAI/article/download/29707/31213')]
def fetch(item):
    name,url=item;p=H/'papers'/(name+'.pdf');assert not p.exists()
    t=time.perf_counter();req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research document review)'})
    with urllib.request.urlopen(req,timeout=45) as r:data=r.read();final=r.url
    assert data.startswith(b'%PDF-');p.write_bytes(data)
    return {'id':name,'requested_url':url,'final_url':final,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'download_seconds':time.perf_counter()-t}
if __name__=='__main__':
    results=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for item in ex.map(fetch,PAPERS):results.append(item);print(item['id'],item['bytes'],flush=True)
    (H/'sources/pdf_downloads.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
