from pathlib import Path
import sys,json
H=Path(__file__).resolve().parent
rows=json.loads((H/'papers'/(sys.argv[1]+'.pages.json')).read_text(encoding='utf-8'))
for i in map(int,sys.argv[2].split(',')):print('\n=== '+sys.argv[1]+' PDF PAGE '+str(i)+' ===\n'+rows[i-1]['text'])
