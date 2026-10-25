"""One-time preregistration. Does not run a planner."""
import json,hashlib,shutil,difflib,datetime,platform,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
S=R/'PPCPP_LAST新开发地图验证_v0.1_20261020'
O=R/'PPCPP保留末采集格候选_v0.1_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def rel(p):return str(p.relative_to(R))
def main():
 assert not (H/'protocol.json').exists()
 for root in (S,O):
  for name,hash_ in read(root/'manifest.json').items():assert sha(root/name)==hash_,str(root/name)
 for name in ('runtime.py','common.py','audit.py','audit_adapter.py'):
  shutil.copyfile(S/name,H/name)
 shutil.copyfile(S/'candidate.py',H/'candidate_v1.py')
 a=(S/'candidate.py').read_bytes();b=a.replace(b"VERSION='PPCPP_LAST_RESERVE_v0.1'",b"VERSION='PPCPP_LAST_RESERVE_v0.2'").replace(b'full.distance(q,s.base)',b'full.distance(s.base,q)')
 assert a!=b and b.replace(b"VERSION='PPCPP_LAST_RESERVE_v0.2'",b"VERSION='PPCPP_LAST_RESERVE_v0.1'").replace(b'full.distance(s.base,q)',b'full.distance(q,s.base)')==a
 (H/'candidate_v2.py').write_bytes(b)
 (H/'minimal_candidate.diff').write_text(''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='candidate_v1.py',tofile='candidate_v2.py')),encoding='utf-8')
 files={};inputs=[];slots=read(S/'protocol.json')['slots']
 # Protect all inherited protocol dependencies and original artifacts used here.
 for root in (S,O):
  files.update(read(root/'protocol.json')['files'])
  for name in ('protocol.json','source_seal.json','manifest.json','candidate.py','runtime.py','worker.py','audit.py','common.py','audit_adapter.py'):
   if (root/name).exists():files[rel(root/name)]=sha(root/name)
 def add(ident,source,batch,golden,golden_p0,meta):
  target=H/'inputs'/batch/(ident+'.json');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  assert sha(source)==sha(target)
  for p in (source,golden,golden_p0):files[rel(p)]=sha(p)
  inputs.append(dict(id=ident,batch=batch,input=str(target.relative_to(H)),source=rel(source),sha256=sha(target),golden=rel(golden),golden_p0=rel(golden_p0),metadata=meta))
 for s in slots:add(s['id'],S/'inputs'/(s['id']+'.json'),'primary54',S/'execution'/(s['id']+'__r0__LAST.json'),S/'execution'/(s['id']+'__r0__PPCPP.json'),s)
 for c in read(O/'protocol.json')['cases']:
  add(c['id'],R/c['input'],'historic60',O/'execution'/(c['id']+'__r0__LAST.json'),O/'execution'/(c['id']+'__r0__PPCPP.json'),dict(batch=c['batch'],name=c['name']))
 assert len(inputs)==114
 fixtures=[]
 for item in read(O/'gate_index.json')['index']:
  if item['kind']=='fixture' and item['method']=='LAST':
   src=O/item['path'];c=read(src)['input'];p=H/'fixtures'/(c['name']+'.json');save(p,c);files[rel(src)]=sha(src)
   fixtures.append(dict(id=c['name'],input=str(p.relative_to(H)),golden=rel(src),sha256=sha(p)))
 assert len(fixtures)==9
 # A predetermined connector counterexample: raw directional A* differs at equal length.
 f={(x,y) for x in range(4) for y in range(4)}-{(1,1)};t={(1,3),(0,3)};covered={(0,3)}
 c=dict(name='equal_length_direction_sensitive',free=sorted(f),targets=sorted(t),covered=sorted(covered),published_targets=sorted(t),deferred_targets=[],current=(3,3),base=(1,0),previous=None,predator=(-1,0),initial_targets=sorted(t),old_route=[(3,3)],distance_budget=1000000)
 p=H/'fixtures'/(c['name']+'.json');save(p,c);fixtures.append(dict(id=c['name'],input=str(p.relative_to(H)),golden=None,sha256=sha(p)))
 order=[];methods=['PPCPP','LAST_V1','LAST_V2']
 for rep in range(5):
  for i,s in enumerate(slots):
   k=(i+rep)%3
   for method in methods[k:]+methods[:k]:order.append(dict(sequence=len(order)+1,case_id=s['id'],method=method,repetition=rep,seed=20261020+rep))
 save(H/'formal_order.json',order)
 whitelist=['raw.version','raw.branches.P0.seconds','raw.branches.P0.accepted_seconds','raw.branches.P0.budget (remaining wall time)','raw.branches.P0.overrun_gt_10ms (time flag)','raw.branches.P1.accepted_seconds','entry_seconds','phase_seconds','injection_events','job/runtime_reads/imported_modules/production_sources (external provenance, checked separately)']
 protocol=dict(version='LAST distance equivalence v0.2',created=datetime.datetime.now().astimezone().isoformat(),inputs=inputs,fixtures=fixtures,slots=slots,files=files,budget=20,watchdog=90,repetitions=list(range(5)),max_formal_calls=810,methods=methods,ordering='for rep, slot index i: rotate [PPCPP,LAST_V1,LAST_V2] left by (i+rep)%3',semantic_whitelist=whitelist,deadline_stages=['p0_done','candidate_distance','phase1','release','return','final_audit_before','final_audit_after','encode_before','encode_after'],bfs_internal_injection='Construct real UnifiedGeometry first; replace only model.time reference with a private clock proxy returning 0,0,2 on successive check_time calls, set deadline=1, query a fresh nonzero distance. The first check is distance entry; next two occur inside BFS. Require DeadlineExceeded, 3 calls, no stored row. Restore in finally. No production mutation persists.',cache_spy='two runs, one per version, fixed incidental_collection fixture; 3 distinct caches and distance_rows, P0/full same F, work=F-e. Fixed geometric orientation fixture separately checks first_direction differs but full path identical.',gates=dict(regression_calls=228,fixture_calls=20,cache_spy_calls=2,deadline_calls=9,total_planner_calls=259,geometry_only_primary=54,exact_calls=0),comparison='All raw fields except enumerated time/version paths, every trace option/goal/phase retained; metrics computed independently twice. Pair only both eligible. Deadline differences retained separately; non-time semantic differences stop immediately.',timing='Identical unchanged run_payload; imports/selection/hash/disk before entry, decode through full raw JSON encode included. Private per-call caches; no timing spy/hooks. Serial fresh processes, environment threads1; all elapsed values kept.',environment=dict(python=sys.version,platform=platform.platform(),executable=sys.executable),stop_rule='No new maps/repeats/optimization. Stop immediately on non-deadline semantic discrepancy; stop after 810 calls. Await review.')
 save(H/'protocol.json',protocol)
 save(H/'input_seal.json',{i['input']:i['sha256'] for i in inputs+fixtures})
 (H/'预登记.md').write_text('''# LAST距离查询等价提速预登记

本文件与protocol.json、formal_order.json在任何新规划器调用前生成。114已见输入：主54、历史60；不生成新地图，不用留出或精确覆盖搜索。门槛259次：228回归、20边界（含新增连接方向敏感夹具）、2缓存Spy、9共同截止。几何查询与采集助手检查另账，不是规划器调用。

唯一生产机制变动是full.distance(q,s.base)→full.distance(s.base,q)，另改版本。runtime/common/audit/audit_adapter按字节复制；candidate_v1按字节复制，candidate_v2仅两行diff。统一隔离封装在计时开始前按绝对路径选择candidate，生产run_payload及正式raw结构不变。封装元数据仅在计时外附加，三方法一致。原版PPCPP绑定V1 candidate，mode=PPCPP；两LAST仍mode=LAST。

F无向四邻接单位边，精确距离对称，坐标tie和set遍历不改。BFSMetricGeometry.first_direction确会随距离查询方向变化，但实际UnifiedGeometry.path跳过该状态，始终用sorted端点调用Geometry.path。P0/F/F-e几何对象继续各自私有。只在无截止截断且双方完成条件下要求完整语义等价；墙钟成功率允许不同，20秒契约必须一致。

完整比较raw全部字段，仅排除protocol.semantic_whitelist列举的版本与时间字段。P0.budget是入口剩余墙钟，不能相等；20秒外层budget不排除。trace局部options、恢复goal、阶段切换、诊断路线、失败原因、所有非时间分支字段均保留。所有非时间指标独立双算；末采集位置另外重建。外层来源元数据单独验，不混语义。

新增15格F夹具：4×4去(1,1)，base=(1,0)，q=(1,3)，current=(3,3)，H={(0,3)}。raw Geometry正反A*同为5步但坐标序不同；先两方向查距离后UnifiedGeometry连接必须逐坐标相等，完整LAST路线/trace/采集也必须相等。夹具在正式前固定，不由正式收益筛选。

9截止位置及单源BFS内部固定钟注入详见protocol，必须P0已完整仍整体拒收。BFS内注入仅替换测试进程model.time私有代理，不改共享文件，distance入口第一次0、BFS内第二次0、第三次2>deadline1，要求抛截止且无部分行被缓存。

原封装一致性：新V1/runtime字节核对；114新回归均逐字段比旧封存同种子r0 LAST与其P0/PPCPP，9旧夹具比旧LAST。V2同样比V1与旧封存。正式再核540个LAST P0与同输入同重复PPCPP。不增加原封装新求解以超出固定门槛。

全部门槛完成后封通过源码，再串行54×3×5=810独立进程。顺序表固定轮换；种子20261020+rep；线程1；20秒暖入口含完整编码；启动/导入/磁盘/外审在外，90秒只作看门狗。出现非时间语义差异立即停止并存反例，计时/失败全部保留。不挑最好重复，不拼旧时长，不追加第二处优化。
''',encoding='utf-8')
 print('PREREGISTERED',len(inputs),'inputs',len(fixtures),'fixtures',len(order),'formal jobs; zero planner calls')
if __name__=='__main__':main()
