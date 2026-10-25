"""Derived CORE4 rewards: old axial arithmetic; certified H1 first-heading scores."""
import math
from fractions import Fraction
from decimal import Decimal, localcontext

def adjacent(p):
    x, y = p
    return ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))

def reward_options(current, heading, pending, free, predator, weights):
    """Copied scoring structure; h replaces previous. No physical previous is made."""
    options=sorted(q for q in adjacent(current) if q in pending and q in free)
    if not options:return []
    ds={q:math.hypot(q[0]-predator[0],q[1]-predator[1]) for q in options}
    lo=min(ds.values());hi=max(ds.values());out=[]
    direction = heading['primitive']
    diagonal = direction is not None and direction[0] != 0 and direction[1] != 0
    assert tuple(weights) == (2., .5)
    for q in options:
        rd=(ds[q]-lo)/(hi-lo) if hi>lo else 0.0
        if direction is None:rs=0.0
        else:
            old=direction
            new=(q[0]-current[0],q[1]-current[1])
            if not diagonal:
                rs=(old[0]*new[0]+old[1]*new[1]+1)/2
            else:
                dot=old[0]*new[0]+old[1]*new[1]
                norm2=old[0]*old[0]+old[1]*old[1]
                with localcontext() as ctx:
                    ctx.prec=40  # display only; never used for choosing or equality
                    rs=float((Decimal(dot)/Decimal(norm2).sqrt()+1)/2)
        n=sum(z in pending and z in free for z in adjacent(q))
        rb=(4-n)/4
        row=dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,
                 score=rd+weights[0]*rs+weights[1]*rb)
        if diagonal:
            # Exact score relative to the original binary64 rd and unchanged rb.
            A=Fraction.from_float(rd)+1+Fraction.from_float(weights[1]*rb)
            row['h1_certificate']=dict(A=str(A), B=dot, N=norm2)
        out.append(row)
    return out

def compare_certificates(a, b):
    """sign((A1-A2)+(B1-B2)/sqrt(N)), exactly over rational inputs."""
    assert a['N'] == b['N'] and a['N'] > 0
    A=Fraction(a['A'])-Fraction(b['A']);B=Fraction(a['B'])-Fraction(b['B']);N=a['N']
    if not A:return (B>0)-(B<0)
    if not B:return (A>0)-(A<0)
    sa=(A>0)-(A<0);sb=(B>0)-(B<0)
    if sa==sb:return sa
    difference=A*A*N-B*B
    if not difference:return 0
    return sa if difference>0 else sb

def choose_neighbor(options):
    if 'h1_certificate' not in options[0]:
        # Exact original expression and Python tie behavior for axial/no-motion.
        return min(options,key=lambda row:(-row['score'],row['cell']))['cell']
    best=options[0]
    for row in options[1:]:
        sign=compare_certificates(row['h1_certificate'],best['h1_certificate'])
        if sign>0 or (sign==0 and row['cell']<best['cell']):best=row
    return best['cell']
