"""One article task per worktree. Scope records are local execution state, not approval."""
import contextlib
import fcntl
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit


class ScopeConflict(ValueError):
    """Unrelated local work requires an isolated destination, not scope rebinding."""


def location(site):
    site = Path(site).resolve()
    if (site / '.git').exists():
        raw = subprocess.check_output(['git', '-C', str(site), 'rev-parse', '--absolute-git-dir'], text=True).strip()
        return Path(raw) / 'article-task.json'
    return site.parent / ('.' + site.name + '.article-task.json')


def url_slug(url):
    value = urlsplit(url)
    if value.scheme != 'https' or value.netloc != 'urspeechislight.github.io' or value.query or value.fragment:
        raise ValueError('use the exact published article URL without a query or fragment')
    path = value.path
    prefix = '/Faith-Reason-in-Islam/'
    if not path.startswith(prefix) or '/' in path[len(prefix):] or not path.endswith('.html'):
        raise ValueError('URL must identify one Faith & Reason article')
    return path[len(prefix):-5]


def git(site,*args):
    result=subprocess.run(['git','-C',str(site),*args],capture_output=True,text=True)
    if result.returncode:raise ValueError('Git worktree check failed: '+' '.join(args)+'; '+result.stderr.strip())
    return result.stdout.strip()


def comparison_base(site,recorded):
    """Exclude only upstream commits proven to descend from this task's baseline."""
    merge=subprocess.run(['git','-C',str(site),'merge-base','HEAD','refs/remotes/origin/main'],capture_output=True,text=True)
    if merge.returncode==0:
        shared=merge.stdout.strip()
        ancestor=subprocess.run(['git','-C',str(site),'merge-base','--is-ancestor',recorded,shared],capture_output=True)
        if ancestor.returncode==0:return shared
    return recorded


def revision_site(parent,site):
    """Validate a clean same-repository destination without modifying either checkout."""
    old=Path(parent['paths']['site_root']).resolve();site=Path(site).resolve()
    if not (old/'.git').exists() or not (site/'.git').exists():raise ValueError('revise --site-root requires registered Git worktrees in the same repository')
    if git(site,'rev-parse','--show-toplevel')!=str(site):raise ValueError('revision site must be the Git worktree root')
    if git(old,'rev-parse','--path-format=absolute','--git-common-dir')!=git(site,'rev-parse','--path-format=absolute','--git-common-dir'):
        raise ValueError('revision destination belongs to a different repository')
    if git(site,'status','--porcelain','--untracked-files=all'):raise ValueError('revision destination must be clean; preserve its edits and choose a fresh worktree')
    if git(site,'rev-parse','HEAD')!=git(site,'rev-parse','refs/remotes/origin/main'):
        raise ValueError('revision destination must start at fetched origin/main; create a fresh worktree there')
    scoped=dict(parent,paths=dict(parent['paths'],site_root=str(site)))
    scoped.pop('task_scope',None)
    check(scoped)
    return site


def check(data,changes=True):
    path = location(data['paths']['site_root'])
    if path.exists():
        scope = json.loads(path.read_text())
        if scope.get('slug') != data['slug']:
            raise ValueError('worktree belongs to article ' + str(scope.get('slug')) + '; this run targets ' + data['slug'] + '. Do not repair another article to unblock this task. Use its separately authorized worktree.')
        if changes and scope.get('base_commit'):
            site=str(Path(data['paths']['site_root']).resolve())
            base=comparison_base(site,scope['base_commit'])
            names=subprocess.check_output(['git','-C',site,'diff','--name-only',base],text=True).splitlines()
            names+=subprocess.check_output(['git','-C',site,'diff','--cached','--name-only',base],text=True).splitlines()
            names+=subprocess.check_output(['git','-C',site,'ls-files','--others','--exclude-standard'],text=True).splitlines()
            slug=data['slug'];allowed={slug+'.html','index.html','facts.html'} | {'.prose-reviews/'+slug+suffix for suffix in ('.baseline.json','.review.json','.handoff.json','.evidence.json')}
            outside=sorted(set(names)-allowed)
            if outside:raise ScopeConflict('worktree has changes outside article '+slug+': '+', '.join(outside[:12])+'. Preserve them; continue with revise --site-root CLEAN_WORKTREE --source CANDIDATE --output NEW_RUN/build.json --reason REASON. Do not edit scope records or unrelated files.')
    elif data.get('task_scope'):
        raise ValueError('worktree task scope is missing; inspect the task before restoring it')


def bind(B, data, requested_url=None):
    if requested_url and url_slug(requested_url) != data['slug']:
        raise ValueError('requested URL and manifest slug differ; stop the scope change')
    path = location(data['paths']['site_root'])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check(data)
        if not path.exists():
            scope={'schema': 1, 'slug': data['slug'], 'requested_url': requested_url}
            site=Path(data['paths']['site_root'])
            if (site/'.git').exists():scope['base_commit']=subprocess.check_output(['git','-C',str(site),'rev-parse','HEAD'],text=True).strip()
            B.write(path,scope)
        data['task_scope'] = {'slug': data['slug'], 'requested_url': requested_url}
        check(data)
    return data


def command(B, a):
    data = B.load(a.manifest)
    bind(B, data, a.url)
    B.write(a.manifest, data)
    print('Worktree scoped to:', data['slug'])
    return 0
