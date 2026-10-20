"""Replay public acceptance decisions independently of scheduler state."""
def check(raw,budget):
 events=raw['candidate_events'];best=None
 for e in events:
  limit=budget/2 if e['stage']=='local' else budget
  eligible=e['valid'] and e['decision_public_elapsed']<=limit
  should=eligible and (best is None or e['steps']<events[best]['steps'])
  assert e['accepted']==should,'acceptance chronology/tie error'
  if should:best=e['candidate_id']
 assert best==raw['selected_candidate_id']
 for st in raw['stages']:
  limit=budget/2 if st['stage']=='local' else budget
  es=[e for e in events if e['stage']==st['stage']];eligible=[e for e in es if e['valid'] and e['decision_public_elapsed']<=limit]
  k=min(eligible,key=lambda e:e['steps'])['candidate_id'] if eligible else None;assert k==st['best_candidate_id']
  if st['raw']:
   inner=st['raw']['detail']['candidate_events'];assert len(inner)==len(es)
   for e,v in zip(es,inner):
    for key in ('route','patch','cfg','valid','route_sha256','validation_complete_public_elapsed'):assert e[key]==v[key]
