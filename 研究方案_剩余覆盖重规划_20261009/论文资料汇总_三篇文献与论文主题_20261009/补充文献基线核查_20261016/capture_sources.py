"""Read-only source capture; never changes planners or experiment outputs."""
from pathlib import Path
import urllib.request, hashlib, json
from datetime import datetime, timezone
from pypdf import PdfReader

OUT = Path(__file__).resolve().parent
url = 'https://linkslab.engr.uconn.edu/wp-content/uploads/sites/246/2018/11/e_star_Preprint.pdf'
p = OUT / 'epsilon_star_author_preprint.pdf'
if p.exists():
    raise SystemExit('Refuse overwrite')
record = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat()}
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = r.read()
        record.update(final_url=r.url, content_type=r.headers.get('Content-Type'))
    if not data.startswith(b'%PDF'):
        raise ValueError('Not PDF')
    p.write_bytes(data)
    reader = PdfReader(p)
    record['pages'] = len(reader.pages)
    (OUT / 'epsilon_star_author_preprint.txt').write_text('\n\n'.join(f'=== PDF page {i+1} ===\n'+page.extract_text() for i,page in enumerate(reader.pages)), encoding='utf-8')
    record['status'] = 'captured'
except Exception as e:
    record.update(status='failed', error=repr(e))
(OUT / 'capture_log.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
old = OUT.parent / '文献基线核查_20261014/候选原文补查'
provenance = [{'path':str(old/n), 'sha256':hashlib.sha256((old/n).read_bytes()).hexdigest()} for n in ['PPCPP_author_manuscript.pdf','PPCPP_author_manuscript.txt']]
(OUT/'existing_sources.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
entries = [{'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(OUT.iterdir()) if f.is_file() and f.name!='sha256_manifest.json']
(OUT/'sha256_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
