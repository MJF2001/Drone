"""Deterministic scientific grid illustration; self-generated, not paper figure."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_22_structural_stress'


def main():
    rows=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    # Fixed selection rule: largest P2 gap, then lexicographic case name.
    candidates=[r for r in rows if r['algorithm']=='P2_SHARED']
    chosen=min(candidates,key=lambda r:(-r.get('gap',-1),r['case']))['case']
    raw=json.loads((OUT/'snapshots.json').read_text(encoding='utf-8'))
    s=next(d for d in raw if d['name']==chosen)
    fontpath='C:/Windows/Fonts/msyh.ttc'
    font=lambda n:ImageFont.truetype(fontpath,n)
    image=Image.new('RGB',(1190,530),'white');draw=ImageDraw.Draw(image)
    draw.text((24,12),'结构性压力测试：唯一基线非最优例（自建仿真，非文献原图）',font=font(24),fill='#203747')
    draw.text((24,49),chosen,font=font(17),fill='#445566')
    domain=set(map(tuple,s['metadata']['domain']));free=set(map(tuple,s['free']))
    covered=set(map(tuple,s['covered']));pending=set(map(tuple,s['targets']))-covered
    blocked=set(map(tuple,s['metadata']['obstacles']))
    minx,miny=min(x for x,y in domain),min(y for x,y in domain)
    maxx,maxy=max(x for x,y in domain),max(y for x,y in domain)
    for panel,(alg,title,color) in enumerate((('EXACT_GRID','精确最优','#287d50'),('P2_SHARED','强基线 P2_SHARED','#b84d37'),('STRIP_HV','横纵条带候选','#4963a3'))):
        r=next(r for r in rows if r['case']==chosen and r['algorithm']==alg)
        ox=24+panel*390;oy=125;cell=min(33,350//(maxx-minx+1),320//(maxy-miny+1))
        draw.text((ox,90),title+'：'+str(r['audit']['length'])+'步',font=font(21),fill=color)
        def center(p):
            return ox+(p[0]-minx)*cell+cell//2,oy+(maxy-p[1])*cell+cell//2
        for p in domain:
            x,y=center(p)
            fill='#d8ebdc' if p in covered else '#f4deb0' if p in pending else '#f2f3f5'
            if p in blocked:fill='#40474e'
            draw.rectangle((x-cell//2,y-cell//2,x+cell//2,y+cell//2),fill=fill,outline='#c6ccd2')
        route=list(map(tuple,r['route']))
        for a,b in zip(route,route[1:]):
            ca,cb=center(a),center(b)
            draw.line((ca,cb),fill=color,width=3)
            ax,ay=ca;bx,by=cb
            mx,my=(ax+bx)//2,(ay+by)//2
            dx,dy=(bx-ax)//cell,(by-ay)//cell
            draw.polygon(((mx+3*dx,my+3*dy),(mx-3*dx+3*dy,my-3*dy-3*dx),(mx-3*dx-3*dy,my-3*dy+3*dx)),fill=color)
        for p,label in ((tuple(s['current']),'S'),(tuple(s['base']),'B')):
            x,y=center(p);draw.ellipse((x-11,y-11,x+11,y+11),fill='white',outline=color,width=2)
            draw.text((x-6,y-11),label,font=font(16),fill=color)
    draw.text((24,475),'黄色：剩余目标；浅绿：已覆盖；深灰：新障碍；浅灰：合法非目标飞行格。S当前位置，B基地。',font=font(17),fill='#34495e')
    draw.text((24,502),'图仅展示反例，不代表典型实例或总体收益；其余95例强基线已达到精确最优。',font=font(17),fill='#34495e')
    image.save(OUT/'unique_counterexample.png')


if __name__=='__main__':
    main()
