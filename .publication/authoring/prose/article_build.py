#!/usr/bin/env python3
"""One run manifest for deterministic article preflight and verified handoff.

No model calls, article rewriting, approval fabrication, Git mutations or publishing.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import fcntl

ROOT=Path(__file__).resolve().parent
_toolchain_lock=None
if (ROOT.parent/'.toolchain-install.lock').exists():
    _toolchain_lock=(ROOT.parent/'.toolchain-install.lock').open('a')
    try:fcntl.flock(_toolchain_lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('BLOCKED: toolchain installation is in progress; retry after it completes')
if (ROOT.parent/'.toolchain-install-active.json').exists():
    raise SystemExit('BLOCKED: interrupted toolchain installation; recover it with install_toolchain.py before running article commands')
sys.path.insert(0,str(ROOT))
import handoff
import evidence
import article_revision
import article_scope
import review_intake
import native_release
import scripture_alignment
import quote_layout
import render_article
import review
SCHEMA=1
RUNTIME=['conversion_review.py','review_intake.py','article_scope.py','native_release.py','release_runner.py','article_revision.py','scripture_alignment.py','article_build.py','render_article.py','handoff.py','scripture.py','quote_layout.py','review.py','contract.md','drafting.md','editorial.md','council-article.md','paragraphs.md','quotation.css','pre_push.py','article-sources.md','article-structure.md','evidence.py']
VALIDATOR=ROOT.parent/'skills/faith-reason-note/validate.py'


def sha_bytes(raw):return hashlib.sha256(raw).hexdigest()
def digest(path):return sha_bytes(Path(path).read_bytes())
def read(path):return json.loads(Path(path).read_text())
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def runtime():
    paths=[ROOT/n for n in RUNTIME]+[VALIDATOR]+[render_article.TEMPLATES/f'template-{t}.html' for t in ('tabs','flowing')]
    return {str(p):digest(p) for p in paths}
def load(manifest):
    data=read(manifest)
    if data.get('schema')!=SCHEMA:raise ValueError('unsupported run manifest schema; preserve it and adopt its retained handoff into a new run')
    if str(data.get('paths',{}).get('site_root','')).startswith('/Users/'):
        raise ValueError('project execution belongs on Titan; use titan-project and a Titan site worktree')
    article_scope.check(data)
    return data

def inputs(data):
    render_article.validate_options(data['render'])
    site=Path(data['paths']['site_root']);target=site/(data['slug']+'.html')
    allowed=article_revision.destination_allowed(sys.modules[__name__],data)
    for key,path in article_revision.destination_paths(data).items():
        if key in allowed and (digest(path) if path.is_file() else None) not in allowed[key]:
            raise ValueError('destination changed outside this run: '+str(path)+'; inspect concurrent edits before creating a new revision')
    source=Path(data['paths']['source'])
    if not source.is_file():raise ValueError('missing canonical candidate: '+str(source))
    text=source.read_text()
    return text,{'source_sha256':handoff.sha(text),'runtime':runtime(),'render':data['render'],'site_root':data['paths']['site_root'],'linked_pages':{v:digest(Path(data['paths']['site_root'])/v.split('#')[0]) for v in data['render'].get('note_map',{}).values()},'year':datetime.date.today().year,'scripture_review_sha256':digest(data['paths']['scripture_review']) if data['paths'].get('scripture_review') and Path(data['paths']['scripture_review']).is_file() else None}

def validator():
    spec=importlib.util.spec_from_file_location('article_html_validator',VALIDATOR);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def init(a):
    path=a.manifest.resolve()
    if path.exists():raise ValueError('manifest exists; use it instead of replacing run history')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',a.slug):raise ValueError('slug must be lowercase words separated by hyphens')
    source=a.source.resolve();site=a.site_root.resolve()
    if str(site).startswith('/Users/'):raise ValueError('project execution belongs on Titan; use titan-project')
    if not source.is_file():raise ValueError('source does not exist: '+str(source))
    if not site.is_dir():raise ValueError('site workspace does not exist: '+str(site))
    if a.operation=='repair' and not (site/(a.slug+'.html')).is_file():raise ValueError('repair must identify the existing article slug in the site workspace')
    if a.operation=='create' and (site/(a.slug+'.html')).exists():raise ValueError('article slug already exists; use repair and preserve its URL')
    root=path.parent
    data={'schema':SCHEMA,'operation':a.operation,'delivery':a.delivery,'slug':a.slug,
          'paths':{'source':str(source),'site_root':str(site),
                   'baseline':str(a.baseline.resolve() if a.baseline else root/'reviews/master.baseline.json'),
                   'review':str(a.review.resolve() if a.review else root/'reviews/master.review.json'),
                   'evidence':str(root/'evidence.json'),'scripture_review':str(root/'reviews/scripture-alignment.json'),
                   'html_baseline':str(root/'reviews/html.baseline.json'),'html_review':str(root/'reviews/html.review.json')},
          'render':read(a.config) if a.config else {},'builds':[],'ready':None}
    render_article.validate_options(data['render'])
    data['render']['slug']=a.slug
    data['initial_source_sha256']=digest(source)
    if a.operation=='repair':data['original_article_sha256']=digest(site/(a.slug+'.html'))
    data['destination_snapshot']=article_revision.destination_snapshot(sys.modules[__name__],data)
    article_scope.bind(sys.modules[__name__],data,getattr(a,'url',None))
    write(path,data);print('Run manifest:',path);return 0


def preflight(a):
    manifest=a.manifest.resolve();data=load(manifest);source,binding=inputs(data)
    key=sha_bytes(json.dumps(binding,sort_keys=True).encode());directory=manifest.parent/'builds'/key[:20]
    result_path=directory/'preflight.json'
    for previous in reversed(data['builds']):
        candidate=Path(previous['preflight'])
        if candidate.is_file():
            cached=read(candidate)
            if cached.get('binding')==binding and cached.get('status')=='passed':
                directory=Path(previous['directory']);result_path=candidate;break
    if result_path.exists():
        result=read(result_path)
        if result.get('binding')!=binding:raise ValueError('preflight binding mismatch')
        for name,value in result.get('artifacts',{}).items():
            if digest(directory/name)!=value:raise ValueError('cached preflight artifact changed: '+name)
        if result['status']=='passed':
            row=next((b for b in data['builds'] if b['preflight']==str(result_path)),None)
            if row is None:
                row={'id':directory.name,'directory':str(directory),'preflight':str(result_path),'source_sha256':binding['source_sha256'],'status':'passed'};data['builds'].append(row)
            if data.get('latest_build')!=row['id']:data['ready']=None
            data['latest_build']=row['id'];write(manifest,data)
            print('Reusing exact preflight:',result_path,'status:',result['status']);return 0
    # Preserve blocked/interrupted attempts and retry browser/dependency failures.
    attempt=0;base=directory
    while directory.exists():
        attempt+=1;directory=base.with_name(base.name+'-'+str(attempt))
    result_path=directory/'preflight.json'
    directory.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    result={'status':'blocked','binding':binding,'errors':[],'artifacts':{},'approval':'none'}
    try:
        receipt=handoff.prepare(source,data['paths']['source'])
        page,receipt=render_article.render(source,receipt,data['render'],data['paths']['site_root'])
        html_path=directory/'article.html';receipt_path=directory/'handoff.preview.json'
        html_path.write_text(page);write(receipt_path,receipt)
        result['artifacts']={p.name:digest(p) for p in (html_path,receipt_path)}
        errors=validator().check(page,register=data['render'].get('register','standard'))
        alignment_path=Path(data['paths'].get('scripture_review',manifest.parent/'reviews/scripture-alignment.json'))
        if scripture_alignment.inventory(source):
            if not alignment_path.exists():write(alignment_path,scripture_alignment.prepare(source))
            errors+=scripture_alignment.errors(source,read(alignment_path))
        # Browser geometry is required even when text/schema checks already found defects.
        if review.extract(page,'html')['quotes']:
            quote_layout.capture(html_path,directory/'render.json')
            record=read(directory/'render.json')
            errors+=quote_layout.render_errors(review.extract(page,'html')['quotes'],record,review.digest(page),require_render=True)
            result['artifacts']['render.json']=digest(directory/'render.json')
            for view in record['viewports']:
                screenshot=Path(view['screenshot'])
                result['artifacts'][screenshot.name]=digest(screenshot)
        result['errors']=errors;result['status']='blocked' if errors else 'passed'
    except Exception as exc:result['errors'].append(type(exc).__name__+': '+str(exc))
    result['elapsed_seconds']=round(time.monotonic()-start,3);write(result_path,result)
    build_id=directory.name
    data['builds'].append({'id':build_id,'directory':str(directory),'preflight':str(result_path),'source_sha256':binding['source_sha256'],'status':result['status']})
    data['latest_build']=build_id;data['ready']=None;write(manifest,data)
    print('Preflight',result['status']+':',result_path)
    for error in result['errors']:print('BLOCKED:',error)
    return 0 if result['status']=='passed' else 1


def current_build(data):
    source,binding=inputs(data)
    row=next((b for b in data['builds'] if b['id']==data.get('latest_build')),None)
    if not row:raise ValueError('run preflight before preparing a reviewed handoff')
    result=read(row['preflight'])
    if result.get('binding')!=binding:raise ValueError('master, render options or toolchain changed; run preflight again')
    if result.get('status')!='passed':raise ValueError('preflight is blocked; fix its located findings before review')
    directory=Path(row['directory'])
    for name,value in result['artifacts'].items():
        if digest(directory/name)!=value:raise ValueError('preflight artifact was edited: '+name)
    return source,directory,result


def prepare(a):
    manifest=a.manifest.resolve();data=load(manifest);source,directory,result=current_build(data)
    if bool(a.baseline)!=bool(a.review):raise ValueError('provide both --baseline and --review')
    baseline_path=a.baseline.resolve() if a.baseline else Path(data['paths']['baseline'])
    review_path=a.review.resolve() if a.review else Path(data['paths']['review'])
    missing=[str(p) for p in (baseline_path,review_path) if not p.is_file()]
    if missing:raise ValueError('missing registered review files: '+', '.join(missing)+'; pass the exact paths to prepare, never search by filename/version guesses')
    baseline=read(baseline_path);record=read(review_path);pending=data['delivery']=='publish'
    errors=review.verify(review.inspect_file(Path(data['paths']['source'])),baseline,record,require_release=not pending)
    if errors:raise ValueError('master review failed: '+'; '.join(errors))
    receipt=read(directory/'handoff.preview.json')
    receipt.update(source_baseline=baseline,source_review=record,release_pending=pending and not record.get('council',{}).get('report',{}).get('release',{}).get('native'))
    errors=handoff.verify((directory/'article.html').read_text(),receipt)
    if errors:raise ValueError('verified conversion changed: '+'; '.join(errors))
    key=sha_bytes((digest(baseline_path)+digest(review_path)+digest(directory/'article.html')).encode())[:20]
    approved=manifest.parent/'handoffs'/key/'handoff.json'
    if approved.exists():
        if read(approved)!=receipt:raise ValueError('existing immutable handoff differs')
    else:write(approved,receipt)
    data['paths'].update(baseline=str(baseline_path),review=str(review_path))
    paths={'source':data['paths']['source'],'baseline':str(baseline_path),'review':str(review_path),'html':str(directory/'article.html'),'handoff':str(approved),'preflight':str(directory/'preflight.json')}
    data['ready']={'status':'awaiting-native-review' if receipt['release_pending'] else 'master-reviewed','paths':paths,'hashes':{name:digest(path) for name,path in paths.items()},'runtime':runtime()}
    write(manifest,data);print('Checked build:',approved);print('Status:',data['ready']['status'],'(no publication performed)');return 0


def verify(a):
    data=load(a.manifest);source,directory,result=current_build(data);ready=data.get('ready')
    if not ready:raise ValueError('no verified handoff; run prepare after real master review')
    if ready['runtime']!=runtime():raise ValueError('toolchain changed since review; no approval-field or hash patching is permitted')
    for name,path in ready['paths'].items():
        if digest(path)!=ready['hashes'][name]:raise ValueError('ready artifact changed: '+name)
    receipt=read(ready['paths']['handoff']);page=Path(ready['paths']['html']).read_text()
    errors=review.verify_handoff(page,receipt,require_release=data['delivery']!='publish')
    if errors:raise ValueError('; '.join(errors))
    final_paths={name:str(getattr(a,name).resolve()) if getattr(a,name,None) else data['paths'][name] for name in ('html_baseline','html_review','evidence')}
    baseline=read(final_paths['html_baseline']);record=read(final_paths['html_review'])
    errors=review.verify_html(page,baseline,record,receipt,require_release=data['delivery']!='publish')
    errors+=evidence.verify(read(final_paths['evidence']),source)
    if data['delivery']=='publish' and not getattr(a,'native_pending',False):
        errors+=native_release.errors(source,page,Path(final_paths['evidence']).read_text(),receipt['source_review']['council']['report'])
    if errors:raise ValueError('combined final verification failed: '+'; '.join(errors))
    data['paths'].update(final_paths);ready['paths'].update(final_paths)
    ready['hashes'].update({name:digest(path) for name,path in final_paths.items()})
    ready['status']=('awaiting-native-review' if getattr(a,'native_pending',False) else 'prepared-for-publication') if data['delivery']=='publish' else 'reviewed-draft'
    if not getattr(a,'read_only',False):write(a.manifest,data)
    print('Combined artifact checks passed. Status:',ready['status']+'. GitHub checks and deployment remain required for publication.');return 0


def paths(a):
    data=load(a.manifest);out=dict(data['paths'])
    row=next((b for b in data['builds'] if b['id']==data.get('latest_build')),None)
    if row:
        directory=Path(row['directory']);out.update(html=str(directory/'article.html'),render=str(directory/'render.json'),preflight=row['preflight'])
    if data.get('ready'):out.update(data['ready']['paths'])
    print(json.dumps(out,ensure_ascii=False,indent=2));return 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    i=sub.add_parser('init');i.add_argument('manifest',type=Path);i.add_argument('--source',type=Path,required=True);i.add_argument('--site-root',type=Path,required=True);i.add_argument('--slug',required=True);i.add_argument('--operation',choices=['create','repair'],required=True);i.add_argument('--delivery',choices=['publish','draft','note'],default='publish');i.add_argument('--baseline',type=Path);i.add_argument('--review',type=Path);i.add_argument('--config',type=Path)
    i.add_argument('--url',help='Exact user-supplied published article URL; must match slug')
    i=sub.add_parser('adopt');i.add_argument('manifest',type=Path);i.add_argument('--handoff',type=Path,required=True);i.add_argument('--source',type=Path);i.add_argument('--site-root',type=Path,required=True);i.add_argument('--slug',required=True);i.add_argument('--delivery',choices=['publish','draft','note'],default='publish');i.add_argument('--config',type=Path)
    i=sub.add_parser('scope');i.add_argument('manifest',type=Path);i.add_argument('--url',required=True)
    i=sub.add_parser('review-request');i.add_argument('manifest',type=Path);i.add_argument('--kind',choices=['master','render','scripture'],required=True);i.add_argument('--source-context',type=Path);i.add_argument('--parent-model',required=True);i.add_argument('--output',type=Path,required=True)
    i=sub.add_parser('review-accept');i.add_argument('manifest',type=Path);i.add_argument('--request',type=Path,required=True);i.add_argument('--response',type=Path,required=True);i.add_argument('--agent-id',required=True);i.add_argument('--model',required=True)
    i=sub.add_parser('preflight');i.add_argument('manifest',type=Path)
    i=sub.add_parser('prepare');i.add_argument('manifest',type=Path);i.add_argument('--baseline',type=Path);i.add_argument('--review',type=Path)
    i=sub.add_parser('verify');i.add_argument('manifest',type=Path);i.add_argument('--html-baseline',type=Path);i.add_argument('--html-review',type=Path);i.add_argument('--evidence',type=Path)
    i=sub.add_parser('paths');i.add_argument('manifest',type=Path)
    i=sub.add_parser('revise');i.add_argument('manifest',type=Path);i.add_argument('--source',type=Path,required=True);i.add_argument('--output',type=Path,required=True);i.add_argument('--reason',required=True)
    i=sub.add_parser('release-request');i.add_argument('manifest',type=Path);i.add_argument('--parent-model',required=True);i.add_argument('--output',type=Path,required=True)
    i=sub.add_parser('release-accept');i.add_argument('manifest',type=Path);i.add_argument('--request',type=Path,required=True);i.add_argument('--response',type=Path,required=True);i.add_argument('--agent-id',required=True);i.add_argument('--model',required=True)
    for command in ['reviews','stage','status']:
        i=sub.add_parser(command);i.add_argument('manifest',type=Path)
    i=sub.add_parser('reuse');i.add_argument('manifest',type=Path);i.add_argument('--confirmation',type=Path,required=True)
    for command in ['advance','evidence']:
        i=sub.add_parser(command);i.add_argument('manifest',type=Path)
        for option in ['ledger','external','claims','db']:i.add_argument('--'+option,type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=='adopt':
            return article_revision.adopt(sys.modules[__name__],a)
        a.manifest.parent.mkdir(parents=True,exist_ok=True)
        with a.manifest.with_suffix(a.manifest.suffix+'.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('another process is using this run manifest')
            if a.command=='scope':return article_scope.command(sys.modules[__name__],a)
            if a.command in {'review-request','review-accept'}:
                return getattr(review_intake,'request' if a.command=='review-request' else 'accept')(sys.modules[__name__],a)
            if a.command in {'release-request','release-accept'}:
                return getattr(native_release,'request' if a.command=='release-request' else 'accept')(sys.modules[__name__],a)
            if a.command in {'revise','reviews','reuse','stage','status','evidence','advance'}:
                method='evidence_export' if a.command=='evidence' else a.command
                return getattr(article_revision,method)(sys.modules[__name__],a)
            return {'init':init,'preflight':preflight,'prepare':prepare,'verify':verify,'paths':paths}[a.command](a)
    except (OSError,ValueError,KeyError,TypeError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
