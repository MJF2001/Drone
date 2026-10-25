"""Seal delivery once, after all analysis/report source and outputs exist."""
from common import *
def main():
 assert read(H/'completion.json')['calls']==810
 assert not (H/'STOPPED.json').exists()
 files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts}
 save(H/'manifest.json',files)
 print('DELIVERY MANIFEST',len(files),'files; only manifest itself and verify.log excluded')
if __name__=='__main__':main()
