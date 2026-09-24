#!/usr/bin/env python3
"""Install a checked complete bundle with drift protection and recoverable rollback."""
import argparse,datetime,fcntl,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ALIASES={f'skills/{skill}/{name}':'../../prose/'+name for skill in ['islamic-note','faith-reason-note'] for name in ['translate.py','translate-style.md']}
REQUIRED=['skills/islamic-note/references/markdown.md','skills/faith-reason-note/references/website.md','skills/faith-reason-research/SKILL.md']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe_name(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe bundle path: '+name)
    return p

def inventory():
    files={}
    for name,expected in json.loads((ROOT/'runtime-manifest.json').read_text()).items():
        source=ROOT/'runtime'/safe_name(name)
        if digest(source)!=expected:raise ValueError('runtime hash mismatch: '+name)
        dest='skills/faith-reason-note/validate.py' if name=='validate_article.py' else 'prose/'+name
        files[dest]=source
    for name,expected in json.loads((ROOT/'authoring-manifest.json').read_text()).items():
        source=ROOT/'authoring'/safe_name(name)
        if digest(source)!=expected:raise ValueError('authoring hash mismatch: '+name)
        if name in files or name in ALIASES:raise ValueError('duplicate installation path: '+name)
        files[name]=source
    if any(name not in files for name in REQUIRED):raise ValueError('bundle missing mandatory workflow references')
    return files

def ensure_path(root,name,alias=False):
    dest=root/safe_name(name)
    for parent in dest.parents:
        if parent==root:break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):raise ValueError('unsafe installation parent: '+str(parent))
    if dest.is_symlink() and not alias:raise ValueError('refusing to replace symlink: '+str(dest))
    if dest.exists() and not dest.is_file() and not (alias and dest.is_symlink()):raise ValueError('installation destination is not a file: '+str(dest))
    return dest

def state(dest):
    if dest.is_symlink():return 'link:'+os.readlink(dest)
    return digest(dest) if dest.is_file() else None

def write_json(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def rollback(root,journal):
    conflicts=[]
    for name,row in reversed(list(journal['entries'].items())):
        dest=ensure_path(root,name,alias=row['kind']=='alias');actual=state(dest)
        if actual==row['before']:continue
        if actual!=row['after']:conflicts.append(name);continue
        if row['before'] is None:dest.unlink()
        else:
            backup=Path(row['backup'])
            if digest(backup)!=row['before']:raise ValueError('rollback backup changed: '+name)
            tmp=dest.with_name(dest.name+'.rollback-'+str(os.getpid()));tmp.write_bytes(backup.read_bytes());tmp.replace(dest)
    return conflicts

def install(a):
    root=a.target.absolute()
    if root.is_symlink():raise ValueError('installation root cannot be a symlink')
    root.mkdir(parents=True,exist_ok=True)
    with (root/'.toolchain-install.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        active=root/'.toolchain-install-active.json'
        if active.exists():
            if a.check:raise ValueError('interrupted installation requires recovery before use')
            old=json.loads(active.read_text());conflicts=rollback(root,old)
            history=Path(old['directory'])/'recovery.json';write_json(history,{'status':'rolled-back','concurrent_files_preserved':conflicts});active.unlink()
            if conflicts:raise ValueError('interrupted install recovered; inspect concurrent files: '+', '.join(conflicts))
        files=inventory();changed={}
        for name,source in files.items():
            dest=ensure_path(root,name)
            if state(dest)!=digest(source):changed[name]=source
        missing=[]
        for name,target in ALIASES.items():
            dest=ensure_path(root,name,alias=True)
            if dest.is_symlink() or dest.exists():
                if not dest.is_symlink() or os.readlink(dest)!=target:raise ValueError('translation alias differs: '+str(dest))
            else:missing.append(name)
        if a.check:
            print('Toolchain identical' if not changed and not missing else 'Toolchain differs: '+', '.join(list(changed)+missing));return int(bool(changed or missing))
        expected=json.loads(a.expected.read_text()) if a.expected else None
        before={name:state(root/name) for name in changed}
        if expected is not None:
            for name,value in before.items():
                if name not in expected or expected[name]!=value:raise ValueError('installed file changed since snapshot: '+name)
        if not changed and not missing:print('Toolchain identical');return 0
        directory=root/'.toolchain-backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');directory.mkdir(parents=True)
        journal={'schema':1,'directory':str(directory),'entries':{}}
        for name,source in changed.items():
            dest=root/name;backup=directory/name
            if before[name] is not None:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(dest.read_bytes())
            journal['entries'][name]={'kind':'file','before':before[name],'after':digest(source),'backup':str(backup)}
        for name in missing:journal['entries'][name]={'kind':'alias','before':None,'after':'link:'+ALIASES[name]}
        write_json(active,journal)
        try:
            for name,row in journal['entries'].items():
                dest=ensure_path(root,name,alias=row['kind']=='alias')
                if state(dest)!=row['before']:raise ValueError('concurrent installed file change: '+name)
                dest.parent.mkdir(parents=True,exist_ok=True)
                if row['kind']=='alias':dest.symlink_to(ALIASES[name])
                else:
                    tmp=dest.with_name(dest.name+'.install-'+str(os.getpid()));tmp.write_bytes(files[name].read_bytes())
                    if digest(tmp)!=row['after'] or state(dest)!=row['before']:raise ValueError('source or installed file changed during installation: '+name)
                    tmp.replace(dest)
            if any(state(root/name)!=row['after'] for name,row in journal['entries'].items()):raise ValueError('installed bytes changed before completion')
        except Exception:
            conflicts=rollback(root,journal);write_json(directory/'result.json',{'status':'rolled-back','concurrent_files_preserved':conflicts});active.unlink();raise
        write_json(directory/'result.json',{'status':'installed','files':list(journal['entries'])});active.unlink()
        print('Installed',len(changed),'files; recoverable previous bytes retained at',directory);return 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--check',action='store_true');p.add_argument('--expected',type=Path);a=p.parse_args(argv)
    try:return install(a)
    except (OSError,ValueError,KeyError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
