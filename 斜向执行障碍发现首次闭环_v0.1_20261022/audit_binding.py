"""Absolute-path package binding. Never change sys.path or generic audit/helpers."""
from pathlib import Path
import importlib.util, sys, json, hashlib, inspect

HERE = Path(__file__).resolve().parent

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def module_identity(module):
    if module is None:
        return None
    source = Path(module.__file__).resolve()
    return {'name':module.__name__, 'file':str(source), 'origin':str(Path(module.__spec__.origin).resolve()),
            'loader':type(module.__spec__.loader).__name__, 'sha256':file_hash(source), 'object_id':id(module)}

def function_identity(function):
    assert callable(function) and inspect.isfunction(function)
    source = Path(function.__code__.co_filename).resolve()
    return {'module':function.__module__, 'qualname':function.__qualname__, 'file':str(source),
            'sha256':file_hash(source), 'first_line':function.__code__.co_firstlineno, 'object_id':id(function)}

class Binding:
    def __init__(self, package, expected):
        self.package, self.expected = package, expected
        self.audit_one = package.audit_one
        self.load_auditor = package.load_auditor
        self.post_auditor = self.load_auditor()
        self.initial_identity = self.identity()

    def identity(self):
        name = self.expected['package']
        modules = {suffix:sys.modules[name+suffix] for suffix in ('', '._audit', '._common', '._geometry', '._h1', '._post_saved', '._post_geometry', '._detect')}
        for relative, digest in self.expected['files'].items():
            assert file_hash(HERE/relative) == digest, ('audit_source_changed', relative)
        for suffix, module in modules.items():
            want = HERE/name/('__init__.py' if not suffix else suffix[2:]+'.py')
            # suffix strips the dot only: ._audit -> _audit.py.
            if suffix:
                want = HERE/name/(suffix[1:]+'.py')
            assert Path(module.__file__).resolve() == want.resolve()
            assert Path(module.__spec__.origin).resolve() == want.resolve()
        main = modules['._audit']
        assert main.A is modules['._geometry'] and main.h1_audit is modules['._h1']
        assert Path(main.HERE).resolve() == HERE
        assert modules['._post_saved'].A is modules['._post_geometry']
        assert self.post_auditor is modules['._post_saved']
        assert self.audit_one is main.audit_one and self.load_auditor is main.load_auditor
        for function,suffix in ((self.audit_one,'_audit.py'),(self.load_auditor,'_audit.py'),(self.post_auditor.audit_one,'_post_saved.py')):
            assert Path(function.__code__.co_filename).resolve()==(HERE/name/suffix).resolve()
            assert function.__module__==name+'.'+suffix[:-3]
        return {'modules':{k:module_identity(v) for k,v in modules.items()},
                'functions':{'audit_one':function_identity(self.audit_one),
                             'load_auditor':function_identity(self.load_auditor),
                             'post_audit_one':function_identity(self.post_auditor.audit_one)}}

    def assert_stable(self):
        current = self.identity()
        assert current == self.initial_identity, 'audit_identity_changed'
        return current

def bind():
    expected = json.loads((HERE/'audit_expected_identity.json').read_text(encoding='utf-8'))
    name = expected['package']
    original_audit = sys.modules.get('audit')
    original_path = list(sys.path)
    for relative, digest in expected['files'].items():
        assert file_hash(HERE/relative) == digest
    package = sys.modules.get(name)
    if package is None:
        directory = HERE/name
        spec = importlib.util.spec_from_file_location(name, directory/'__init__.py', submodule_search_locations=[str(directory)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    binding = Binding(package, expected)
    assert sys.modules.get('audit') is original_audit, 'generic_audit_was_modified'
    assert sys.path == original_path, 'auditor_binding_changed_sys_path'
    return binding

def baseline_identity(required=True):
    expected = json.loads((HERE/'audit_expected_identity.json').read_text(encoding='utf-8'))
    module = sys.modules.get('audit')
    if module is None:
        assert not required
        return None
    assert Path(module.__file__).resolve() == Path(expected['baseline_audit_path']).resolve(), 'generic_audit_wrong_source'
    assert hasattr(module,'audit') and not hasattr(module,'load_auditor')
    return module_identity(module)

def helpers_identity():
    result = {}
    for name in ('common','pipeline','exact','geometry','connector','h1_direction','h1_rewards','native_loader','public_contract','detector','executor'):
        module = sys.modules.get(name)
        if module is not None:
            actual = Path(module.__file__).resolve()
            assert actual == (HERE/(name+'.py')).resolve(), ('generic_helper_source_conflict',name,str(actual))
            result[name] = module_identity(module)
    return result
