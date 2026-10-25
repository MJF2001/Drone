from support import *
if __name__=='__main__':
 assert read(H/'completion.json')['entries']==324 and not (H/'STOPPED.json').exists()
 save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts})
 print('Delivery sealed; only manifest/verify.log excluded')
