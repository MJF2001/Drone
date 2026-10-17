from pathlib import Path
import json,hashlib
import pypdfium2 as pdfium

out=Path(__file__).resolve().parent
old=out.parent/'补充文献基线核查_20261016/epsilon_star_author_preprint.pdf'
doc=pdfium.PdfDocument(old)
for i in [2,3,4]:
    p=out/f'epsilon_page_{i+1}.png'
    if p.exists(): raise SystemExit('refuse overwrite')
    page=doc[i]; bitmap=page.render(scale=1.5)
    bitmap.to_pil().save(p)
    bitmap.close(); page.close()
doc.close()
sources=[old,out.parent/'文献基线核查_20261014/候选原文补查/PPCPP_author_manuscript.pdf']
(out/'original_source_hashes.json').write_text(json.dumps([{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],ensure_ascii=False,indent=2),encoding='utf-8')
for n in ['01_four_mechanisms.json','02_baseline_identity.json','03_access_gaps.json']:
    assert json.loads((out/n).read_text(encoding='utf-8'))['response']
entries=[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir()) if p.is_file() and p.name!='sha256_manifest.json']
(out/'sha256_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS:',len(entries),'artifacts; 3 original PDF pages rendered; 3 web captures parsed')
