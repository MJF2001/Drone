from tail_analysis import H,sha,save
if __name__=='__main__':
    files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','verify.log','call_ledger.json')}
    save(H/'manifest.json',files);print('SEALED',len(files),'files; actual verify.log/call_ledger.json excluded from self-reference.')
