"""Read four primary PDFs; page-numbered text and selected visual pages only."""
from pathlib import Path
import json,fitz
H=Path(__file__).resolve().parent
if __name__=='__main__':
    out=[]
    for p in sorted((H/'papers').glob('*.pdf')):
        d=fitz.open(p);pages=[]
        for i,page in enumerate(d):pages.append({'pdf_page_1based':i+1,'text':page.get_text()})
        (p.with_suffix('.pages.json')).write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
        (p.with_suffix('.txt')).write_text('\n\n'.join('=== PDF PAGE '+str(x['pdf_page_1based'])+' ===\n'+x['text'] for x in pages),encoding='utf-8')
        out.append({'id':p.stem,'pages':len(d),'metadata':d.metadata})
    (H/'papers/page_index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(out)
