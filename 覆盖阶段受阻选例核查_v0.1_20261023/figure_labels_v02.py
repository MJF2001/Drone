from common import *
from PIL import Image,ImageDraw,ImageFont
def main():
 assert not (H/'figure_qa.json').exists()
 old=H/'figures_export_v01';old.mkdir(exist_ok=True)
 for x in read(H/'summary.json')['selected']:
  file=H/'figures'/(x['id']+'.png');(old/file.name).write_bytes(file.read_bytes());r=read(H/'records'/(x['id']+'.json'));im=Image.open(file).convert('RGB');d=ImageDraw.Draw(im);font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
  d.rectangle((0,878,1699,1171),fill='white');d.text((35,885),'旧后缀行进索引：边起点尚未完成的目标数；短刻线=各任务首次格心服务位置',font=font(20),fill='#17263c')
  left=90;right=1600;top=960;bottom=1120;maxu=r['summary']['remaining_tasks'];num=len(r['suffix'])-1
  def pt(i,p):return left+(right-left)*i/num,bottom-(bottom-top)*p/maxu
  d.line([(left,top),(left,bottom),(right,bottom)],fill='#495e76',width=2);d.line([pt(e['edge'],e['pending_at_start']) for e in r['edges']],fill='#2469ac',width=3)
  for f in r['first_services']:
   xx,_=pt(f['vertex_index'],0);d.line([(xx,bottom+4),(xx,bottom+12)],fill='#749fc6',width=1)
  for i,color,label in [(x['first_invalid_edge'],'#c84327','阻断边'),(x['last_first_service_index'],'#687888','末次服务')]:
   xx,_=pt(i,0);d.line([(xx,top),(xx,bottom)],fill=color,width=2);d.text((min(xx+4,1530),top-32),label+' '+str(i),font=font(17),fill=color)
  d.text((left-48,top-10),str(maxu),font=font(17),fill='#17263c');d.text((left-30,bottom-10),'0',font=font(17),fill='#17263c');d.text((left,bottom+20),'0',font=font(17),fill='#17263c');d.text((right-25,bottom+20),str(num),font=font(17),fill='#17263c');im.save(file)
 p=H/'02_可用快照与阻断证书.md';text=p.read_text(encoding='utf-8').replace('严格内部失效证书：\n-','严格内部失效证书：\n\n-');p.write_text(text,encoding='utf-8')
 dump(H/'figure_qa.json',{'count':2,'first_versions':'figures_export_v01/ retained','revision':'v02 separates timeline heading from selected-edge labels; no data/candidate change','saved_routes_only':True,'new_geometry_BFS_core_R_post':0})
 print({'figures_v02':2,'new_calls':0})
if __name__=='__main__':main()
