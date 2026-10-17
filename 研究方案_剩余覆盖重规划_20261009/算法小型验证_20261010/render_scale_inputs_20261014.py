"""Plot saved geometry, never call a planner. Requires Pillow only."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont


def main():
    root=Path(__file__).parent/'scale_inputs/development_v0.1_20261014'
    out=root.parent/'development_v0.1_20261014_verification'/'scene_atlas.png'
    if out.exists():raise FileExistsError(out)
    records={}
    for line in (root/'snapshots.jsonl').open(encoding='utf-8'):
        s=json.loads(line);m=s['metadata']
        if m['history']=='H' and m['progress_percent']==50 and m['event']=='corner_obstacle':
            records[m['scale'],m['stratum']]=s
    image=Image.new('RGB',(2200,1610),'white');draw=ImageDraw.Draw(image)
    fontpath='C:/Windows/Fonts/segoeui.ttf'
    font=ImageFont.truetype(fontpath,20);small=ImageFont.truetype(fontpath,16)
    draw.text((24,12),'Development input geometry | H history, 50% checkpoint, corner + obstacle | No algorithm routes',fill='black',font=font)
    colors={'free':'#edf1f4','pending':'#8bb9db','covered':'#aeb6bd',
            'extension':'#52bf8c','blocked':'#24292f','deferred':'#f2a33b'}
    x=24
    for label,color in colors.items():
        draw.rectangle((x,50,x+16,66),fill=color);draw.text((x+22,45),label,fill='black',font=small);x+=150
    draw.text((950,45),'S: current (magenta)   B: base (blue); panels use independent scales',fill='black',font=small)
    selected=[]
    for row,scale in enumerate(('small','medium','large')):
        for col in range(4):
            s=records[scale,col+1];m=s['metadata'];selected.append(s['name'])
            pts=lambda raw:set(map(tuple,raw))
            free=pts(s['free']);blocked=pts(m['obstacles']);domain=free|blocked
            old=pts(m['initial_targets']);covered=pts(s['covered']);targets=pts(s['targets'])
            extra=pts(m['published_targets'])-old;deferred=pts(m['deferred_targets'])
            x0=min(x for x,y in domain);x1=max(x for x,y in domain)
            y0=min(y for x,y in domain);y1=max(y for x,y in domain)
            left=col*550+18;top=row*500+94
            draw.text((left,top),f'{scale} / geometry {col+1}',font=font,fill='black')
            draw.text((left,top+28),f"pending={len(targets-covered)}, deferred={len(deferred)}, new={len(extra)}",font=small,fill='black')
            factor=min(510/(x1-x0+1),400/(y1-y0+1))
            def box(p):
                x,y=p;a=left+8+(x-x0)*factor;b=top+65+(y1-y)*factor
                return a,b,a+factor,b+factor
            for cells,color in ((domain,colors['free']),(targets-covered,colors['pending']),
                (covered-blocked,colors['covered']),(extra-blocked,colors['extension']),
                (blocked,colors['blocked']),(deferred,colors['deferred'])):
                for p in sorted(cells):draw.rectangle(box(p),fill=color)
            for raw,label,color in ((s['base'],'B','#005dcc'),(s['current'],'S','#ae16a5')):
                a,b,c,d=box(tuple(raw));cx=(a+c)/2;cy=(b+d)/2
                draw.ellipse((cx-5,cy-5,cx+5,cy+5),fill=color)
                draw.text((cx+6,cy-12),label,font=small,fill=color,stroke_width=1,stroke_fill='white')
    image.save(out)
    (out.parent/'scene_atlas_selection.json').write_text(json.dumps(dict(
        selection_rule='all development maps; H; p50; corner_obstacle; no result-based selection',
        state_ids=selected,algorithm_routes_shown=False),indent=2),encoding='utf-8')
    print(out)


if __name__=='__main__':main()
