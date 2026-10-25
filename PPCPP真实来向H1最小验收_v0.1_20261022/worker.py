"""One budgeted real entry per process. Observability is identical for both."""
from pathlib import Path
import sys,time,json,hashlib,traceback

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

class Recorder:
    def __init__(self, original, newer, marker):
        import model,bfs_metric_geometry,unified_geometry
        self.codes={original.native.solve.__code__:'core',newer.native.solve.__code__:'core',
            model.Geometry.__init__.__code__:'context',model.Geometry.path.__code__:'astar',
            model.Geometry.precheck.__code__:'precheck',bfs_metric_geometry.BFSMetricGeometry.distance.__code__:'distance',
            unified_geometry.UnifiedGeometry.path.__code__:'path',unified_geometry.single_cell_audit.__code__:'audit',
            original.native.core.reward_options.__code__:'reward',newer.native.reward_options.__code__:'reward',
            newer.native.choose_neighbor.__code__:'selection',original.native.core.choose_neighbor.__code__:'selection',
            newer.native.parse_heading.__code__:'heading_parse',newer.native.after_edge.__code__:'heading_update'}
        self.counts={x:0 for x in ('core_started','core_returned','core_complete','context_BFS_started','context_BFS_completed',
          'distance_row_BFS_started','distance_row_BFS_completed','Astar_started','Astar_completed',
          'geometry_distance_calls','geometry_path_calls','geometry_precheck_calls','main_audit_calls','main_audit_returns','main_audit_valid',
          'reward_calls','scored_neighbor_rows','selection_calls','heading_parse_calls','heading_update_calls')}
        self.rows={};self.marker=marker
        self.lines={}
        patterns={'context':{'start':'queue = deque([snapshot.current])','done':'self.views = {}'},
                  'distance':{'start':'ds={a:0};queue=deque([a])','done':'self.bfs_rows_built+=1'},
                  'astar':{'start':'self.searches += 1'}}
        for code,kind in self.codes.items():
            if kind in patterns:
                text=Path(code.co_filename).read_text(encoding='utf-8-sig').splitlines()
                self.lines[code]={tag:next(i for i,t in enumerate(text,1) if s in t) for tag,s in patterns[kind].items()}
    def mark(self,tag,**data):
        with self.marker.open('a',encoding='utf8') as f:f.write(json.dumps(dict(tag=tag,**data),ensure_ascii=False)+'\n')
    def trace(self,frame,event,arg):
        code=frame.f_code
        if event=='call':
            kind=self.codes.get(code)
            if kind is None:return None
            self.rows[id(frame)]=dict(kind=kind,started=False,done=False)
            if kind=='core':self.counts['core_started']+=1;self.mark('core_started')
            if kind in ('distance','path','precheck'):self.counts['geometry_'+kind+'_calls']+=1
            if kind=='audit':self.counts['main_audit_calls']+=1
            if kind in ('reward','selection','heading_parse','heading_update'):self.counts[kind+'_calls']+=1
            if code not in self.lines:frame.f_trace_lines=False
            return self.trace
        record=self.rows.get(id(frame))
        if record is None:return None
        kind=record['kind']
        if event=='line' and code in self.lines:
            spec=self.lines[code]
            if frame.f_lineno==spec['start'] and not record['started']:
                record['started']=True
                key={'context':'context_BFS_started','distance':'distance_row_BFS_started','astar':'Astar_started'}[kind]
                self.counts[key]+=1
            if 'done' in spec and frame.f_lineno==spec['done'] and not record['done']:
                record['done']=True
                self.counts[{'context':'context_BFS_completed','distance':'distance_row_BFS_completed'}[kind]]+=1
        elif event=='return':
            if kind=='core':
                normal=isinstance(arg,dict);self.counts['core_returned']+=normal
                self.counts['core_complete']+=bool(normal and arg.get('status')=='core_complete')
                self.mark('core_exited',returned=normal,status=arg.get('status') if normal else 'exception')
            if kind=='astar' and record['started'] and isinstance(arg,tuple):self.counts['Astar_completed']+=1
            if kind=='audit' and isinstance(arg,dict):
                self.counts['main_audit_returns']+=1;self.counts['main_audit_valid']+=bool(arg.get('valid'))
            if kind=='reward' and isinstance(arg,list):self.counts['scored_neighbor_rows']+=len(arg)
            self.rows.pop(id(frame),None)
        return self.trace

