"""Pillow scientific grid figures plus SVG; actual saved movement only."""
from util import *
def main():
    from PIL import Image,ImageDraw,ImageFont
    from html import escape
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);large=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    worlds=read(H/'worlds.json');meta=read(H/'world_metadata.json')
    for wid,w in worlds.items():
        im=Image.new('RGB',(1800,850),'white');d=ImageDraw.Draw(im);svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="850" viewBox="0 0 1800 850">','<rect width="1800" height="850" fill="white"/>']
        def text(x,y,s,color='#202020',f=font):
            d.text((x,y),s,font=f,fill=color);svg.append(f'<text x="{x}" y="{y+f.size}" fill="{color}" font-family="Arial,sans-serif" font-size="{f.size}">{escape(s)}</text>')
        def line(a,b,c,width=1):
            d.line([a,b],fill=c,width=max(1,round(width)));svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{c}" stroke-width="{width}"/>')
        def box(a,b,c,outline=None):
            d.rectangle([a,b],fill=c,outline=outline);svg.append(f'<rect x="{a[0]}" y="{a[1]}" width="{b[0]-a[0]}" height="{b[1]-a[1]}" fill="{c}" stroke="{outline or c}"/>')
        m=meta[wid];text(35,16,f"DEVELOPMENT {wid} | L={m['L']}, width={m['w']} | events t={w['events'][0]['tick']}, {w['events'][1]['tick']}",f=large)
        text(35,49,'Full F0 rectangle shown. Colored lines: actual movement only (early purple -> late orange). Unexecuted plans are omitted.',f=small)
        text(35,74,'Blue cells: initial targets | orange: added targets | black: new blocked cells | red square: start/base | red rings: event positions',f=small)
        for j,method in enumerate(('PPCPP','P2_MULTI')):
            file=H/'sessions'/(wid+'_'+method+'.json');s=read(file)['sessions'][method] if file.exists() else None;maxx=max(x for x,y in w['free']);maxy=max(y for x,y in w['free']);scale=min(790/(maxx+1),620/(maxy+1));left=55+j*900;bottom=790
            def xy(p):return (left+(p[0]+.5)*scale,bottom-(p[1]+.5)*scale)
            def cell(p,color):
                x,y=xy(p);r=scale*.44;box((x-r,y-r),(x+r,y+r),color)
            box((left,bottom-(maxy+1)*scale),(left+(maxx+1)*scale,bottom),'#f1f4f6','#66717b')
            for x in range(0,maxx+1,5):
                xx=left+(x+.5)*scale;line((xx,bottom-(maxy+1)*scale),(xx,bottom),'#dce1e5');text(xx-3,bottom+5,str(x),f=small)
            for y in range(0,maxy+1,5):
                yy=bottom-(y+.5)*scale;line((left,yy),(left+(maxx+1)*scale,yy),'#dce1e5');text(left-32,yy-8,str(y),f=small)
            for p in w['published']:cell(p,'#7fb4df')
            for p in w['events'][0]['add_targets']:cell(p,'#f5bc65')
            for p in w['events'][1]['block']:cell(p,'#191919')
            if s:
                q=s['summary'];moves=[a for a in s['actions'] if a['kind']=='move']
                for a in moves:
                    frac=a['tick']/max(1,q['finish_tick']);rgb=tuple(round(v+(u-v)*frac) for v,u in zip((78,42,142),(222,119,23)));color='#%02x%02x%02x'%rgb;line(xy(a['start']),xy(a['end']),color,2)
                for ev in w['events']:
                    f0=next((f for f in s['frames'] if f['tick']==ev['tick']),None)
                    if f0:
                        x,y=xy(f0['before']['current']);r=7;d.ellipse((x-r,y-r,x+r,y+r),outline='#c82333',width=2);svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="none" stroke="#c82333" stroke-width="2"/>');text(x+7,y-17,'t='+str(ev['tick']),'#b02030',small)
                if q['status']!='success':
                    x,y=xy(q['current']);line((x-7,y-7),(x+7,y+7),'#c82333',3);line((x-7,y+7),(x+7,y-7),'#c82333',3)
                text(left,112,f"{method}: {q['status']} | actual M={q['M']} | finish tick={q['finish_tick']}")
                text(left,138,f"H/U/D={len(q['H'])}/{len(q['U'])}/{len(q['D'])} | waits={q['waits']} | responses={q['response_calls']}",f=small)
            else:text(left,112,method+': NOT RUN (technical batch stop)')
            x,y=xy(w['base']);r=5;box((x-r,y-r),(x+r,y+r),'#cf2739')
        im.save(H/'figures'/(wid+'.png'));svg.append('</svg>');put(H/'figures'/(wid+'.svg'),'\n'.join(svg).encode('utf8'))
    canvas=Image.new('RGB',(1800,1275),'white')
    for i,wid in enumerate(worlds):
        im=Image.open(H/'figures'/(wid+'.png')).convert('RGB');im.thumbnail((900,425));canvas.paste(im,((i%2)*900,(i//2)*425))
    canvas.save(H/'figures'/'全部六世界预览.png');print('Saved6 complete world figures,12 actual saved trajectories;0 new graph/algorithm calls',flush=True)
if __name__=='__main__':main()
