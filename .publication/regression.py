#!/usr/bin/env python3
"""Reuse only a recent successful main run of the exact reviewer contract."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

PATHS=['.publication/runtime','.publication/evaluate.py','.publication/regression.py','.github/workflows/publication.yml']
STEP='Run required reviewer regressions'
MAX_AGE_HOURS=24


def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.DEVNULL)


def fingerprint(commit='HEAD'):
    raw=git('ls-tree','-r',commit,'--',*PATHS)
    return hashlib.sha256(raw).hexdigest()


def eligible(run,repo,now):
    try:age=now-datetime.datetime.fromisoformat(run['updated_at'].replace('Z','+00:00'))
    except (KeyError,TypeError,ValueError):return False
    return (run.get('conclusion')=='success' and run.get('event')=='push' and run.get('head_branch')=='main'
            and run.get('head_repository',{}).get('full_name')==repo
            and datetime.timedelta(0)<=age<=datetime.timedelta(hours=MAX_AGE_HOURS))


def api(path):
    req=urllib.request.Request('https://api.github.com/'+path,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)


def find_receipt():
    repo=os.environ.get('GITHUB_REPOSITORY');token=os.environ.get('GITHUB_TOKEN')
    if not repo or not token or os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch':return None
    now=datetime.datetime.now(datetime.timezone.utc);wanted=fingerprint()
    try:
        for run in api(f'repos/{repo}/actions/workflows/publication.yml/runs?status=success&per_page=30')['workflow_runs']:
            if not eligible(run,repo,now):continue
            commit=run['head_sha']
            if subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:continue
            if fingerprint(commit)!=wanted:continue
            jobs=api(f'repos/{repo}/actions/runs/{run["id"]}/jobs?per_page=100')['jobs']
            if any(j.get('conclusion')=='success' and any(s.get('name')==STEP and s.get('conclusion')=='success' for s in j.get('steps',[])) for j in jobs):
                return {'run_id':run['id'],'commit':commit,'fingerprint':wanted,'url':run['html_url']}
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):return None
    return None


def main():
    proof=find_receipt();needs=proof is None
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('needed='+str(needs).lower()+'\n')
    directory=Path(os.environ['RUNNER_TEMP'])/'reviewer-evaluation';directory.mkdir(parents=True,exist_ok=True)
    (directory/'reuse.json').write_text(json.dumps({'phase':'regression','fresh_run_required':needs,'receipt':proof},indent=2)+'\n')
    if proof:(directory/'result.json').write_text(json.dumps({'phase':'regression','status':'passed','reused':True,'receipt':proof},indent=2)+'\n')
    print('Reviewer regression:', 'required' if needs else 'verified exact-contract main receipt '+str(proof['run_id']))
if __name__=='__main__':main()
