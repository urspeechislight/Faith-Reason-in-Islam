#!/usr/bin/env python3
"""Regenerate public indexes from reviewed article HTML, using maintained code."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
HERE=Path(__file__).resolve().parent

def strip_catalog(text):
    result,n=re.subn(r'<!-- CATALOG:BEGIN -->.*?<!-- CATALOG:END -->','CATALOG',text,flags=re.S)
    if n!=1:raise ValueError('exactly one catalog block is required')
    return result

def normalized(text):
    return re.sub(r'"generated":"\d{4}-\d{2}-\d{2}"','"generated":"DATE"',text)

def build(site):
    env=dict(os.environ,PUBLICATION_SITE_DIR=str(site.resolve()))
    for name in ['gen_facts_index.py','gen_catalog.py']:
        subprocess.run(['python3',str(HERE/name)],env=env,check=True,stdout=subprocess.DEVNULL)

def check(site):
    actual=(site/'index.html').read_text()
    if strip_catalog(actual)!=strip_catalog((HERE/'index-template.html').read_text()):
        raise ValueError('index template changed; maintain its checked template explicitly')
    with tempfile.TemporaryDirectory(prefix='derived-indexes-') as d:
        temp=Path(d)
        for path in site.glob('*.html'):shutil.copy2(path,temp/path.name)
        build(temp)
        for name in ['index.html','facts.html']:
            if normalized((site/name).read_text())!=normalized((temp/name).read_text()):
                raise ValueError(name+' is stale or manually changed; run python3 .publication/build_indexes.py')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--site',type=Path,default=Path.cwd());a=p.parse_args()
    if a.check:check(a.site)
    else:build(a.site)
