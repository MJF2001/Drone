"""Render fixed-domain/input semantics, without recomputing any algorithm."""
from pathlib import Path
import argparse
import json
from PIL import Image, ImageDraw, ImageFont


def render(folder):
    rows = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    families = [('no_change', 'Before change'), ('straight', 'New inspection targets'),
                ('corner_channel', 'Corner extension + no-fly cells')]
    font_path = 'C:/Windows/Fonts/arial.ttf'
    font = ImageFont.truetype(font_path, 16)
    small = ImageFont.truetype(font_path, 13)
    examples = [next(r for r in rows if r['name'] == f'v2_corridor_{family}_L24_W9_p25')
                for family, label in families]
    domain = set(map(tuple, examples[0]['metadata']['domain']))
    xmin, xmax = min(x for x,y in domain), max(x for x,y in domain)
    ymin, ymax = min(y for x,y in domain), max(y for x,y in domain)
    scale = 12
    width, height = (xmax-xmin+1)*scale+30, (ymax-ymin+1)*scale+100
    canvas = Image.new('RGB', (3*width, height+75), 'white')
    d = ImageDraw.Draw(canvas)
    d.text((12, 8), 'Same flight-permission domain D in all three panels (L24/W9, 25% checkpoint)', font=font, fill='black')
    for i, (r, (_, title)) in enumerate(zip(examples, families)):
        targets, completed = set(map(tuple, r['targets'])), set(map(tuple, r['covered']))
        old = set(map(tuple, r['metadata']['initial_targets']))
        blocked = set(map(tuple, r['metadata']['obstacles']))
        ox, oy = i*width+15, 70
        def box(p):
            x,y = p
            left, top = ox+(x-xmin)*scale, oy+(ymax-y)*scale
            return left, top, left+scale, top+scale
        def center(p):
            a,b,_,_ = box(p)
            return a+scale/2,b+scale/2
        d.text((ox, 40), title, font=font, fill='black')
        for p in sorted(domain):
            colour = '#eeeeee'
            if p in targets: colour = '#fff2cc'
            if p in targets-old: colour = '#b8dcff'
            if p in completed: colour = '#cfe9ce'
            if p in blocked: colour = '#333333'
            d.rectangle(box(p), fill=colour, outline='#cccccc')
        route = list(map(tuple, r['old_route']))
        if len(route)>1:
            d.line([center(p) for p in route], fill='#dc7946', width=2)
        for label, p, colour in [('S', r['current'], '#ae1313'), ('B', r['base'], '#111111')]:
            x,y = center(p)
            d.ellipse((x-4,y-4,x+4,y+4), fill=colour)
            d.text((x+5,y-16), label, font=small, fill=colour)
    legend = 'Grey: flight only | Yellow: old pending | Green: completed | Blue: new targets | Black: no-fly'
    d.text((12, height+5), legend, font=small, fill='black')
    d.text((12, height+28), 'Orange: OLD remaining route (may be invalid after event). S: current. B: base. Ideal 3x3 footprint; no occlusion.', font=small, fill='black')
    canvas.save(folder/'fixed_domain_model.png')
    print(folder/'fixed_domain_model.png')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    render(Path(p.parse_args().folder))
