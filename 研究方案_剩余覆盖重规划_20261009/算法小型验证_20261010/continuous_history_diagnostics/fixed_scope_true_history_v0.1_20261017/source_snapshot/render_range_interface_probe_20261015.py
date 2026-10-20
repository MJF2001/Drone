"""Static route diagrams from verified tiny fixtures, not algorithm evaluation."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_range_probes/v0.1_20261015'
OUT=ALGO/'development_range_probes/v0.1_20261015_verification'
def main():
    assert json.loads((OUT/'summary.json').read_text(encoding='utf-8'))['status']=='independently_verified_tiny_splice'
    dest=OUT/'AB_ABC_full_routes.png';assert not dest.exists()
    data=json.loads((SOURCE/'results.json').read_text(encoding='utf-8'))
    rows=('loop_AB_sufficient','open_boundary_tradeoff');names=('AB已足够：三种范围均16步','扩大范围有收益：20 → 18 → 18步')
    im=Image.new('RGB',(1560,990),'#f5f7fa');d=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
    d.text((28,14),'重排范围机制检查：橙色为重规划段，蓝色为保留后缀',fill='#14263d',font=font(28))
    d.text((28,57),'五个人工微型夹具中的两个说明例；全范围为该微型栅格问题的精确值，不是同预算基线比较。',fill='#586b82',font=font(19))
    for row,sid in enumerate(rows):
        c=json.loads((SOURCE/'cases'/(sid+'.json')).read_text(encoding='utf-8'))
        free=set(map(tuple,c['free']));initial=set(map(tuple,c['metadata']['initial_free']))
        targets=set(map(tuple,c['targets']));blocked=set(map(tuple,c['metadata']['obstacles']))
        xmin=min(x for x,y in initial);xmax=max(x for x,y in initial);ymin=min(y for x,y in initial);ymax=max(y for x,y in initial)
        top=100+row*385
        d.text((28,top),names[row],fill='#14263d',font=font(24))
        for col,scope in enumerate(('AB','ABC','ALL')):
            r=next(r['result'] for r in data if r['case']==sid and r['scope']==scope)
            left=25+col*515;paneltop=top+42
            d.rounded_rectangle((left,paneltop,left+495,paneltop+320),radius=10,fill='white',outline='#d6dfe9',width=2)
            d.text((left+15,paneltop+10),f'{scope}    总路程 {r["steps"]} 步',fill='#14263d',font=font(23))
            size=min(32,int(450/(xmax-xmin+1)));ox=left+27;oy=paneltop+90
            xy=lambda p:(ox+(p[0]-xmin+.5)*size,oy+(ymax-p[1]+.5)*size)
            for p in initial:
                x,y=xy(p);color='#e7edf3' if p not in targets else '#d6efdf'
                if p in blocked:color='#d75d5d'
                d.rectangle((x-size*.47,y-size*.47,x+size*.47,y+size*.47),fill=color,outline='white')
            for route,color,width in ((r['scope_info']['suffix'],'#346eac',4),(r['patch'],'#e07a20',4)):
                if len(route)>1:d.line([xy(p) for p in route],fill=color,width=width,joint='curve')
            for label,key,color in (('S','current','#0b5946'),('H','base','#14263d')):
                x,y=xy(c[key]);d.ellipse((x-9,y-9,x+9,y+9),fill=color)
                d.text((x-7,y-12),label,fill='white',font=font(16))
            for b in c['blocks']:
                x,y=xy(b['service'][0]);d.text((x-8,y-size-23),b['label'],fill='#18452c',font=font(18))
            x,y=xy(r['scope_info']['join']);d.ellipse((x-11,y-11,x+11,y+11),outline='#9846bb',width=3)
            d.text((left+14,paneltop+266),f'局部段 {r["patch_steps"]} + 保留后缀 {r["preserved_tail_steps"]}',fill='#586b82',font=font(19))
    d.text((28,891),'绿格：当前目标；红格：新障碍；S：当前位置；H：基地；紫圈：接回接口。',fill='#43566d',font=font(22))
    d.text((28,934),'所有移动按四邻接计步；路线可经过范围外自由格，局部段不等于局部地图裁剪。',fill='#586b82',font=font(21))
    im.save(dest);print(dest)
if __name__=='__main__':main()
