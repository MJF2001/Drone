"""Explicit cold loading; no planner entry runs on import of this module."""
from pathlib import Path
import sys, importlib.util, time
from common import HERE, ROOT, sha

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def modules():
    begin = time.perf_counter()
    import_calls = []
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code.co_name in ('solve', 'run_payload', 'process', 'core_route', 'pipeline'):
            path = Path(frame.f_code.co_filename).resolve()
            if path.is_relative_to(ROOT):
                import_calls.append({'file': str(path), 'name': frame.f_code.co_name})
    sys.setprofile(profile)
    try:
        sys.path.insert(0, str(ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'))
        import runtime, p2_adapter
        sys.path.insert(0, str(HERE/'derived'))
        sys.path.insert(0, str(HERE))
        import runtime_h1
        post_geometry = load('_stop_post_geometry', HERE/'postsrc/geometry.py')
        old = sys.modules.get('geometry')
        sys.modules['geometry'] = post_geometry
        try:
            engine = load('_stop_frozen_shortcut', HERE/'postsrc/engine.py')
        finally:
            if old is None:
                sys.modules.pop('geometry', None)
            else:
                sys.modules['geometry'] = old
    finally:
        sys.setprofile(None)
    assert not import_calls, ('import_task_side_effect', import_calls)
    assert sha(runtime_h1.native.__file__) == sha(HERE/'source_snapshot/h1_ppcpp.py')
    return runtime_h1, p2_adapter, engine, {'cold_import_seconds': time.perf_counter()-begin,
             'import_task_calls': import_calls, 'actual_h1_native_source': runtime_h1.native.__file__,
             'source_alias_byte_verified': True}

def loaded_hashes():
    files = {}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            p = Path(name).resolve()
            if p.is_file() and p.is_relative_to(ROOT):
                files[str(p)] = sha(p)
    return files
