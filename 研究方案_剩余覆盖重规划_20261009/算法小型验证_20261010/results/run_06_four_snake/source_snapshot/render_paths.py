"""Static, inspectable path plots from recorded results (Pillow only)."""
from pathlib import Path
import argparse
import json
from PIL import Image, ImageDraw, ImageFont


def render(folder):
    snapshots = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    results = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    examples = [s for s in snapshots if '_L18_W6_p50' in s['name']]
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    font = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()
    small = ImageFont.truetype(str(font_path), 13) if font_path.exists() else font
    cards = []
    for s in examples:
        meta = s['metadata']
        domain = set(map(tuple, meta['domain']))
        targets = set(map(tuple, s['targets']))
        covered = set(map(tuple, s['covered']))
        blocked = set(map(tuple, meta['obstacles']))
        new = targets-set(map(tuple, meta['initial_targets']))
        xmin, xmax = min(x for x,y in domain), max(x for x,y in domain)
        ymin, ymax = min(y for x,y in domain), max(y for x,y in domain)
        scale, margin = 15, 20
        pw, ph = (xmax-xmin+1)*scale+2*margin, (ymax-ymin+1)*scale+85
        card = Image.new('RGB', (2*pw, ph+35), 'white')
        d = ImageDraw.Draw(card)
        d.text((10, 5), s['name'], font=font, fill='black')
        for col, algorithm in enumerate(('P1', 'P2')):
            record = next(r for r in results if r['case'] == s['name'] and r['algorithm'] == algorithm and r['repeat'] == 0)
            ox = col*pw+margin
            def box(p):
                x,y=p
                left=ox+(x-xmin)*scale
                top=65+(ymax-y)*scale
                return left,top,left+scale,top+scale
            def center(p):
                l,t,_,_=box(p)
                return l+scale//2,t+scale//2
            for p in domain:
                colour = '#eeeeee'
                if p in targets: colour='#fff2cc'
                if p in new: colour='#d4ebff'
                if p in covered: colour='#cfe9ce'
                if p in blocked: colour='#333333'
                d.rectangle(box(p), fill=colour, outline='#d0d0d0', width=1)
            route=list(map(tuple,record['route']))
            if len(route)>1:
                d.line([center(p) for p in route], fill='#c51b32' if col==0 else '#195cad',width=2)
            for label,p,colour in [('S',s['current'],'#ff6500'),('B',s['base'],'#000000')]:
                cx,cy=center(p)
                d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=colour)
                d.text((cx+4,cy-15),label,font=small,fill=colour)
            d.text((ox,35),f'{algorithm}: {record["audit"]["length"]} steps; {record["seconds"]*1000:.1f} ms',font=small,fill='black')
        cards.append(card)
    width=max(c.width for c in cards)
    height=sum(c.height for c in cards)+70
    canvas=Image.new('RGB',(width,height),'white')
    draw=ImageDraw.Draw(canvas)
    draw.text((10,10),'Exploratory snapshots. Left: repair P1. Right: rebuild P2.',font=font,fill='black')
    draw.text((10,35),'Green: completed; yellow: old pending; blue: newly released; black: no-fly.',font=small,fill='black')
    y=65
    for card in cards:
        canvas.paste(card,(0,y));y+=card.height
    canvas.save(folder/'paths_overview.png')
    print(folder/'paths_overview.png')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',nargs='?',default='results/run_01')
    render(Path(parser.parse_args().folder))
