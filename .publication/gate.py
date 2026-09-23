#!/usr/bin/env python3
"""Validate the exact public tree and obtain fresh independent release decisions.

Unchanged legacy pages are explicitly grandfathered, not retroactively approved.
Reusable evidence requires a successful main ancestor, or an identical commit
checked in a successful push run in this repository.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'))
import evidence
import handoff
import quote_layout
import release_runner
import review
import validate_article
import build_indexes
import public_files


def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.DEVNULL)
def read(path):return json.loads(Path(path).read_text())
def files():return git('ls-files','-z').decode().strip('\0').split('\0')
def old_blob(commit,path):
    try:return git('show',commit+':'+path)
    except subprocess.CalledProcessError:return None


def eligible_prior_run(run, head, repository):
    if run.get('conclusion')!='success' or run.get('event')!='push':return False
    if run.get('head_repository',{}).get('full_name')!=repository:return False
    return run.get('head_sha')==head or run.get('head_branch')=='main'


def runtime_only_paths(names):
    allowed={'.publication/gate.py','.publication/test_gate.py','.publication/sync_runtime.py',
             '.publication/runtime-manifest.json','.github/workflows/publication.yml'}
    return bool(names) and all(n in allowed or n.startswith('.publication/runtime/') for n in names)


def changes(base, head='HEAD'):
    return git('diff','--name-only',base,head).decode().splitlines()


def completed_publication_job(data):
    return any(job.get('conclusion')=='success' and any(
        step.get('name')=='Validate exact public artifacts and obtain independent decisions'
        and step.get('conclusion')=='success' for step in job.get('steps',[]))
        for job in data.get('jobs',[]))


def classify_event():
    event=read(os.environ['GITHUB_EVENT_PATH']);kind=os.environ.get('GITHUB_EVENT_NAME')
    base=None
    if kind=='pull_request':base=event['pull_request']['base']['sha']
    elif kind=='push':
        base=event.get('before')
        if not base or set(base)=={'0'}:base=git('merge-base','origin/main','HEAD').decode().strip()
    mode='runtime' if base and runtime_only_paths(changes(base)) else 'publication'
    with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write(f'mode={mode}\nbase={base or ""}\n')
    print('Check mode:',mode)


def validate_runtime_only(base):
    if not base or not runtime_only_paths(changes(base)):
        raise ValueError('runtime-only mode requires exclusively runtime/workflow changes')
    names=files()
    previous=git('ls-tree','-r','--name-only',base).decode().splitlines()
    def protected(items):return set(public_files.public_names(items)) | {n for n in items if n.startswith('.prose-reviews/')}
    if protected(names)!=protected(previous):raise ValueError('runtime update changed public/review inventory')
    if any(old_blob(base,n)!=Path(n).read_bytes() for n in protected(names)):
        raise ValueError('runtime update changed article, public asset or review bytes')
    manifest=read(HERE/'runtime-manifest.json')
    actual={p.name:review.digest(p.read_bytes()) for p in (HERE/'runtime').iterdir() if p.suffix in {'.py','.md'}}
    if actual!=manifest:raise ValueError('CI runtime snapshot differs from manifest')
    return {'status':'passed','mode':'runtime-only','base':base,
            'commit':git('rev-parse','HEAD').decode().strip(),
            'public_files':public_files.snapshot(),'article_approvals':[]}


def prior_success(allow_older_policy=False):
    token=os.environ.get('GITHUB_TOKEN');repo=os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo:return None
    url=f'https://api.github.com/repos/{repo}/actions/workflows/publication.yml/runs?status=success&per_page=30'
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
    head=git('rev-parse','HEAD').decode().strip()
    for run in data['workflow_runs']:
        if not eligible_prior_run(run,head,repo):continue
        commit=run['head_sha']
        if subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],stderr=subprocess.DEVNULL).returncode:continue
        # Current-policy reuse requires identical checking code. A separately labelled
        # preservation path may retain an older approval for identical article
        # and evidence bytes; it never approves an edited candidate.
        if not allow_older_policy and git('diff','--name-only',commit,'HEAD','--','.publication','.github/workflows/publication.yml').strip():continue
        jobs_request=urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/runs/{run["id"]}/jobs?per_page=100',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(jobs_request,timeout=30) as response:jobs=json.load(response)
        if not completed_publication_job(jobs):continue
        return commit
    return None


def article_paths(names):
    return [p for p in names if public_files.is_article(p)]


def packet_for(receipt, page):
    source=receipt['source_markdown'];record=receipt['source_review'];report=record['council']['report']
    return {'candidate':source,'artifact_sha256':review.digest(source),
            'rendered_artifact_sha256':review.digest(page),'rendered_authored_blocks':review.extract(page,'html')['blocks'],
            'report':{k:v for k,v in report.items() if k!='release'},'council_sha256':review.council_digest(report),
            'writer_dispositions':record.get('findings',[]),'required_disposition_ids':sorted(review.council_finding_ids(report))}


def validate_article_files(path):
    page=Path(path).read_text();base=Path('.prose-reviews')/Path(path).stem
    receipt=read(str(base)+'.handoff.json');record=read(str(base)+'.review.json');baseline=read(str(base)+'.baseline.json')
    errors=review.verify_handoff(page,receipt,require_release=False)
    draft=review.inspect_file(Path(path))
    errors+=review.verify(draft,baseline,record,receipt['source_sha256'],require_release=False)
    errors+=validate_article.check(page,register=record.get('register','standard'))
    bundle=read(str(base)+'.evidence.json')
    errors+=evidence.verify(bundle,receipt['source_markdown'])
    if errors:raise ValueError(path+': '+'; '.join(errors))
    return page,receipt,bundle


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--client',default='copilot');p.add_argument('--classify',action='store_true');p.add_argument('--runtime-base')
    a=p.parse_args()
    if a.classify:classify_event();return 0
    if a.output is None:p.error('--output is required')
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    if a.runtime_base:
        result=validate_runtime_only(a.runtime_base)
        (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('Runtime checked; public and review bytes unchanged. No article approval or site deployment.');return 0
    names=files();legacy=read(HERE/'legacy.json')['files'];prior=prior_success();preserved=prior or prior_success(allow_older_policy=True);results=[]
    # The index generators are separate from the article review. Changes to their
    # public text must remain generated from the article collection; no new HTML
    # filename may opt into this exception.
    try:
        manifest=read(HERE/'runtime-manifest.json')
        actual={p.name:review.digest(p.read_bytes()) for p in (HERE/'runtime').iterdir() if p.suffix in {'.py','.md'}}
        if actual!=manifest:raise ValueError('CI runtime snapshot differs from its manifest; synchronize and test it')
        inventory=public_files.snapshot()
        assets={n:h for n,h in inventory.items() if Path(n).suffix.lower() in public_files.STATIC}
        if assets!=read(HERE/'assets.json'):raise ValueError('static assets changed; validate rendering and update the checked asset manifest')
        public_html=[p for p in inventory if p.lower().endswith(('.html','.htm'))]
        if any(review.digest(Path(p).read_bytes())!=legacy.get(p) for p in public_html):
            build_indexes.check(Path.cwd())
        for path in article_paths(names):
            if Path(path).is_symlink():raise ValueError('public article symlink forbidden: '+path)
            raw=Path(path).read_bytes();stem=Path(path).stem
            if review.digest(raw)==legacy.get(path):
                results.append({'path':path,'status':'unchanged-legacy'});continue
            dependencies=[path]+['.prose-reviews/'+stem+suffix for suffix in ['.baseline.json','.review.json','.handoff.json','.evidence.json']]
            if preserved and all(Path(n).is_file() and old_blob(preserved,n)==Path(n).read_bytes() for n in dependencies):
                results.append({'path':path,'status':'reused-server-review' if prior else 'preserved-prior-policy-review','commit':preserved});continue
            page,receipt,bundle=validate_article_files(path)
            directory=a.output/stem;directory.mkdir()
            quote_layout.capture(Path(path).resolve(),directory/'render.json')
            errors=quote_layout.render_errors(review.extract(page,'html')['quotes'],read(directory/'render.json'),review.digest(page),require_render=True)
            if errors:raise ValueError(path+': '+'; '.join(errors))
            packet=packet_for(receipt,page)
            release_runner.run(packet,bundle,directory/'independent-review',a.client)
            results.append({'path':path,'status':'passed','artifact_sha256':review.digest(raw)})
        (a.output/'result.json').write_text(json.dumps({'status':'passed','commit':git('rev-parse','HEAD').decode().strip(),'public_files':inventory,'results':results},indent=2)+'\n')
        print('Publication checks passed:',sum(r['status']=='passed' for r in results),'fresh reviews;',len(results),'articles accounted for.')
        return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        (a.output/'result.json').write_text(json.dumps({'status':'blocked','error':str(error),'results':results},indent=2)+'\n')
        print('PUBLICATION BLOCKED:',error);return 1
if __name__=='__main__':raise SystemExit(main())
