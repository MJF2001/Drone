"""Privileged data extractor; estimator is a separate process with read guard."""
from common import *
from policy import clip
def main():
 start=time.perf_counter();guard();manifest=read(H/'manifest.json');ixs={x['key']:x for x in read(STRUCT/'pair_index.json')};registries={k:{r['id']:r for r in read(p/'state_registry.json')} for k,p in [('base',BASE),('variants',VAR)]};receipts=[]
 for slot in manifest['slots']:
  t=time.perf_counter();ix=ixs[slot['key']];record=read(STRUCT/ix['file']);src=Path(record['source'][slot['arm']]);o=read(src);c=o['input'];tr=o['diagnostic']['trigger'];row=registries[ix['dataset']][ix['id']];raw=o['native']['raw']['route'];k=tr['route_index'];q=tr['chosen_goal'];choice_pending=ps(c['targets'])-ps(c['covered'])-ps(raw[:k+1]);assert choice_pending==ps(tr['pending'])
  limited=clip(raw,k,q,choice_pending,ps(c['free']),tr['previous']);finite=limited.pop('path')
  packet=dict(schema='shadow_crop_v1',id=slot['id'],key=slot['key'],arm=slot['arm'],event=c,seed=20261020,old_order=row['old_order'],common_prefix=raw[:k+1],choice_state=dict(current=tr['current'],previous=tr['previous'],pending=tr['pending'],source_index=k),selected_q=q,finite_prefix=finite,stop_state=limited)
  assert set(packet)==set(manifest['input_whitelist']);dump(H/slot['crop'],packet)
  receipt=dict(id=slot['id'],source=str(src),source_sha256=sha(src),registry=str((BASE if ix['dataset']=='base' else VAR)/'state_registry.json'),crop_sha256=sha(H/slot['crop']),common_edges=k,finite_edges=limited['edges'],reason=limited['reason'],source_route_vertices_read=len(raw),seconds=time.perf_counter()-t,scope='privileged extraction reads source; no complete suffix or outcomes in crop')
  receipts.append(receipt)
 dump(H/'extraction_receipt.json',dict(passed=True,arms=len(receipts),wall_seconds=time.perf_counter()-start,receipts=receipts,new_core=0,new_post=0))
 print(dict(extracted=len(receipts),reasons={r:sum(x['reason']==r for x in receipts) for r in sorted({x['reason'] for x in receipts})},seconds=time.perf_counter()-start))
if __name__=='__main__':main()
