from pathlib import Path
import json,urllib.request,hashlib,concurrent.futures,datetime
import pypdfium2 as pdfium
H=Path(__file__).resolve().parent
urls={
 'crossref_OARP':'https://api.crossref.org/works/10.1109/TRO.2024.3454417',
 'crossref_FALCON':'https://api.crossref.org/works/10.1109/TRO.2024.3522148',
 'FALCON_commit':'https://api.github.com/repos/HKUST-Aerial-Robotics/FALCON/commits?sha=ros1-noetic&until=2026-10-23T23:59:59Z&per_page=1',
 'LS_MCPP_commit':'https://api.github.com/repos/reso1/LS-MCPP/commits?sha=aaai24&until=2026-10-23T23:59:59Z&per_page=1',
 'AAAI_landing':'https://ojs.aaai.org/index.php/AAAI/article/view/29707',
 'TRACE_author':'https://ouyaming.github.io/'
}
def get(kv):
 k,u=kv
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'ResearchEvidenceAudit/1.0'})
  with urllib.request.urlopen(req,timeout=45) as r: b=r.read()
  p=H/'sources'/(k+('.html' if k in ('AAAI_landing','TRACE_author') else '.json'))
  p.write_bytes(b)
  return dict(id=k,url=u,path=str(p.relative_to(H)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),ok=True)
 except Exception as e:return dict(id=k,url=u,ok=False,error=str(e))
rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(get,urls.items()))
(H/'sources'/'metadata_fetches.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
out=H/'papers'/'rendered';out.mkdir(exist_ok=True)
render=[]
for paper,pages in {'TRACE':[9,10],'OARP_Replan':[11,14],'FALCON':[12,15],'LS_MCPP':[6,7]}.items():
 doc=pdfium.PdfDocument(str(H/'papers'/(paper+'.pdf')))
 for n in pages:
  im=doc[n-1].render(scale=1.5).to_pil();p=out/(paper+'__p'+str(n)+'.png');im.save(p)
  render.append(dict(paper=paper,pdf_page=n,path=str(p.relative_to(H)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 doc.close()
(H/'papers'/'render_receipt.json').write_text(json.dumps(render,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'fetches':rows,'rendered_pages':len(render)},ensure_ascii=False))
