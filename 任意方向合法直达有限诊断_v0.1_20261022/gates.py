"""Register fixtures BEFORE execution; at most three gate attempts, no saved batch."""
from pathlib import Path
from fractions import Fraction as Q
from decimal import Decimal
import json,sys,hashlib,time
import geometry as G
import audit_geometry as A
import engine
H=Path(__file__).resolve().parent
def rect(w,h):return [(x,y) for x in range(w) for y in range(h)]
def query(name,F,a,b,expect,note):return {'name':name,'type':'geometry','F':F,'a':list(map(str,a)),'b':list(map(str,b)),'expected':expect,'manual_reason':note}
def route(name,F,path,U,E,expected,note,**opts):return {'name':name,'type':'route','F':F,'route':path,'U':U,'E':E,'expected':expected,'manual_reason':note,'options':opts}
def fixtures():
    square=rect(2,2);wide=rect(3,2)
    return [
      query('01_中间穿障碍',[(0,0),(2,0)],(0,0),(2,0),False,'中间格禁止'),
      query('02_擦障碍角',[(0,0),(0,1),(1,1)],(0,0),(1,1),False,'半半角点邻有禁止象限'),
      query('03_仅角点接触',[(0,0),(1,1)],(0,0),(1,1),False,'对角格间不通'),
      query('04_沿障碍边',[p for p in rect(3,3) if p!=(1,1)],(0,Q(1,2)),(2,Q(1,2)),False,'中段在缺格下边'),
      query('05_沿外边界',rect(3,1),(0,Q(1,2)),(2,Q(1,2)),False,'外边不属开放域'),
      query('06_沿共享自由边',square,(Q(1,2),0),(Q(1,2),1),True,'两侧及交点四格均自由'),
      query('07_四自由格交点',square,(0,0),(1,1),True,'半半四象限自由'),
      query('08_非目标通行',rect(3,1),(0,0),(2,0),True,'F决定通行而非目标集合'),
      query('09_F缺口',[(0,0),(0,1),(2,0),(2,1)],(0,0),(2,1),False,'中列缺失，不能由包围盒补成自由格'),
      query('10_起点非法',square,(-1,0),(1,0),False,'起点在F外'),
      query('11_终点非法',square,(0,0),(2,0),False,'终点在F外'),
      dict(query('12_穿格不穿中心',wide,(0,0),(2,1),True,'经过(1,0)格内但中心不在线上'),hit_point=[1,0],hit_expected=None),
      dict(query('13_顺带中心信用',rect(3,1),(0,0),(2,0),True,'中点中心参数一半'),hit_point=[1,0],hit_expected='1/2'),
      route('14_起点即时信用',rect(2,1),[(0,0),(1,0)],[(0,0)],1,{'L':1,'first':[0,0]},'起点任务无需移动'),
      route('15_空任务返航',rect(3,1),[(2,0),(1,0),(0,0)],[],2,{'L':2},'空任务仍完整返航'),
      route('16_空任务同点',[(0,0)],[(0,0)],[],0,{'L':0},'零移动合法'),
      route('17_同点跨索引闭环',rect(2,1),[(0,0),(1,0),(0,0)],[],2,{'L':0,'span':2},'无责任闭环以零长边保留原索引0到2'),
      route('18_资源恰好边界',rect(2,1),[(0,0),(1,0)],[],1,{'L':1},'恰好等于E应接受'),
      route('19_来源资源超限',rect(2,1),[(0,0),(1,0)],[],0.999,{'reject':True},'源已超限必须拒绝'),
      route('20_自由2乘2正控制',square,[(0,0),(1,0),(1,1)],[],2,{'sqrt2':True},'无中间任务2变根号2，不逐段取整'),
      route('21_中间中心必检',square,[(0,0),(1,0),(1,1)],[(1,0)],2,{'L':2,'first':[1,0]},'锁住中间任务，禁止漏检'),
      route('22_次数上限回退',square,[(0,0),(1,0),(1,1)],[],2,{'L':2,'fallback':'candidate_cap'},'0候选保留完整原后缀',limit=0),
      route('23_软截止回退',square,[(0,0),(1,0),(1,1)],[],2,{'L':2,'fallback':'soft_deadline'},'0秒软截止保留原后缀',soft=0),
      route('24_真实信用顺序改变',wide,[(0,0),(0,1),(1,1),(2,1),(2,0),(1,0),(0,0)],[(2,0),(1,0)],6,{'changed':True,'first':[1,0]},'首名义锚点2,0前顺带服务1,0，仍保留两个锚点'),
    ]
