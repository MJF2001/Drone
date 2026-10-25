"""Render the local HTML in a separate headless Chrome profile for visual QA."""
from pathlib import Path
import subprocess,json
from html.parser import HTMLParser

H=Path(__file__).resolve().parent
TARGET=H/'导师汇报稿_图文阅读版.html'
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
PREVIEW=H/'html_v2_preview'
PREVIEW.mkdir(exist_ok=True)
class Attributes(HTMLParser):
 def __init__(self):super().__init__();self.result=None
 def handle_starttag(self,tag,attrs):
  if tag=='html':
   data=dict(attrs).get('data-report-qa')
   if data:self.result=json.loads(data)

receipts=[]
for name,w,h,fragment in [('desktop_top',1440,1000,''),('desktop_cases',1440,1100,'#cases'),('desktop_chart',1440,1100,'#hypothesis'),('mobile_top',390,1000,'')]:
 args=[str(CHROME),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions','--disable-background-networking','--disable-sync',f'--user-data-dir={PREVIEW/"browser_profile"}',f'--window-size={w},{h}','--force-device-scale-factor=1','--virtual-time-budget=1700',f'--screenshot={PREVIEW/(name+".png")}','--dump-dom',TARGET.as_uri()+fragment]
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40,startupinfo=startup)
 parser=Attributes();parser.feed(result.stdout.decode('utf-8',errors='replace'))
 receipt=dict(name=name,exit_code=result.returncode,screenshot=str(PREVIEW/(name+'.png')),browser_checks=parser.result)
 assert result.returncode==0,receipt
 assert parser.result is not None,receipt
 assert parser.result['brokenImages']==0,receipt
 assert not parser.result['layoutOverflow'],receipt
 assert parser.result['bodyWidth']<=parser.result['viewport']+2,receipt
 receipts.append(receipt)
(PREVIEW/'browser_qa.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipts,ensure_ascii=False,indent=2))
