"""Namespace-local audit binding; frozen native loader used only for the old core."""
from pathlib import Path
import importlib.util,sys,inspect
from .utils import HERE,ROOT,read,sha
from . import service,pipeline,executor,observe
from . import audit
from .audit import _post_saved,region,pure
from .post import engine

PKG=Path(__file__).resolve().parent
NAME=__package__

class Binding:
    def __init__(self):
        self.package=audit
        self.audit_one=audit.audit_one
        self.post_auditor=_post_saved
        self.initial=self.identity()
    def identity(self):
        expected=read(HERE/'namespace_expected.json')
        rows={}
        for key,digest in expected.items():
            assert sha(HERE/key)==digest,('namespace_source_changed',key)
        for name,m in tuple(sys.modules.items()):
            if name==NAME or name.startswith(NAME+'.'):
                path=Path(m.__file__).resolve()
                assert path.is_relative_to(PKG)
                assert Path(m.__spec__.origin).resolve()==path
                assert str(path.relative_to(HERE)) in expected
                rows[name]={'file':str(path),'sha256':sha(path),'object_id':id(m),'origin':m.__spec__.origin}
        assert audit._audit.Z is region and audit._audit.A is audit._geometry
        assert engine.C is service and engine.C.intersection is not region.intersection
        assert service.intersection.__module__==NAME+'.service'
        assert region.intersection.__module__==NAME+'.audit.region'
        return {'modules':rows,'primary_service_function':{'file':inspect.getsourcefile(service.intersection),'id':id(service.intersection)},
                'independent_service_function':{'file':inspect.getsourcefile(region.intersection),'id':id(region.intersection)}}
    def assert_stable(self):
        current=self.identity()
        # Additional orchestration modules are not an identity change of an existing helper.
        assert set(current['modules'])==set(self.initial['modules'])
        assert current==self.initial
        return current

def bind_saved():
    return Binding()

def baseline():
    m=sys.modules.get('audit')
    assert m is not None
    expected=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/audit.py'
    assert Path(m.__file__).resolve()==expected.resolve()
    return {'file':str(expected),'sha256':sha(expected),'id':id(m)}

def prepare_context():
    old=ROOT/'斜向执行障碍发现首次闭环_v0.1_20261022'
    sys.path.insert(0,str(old))
    key='_center_credit_readonly_legacy_native_loader'
    spec=importlib.util.spec_from_file_location(key,old/'native_loader.py')
    loader=importlib.util.module_from_spec(spec);sys.modules[key]=loader;spec.loader.exec_module(loader)
    h1,p2,unused_old_post,cold=loader.modules()
    before=baseline()
    binding=Binding()
    assert before==baseline()
    loaded=loader.loaded_hashes()
    guards=read(HERE/'external_source_guards.json')
    expected=read(HERE/'namespace_expected.json')
    for path,digest in loaded.items():
        source=Path(path)
        if source.is_relative_to(HERE):
            assert expected[str(source.relative_to(HERE))]==digest
        else:
            assert guards[path]==digest,('unbound_legacy_source',path)
    return h1,p2,engine,binding,cold,loaded,{'namespace':binding.initial,'baseline':before}

def stable_context(binding,before):
    result={'namespace':binding.assert_stable(),'baseline':baseline()}
    assert result==before
    return result
