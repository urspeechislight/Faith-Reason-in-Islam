"""Revision lifecycle operations for article_build. No authoring or approvals."""
from collections import Counter
import copy
import fcntl
import os
import json
from pathlib import Path
from types import SimpleNamespace
import shutil
import tempfile
import review
import scripture_alignment


def previous_source(B,data):
    row=next((b for b in data['builds'] if b['id']==data.get('latest_build')),None)
    if not row:raise ValueError('parent has no retained preflight; preserve a source snapshot before revising')
    result=B.read(row['preflight']);directory=Path(row['directory'])
    for name,value in result.get('artifacts',{}).items():
        if B.digest(directory/name)!=value:raise ValueError('parent preflight artifact changed: '+name)
    source=B.read(directory/'handoff.preview.json')['source_markdown']
    if review.digest(source)!=row['source_sha256']:raise ValueError('parent snapshot hash mismatch')
    return source


def mapping(old,new):
    old_blocks=review.extract(old,'md')['blocks'];new_blocks=review.extract(new,'md')['blocks']
    old_count=Counter((x['kind'],x['text']) for x in old_blocks);new_count=Counter((x['kind'],x['text']) for x in new_blocks)
    by_text={(x['kind'],x['text']):x for x in old_blocks}
    # Any changed protected quotation/link invalidates contextual reuse throughout
    # the article; a reviewer must reconsider how the prose relies on that evidence.
    a=review.extract(old,'md');b=review.extract(new,'md')
    protected_same=all(a[k]==b[k] for k in ['protected_sha256','links_sha256'])
    # Include complete heading sections so a far-away edit in the same argument
    # is not mistaken for unchanged context merely because neighbours match.
    import re
    def sections(text):
        parts=re.split(r'(?m)(?=^#{1,6} )',text);return parts
    old_sections=sections(old);new_sections=sections(new)
    out=[]
    for block in new_blocks:
        key=(block['kind'],block['text']);previous=by_text.get(key)
        unique=old_count[key]==new_count[key]==1
        old_context=[s for s in old_sections if block['text'] in s]
        new_context=[s for s in new_sections if block['text'] in s]
        same_section=(len(old_context)==len(new_context)==1 and old_context==new_context)
        eligible=bool(previous and unique and same_section and protected_same)
        out.append({'current_id':block['id'],'previous_id':previous['id'] if previous and unique else None,
                    'text_sha256':review.digest(block['text']),'eligible_for_context_review':eligible,
                    'reason':'exact text and section, with unchanged protected evidence' if eligible else 'changed, ambiguous, or affected context; fresh judgment required'})
    return out


def retained_alignment(B,parent,old,new):
    """Keep valid per-quotation fidelity evidence; never approve changed layers."""
    ref=parent['paths'].get('scripture_review')
    if not ref or not Path(ref).is_file():return None
    record=B.read(ref)
    row=next((b for b in parent['builds'] if b['id']==parent.get('latest_build')),None)
    binding=B.read(row['preflight'])['binding'] if row else {}
    if binding.get('scripture_review_sha256')!=B.digest(ref) or scripture_alignment.errors(old,record):return None
    result=scripture_alignment.prepare(new)
    def key(q):return (q['caption'],q['layers_sha256'])
    old_count=Counter(key(q) for q in record['quotes']);new_count=Counter(key(q) for q in result['quotes'])
    by_key={key(q):q for q in record['quotes']}
    for index,q in enumerate(result['quotes']):
        k=key(q)
        if old_count[k]==new_count[k]==1:
            prior=copy.deepcopy(by_key[k]);prior['id']=q['id']
            prior['retained_from']={'record_sha256':B.digest(ref),'reviewer':record['reviewer'],'quote_id':by_key[k]['id']}
            result['quotes'][index]=prior
    result['reviewer']=record['reviewer']
    if all(q['status']=='passed' for q in result['quotes']):result['status']='approved'
    return result


