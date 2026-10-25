"""Package-local path helper; no generic common module import."""
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
