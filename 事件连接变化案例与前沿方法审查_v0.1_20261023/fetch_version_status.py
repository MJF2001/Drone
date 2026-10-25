from pathlib import Path
import json,urllib.request,hashlib,datetime
H=Path(__file__).resolve().parent
u='https://api.github.com/repos/reso1/LS-MCPP/branches?per_page=100'
req=urllib.request.Request(u,headers={'User-Agent':'ResearchEvidenceAudit/1.0'})
with urllib.request.urlopen(req,timeout=30) as r:b=r.read()
(H/'sources'/'LS_MCPP_branches.json').write_bytes(b)
rows=json.loads(b)
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':u,'sha256':hashlib.sha256(b).hexdigest(),'branches':[{'name':x['name'],'sha':x['commit']['sha']} for x in rows],'conclusion':'README claims aaai24; preceding sha=aaai24 query returned HTTP404. No checkout or execution. Exact AAAI24 source not independently verified.'}
(H/'sources'/'LS_MCPP_version_status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
