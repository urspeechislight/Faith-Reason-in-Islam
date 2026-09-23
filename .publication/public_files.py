"""Public inventory shared by validation and staging; research stays private."""
from pathlib import Path
import hashlib
import json
import subprocess

STATIC={'.css','.js','.svg','.png','.jpg','.jpeg','.webp','.ico','.woff','.woff2','.ttf','.pdf'}
def digest(data):return hashlib.sha256(data).hexdigest()
def tracked():return subprocess.check_output(['git','ls-files','-z']).decode().strip('\0').split('\0')
def is_article(name):
    p=Path(name)
    return (p.suffix.lower() in {'.html','.htm'} and not any(x.startswith('.') for x in p.parts)
            and not p.name.startswith(('council-','draft-')) and not any(x in {'runs','rewrites','drafts'} for x in p.parts)
            and name not in {'index.html','facts.html'})
def public_names(names):
    selected=[]
    for name in names:
        p=Path(name)
        if any(x.startswith('.') or x in {'runs','rewrites','drafts'} for x in p.parts):continue
        if p.name.startswith(('council-','draft-')):continue
        if is_article(name) or name in {'index.html','facts.html','robots.txt','sitemap.xml','CNAME'} or p.suffix.lower() in STATIC:
            selected.append(name)
    return sorted(selected)
def snapshot():
    result={}
    for name in public_names(tracked()):
        p=Path(name)
        if p.is_symlink() or any(parent.is_symlink() for parent in p.parents):raise ValueError('public symlink forbidden: '+name)
        result[name]=digest(p.read_bytes())
    return result
