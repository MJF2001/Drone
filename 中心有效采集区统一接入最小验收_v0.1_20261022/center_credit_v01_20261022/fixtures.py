"""35 fixed cases in the 16 requested classes. Expected credit sets are handwritten."""
from fractions import Fraction as Q
def rat(v):
    v=Q(v);return {'n':v.numerator,'d':v.denominator}
def pt(x,y):
    return [rat(x),rat(y)]
def expr(n=0):
    return {'terms':[] if not n else [{'r':1,'c':rat(n)}]}
def move(x,y,**kw):
    return {'kind':'move','to':pt(x,y),**kw}

def build():
    out=[]
    def add(group,label,start,actions,H,P=((1,1),),**extra):
        ident='C'+str(len(out)+1).zfill(2)
        out.append({'id':ident,'group':group,'label':label,
          'public':{'F_nominal':[[x,y] for x in range(5) for y in range(5)],'P':[list(v) for v in P],
                    'base':[0,0],'start':[0,0],'E':100,'seed':20261022},
          'private':{'O_truth':[[4,4]]},
          'initial':{'S':pt(*start),'h':pt(1,0),'H':[],'known':[],'E':expr(100),'M':expr()},
          'actions':actions,'expect':{'H':[list(p) for p in H]},**extra})
    for label,p,H in [('格心',(1,1),[(1,1)]),('严格内部',('11/10','9/10'),[(1,1)]),('严格外部',('121/100',1),[])]:
        add(1,label,p,[{'kind':'collect_here'}],H)
    for x,y in [('4/5',1),('6/5',1),(1,'4/5'),(1,'6/5'),('4/5','4/5'),('4/5','6/5'),('6/5','4/5'),('6/5','6/5')]:
        add(2,'开区边或角不采集',(x,y),[{'kind':'collect_here'}],[])
    add(3,'轴向不经格心穿越',(0,'11/10'),[move(2,'11/10')],[(1,1)],
        expect_interval={'lower':rat('2/5'),'upper':rat('3/5'),'lower_closed':False,'upper_closed':False},old_center_difference=True)
    add(4,'斜向不经格心正控制',(0,0),[move(2,'9/5')],[(1,1)],
        expect_interval={'lower':rat('4/9'),'upper':rat('3/5'),'lower_closed':False,'upper_closed':False},old_center_difference=True)
    add(5,'整段贴边不采集',(0,'6/5'),[move(2,'6/5')],[])
    add(6,'极短非空内部穿越',('799999/1000000',1),[move('800001/1000000',1)],[(1,1)],
        expect_interval={'lower':rat('1/2'),'upper':rat(1),'lower_closed':False,'upper_closed':True})
    add(6,'极短空交集',('799997/1000000',1),[move('799999/1000000',1)],[])
    add(7,'区内显式动作',('11/10','11/10'),[{'kind':'collect_here'}],[(1,1)])
    add(7,'区内零移动仍不自动采集',(1,1),[move(1,1)],[])
    add(8,'重复穿越不重复信用',(0,'11/10'),[move(2,'11/10'),move(0,'11/10')],[(1,1)],expected_credits=1)
    add(9,'非目标只通行',(0,'11/10'),[move(2,'11/10')],[],P=())
    add(10,'发布前经过不追溯；发布后显式采集',(0,0),[move(1,1),{'kind':'publish','P':[[1,1]],'blocked':[]},{'kind':'collect_here'}],[(1,1)],P=(),expected_history=[[],[],[[1,1]]])
    add(11,'未采先遮挡则暂缓',(1,1),[{'kind':'publish','P':[],'blocked':[[1,1]]},{'kind':'collect_here'}],[],expected_D=[[1,1]],expected_statuses=['published','unsafe'])
    add(11,'已采后遮挡不删除信用',(1,1),[{'kind':'collect_here'},{'kind':'publish','P':[],'blocked':[[1,1]]},{'kind':'collect_here'}],[(1,1)],expected_D=[],expected_statuses=['committed','published','unsafe'])
    add(12,'未执行计划只等待不产生实际信用',(0,'11/10'),[{'kind':'plan_wait','route':[pt(0,'11/10'),pt(2,'11/10')]}],[])
    for label,x,H in [('进入前边界停止','4/5',[]),('内部停止',1,[(1,1)]),('离开后停止','5/4',[(1,1)])]:
        add(13,label,(0,'11/10'),[move(x,'11/10',before_event=True)],H)
    add(14,'同刻先公开障碍再显式采集',(1,1),[{'kind':'publish','P':[],'blocked':[[1,1]]},{'kind':'collect_here'}],[],expected_D=[[1,1]],expected_statuses=['published','unsafe'])
    add(15,'完整直线不分段',(0,'11/10'),[move(2,'11/10')],[(1,1)],segmentation_pair='whole')
    add(15,'相同直线按边界与内部点分段',(0,'11/10'),[move('4/5','11/10'),move('9/10','11/10'),move(1,'11/10'),move('6/5','11/10'),move(2,'11/10')],[(1,1)],segmentation_pair='split')
    add(16,'合法计费首连接的预测与实际共同信用',('19/25','11/10'),[{'kind':'entry_prediction'},move(1,1)],[(1,1)],expected_q=[1,1],expected_M=expr('13/50'))
    add(16,'斜向返航顺带进入中心区',(2,'11/5'),[move(0,0)],[(1,1)],old_center_difference=True,expected_return=True)
    add(16,'不足资源整段原子拒绝',(0,0),[move(2,0)],[],expected_statuses=['resource_refused'],expected_M=expr())
    out[-1]['initial']['E']=expr(1)
    add(16,'零动作不覆盖最后非零来向',(0,0),[move(1,1),{'kind':'collect_here'},move(1,1)],[(1,1)],expected_h=pt(1,1))
    add(4,'见证及未执行信用篡改负控制',(0,'11/10'),[move(2,'11/10')],[(1,1)],P=((1,1),(3,1)),negative_controls=['witness_point','unexecuted_credit'])
    assert len(out)==35 and set(x['group'] for x in out)==set(range(1,17))
    return out
