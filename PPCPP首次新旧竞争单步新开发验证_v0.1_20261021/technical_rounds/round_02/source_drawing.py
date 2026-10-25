"""Final reports, actual saved OFF/ON diagrams and separate call/search ledgers."""
from common import *
import html,datetime
def draw(st,a):
    job=next(r['job'] for r in a['rows'] if r['job']['state']==st['id']);c=read(H/job['input']);F=set(map(tuple,c['free']));T=set(map(tuple,c['targets']));old=set(map(tuple,c['initial_targets']));A=T-old;hist=set(map(tuple,c['covered']));s=12;pw=(st['L']+8)*s+30;height=(st['w']+8)*s+115;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw*3}" height="{height}"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Microsoft YaHei,Arial,sans-serif;font-size:11px}}</style>']
    for k,mode in enumerate(('INPUT','OFF','ON')):
        x0=k*pw+12;y0=44;row=None;r=[]
        if mode!='INPUT':
            row=next(r for r in a['rows'] if r['job']['state']==st['id'] and r['job']['seed']==20261020 and r['job']['mode']==mode);file=H/'outputs'/f'{row["job"]["id"]}.json'
            if file.exists():r=read(file)['result']['raw'].get('route',[])
        text=st['id'] if mode=='INPUT' else f'{mode} L={row["metrics"]["length"] if row["metrics"] else "NA"}, timely={row["timely"]}'
        parts.append(f'<text x="{x0}" y="16">{html.escape(text)}</text>')
        if row and row.get('audit'):parts.append(f'<text x="{x0}" y="32">C={row["metrics"]["completion_step"]}, R={row["metrics"]["return_tail_steps"]}, trigger={row["audit"]["trigger_count"]}</text>')
        for x,y in sorted(F):
            p=(x,y);fill='#ffb64d' if p in A else '#8bb7ec' if p in hist else '#ffeaaa' if p in T else '#f4f4f4';parts.append(f'<rect x="{x0+x*s}" y="{y0+y*s}" width="{s}" height="{s}" fill="{fill}" stroke="#ccc" stroke-width=".4"/>')
        if r:
            C=row['metrics']['completion_step']
            for rr,color,dash in [(r[:C+1],'#206b34',''),(r[C:],'#b51c3e','stroke-dasharray="3 2"')]:
                pts=' '.join(f'{x0+(p[0]+.5)*s},{y0+(p[1]+.5)*s}' for p in rr);parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.7" {dash}/>')
            if mode=='ON' and row['audit']['intervention_log']:
                ev=row['audit']['intervention_log'][0];pts=' '.join(f'{x0+(p[0]+.5)*s},{y0+(p[1]+.5)*s}' for p in (ev['current'],ev['forced_selected']));parts.append(f'<polyline points="{pts}" stroke="#a400ff" stroke-width="4" fill="none"><title>唯一强制一步</title></polyline>')
        for p,color in [(c['base'],'black'),(c['current'],'#e50070')]:parts.append(f'<circle cx="{x0+(p[0]+.5)*s}" cy="{y0+(p[1]+.5)*s}" r="3.5" fill="{color}"/>')
    parts.append(f'<text x="12" y="{height-18}">固定seed20261020；橙新任务／蓝历史／黄旧待检；绿采集段／红虚线返航／紫唯一干预步；全部实际保存路线。</text></svg>');p=H/'figures'/f'{st["id"]}.svg'
    with p.open('x',encoding='utf8') as f:f.write(''.join(parts))
    return p.name
