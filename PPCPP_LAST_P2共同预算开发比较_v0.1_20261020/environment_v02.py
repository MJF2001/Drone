"""Complete audit/input/config scope before any gate; discovery v01 retained."""
import environment,common
from support import *
original=environment.worker.imported
extras=[common.pa.__file__,common.metric.__code__.co_filename,common.cross.__code__.co_filename]
extras += [str(p.resolve()) for p in H.glob('*.json')]
extras += [str(p.resolve()) for p in (H/'inputs').glob('*.json')]
extras += [str((H/'预登记.md').resolve())]
environment.worker.imported=lambda:sorted(set(original())|{str(Path(p).resolve()) for p in extras})
if __name__=='__main__':environment.main()
