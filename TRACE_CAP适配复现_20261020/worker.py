import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'))
from planners import solve
if __name__=='__main__':
    job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    c=json.loads(Path(job['input']).read_text(encoding='utf-8'))
    result=solve(c,job['method'],job['budget'],job['seed'])
    Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
