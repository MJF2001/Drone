from common import *
eq=load('last_newdev_equivalence',R/'PPCPP结束位置跨几何验证_v0.1_20261020/equivalence.py')
def normalized(c):
 def point(p):return [int(x) if float(x).is_integer() else x for x in p] if p is not None else None
 data={k:sorted(point(q) for q in c[k]) for k in ('free','targets','covered','published_targets','deferred_targets','initial_targets')}
 for k in ('current','base','previous','predator'):data[k]=point(c[k])
 data['old_route']=[point(p) for p in c['old_route']];data['distance_budget']=c['distance_budget'];return data
def signs(c):
 c=normalized(c)
 return dict(raw=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest(),translation=eq.signature(c,'state',False),state=eq.signature(c,'state',True),shape=eq.signature(c,'shape',True))
def compute():
 catalog=read(H/'old_input_catalog.json');old=[];cache={}
 for item in catalog['records']:
  assert sha(item['path'])==item['sha256']
  if item['sha256'] not in cache:cache[item['sha256']]=signs(read(item['path']))
  old.append(dict(**item,signatures=cache[item['sha256']]))
 new=[]
 for s in read(H/'protocol.json')['slots']:
  path=H/'inputs'/f"{s['id']}.json"
  if not path.exists():continue
  ss=signs(read(path));matches={k:[f"{o['collection']}:{o['batch']}:{o['name']}" for o in old if ss[k]==o['signatures'][k]] for k in ss}
  new.append(dict(id=s['id'],signatures=ss,old_matches=matches,old_copy=bool(matches['raw'] or matches['translation'] or matches['state']),old_shape_copy=bool(matches['shape'])))
 groups=sorted({c['signatures']['shape'] for c in new});state_groups=sorted({c['signatures']['state'] for c in new})
 for c in new:c.update(shape_group=f"G{groups.index(c['signatures']['shape'])+1:02d}",state_group=f"S{state_groups.index(c['signatures']['state'])+1:02d}")
 return dict(old_records=len(old),old_unique_byte_inputs=len(cache),old_collections={name:sum(o['collection']==name for o in old) for name in sorted({o['collection'] for o in old})},old=old,new=new,shape_groups=len(groups),state_groups=len(state_groups))
def main():
 protect();x=compute();save(H/'novelty.json',x);print('novelty audit',x['old_records'],'old records;',len(x['new']),'new slots;',x['shape_groups'],'shape groups; full copies',sum(c['old_copy'] for c in x['new']),flush=True)
if __name__=='__main__':main()