def main():
    reg=H/'24门槛预登记.json'
    if sys.argv[1]=='register':
        with reg.open('x',encoding='utf8') as f:json.dump(fixtures(),f,ensure_ascii=False,indent=2)
        print('registered 24 fixtures; not executed');return
    attempts=list(H.glob('gate_attempt_*.json'));assert len(attempts)<3
    fs=json.loads(reg.read_text(encoding='utf8'));assert len(fs)==24;results=[];passed=True
    for f in fs:
        begin=time.perf_counter();counts={'direct_main':0,'direct_independent':0,'service_main':0,'service_independent':0};item={'name':f['name'],'queries_registered':1,'counts':counts}
        try:
            F=set(map(tuple,f['F']))
            if f['type']=='geometry':
                a=tuple(map(Q,f['a']));b=tuple(map(Q,f['b']));counts['direct_main']+=1;x=G.legal(F,a,b);counts['direct_independent']+=1;y=A.legal(F,a,b);assert x==y==f['expected'];item['legal']=x
                if 'hit_point' in f:
                    p=tuple(f['hit_point']);counts['service_main']+=1;counts['service_independent']+=1
                    assert (None if G.hit(a,b,p) is None else str(G.hit(a,b,p)))==f['hit_expected'];assert G.hit(a,b,p)==A.hit(a,b,p)
            else:
                path=f['route'];c={'free':f['F'],'targets':f['U'],'covered':[],'published_targets':f['U'],'deferred_targets':[],'current':path[0],'base':path[-1],'previous':None,'distance_budget':f['E']};payload=json.dumps({'id':f['name'],'input':c,'raw':{'route':path,'trace':[]}})
                if f['expected'].get('reject'):
                    try:engine.process(payload,**f['options'])
                    except AssertionError:item['source_rejected']=True
                    else:raise AssertionError('source resource excess not rejected')
                else:
                    encoded,env=engine.process(payload,**f['options']);r=json.loads(encoded);item['output']=r;item['envelope']=env
                    for a,b in zip(r['vertices'],r['vertices'][1:]):counts['direct_independent']+=1;assert A.legal(F,a,b)
                    cc={'service_intersections':0};cr=engine.credits(list(map(tuple,r['vertices'])),set(map(tuple,f['U'])),cc,A.hit);counts['service_independent']=cc['service_intersections'];assert cr==r['first_actual']
                    e=f['expected'];lo,hi=map(Decimal,r['Lshortcut_interval'])
                    if 'L' in e:assert lo==hi==e['L']
                    if e.get('sqrt2'):assert lo*lo<=2<=hi*hi and 1<lo<hi<2
                    if 'first' in e:assert r['first_actual'][0]['point']==e['first']
                    if 'span' in e:assert r['edges'][0]['right']==e['span']
                    if 'fallback' in e:assert r['fallback']==e['fallback']
                    if 'changed' in e:assert r['actual_order_changed']==e['changed']
            item['passed']=True
        except Exception as ex:item['passed']=False;item['error']=repr(ex);passed=False
        item['seconds']=time.perf_counter()-begin;results.append(item)
    record={'attempt':len(attempts)+1,'passed':passed,'registration_sha256':hashlib.sha256(reg.read_bytes()).hexdigest(),'results':results,'planning_core_graph_exact_closed_loop':0,'note':'Each fixture has one registered segment or route case. All internal source/candidate/output and independent geometry/service costs are separately retained.'}
    (H/('gate_attempt_%d.json'%(len(attempts)+1))).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'passed':passed,'attempt':len(attempts)+1,'failed':[r['name'] for r in results if not r['passed']]},ensure_ascii=False));sys.exit(0 if passed else 1)
if __name__=='__main__':main()

