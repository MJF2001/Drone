"""Paper-model core plus explicit single-cell UAV adaptation."""
import sys
from pathlib import Path
_deps = Path(__file__).resolve().parent.parent/'.deps'
if str(_deps) not in sys.path:
    sys.path.insert(0, str(_deps))
