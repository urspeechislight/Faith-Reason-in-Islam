"""Public inventory shared by validation and staging; research stays private."""
from pathlib import Path
import hashlib
import json
import subprocess

STATIC={'.css','.js','.svg','.png','.jpg','.jpeg','.webp','.ico','.woff','.woff2','.ttf','.pdf'}
# Interactive tools are self-contained pages, not prose articles. A page is a tool
# only when it sits directly in tools/ AND its exact path is registered in the
# checked tools.json manifest. Anything else stays an article (fail closed), and
# the gate checks each registered tool's bytes and mechanical rules.
TOOLS_DIR='tools'
TOOLS_MANIFEST=Path(__file__).resolve().parent/'tools.json'
def registered_tools():
    try:return json.loads(TOOLS_MANIFEST.read_text())
    except FileNotFoundError:return {}
def is_tool(name):
    p=Path(name)
    return (len(p.parts)==2 and p.parts[0]==TOOLS_DIR and p.suffix.lower()=='.html'
            and not p.name.startswith(('.','council-','draft-')) and name in registered_tools())
def digest(data):return hashlib.sha256(data).hexdigest()
def tracked():return subprocess.check_output(['git','ls-files','-z']).decode().strip('\0').split('\0')
def is_article(name):
    p=Path(name)
    return (p.suffix.lower() in {'.html','.htm'} and not any(x.startswith('.') for x in p.parts)
            and not p.name.startswith(('council-','draft-')) and not any(x in {'runs','rewrites','drafts'} for x in p.parts)
            and name not in {'index.html','facts.html'} and not is_tool(name))
def public_names(names):
    selected=[]
    for name in names:
        p=Path(name)
        if any(x.startswith('.') or x in {'runs','rewrites','drafts'} for x in p.parts):continue
        if p.name.startswith(('council-','draft-')):continue
        if is_article(name) or is_tool(name) or name in {'index.html','facts.html','robots.txt','sitemap.xml','CNAME'} or p.suffix.lower() in STATIC:
            selected.append(name)
    return sorted(selected)
def snapshot():
    result={}
    for name in public_names(tracked()):
        p=Path(name)
        if p.is_symlink() or any(parent.is_symlink() for parent in p.parents):raise ValueError('public symlink forbidden: '+name)
        result[name]=digest(p.read_bytes())
    return result
