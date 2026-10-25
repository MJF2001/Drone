"""Domain-function and graph-search observation, identical for H1/P2."""
from collections import Counter
from pathlib import Path
import time, json
from .pipeline import PipelineStop
from . import pipeline

class Recorder:
    def __init__(self, h1, p2, engine, marker):
        import model, bfs_metric_geometry, unified_geometry
        self.begin = None
        self.marker = marker
        self.counts = Counter()
        self.rows = {}
        self.codes = {h1.native.solve.__code__: 'h1_core', p2.p2_solve.__code__: 'p2_core',
                      model.Geometry.__init__.__code__: 'context', model.Geometry.path.__code__: 'astar',
                      model.Geometry.precheck.__code__: 'precheck',
                      bfs_metric_geometry.BFSMetricGeometry.distance.__code__: 'distance',
                      unified_geometry.UnifiedGeometry.path.__code__: 'path',
                      unified_geometry.single_cell_audit.__code__: 'audit',
                      h1.native.reward_options.__code__: 'reward', h1.native.choose_neighbor.__code__: 'selection',
                      h1.native.parse_heading.__code__: 'heading_parse', h1.native.after_edge.__code__: 'heading_update',
                      engine.process.__code__: 'post_entry', engine.G.legal.__code__: 'post_geometry',
                      engine.C.intersection.__code__: 'post_hit', engine.G.interval.__code__: 'post_interval'}
        self.engine_credit_code=engine.credits.__code__
        self.pipeline_audit_code=pipeline.main_audit.__code__
        self.pipeline_run_code=pipeline.run.__code__
        self.lines = {}
        patterns = {'context': {'start': 'queue = deque([snapshot.current])', 'done': 'self.views = {}'},
                    'distance': {'start': 'ds={a:0};queue=deque([a])', 'done': 'self.bfs_rows_built+=1'},
                    'astar': {'start': 'self.searches += 1'}}
        for code, kind in self.codes.items():
            if kind in patterns:
                lines = Path(code.co_filename).read_text(encoding='utf-8-sig').splitlines()
                self.lines[code] = {tag: next(i for i, s in enumerate(lines, 1) if text in s)
                                    for tag, text in patterns[kind].items()}
        text = Path(engine.__file__).read_text(encoding='utf-8-sig').splitlines()
        self.post_lines = {next(i for i, s in enumerate(text, 1) if needle in s): kind for needle, kind in
              [("counts['candidate']+=1;ok=G.legal", 'candidate'),
               ("counts['source_validation']+=1", 'source'), ("counts['output_validation']+=1", 'output')]}
        self.limits = {'geometry_distance_calls': 1000000, 'geometry_path_calls': 10000, 'main_audit_calls': 64,
                       'context_BFS_started': 1, 'distance_row_BFS_started': 25, 'Astar_started': 625,
                       'post_candidate_geometry': 4096, 'post_source_geometry': 100, 'post_output_geometry': 100,
                       'post_service_intersections': 1200, 'post_service_queries_total_protected':1200}

    def add(self, key, value=1):
        self.counts[key] += value
        if key in self.limits and self.counts[key] > self.limits[key]:
            raise PipelineStop('observer_cap:'+key)

    def mark(self, tag, **values):
        with self.marker.open('a', encoding='utf-8') as file:
            file.write(json.dumps({'tag': tag, 'pipeline_seconds': time.perf_counter()-self.begin if self.begin else None,
                                   **values}, ensure_ascii=False)+'\n')

    def trace(self, frame, event, arg):
        code = frame.f_code
        if event == 'call':
            kind = self.codes.get(code)
            if kind is None:
                return None
            if kind=='post_hit':
                owner=frame.f_back
                scope=None
                while owner:
                    if owner.f_code is self.engine_credit_code:
                        scope='engine';break
                    if owner.f_code is self.pipeline_audit_code:
                        scope='wrapper_'+owner.f_locals['phase'];break
                    if owner.f_code is self.pipeline_run_code:
                        scope='wrapper_prediction';break
                    owner=owner.f_back
                if scope is None:
                    raise PipelineStop('unclassified_region_query_owner')
                self.add('shared_region_queries_total')
                self.add('scope_'+scope+'_region_queries')
                if scope=='engine' or scope=='wrapper_post':
                    self.add('post_service_queries_total_protected')
                if scope=='engine':
                    self.add('post_service_intersections')
                return None
            row = {'kind': kind, 'started': False, 'done': False}
            self.rows[id(frame)] = row
            if kind.endswith('_core'):
                self.add('core_started')
                self.mark('core_started', kind=kind, source=code.co_filename, budget=frame.f_locals.get('budget'))
            elif kind in ('distance', 'path', 'precheck'):
                self.add('geometry_'+kind+'_calls')
            elif kind == 'audit':
                self.add('main_audit_calls')
            elif kind == 'post_geometry':
                phase = self.post_lines.get(frame.f_back.f_lineno)
                if phase is None:
                    raise PipelineStop('unclassified_post_geometry')
                if phase == 'candidate' and time.perf_counter()-self.begin >= 28:
                    self.add('post_candidate_aborted_before_predicate')
                    raise PipelineStop('post_candidate_absolute_deadline')
                self.add('post_'+phase+'_geometry')
            elif kind == 'post_hit':
                self.add('post_service_intersections')
            elif kind == 'post_interval':
                self.add('post_interval_calls')
            else:
                self.add(kind+'_calls')
            if code not in self.lines:
                frame.f_trace_lines = False
            return self.trace
        row = self.rows.get(id(frame))
        if row is None:
            return None
        kind = row['kind']
        if event == 'line' and code in self.lines:
            spec = self.lines[code]
            label = {'context': 'context_BFS', 'distance': 'distance_row_BFS', 'astar': 'Astar'}[kind]
            if frame.f_lineno == spec['start'] and not row['started']:
                row['started'] = True
                self.add(label+'_started')
            if frame.f_lineno == spec.get('done') and not row['done']:
                row['done'] = True
                self.add(label+'_completed')
        elif event == 'return':
            if kind.endswith('_core'):
                normal = isinstance(arg, dict)
                self.add('core_returned', int(normal))
                complete = normal and arg.get('status') in ('core_complete', 'finished') and bool(arg.get('route'))
                self.add('core_complete', int(complete))
                self.mark('core_exited', kind=kind, normal=normal, status=arg.get('status') if normal else 'exception')
            if kind == 'astar' and row['started'] and isinstance(arg, tuple):
                self.add('Astar_completed')
            if kind == 'audit' and isinstance(arg, dict):
                self.add('main_audit_returns')
                self.add('main_audit_valid', int(arg.get('valid', False)))
            if kind == 'reward' and isinstance(arg, list):
                self.add('scored_neighbor_rows', len(arg))
            self.rows.pop(id(frame), None)
        return self.trace
