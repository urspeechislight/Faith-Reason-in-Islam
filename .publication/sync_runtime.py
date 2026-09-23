#!/usr/bin/env python3
"""Snapshot the installed Titan review runtime into the controlled CI package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
FILES=['review.py','quote_layout.py','handoff.py','pre_push.py','release_runner.py','evidence.py','contract.md','drafting.md','editorial.md','council-article.md','paragraphs.md']
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    sources={n:Path.home()/'.agents/prose'/n for n in FILES}
    sources['validate_article.py']=Path.home()/'.agents/skills/faith-reason-note/validate.py'
    failures=[]
    for name,source in sources.items():
        target=ROOT/'runtime'/name
        if a.check:
            if source.read_bytes()!=target.read_bytes():failures.append(name)
        else:shutil.copy2(source,target)
    if failures:raise SystemExit('Runtime differs: '+', '.join(failures))
    if not a.check:
        manifest={n:hashlib.sha256((ROOT/'runtime'/n).read_bytes()).hexdigest() for n in sources}
        (ROOT/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
