"""Check only the new report and its saved source hashes; no experiment imports."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,zipfile

H=Path(__file__).resolve().parent
sources=json.loads((H/'source_manifest.json').read_text(encoding='utf-8'))
for x in sources:
 assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
 if 'output' in x:assert hashlib.sha256((H/x['output']).read_bytes()).hexdigest()==x['sha256']
s=(H/'导师汇报稿_图文阅读版.html').read_text(encoding='utf-8')
HTMLParser().feed(s)
ids=set(re.findall(r'id="([^"]+)"',s))
targets=re.findall(r'href="#([^"]+)"',s)
assert all(t in ids for t in targets)
assert s.count('<figure>')==9
assert s.count('<img src="data:image/png;base64,')==9
md=(H/'导师汇报稿_研究思路与实验证据.md').read_text(encoding='utf-8')
for p in re.findall(r'!\[[^]]*\]\(([^)]+)\)',md):assert (H/p).exists()
record=json.loads((H/'制作与核对记录.json').read_text(encoding='utf-8'))
record.update(source_hashes_rechecked=len(sources),internal_anchor_links_checked=len(targets),all_images_manually_viewed_in_contact_sheet=True,html_syntax_parsed=True,browser_execution_tested=False,markdown_characters=len(md),html_bytes=(H/'导师汇报稿_图文阅读版.html').stat().st_size)
(H/'制作与核对记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme='''# 阅读说明

优先打开“导师汇报稿_图文阅读版.html”。图片已经嵌入，可以单独发送给导师；正文有目录，每张图可以点击放大。可用浏览器打印功能保存PDF。

“导师汇报稿_研究思路与实验证据.md”是可修改源稿，使用同目录images中的图片。“证据来源与核对清单.md”列出原始本地证据。源报告路径需要原研究项目文件夹才能访问。

汇报截止于I正例及其受控变体，未纳入后来完成的任务块结构整理。没有重跑实验、安装技能或修改旧证据。
'''
(H/'阅读说明.md').write_text(readme,encoding='utf-8')
files=[H/n for n in ['导师汇报稿_图文阅读版.html','导师汇报稿_研究思路与实验证据.md','证据来源与核对清单.md','source_manifest.json','制作与核对记录.json','阅读说明.md']]+list((H/'images').glob('*.png'))
zip_path=H/'导师汇报稿_图文与源稿.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(H))
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
print(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(dict(delivery_zip=str(zip_path),zip_files=len(files),zip_bytes=zip_path.stat().st_size),ensure_ascii=False))
