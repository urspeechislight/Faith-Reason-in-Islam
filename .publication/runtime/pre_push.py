#!/usr/bin/env python3
"""Verify reviews for changed article blobs in outgoing commits, before push."""
import json
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from review import extract, digest, verify, verify_handoff, VERSION
import handoff

ZERO='0'*40

def git(*args):
    return subprocess.check_output(['git',*args])

def blob(revision,path):
    return git('show',revision+':'+path)

def check_update(local,remote,require_release=True):
    if local==ZERO:
        return []
    if remote==ZERO:
        # A new branch is checked against the existing remote main when present.
        try:remote=git('merge-base',local,'refs/remotes/origin/main').decode().strip()
        except subprocess.CalledProcessError:remote=None
    names=(git('diff','--name-only','--diff-filter=ACMRT',remote,local,'--','*.html').decode().splitlines()
           if remote else [p for p in git('ls-tree','-r','--name-only',local).decode().splitlines() if p.endswith('.html')])
    errors=[]
    for path in names:
        page=blob(local,path)
        # Merging main into a branch can introduce an article already published
        # there. It is not a new article revision in this outgoing change. The
        # hosted gate independently decides whether its approval is reusable.
        try:
            if blob('refs/remotes/origin/main',path)==page:continue
        except subprocess.CalledProcessError:pass
        pattern=rb'<main\b[^>]*data-category=["\'](?:debate|exegesis|narration|commentary)'
        is_article=bool(re.search(pattern,page))
        if not is_article and remote:
            try:is_article=bool(re.search(pattern,blob(remote,path)))
            except subprocess.CalledProcessError:pass  # Newly added file has no prior blob.
        if not is_article:
            continue
        stem=Path(path).stem
        base='.prose-reviews/'+stem
        try:
            baseline=json.loads(blob(local,base+'.baseline.json'))
            review=json.loads(blob(local,base+'.review.json'))
            draft=extract(page.decode(),'html')
            draft.update(schema=VERSION,artifact_sha256=digest(page),format='html')
            failures=[]
            council_source=None
            needs_handoff=b'source-note-sha256' in page
            if remote:
                try:needs_handoff=needs_handoff or b'source-note-sha256' in blob(remote,path)
                except subprocess.CalledProcessError:pass
            if needs_handoff:
                receipt=json.loads(blob(local,base+'.handoff.json'))
                handoff_errors=verify_handoff(page.decode(),receipt,require_release=require_release)
                failures.extend(handoff_errors)
                if not handoff_errors:council_source=receipt['source_sha256']
            failures.extend(verify(draft,baseline,review,council_source,require_release=require_release))
            required=['structural_validation','council']
            if re.search('[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]',page.decode()):
                required+=['source_verification','translation_fidelity']
            for field in required:
                if review.get(field,{}).get('status')!='passed':
                    failures.append(field+' must pass for this article')
            validator=Path.home()/'.agents/skills/faith-reason-note/validate.py'
            spec=importlib.util.spec_from_file_location('article_validator',validator)
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            failures.extend(module.check(page.decode(),register=review.get('register','standard')))
            errors.extend(path+': '+e for e in failures)
        except (subprocess.CalledProcessError,ValueError,TypeError,KeyError) as exc:
            errors.append(path+': missing or invalid committed review records ('+str(exc)+')')
    return errors

def main():
    errors=[]
    try:
        for line in sys.stdin:
            fields=line.split()
            if len(fields)!=4:raise ValueError('invalid pre-push ref input')
            # Enabled only after the protected hosted gate is installed. The
            # local hook checks preparation; GitHub obtains final approval.
            try: hosted=git('config','--get','publication.serverGate').decode().strip()=='true'
            except subprocess.CalledProcessError: hosted=False
            errors.extend(check_update(fields[1],fields[3],require_release=not hosted))
    except (subprocess.CalledProcessError,ValueError,OSError) as exc:
        errors.append(str(exc))
    if errors:
        print('Publication blocked: final article review is missing, stale, or incomplete.',file=sys.stderr)
        for error in errors:print(error,file=sys.stderr)
        print('Follow ~/.agents/prose/editorial.md; review the actual outgoing artifact.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
