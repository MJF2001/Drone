"""Twelve hand-computed detection/execution sessions; no planner calls."""
from fractions import Fraction as Q

def r(v):
    v=Q(v)
    return {'n':v.numerator,'d':v.denominator}
def p(x,y):
    return [r(x),r(y)]
def e(n=0,roots=None):
    return {'terms':([{'r':1,'c':r(n)}] if n else [])+[{'r':k,'c':r(v)} for k,v in (roots or {}).items()]}
def move(x,y):
    return {'kind':'move','to':p(x,y)}

def build():
    F=[[x,y] for x in range(5) for y in range(3)]
    cases=[]
    def add(ident,label,start,end,O=(2,1),P=None,h=(1,0),known=None,actions=None,expect=None,**extra):
        P=[] if P is None else P
        initial={'S':p(*start),'h':None if h is None else p(*h),'H':[],
                 'E':e(100),'M':e(),'known':[] if known is None else [list(v) for v in known]}
        case={'id':ident,'label':label,'public':{'F_nominal':F,'P':[list(v) for v in P],
              'start':[0,0],'base':[0,0],'E':100,'seed':20261022},
              'private':{'O_truth':[list(O)]},'initial':initial,
              'actions':actions if actions is not None else [move(*end)],'expect':expect or {},**extra}
        cases.append(case)
    add('T01','轴向首次带交点',(0,1),(4,1),P=[(1,1),(2,1),(3,1)],
        expect={'statuses':['detected'],'S':p('11/8',1),'H':[[1,1]],'known':[[2,1]],
                'E':e('789/8'),'M':e('11/8'),'h':p('11/8',0),'detected_t':r('11/32')},contract_probe=True)
    add('T02','斜向首次带交点',(0,2),(4,0),P=[(2,1)],
        expect={'statuses':['detected'],'S':p('11/8','21/16'),'H':[],
                'E':e(100,{5:'-11/16'}),'M':e(0,{5:'11/16'}),'h':p('11/8','-11/16'),'detected_t':r('11/32')})
    add('T03','闭带格角仅相切也检测',(1,'5/4'),(2,'9/4'),
        expect={'statuses':['detected'],'S':p('11/8','13/8'),'H':[],'detected_t':r('3/8')})
    add('T04','安全但起点已在带内立即停止',('7/5',1),(1,1),P=[(1,1),(2,1)],
        expect={'statuses':['detected'],'S':p('7/5',1),'H':[],'E':e(100),'M':e(),'h':p(1,0),'detected_t':r(0)})
    add('T05','带外不公开远处障碍',(0,0),(1,0),O=(3,2),P=[(1,0),(3,2)],
        expect={'statuses':['committed'],'S':p(1,0),'H':[[1,0]],'known':[],'E':e(99),'M':e(1)})
    add('T06','起点显式采集及前缀中心采集',(0,1),(4,1),P=[(0,1),(1,1),(2,1),(3,1)],
        actions=[{'kind':'collect_here'},move(4,1)],
        expect={'statuses':['committed','detected'],'H':[[0,1],[1,1]],'S':p('11/8',1),'known':[[2,1]]})
    add('T07','预测信用与中断实际隔离',(0,2),(4,0),P=[(0,2),(2,1),(4,0)],
        actions=[{'kind':'collect_here'},{'kind':'plan_wait','route':[p(0,2),p(4,0)],
                  'predicted_H':[[0,2],[2,1],[4,0]]},move(4,0)],
        expect={'statuses':['committed','plan_wait','detected'],'H':[[0,2]],'S':p('11/8','21/16'),
                'E':e(100,{5:'-11/16'}),'M':e(0,{5:'11/16'})})
    add('T08','恰好资源及下一段不足原子拒绝',(0,0),(1,0),O=(4,2),P=[(1,0),(2,0)],
        actions=[move(1,0),move(2,0)],expect={'statuses':['committed','resource_refused'],'S':p(1,0),
                'H':[[1,0]],'E':e(),'M':e(4),'h':p(1,0)})
    cases[-1]['initial']['E']=e(1)
    cases[-1]['initial']['M']=e(3)
    add('T09','已知障碍带内经过不重复发布',(1,'8/5'),(3,'8/5'),known=[(2,1)],P=[(2,1)],
        expect={'statuses':['committed'],'S':p(3,'8/5'),'H':[],'known':[[2,1]],'E':e(98),'M':e(2),'event_count':1})
    add('T10','无探测斜段完整提交',(0,0),(1,1),O=(4,2),P=[(1,1)],
        expect={'statuses':['committed'],'S':p(1,1),'H':[[1,1]],'known':[],
                'E':e(100,{2:-1}),'M':e(0,{2:1}),'h':p(1,1)})
    add('T11','空任务也实际返航',(2,0),(0,0),O=(4,2),P=[],h=(0,1),
        expect={'statuses':['committed'],'S':p(0,0),'H':[],'E':e(98),'M':e(2),'completed':True})
    add('T12','同刻安全优先于中心采集',(2,1),(2,1),P=[(2,1)],
        actions=[{'kind':'collect_here'}],expect={'statuses':['unsafe'],'S':p(2,1),'H':[],
                'E':e(100),'M':e(),'known':[]},
        note='负夹具：起点已在禁飞闭格中心，unsafe先于同刻采集；安全格心不可能恰在1/8带边界，不伪造该几何平局')
    return cases
