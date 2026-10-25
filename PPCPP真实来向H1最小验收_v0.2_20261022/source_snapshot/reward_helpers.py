def reward_options(current,previous,pending,free,predator,weights):
    """Pure scoring helper; neighbors are actual uncovered cardinal cells."""
    options=sorted(q for q in adjacent(current) if q in pending and q in free)
    if not options:return []
    ds={q:math.hypot(q[0]-predator[0],q[1]-predator[1]) for q in options}
    lo=min(ds.values());hi=max(ds.values());out=[]
    for q in options:
        rd=(ds[q]-lo)/(hi-lo) if hi>lo else 0.0
        if previous is None:rs=0.0
        else:
            old=(current[0]-previous[0],current[1]-previous[1])
            new=(q[0]-current[0],q[1]-current[1])
            rs=(old[0]*new[0]+old[1]*new[1]+1)/2
        n=sum(z in pending and z in free for z in adjacent(q))
        rb=(4-n)/4
        out.append(dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,
                        score=rd+weights[0]*rs+weights[1]*rb))
    return out

def choose_neighbor(options):
    return min(options,key=lambda row:(-row['score'],row['cell']))['cell']
