"""Copy latest research into existing repository, without modifying source deliveries."""
import hashlib,json,os,re,shutil
from pathlib import Path
WORK=Path(__file__).resolve().parent
REPO=WORK/'.remote_Drone'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    folders=[p for p in WORK.iterdir() if p.is_dir() and (p.name.startswith(('DeepSeek_','OARP')) or p.name in ('导师汇报_20261018','主会话验收_DeepSeek_20261018'))]
    folders.append(WORK/'outputs/算法详细结果_20261018')
    sources=[WORK/'底层算法研究决策_20261018.md',Path(__file__).resolve()]
    skipped=[]
    for folder in folders:
        for root,dirs,files in os.walk(folder,followlinks=False):
            kept=[]
            for name in dirs:
                path=Path(root)/name
                if name in ('.git','node_modules') or path.is_symlink() or path.is_junction():skipped.append(str(path.relative_to(WORK)))
                else:kept.append(name)
            dirs[:]=kept
            for name in files:
                path=Path(root)/name
                if path.is_symlink():skipped.append(str(path.relative_to(WORK)))
                else:sources.append(path)
    manifest={}
    secret=re.compile(rb'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-proj-[A-Za-z0-9_-]{40,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    for p in sorted(sources):
        relative=p.relative_to(WORK);target=REPO/relative
        data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if p.suffix.lower() in ('.json','.jsonl','.py','.md','.txt','.toml','.yaml','.yml','.ps1','.mjs') and secret.search(data):
            raise RuntimeError('Credential-pattern review required: '+str(relative))
        assert not target.exists(),'Destination already exists: '+str(relative)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        assert sha(target)==sha(p)==digest
        manifest[relative.as_posix()]={'bytes':len(data),'sha256':digest}
    report={'date':'2026-10-19','repository':'https://github.com/MJF2001/Drone.git','copied_files':manifest,
        'skipped_links_or_dependency_mounts':skipped,'policy':'Add latest research deliveries byte-for-byte; preserve historical evidence. Do not copy unrelated design materials or external node_modules mounts.',
        'portability':'Original manifests and absolute source paths are preserved; byte-identical upload does not certify a fresh machine can execute every historical command.'}
    (REPO/'GitHub更新文件清单_20261019.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'copied_files':len(manifest),'MB':sum(x['bytes'] for x in manifest.values())/1e6,'skipped':skipped},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
