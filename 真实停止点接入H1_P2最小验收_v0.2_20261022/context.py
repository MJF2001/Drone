"""Same precore context for actual worker and dedicated import prechecks."""
from pathlib import Path
from v02_utils import HERE, read, sha
from audit_binding import bind, baseline_identity, helpers_identity

def prepare_context():
    from native_loader import modules, loaded_hashes
    h1, p2, engine, cold = modules()
    generic_before = baseline_identity()
    binding = bind()
    generic_after = baseline_identity()
    assert generic_before == generic_after
    from observe import Recorder
    loaded = loaded_hashes()
    guards = read(HERE/'external_source_guards.json')
    for name, digest in loaded.items():
        if not Path(name).is_relative_to(HERE):
            assert name in guards and guards[name] == digest, ('unbound_loaded_source',name)
    identity = {'auditor':binding.assert_stable(), 'baseline_audit':generic_after, 'helpers':helpers_identity()}
    return h1,p2,engine,binding,cold,loaded,identity

def stable_context(binding, before):
    after = {'auditor':binding.assert_stable(), 'baseline_audit':baseline_identity(), 'helpers':helpers_identity()}
    assert before == after, 'precore_postcore_module_identity_changed'
    return after
