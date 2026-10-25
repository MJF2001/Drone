"""Post-run supplementary import inventory, never described as pre-run seal."""
from common import *
def main():
 assert read(H/'completion.json')['calls']==810
 files={};missing=[];counts=set();protocol=read(H/'protocol.json');unsealed=set()
 for p in sorted((H/'execution').glob('*.json')):
  x=read(p);counts.add(len(x['imported_modules']))
  for name in x['imported_modules']:
   q=Path(name)
   if name not in files:
    if q.is_file():files[name]=sha(q)
    else:missing.append(name)
   if q.is_relative_to(R) and not q.is_relative_to(R/'运行环境') and name not in x['production_sources'] and str(q.relative_to(R)) not in protocol['files']:unsealed.add(name)
 assert not missing
 assert all('.deps' in Path(p).parts for p in unsealed)
 save(H/'imported_dependency_inventory.json',dict(phase='after all 810 formal calls; supplementary installed-file inventory, NOT a pre-run content seal or proof of unchanged loaded bytes',files=files,worker_module_counts=sorted(counts),optional_package_files_without_individual_preseal=sorted(unsealed),limitation='All executed project production sources/dependencies were presealed and critical sources hashed/logged per worker before entry. Eager optional .deps package imports from frozen baseline_suite are logged per worker; individual optional package source files were inventoried after timing. Their byte identity throughout timing is not established by this supplementary inventory. No second measurement batch or package change was made.'))
 print('post-run imported files',len(files),'optional package files without individual preseal',len(unsealed))
if __name__=='__main__':main()
