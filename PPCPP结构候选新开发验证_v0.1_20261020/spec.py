SIZES={'small':(18,3),'medium':(42,5),'large':(84,9)}
LAYOUTS=('A','B')
EVENTS=('straight','corner','obstacle')
PROGRESS=(25,60)
SEEDS=(20261021,20261022,20261023,20261024,20261025)
METHODS=('PPCPP','FIRST','STRUCT')
def plans():
    for size,(length,width) in SIZES.items():
        for layout in LAYOUTS:yield dict(plan_id=size+'_'+layout,size=size,length=length,width=width,layout=layout)
def cases():
    for p in plans():
        for event in EVENTS:
            for progress in PROGRESS:yield dict(**p,case_id=f"{p['plan_id']}_{event}_p{progress}",batch='newdev36',event=event,progress=progress)
