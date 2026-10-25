import json
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
    d=json.loads((H/'diagnosis.json').read_text(encoding='utf-8'));out={}
    for batch in ('original20','controlled27'):
        own=[x for x in d['states'] if x['batch']==batch];totals={}
        for policy,label in [('near','nearest_base'),('far','farthest_base')]:
            selected=[]
            for x in own:
                b=next((b for b in x['branches'] if label in b['labels']),x['branches'][0]);selected.append((x,b))
            totals[policy]=dict(total_steps=sum(b['metrics']['length'] for x,b in selected),shorter=sum(b['difference_vs_original']<0 for x,b in selected),equal=sum(b['difference_vs_original']==0 for x,b in selected),longer=sum(b['difference_vs_original']>0 for x,b in selected))
        out[batch]=totals
    (H/'saved_branch_policy_accounting.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
