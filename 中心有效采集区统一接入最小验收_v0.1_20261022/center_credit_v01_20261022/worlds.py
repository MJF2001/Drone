"""Fixed worlds, independent of planner results. No search or geometry calls."""
def build():
    line=[(x,y) for x in range(5) for y in range(2)]
    corner=sorted(set((x,y) for x in range(4) for y in range(2))|set((x,y) for x in (2,3) for y in (2,3)))
    side=[(x,y) for x in range(5) for y in range(3)]
    definitions=[('W1','双格宽直路',line,line,(2,0)),
                 ('W2','双格宽拐角',corner,[(0,0),(0,1),(3,1),(3,3),(2,3)],(2,2)),
                 ('W3','有侧向连接的矩形',side,[(0,0),(0,2),(4,0),(4,2),(2,1)],(2,1))]
    out=[]
    for ident,label,F,P,O in definitions:
        out.append({'id':ident,'label':label,
            'public':{'F_nominal':[list(p) for p in sorted(F)],'P':[list(p) for p in sorted(P)],
                      'base':[0,0],'start':[0,0],'E':100,'seed':20261022},
            'private':{'O_truth':[list(O)],'exists_since_initialization':True},
            'design':'手工固定微型几何，不随任一方法返回路线移动障碍；未保证每法必斜向触发'})
    return out
