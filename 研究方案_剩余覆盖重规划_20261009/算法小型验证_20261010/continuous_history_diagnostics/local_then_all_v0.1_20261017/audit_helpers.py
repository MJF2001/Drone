"""Independent sequence/ledger checks, without optimizer or shortest-path calls."""
def route_errors(c,route):
    r=list(map(tuple,route));free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']));errors=[]
    if not r:return ['no_route']
    if r[0]!=tuple(c['current']):errors.append('wrong_start')
    if r[-1]!=tuple(c['base']):errors.append('missing_return')
    if not set(r)<=free:errors.append('collision')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(r,r[1:])):errors.append('illegal_step')
    if targets-covered-set(r):errors.append('omitted_target')
    if len(r)-1>c['distance_budget']:errors.append('resource')
    return errors

def compatibility(c,route,cfg):
    r=list(map(tuple,route));old=list(map(tuple,c['old_route']));l=cfg['left'];right=cfg['right'];suffix_steps=len(old)-1-right
    errors=route_errors(c,r);prefix=old[:l+1];suffix=old[right:]
    if r[:len(prefix)]!=prefix:errors.append('changed_fixed_prefix')
    if r[-len(suffix):]!=suffix:errors.append('changed_fixed_suffix')
    stop=len(r)-suffix_steps;patch=r[l:stop]
    if not patch or patch[0]!=old[l] or patch[-1]!=old[right]:errors.append('core_ports')
    if not set(map(tuple,cfg['required']))<=set(patch):errors.append('core_responsibility_omission')
    return dict(valid=not errors,errors=errors,patch=patch,patch_steps=len(patch)-1)

def check_unique(rows):
    assert len(rows)==len({r['run_id'] for r in rows}),'duplicate run_id'

def check_acceptances(events,budget):
    for e in events:
        if e.get('accepted'):
            assert e['valid'] and e['accepted_public_elapsed']<=budget,'late or invalid acceptance'

def check_selected(raw,events):
    selected=raw.get('selected_candidate_id')
    if selected is not None:
        e=next(e for e in events if e['candidate_id']==selected)
        assert e['accepted'] and raw['source']==e['source'] and raw['route']==e['route'],'wrong selected source or route'
