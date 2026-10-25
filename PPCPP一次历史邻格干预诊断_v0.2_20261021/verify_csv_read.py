"""Read-only report-reader fix: size limit only; original presealed verifier unchanged."""
from pathlib import Path
import sys,csv,runpy
folder=Path(__file__).resolve().parent
bound=max(131072,max(p.stat().st_size for p in folder.glob('*.csv')))
csv.field_size_limit(bound)
print('CSV reader-only bound set to maximum saved CSV file size:',bound,'bytes; no result/source modification',flush=True)
sys.path.insert(0,str(folder));runpy.run_path(str(folder/'verify.py'),run_name='__main__')