def revise(B,a):
    parent=B.load(a.manifest)
    if parent.get('staging'):raise ValueError('resume the interrupted stage before creating a revision')
    old=previous_source(B,parent)
    source=a.source.resolve();target=a.output.resolve()
    if target.name!='build.json':raise ValueError('revision output must be NEW_DIRECTORY/build.json')
    if not source.is_file():raise ValueError('revised source missing')
    if target.parent.exists():raise ValueError('revision directory exists; use a new directory to preserve all prior attempts')
    # inputs checks destination ownership even if the parent candidate was edited.
    B.inputs(parent)
    text=source.read_text();site=Path(parent['paths']['site_root']);slug=parent['slug']
    target.parent.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.revision-',dir=target.parent.parent) as temp:
        root=Path(temp);(root/'candidate.md').write_text(text);(root/'previous.md').write_text(old)
        child=copy.deepcopy(parent);child['paths']={k:str(target.parent/v) for k,v in {
            'source':'candidate.md','baseline':'reviews/master.baseline.json','review':'reviews/master.review.json',
            'evidence':'evidence.json','html_baseline':'reviews/html.baseline.json','html_review':'reviews/html.review.json','scripture_review':'reviews/scripture-alignment.json'}.items()}
        child['paths']['site_root']=str(site);child['builds']=[];child['ready']=None;child.pop('latest_build',None);child.pop('staged',None)
        child['initial_source_sha256']=review.digest(text)
        child['destination_snapshot']=destination_snapshot(B,child)
        if (site/(slug+'.html')).exists():child['operation']='repair';child['original_article_sha256']=B.digest(site/(slug+'.html'))
        child['parent']={'manifest':str(a.manifest.resolve()),'manifest_sha256':B.digest(a.manifest),'source_sha256':review.digest(old),'reason':a.reason}
        plan={'schema':1,'parent':child['parent'],'artifact_sha256':review.digest(text),'blocks':mapping(old,text),'approval':'none'}
        B.write(root/'revision.json',plan);B.write(root/target.name,child)
        alignment=retained_alignment(B,parent,old,text)
        if alignment is not None:B.write(root/'reviews/scripture-alignment.json',alignment)
        # Retain previous judgments as evidence, never as a current approval.
        for key in ['baseline','review']:
            p=Path(parent['paths'][key])
            if p.is_file():shutil.copy2(p,root/('previous.'+key+'.json'))
        if parent.get('evidence_recipe'):child['evidence_recipe']=copy.deepcopy(parent['evidence_recipe']);B.write(root/target.name,child)
        target.parent.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(root),str(target.parent))
    print('Revision created:',target);print('Next: preflight, evidence, reviews, and real review. Prior approvals were not copied.');return 0


def baseline(B,path,draft):
    if path.exists():
        if B.read(path)!=draft:raise ValueError('review baseline differs; create a revision instead of replacing it')
    else:B.write(path,draft)


def reviews(B,a):
    data=B.load(a.manifest);source,directory,_=B.current_build(data)
    for label,path in [('master',Path(data['paths']['source'])),('html',directory/'article.html')]:
        draft=review.inspect_file(path);bp=Path(data['paths']['baseline' if label=='master' else 'html_baseline']);rp=Path(data['paths']['review' if label=='master' else 'html_review'])
        baseline(B,bp,draft)
        if not rp.exists():
            record=review.template(draft,draft)
            historical=a.manifest.resolve().parent/'previous.review.json'
            if label=='master' and historical.is_file():
                previous=B.read(historical)
                record['council']['report']=copy.deepcopy(previous.get('council',{}).get('report',{}))
                record['council']['report'].pop('release',None)
                record['council']['historical_only']=True
            if label=='html' and (directory/'render.json').is_file():record['rendered_layout']=B.read(directory/'render.json')
            B.write(rp,record)
        elif B.read(rp).get('artifact_sha256')!=draft['artifact_sha256']:raise ValueError('review record belongs to earlier bytes; create a revision')
    print('Registered master and HTML review records ready; approvals remain pending.');return 0


