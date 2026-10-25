"""Finalize only after all offline artifacts exist. Refuses overwrite."""
from bridge_analysis import H,read,save,sha
if __name__=='__main__':
    assert (H/'example_shortest_path_ledger.json').is_file()
    assert len(list((H/'outputs').glob('*.json')))==432
    files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','verify.log')}
    save(H/'manifest.json',files)
    print('FINAL MANIFEST',len(files),'files; verify.log deliberately excluded.')
