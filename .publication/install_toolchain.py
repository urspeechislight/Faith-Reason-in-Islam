#!/usr/bin/env python3
"""Install the hash-checked, versioned article toolchain; retain replaced files."""
import argparse,datetime,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory():
    files={}
    for name,expected in json.loads((ROOT/'runtime-manifest.json').read_text()).items():
        source=ROOT/'runtime'/name
        if digest(source)!=expected:raise ValueError('runtime hash mismatch: '+name)
        dest='skills/faith-reason-note/validate.py' if name=='validate_article.py' else 'prose/'+name
        files[dest]=source
    for name,expected in json.loads((ROOT/'authoring-manifest.json').read_text()).items():
        source=ROOT/'authoring'/name
        if digest(source)!=expected:raise ValueError('authoring hash mismatch: '+name)
        if name in files:raise ValueError('duplicate installation path: '+name)
        files[name]=source
    return files

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--check',action='store_true');p.add_argument('--expected',type=Path,help='JSON map of target-relative paths to pre-install hashes or null');a=p.parse_args(argv)
    try:
        files=inventory();changed={name:source for name,source in files.items() if not (a.target/name).is_file() or digest(a.target/name)!=digest(source)}
        if a.check:
            print('Toolchain identical' if not changed else 'Toolchain differs: '+', '.join(changed));return bool(changed)
        if a.expected:
            expected=json.loads(a.expected.read_text())
            for name in changed:
                dest=a.target/name;actual=digest(dest) if dest.is_file() else None
                if name not in expected or expected[name]!=actual:raise ValueError('installed file changed since snapshot: '+name)
        backup=a.target/'.toolchain-backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        for name,source in changed.items():
            dest=a.target/name
            if dest.is_symlink():raise ValueError('refusing to replace symlink: '+str(dest))
        for name,source in changed.items():
            dest=a.target/name;dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():
                old=backup/name;old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(dest.read_bytes())
            tmp=dest.with_name(dest.name+'.install-'+str(os.getpid()));tmp.write_bytes(source.read_bytes());tmp.replace(dest)
        print('Installed',len(changed),'files; replaced bytes retained at',backup);return 0
    except (OSError,ValueError,KeyError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