def reuse(B,a):
    data=B.load(a.manifest);source,_,_=B.current_build(data);root=a.manifest.resolve().parent
    plan=B.read(root/'revision.json')
    if plan['artifact_sha256']!=review.digest(source):raise ValueError('revision plan is stale')
    confirmation=B.read(a.confirmation)
    if confirmation.get('artifact_sha256')!=review.digest(source) or confirmation.get('revision_sha256')!=B.digest(root/'revision.json') or not str(confirmation.get('reviewer','')).strip():raise ValueError('context confirmation must bind this revision and name its reviewer')
    old=Path(root/'previous.md');old_draft=review.inspect_file(old);previous=B.read(root/'previous.review.json');old_base=B.read(root/'previous.baseline.json')
    failures=review.verify(old_draft,old_base,previous,require_release=False)
    if failures:raise ValueError('prior review is not reusable under current policy: '+'; '.join(failures))
    record=B.read(data['paths']['review'])
    if record.get('artifact_sha256')!=review.digest(source) or record.get('status')!='pending':raise ValueError('reuse requires the current pending review')
    proposals={x['current_id']:x for x in plan['blocks']};old_rows={x['id']:x for x in previous['blocks']};rows={x['id']:x for x in record['blocks']}
    requested=confirmation.get('blocks')
    if not isinstance(requested,list) or not requested:raise ValueError('list explicitly inspected unchanged block IDs and contextual reasons')
    for entry in requested:
        if not isinstance(entry,dict) or len(str(entry.get('reason','')).split())<8:raise ValueError('each reused block needs a substantive context confirmation')
        key=entry.get('id');proposal=proposals.get(key,{})
        if not proposal.get('eligible_for_context_review'):raise ValueError('fresh review required for '+str(key))
        row=rows[key];prior=old_rows[proposal['previous_id']]
        if review.digest(row['text'])!=proposal['text_sha256'] or row['text']!=prior['text']:raise ValueError('reuse text mismatch')
        for field in ['decision','function','observation']:row[field]=prior[field]
        row['reuse']={'reviewer':confirmation['reviewer'],'reason':entry['reason'],'previous_review_sha256':B.digest(root/'previous.review.json'),'previous_id':prior['id']}
    # No global status, council, semantic category, cue disposition, or changed
    # block judgment is ported. The final reviewer must complete current evidence.
    B.write(data['paths']['review'],record)
    print('Confirmed unchanged block judgments reused; changed blocks and current approval remain pending.');return 0


def evidence_export(B,a):
    data=B.load(a.manifest);source,_=B.inputs(data)
    recipe=dict(data.get('evidence_recipe',{}))
    for key in ['ledger','external','claims','db']:
        value=getattr(a,key,None)
        if value:recipe[key]=str(value.resolve())
    if 'ledger' not in recipe:raise ValueError('first evidence export requires --ledger; later revisions inherit its exact path')
    recipe.setdefault('db','/home/fahmy/code/islamic/index/corpus.db')
    alignment_path=Path(data['paths'].get('scripture_review',a.manifest.parent/'reviews/scripture-alignment.json'))
    alignment=B.read(alignment_path) if alignment_path.exists() else None
    bundle=B.evidence.export(recipe['db'],source,B.read(recipe['ledger']),B.read(recipe['external']) if recipe.get('external') else None,B.read(recipe['claims']) if recipe.get('claims') else None,alignment=alignment)
    key=review.digest(json.dumps(bundle,sort_keys=True,ensure_ascii=False));path=a.manifest.resolve().parent/'evidence'/key/'sources.json'
    if path.exists():
        if B.read(path)!=bundle:raise ValueError('immutable evidence archive was altered')
    else:B.write(path,bundle)
    data['evidence_recipe']=recipe;data['paths']['evidence']=str(path)
    B.write(a.manifest,data);print('Verified current source archive:',path);return 0


def destination_paths(data):
    site=Path(data['paths']['site_root']);slug=data['slug'];base=site/'.prose-reviews'/slug
    return {'html':site/(slug+'.html'),**{key:Path(str(base)+suffix) for key,suffix in [('html_baseline','.baseline.json'),('html_review','.review.json'),('handoff','.handoff.json'),('evidence','.evidence.json')]}}


def destination_snapshot(B,data):
    return {key:B.digest(path) if path.is_file() else None for key,path in destination_paths(data).items()}


def destination_allowed(B,data):
    expected=dict(data.get('destination_snapshot',{}))
    if not expected:expected={'html':data.get('original_article_sha256')}
    allowed={key:{value} for key,value in expected.items()}
    for field in ['staging','staged']:
        ref=data.get(field)
        if not ref:continue
        path=Path(ref['path'])
        if not path.is_file() or B.digest(path)!=ref['sha256']:raise ValueError('staging journal changed; inspect the retained transaction')
        journal=B.read(path)
        for key,entry in journal['entries'].items():allowed.setdefault(key,set()).add(entry['after'])
    return allowed


