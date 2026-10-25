"""Annotate I_M saved prefixes only, never find or alter a route."""
from common import *
def main():
    violations=install_guard();require_sources()
    from PIL import Image,ImageDraw,ImageFont
    w=read(S/'worlds.json')['I_M'];data={};im=Image.new('RGB',(1720,650),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);large=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    draw.text((30,15),'I_M: observed prefixes through arrival tick48, no alternative trajectories',fill='#202020',font=large);draw.text((30,49),'Viewport x=0..30, y=0..9 is a drawing window, not a new world. The original F0 continues beyond it.',fill='#333333',font=small);draw.text((30,74),'Green=already credited, pale blue=remaining, orange border=event1 tasks, black=blocked at48 (earlier paths may cross).',fill='#333333',font=small)
    for j,method in enumerate(('PPCPP','P2_MULTI')):
        s=read(S/'sessions'/('I_M_'+method+'.json'))['sessions'][method];c=s['requests'][-1]['input'];moves=[a for a in s['actions'] if a['kind']=='move' and a['arrival_tick']<=48];route=[w['start']]+[a['end'] for a in moves];diff=next(a for a in moves if a['tick']==13);data[method]=dict(source=str(S/'sessions'/('I_M_'+method+'.json')),route=route,first_different_action=diff,last_event_input_current=c['current'],last_event_input_previous=c['previous'],covered=c['covered'],remaining=ls(ps(c['targets'])-ps(c['covered'])))
        left=45+j*850;bottom=570;scale=25
        def xy(p):return (left+scale*(p[0]+.5),bottom-scale*(p[1]+.5))
        draw.rectangle((left,bottom-250,left+775,bottom),fill='#f4f6f8',outline='#889099')
        for x in range(0,31,5):
            q=xy([x,0])[0];draw.line([(q,bottom-250),(q,bottom)],fill='#d7dde2');draw.text((q-5,bottom+5),str(x),fill='#333333',font=small)
        for y in range(0,10,2):
            q=xy([0,y])[1];draw.line([(left,q),(left+775,q)],fill='#d7dde2');draw.text((left-25,q-8),str(y),fill='#333333',font=small)
        for p in c['published_targets']:
            x,y=xy(p);color='#9bc8a5' if p in c['covered'] else '#c6dcee';draw.rectangle((x-10,y-10,x+10,y+10),fill=color)
        for p in w['events'][0]['add_targets']:
            x,y=xy(p);draw.rectangle((x-10,y-10,x+10,y+10),outline='#e47d13',width=2)
        color='#6944a1' if method=='PPCPP' else '#d57823';draw.line([xy(p) for p in route],fill=color,width=3)
        for p in w['events'][-1]['block']:
            x,y=xy(p);draw.rectangle((x-8,y-8,x+8,y+8),fill='#222222')
        for p,label in ((c['current'],'current@48'),(diff['end'],'arrival@14')):
            x,y=xy(p);draw.ellipse((x-9,y-9,x+9,y+9),outline='#c82333',width=3);draw.text((x+10,y-24),label,fill='#ad152a',font=small)
        a,b=xy(diff['start']),xy(diff['end']);draw.line([a,b],fill='#d31733',width=5)
        x,y=xy(w['base']);draw.rectangle((x-6,y-6,x+6,y+6),fill='#cc263a');draw.text((left,117),method+' | H='+str(len(c['covered']))+' U='+str(len(data[method]['remaining'])),fill='#202020',font=font);draw.text((left,146),'current='+str(c['current'])+' previous='+str(c['previous']),fill='#202020',font=small)
    im.save(H/'I_M保存轨迹注记.png');save(H/'I_M绘图仅用保存数据.json',data);save(H/'figure_zero_ledger.json',zeros('annotate_saved_prefixes',violations));print('Saved existing I_M prefix annotation; new route/world/search0',flush=True)
if __name__=='__main__':main()