def main(slot):
    job=read(HERE/'jobs'/f'{slot:03d}.json');out=HERE/'outputs'/(job['id']+'.json');marker=HERE/'logs'/(job['id']+'_markers.jsonl')
    assert not out.exists() and not marker.exists(),'slot already attempted'
    frozen=read(HERE/'freeze.json')
    for rel,digest in frozen['package_files'].items():assert sha(HERE/rel)==digest,('package conflict',rel)
    for path,digest in read(HERE/'原来源hash.json').items():assert sha(Path(path))==digest,('source conflict',path)
    cold=time.perf_counter()
    sys.path.insert(0,str(ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'))
    import runtime as original
    sys.path.insert(0,str(HERE/'derived'))
    import runtime_h1 as newer
    # The static import review was completed and frozen before this import.
    cold_seconds=time.perf_counter()-cold
    loaded={}
    for m in list(sys.modules.values()):
        p=getattr(m,'__file__',None)
        if p and Path(p).is_file() and Path(p).resolve().is_relative_to(ROOT):loaded[str(Path(p).resolve())]=sha(Path(p))
    c=read(HERE/job['input']);original_bytes=(HERE/job['input']).read_bytes()
    if job['method']=='H1':
        request={k:v for k,v in c.items() if k!='previous'};request['incoming_heading']=job['heading']
        payload=json.dumps(request,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
    else:request=c;payload=original_bytes
    recorder=Recorder(original,newer,marker);result=dict(job=job,input=c,source_input_sha256=sha(HERE/job['input']),
        request_utf8=payload.decode('utf8'),request_sha256=hashlib.sha256(payload).hexdigest(),cold_import_seconds=cold_seconds,
        loaded_source_hashes=loaded,entry=None,audit=None,failure=None)
    try:
        recorder.mark('warm_entry_started',method=job['method']);sys.settrace(recorder.trace)
        try:
            entry=(original if job['method']=='ORIGINAL' else newer).run_payload(payload,'PPCPP',20,job['seed'])
        finally:sys.settrace(None)
        recorder.mark('warm_entry_returned',eligible=entry['eligible']);result['entry']=entry
        result['accounts']=recorder.counts
        dump(out,result)  # Preserve returned output before any independent audit can fail.
        assert entry['eligible'] and entry['entry_seconds']<20, 'entry deadline/failure'
        raw=entry['raw']['branches']['P0'];assert raw['status']=='core_complete'
        from independent_audit import audit_output
        begin=time.perf_counter();audit=audit_output(c,job['heading'],raw,job['method']=='H1')
        if job['method']=='H1':
            route=raw['route'];last=raw['final_heading']
            if len(route)>1:assert last['primitive']==[route[-1][k]-route[-2][k] for k in (0,1)]
        result['audit']=audit;result['independent_audit_seconds']=time.perf_counter()-begin
        assert recorder.counts['core_started']==recorder.counts['core_returned']==recorder.counts['core_complete']==1
        assert recorder.counts['main_audit_calls']==recorder.counts['main_audit_valid']==2
        result['passed']=True
    except BaseException as ex:
        sys.settrace(None);result.update(failure=dict(reason=repr(ex),traceback=traceback.format_exc()),passed=False)
    for m in list(sys.modules.values()):
        p=getattr(m,'__file__',None)
        if p and Path(p).is_file() and Path(p).resolve().is_relative_to(ROOT):loaded[str(Path(p).resolve())]=sha(Path(p))
    for p in (original.native.__file__,original.native.core.__file__,newer.native.__file__,original.validate.__code__.co_filename):
        loaded[str(Path(p).resolve())]=sha(Path(p))
    result['accounts']=recorder.counts;result['loaded_source_hashes']=loaded;dump(out,result)
    print(json.dumps(dict(slot=slot,id=job['id'],passed=result['passed'],failure=result['failure']),ensure_ascii=False))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main(int(sys.argv[1]))
