#!/usr/bin/env python3
"""Snapshot the installed Titan review runtime into the controlled CI package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
FILES=['article-sources.md','native_release.py','publication_status.py','scripture_alignment.py','scripture.py','review.py','quote_layout.py','handoff.py','pre_push.py','release_runner.py','evidence.py','contract.md','drafting.md','editorial.md','council-article.md','paragraphs.md']
AUTHORING_PROSE=['translate.py','translate-style.md','article_build.py','article_revision.py','render_article.py','quotation.css','article-workflow.md','article-build.md','article-structure.md','publication.md','translation.md','test_article_build.py','test_revision_workflow.py','test_native_release.py','test_pipeline.py','test_scripture.py','test_handoff.py','test_quote_layout.py']
AUTHORING_SKILLS={'islamic-note':['SKILL.md','validate.py','references/markdown.md'],
 'faith-reason-note':['SKILL.md','template-tabs.html','template-flowing.html','references/website.md'],
 'faith-reason-research':['SKILL.md','references/article-modes.md','references/prose-translation.md','references/debate-mode.md','references/research-framework.md']}

def refresh_manifests():
    for folder,manifest in [('runtime','runtime-manifest.json'),('authoring','authoring-manifest.json')]:
        paths=[p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.md','.html','.css'} and '__pycache__' not in p.parts]
        for path in paths:
            if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
        (ROOT/manifest).write_text(json.dumps({str(p.relative_to(ROOT/folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},indent=2)+'\n')

def unchanged_package():
    for folder,manifest in [('runtime','runtime-manifest.json'),('authoring','authoring-manifest.json')]:
        for name,expected in json.loads((ROOT/manifest).read_text()).items():
            target=ROOT/folder/name
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
                raise ValueError('packaged edits would be overwritten: '+str(target)+'; edit/test the versioned bundle and use --refresh-manifests instead')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--agents-root',type=Path);p.add_argument('--refresh-manifests',action='store_true');a=p.parse_args()
    if a.refresh_manifests:
        if a.agents_root or a.check:p.error('--refresh-manifests cannot copy installed files')
        refresh_manifests();print('Refreshed versioned bundle manifests; run tests before installation.');return
    if not a.agents_root:p.error('choose an explicit --agents-root to export, or --refresh-manifests for versioned edits')
    if not a.check:unchanged_package()
    sources={n:a.agents_root/'prose'/n for n in FILES}
    sources['validate_article.py']=a.agents_root/'skills/faith-reason-note/validate.py'
    failures=[]
    for name,source in sources.items():
        target=ROOT/'runtime'/name
        if a.check:
            if source.read_bytes()!=target.read_bytes():failures.append(name)
        else:shutil.copy2(source,target)
    authoring={('prose/'+n):a.agents_root/'prose'/n for n in AUTHORING_PROSE}
    authoring.update({('skills/'+skill+'/'+n):a.agents_root/'skills'/skill/n for skill,names in AUTHORING_SKILLS.items() for n in names})
    for name,source in authoring.items():
        target=ROOT/'authoring'/name
        if a.check:
            if not target.is_file() or source.read_bytes()!=target.read_bytes():failures.append(name)
        else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    if not a.check:
        (ROOT/'authoring-manifest.json').write_text(json.dumps({n:hashlib.sha256((ROOT/'authoring'/n).read_bytes()).hexdigest() for n in authoring},indent=2)+'\n')
    if failures:raise SystemExit('Runtime differs: '+', '.join(failures))
    if not a.check:
        manifest={n:hashlib.sha256((ROOT/'runtime'/n).read_bytes()).hexdigest() for n in sources}
        (ROOT/'runtime-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