def stage(B,a):
    data=B.load(a.manifest)
    root=Path(tempfile.gettempdir())/('article-build-locks-'+str(os.getuid()))
    root.mkdir(mode=0o700,exist_ok=True)
    key=review.digest(str(Path(data['paths']['site_root']).resolve())+'/'+data['slug'])
    with (root/(key+'.lock')).open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('another run is staging this article; inspect it before retrying')
        return stage_locked(B,a)


def stage_locked(B,a):
    data=B.load(a.manifest)
    # Resume only the same recorded immutable transaction. No commits or pushes.
    if data.get('staging'):
        ref=data['staging'];journal_path=Path(ref['path'])
        if B.digest(journal_path)!=ref['sha256']:raise ValueError('staging journal changed')
        journal=B.read(journal_path)
        for key,entry in journal['entries'].items():
            if B.digest(entry['source'])!=entry['after']:raise ValueError('staging source changed: '+key)
    else:
        B.verify(SimpleNamespace(manifest=a.manifest,html_baseline=None,html_review=None,evidence=None))
        data=B.load(a.manifest);ready=data['ready'];destinations=destination_paths(data)
        journal={'schema':1,'source_sha256':ready['hashes']['source'],'entries':{}}
        for key,dest in destinations.items():
            src=Path(ready['paths'][key]);journal['entries'][key]={'source':str(src),'destination':str(dest),'before':B.digest(dest) if dest.is_file() else None,'after':B.digest(src)}
        key=review.digest(json.dumps(journal,sort_keys=True))
        journal_path=a.manifest.resolve().parent/'stages'/key/'transaction.json'
        B.write(journal_path,journal)
        data['staging']={'path':str(journal_path),'sha256':B.digest(journal_path)};B.write(a.manifest,data)
    # Revalidate the whole ready bundle on resume, including the candidate and
    # policy. inputs permits only original or journalled destination bytes.
    B.verify(SimpleNamespace(manifest=a.manifest,html_baseline=None,html_review=None,evidence=None))
    for key,entry in journal['entries'].items():
        dest=Path(entry['destination']);actual=B.digest(dest) if dest.is_file() else None
        if actual not in {entry['before'],entry['after']}:raise ValueError('concurrent destination edit during staging: '+str(dest))
    for key,entry in journal['entries'].items():
        dest=Path(entry['destination']);actual=B.digest(dest) if dest.is_file() else None
        if actual==entry['after']:continue
        if actual!=entry['before']:raise ValueError('concurrent destination edit during staging: '+str(dest))
        if dest.exists():
            backup=journal_path.parent/(key+'.before');
            if not backup.exists():shutil.copy2(dest,backup)
        dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_name(dest.name+'.article-build.'+journal_path.parent.name[:12]+'.tmp')
        if temp.exists():
            if B.digest(temp)!=entry['after']:raise ValueError('interrupted stage temp bytes differ: '+str(temp))
        else:
            with temp.open('xb') as f:f.write(Path(entry['source']).read_bytes())
        if B.digest(temp)!=entry['after']:raise ValueError('staging source changed while copying: '+key)
        actual=B.digest(dest) if dest.is_file() else None
        if actual!=entry['before']:raise ValueError('concurrent destination edit before replacement: '+str(dest))
        temp.replace(dest)
    for key,entry in journal['entries'].items():
        if B.digest(entry['destination'])!=entry['after'] or B.digest(entry['source'])!=entry['after']:
            raise ValueError('staging bytes changed before completion: '+key)
    data=B.load(a.manifest);data['staged']=data.pop('staging');B.write(a.manifest,data)
    print('Exact verified artifacts staged in the registered worktree. Regenerate indexes and inspect the diff; no commit, push, or publication performed.');return 0


def status(B,a):
    data=B.load(a.manifest);result={'manifest':str(a.manifest.resolve()),'slug':data['slug'],'state':'needs-preflight','next':'preflight','errors':[]}
    try:
        source,directory,_=B.current_build(data)
        result.update(state='needs-evidence-and-reviews',next='evidence; reviews; complete actual review')
        if data.get('staging'):result.update(state='staging-interrupted',next='stage')
        elif data.get('staged'):result.update(state='staged',next='inspect Git diff and publication status')
        elif data.get('ready'):result.update(state=data['ready']['status'],next='verify' if data['ready']['status']!='prepared-for-hosted-review' else 'stage')
    except (OSError,ValueError,KeyError,TypeError) as exc:result['errors'].append(str(exc))
    print(json.dumps(result,indent=2));return 0
