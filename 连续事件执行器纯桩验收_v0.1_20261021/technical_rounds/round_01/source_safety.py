"""Test-only import barrier. No algorithm module is loaded by this package."""
import sys,importlib.abc
DENY={'runtime','candidate','portable_frozen','model','baseline_suite','ppcpp_independent','p2_search_audit','unified_geometry','planners','networkx'}
class NoRealAlgorithms(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in DENY:raise ImportError('REAL_ALGORITHM_IMPORT_FORBIDDEN:'+fullname)
def install():
    assert not DENY.intersection(sys.modules),'real module already loaded';finder=NoRealAlgorithms();sys.meta_path.insert(0,finder);return finder
def clear():assert not DENY.intersection(sys.modules)
