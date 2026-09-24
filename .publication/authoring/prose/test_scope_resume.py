"""Published repair resumption across upstream changes and occupied worktrees."""
import contextlib,io,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import article_build as B
import article_scope as S
from test_article_build import note

class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.site=self.root/'site';self.site.mkdir()
        self.git('init','-b','main');self.git('config','user.name','Synthetic fixture');self.git('config','user.email','fixture@example.invalid')
        (self.site/'reading.html').write_text('Previous published fixture')
        self.git('add','.');self.git('commit','-m','Initial publication')
        self.git('update-ref','refs/remotes/origin/main','HEAD')
        self.source=self.root/'candidate.md';self.source.write_text(note())
        self.manifest=self.root/'run/build.json'
        self.assertEqual(self.call('init',self.manifest,'--source',self.source,'--site-root',self.site,'--slug','reading','--operation','repair','--url','https://urspeechislight.github.io/Faith-Reason-in-Islam/reading.html'),0)
    def tearDown(self):self.tmp.cleanup()
    def git(self,*args,site=None):
        return subprocess.check_output(['git','-C',str(site or self.site),*args],stderr=subprocess.DEVNULL,text=True).strip()
    def call(self,*args):
        with contextlib.redirect_stdout(io.StringIO()):return B.main([str(a) for a in args])
    def upstream(self):
        (self.site/'workflow.txt').write_text('Merged shared format change')
        self.git('add','workflow.txt');self.git('commit','-m','Upstream workflow')
        self.git('update-ref','refs/remotes/origin/main','HEAD')
    def test_merged_upstream_is_not_a_local_scope_violation(self):
        scope=S.location(self.site);before=scope.read_bytes();manifest=self.manifest.read_bytes()
        self.upstream();S.check(B.read(self.manifest))
        self.assertEqual(scope.read_bytes(),before);self.assertEqual(self.manifest.read_bytes(),manifest)
        (self.site/'reading.html').write_text('Authorized article edit');S.check(B.read(self.manifest))
    def test_upstream_does_not_hide_any_local_unrelated_edit(self):
        self.upstream()
        for mode in ('untracked','unstaged','staged','committed'):
            with self.subTest(mode=mode):
                name='new.txt' if mode=='untracked' else 'workflow.txt';path=self.site/name;path.write_text('Unrelated local work')
                if mode in ('staged','committed'):self.git('add',name)
                if mode=='committed':self.git('commit','-m','Unmerged local runtime change')
                with self.assertRaisesRegex(ValueError,'outside article'):S.check(B.read(self.manifest))
                self.assertEqual(path.read_text(),'Unrelated local work')
                if mode=='untracked':path.unlink()
                else:self.git('reset','--hard','refs/remotes/origin/main')
    def test_staged_edit_cannot_hide_behind_restored_worktree_bytes(self):
        self.upstream();path=self.site/'workflow.txt';original=path.read_text()
        path.write_text('Staged other-session work');self.git('add','workflow.txt');path.write_text(original)
        index=self.git('show',':workflow.txt')
        with self.assertRaisesRegex(ValueError,'outside article'):S.check(B.read(self.manifest))
        self.assertEqual(self.git('show',':workflow.txt'),index);self.assertEqual(path.read_text(),original)
    def test_other_article_scope_is_still_rejected(self):
        self.upstream();data=B.read(self.manifest);data['slug']='another'
        with self.assertRaisesRegex(ValueError,'belongs to article'):S.check(data)
    def test_new_format_reports_revision_even_for_a_staged_run(self):
        self.assertEqual(self.call('preflight',self.manifest),0)
        data=B.read(self.manifest);journal=self.root/'staged.json';B.write(journal,{'entries':{}})
        data['staged']={'path':str(journal),'sha256':B.digest(journal)};B.write(self.manifest,data)
        binding=B.inputs(B.read(self.manifest))[1];binding=dict(binding,year=binding['year']+1)
        output=io.StringIO();before=self.manifest.read_bytes()
        with patch.object(B,'inputs',return_value=(self.source.read_text(),binding)),contextlib.redirect_stdout(output):
            self.assertEqual(B.main(['status',str(self.manifest)]),0)
        state=json.loads(output.getvalue());self.assertEqual(state['state'],'needs-revision');self.assertFalse(state['format_current'])
        self.assertEqual(self.manifest.read_bytes(),before)
    def fresh(self):
        fresh=self.root/'fresh';self.git('worktree','add','-b','next',str(fresh),'refs/remotes/origin/main');return fresh
    def test_revision_moves_to_clean_worktree_preserving_busy_parent(self):
        self.assertEqual(self.call('preflight',self.manifest),0)
        self.upstream();fresh=self.fresh();(self.site/'workflow.txt').write_text('Other session still editing')
        before=self.manifest.read_bytes();scope=S.location(self.site).read_bytes()
        child=self.root/'next/build.json'
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--site-root',fresh,'--output',child,'--reason','Current reader format'),0)
        data=B.read(child);self.assertEqual(data['paths']['site_root'],str(fresh));self.assertIsNone(data['ready']);self.assertEqual(data['builds'],[])
        self.assertEqual(self.manifest.read_bytes(),before);self.assertEqual(S.location(self.site).read_bytes(),scope)
        self.assertEqual((self.site/'workflow.txt').read_text(),'Other session still editing')
        self.assertEqual(json.loads(S.location(fresh).read_text())['slug'],'reading')
        self.assertEqual((fresh/'reading.html').read_text(),'Previous published fixture')
        self.assertEqual(self.call('preflight',child),0)
    def test_staged_publication_then_renderer_update_and_busy_worktree(self):
        import review
        from test_pipeline import ReviewTests
        from test_native_release import finish_fixture
        self.assertEqual(self.call('preflight',self.manifest),0);data=B.read(self.manifest)
        fixture=ReviewTests();master=review.inspect_file(self.source)
        B.write(data['paths']['baseline'],master);B.write(data['paths']['review'],fixture.approved(master))
        self.assertEqual(self.call('prepare',self.manifest),0)
        ready=B.read(self.manifest)['ready'];html=review.inspect_file(Path(ready['paths']['html']))
        B.write(data['paths']['html_baseline'],html);B.write(data['paths']['html_review'],fixture.approved(html))
        B.write(data['paths']['evidence'],{'schema':1,'artifact_sha256':review.digest(self.source.read_text()),'sources':[{'kind':'external','id':'fixture','citation':'Synthetic witness only','url':'https://example.invalid','accessed':'2026-09-24','raw':'He went home.','raw_sha256':review.digest('He went home.')}],'claims':[]})
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(finish_fixture(B,self.manifest),0)
        self.assertEqual(self.call('stage',self.manifest),0)
        self.git('add','reading.html','.prose-reviews');self.git('commit','-m','Publish synthetic five-artifact bundle')
        self.upstream();fresh=self.fresh()
        before=self.manifest.read_bytes();data=B.read(self.manifest)
        published=B.article_revision.destination_snapshot(B,data)
        self.assertEqual(len(published),5);self.assertTrue(all(published.values()))
        runtime=B.render_runtime();runtime=dict(runtime,**{'synthetic-renderer-version':'updated'})
        with patch.object(B,'render_runtime',return_value=runtime):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):self.assertEqual(B.main(['status',str(self.manifest)]),0)
            self.assertEqual(json.loads(out.getvalue())['state'],'needs-revision')
            (self.site/'workflow.txt').write_text('Concurrent unrelated edits')
            child=self.root/'combined/build.json'
            self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--site-root',fresh,'--output',child,'--reason','Renderer upgrade'),0)
            self.assertEqual(self.call('preflight',child),0)
        new=B.read(child);self.assertIsNone(new['ready']);self.assertNotIn('staged',new)
        self.assertEqual(new['destination_snapshot'],published);self.assertEqual(self.manifest.read_bytes(),before)
        self.assertEqual((child.parent/'previous.review.json').read_bytes(),Path(data['paths']['review']).read_bytes())
        self.assertEqual((self.site/'workflow.txt').read_text(),'Concurrent unrelated edits')

    def test_revision_cannot_take_dirty_wrong_repository_or_other_article(self):
        self.assertEqual(self.call('preflight',self.manifest),0);fresh=self.fresh()
        before=self.manifest.read_bytes()
        def attempt(label):
            child=self.root/(label+'/build.json')
            self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--site-root',fresh,'--output',child,'--reason','Fixture'),1)
            self.assertFalse(child.exists());self.assertEqual(self.manifest.read_bytes(),before)
        (fresh/'unrelated.txt').write_text('Busy');attempt('dirty');(fresh/'unrelated.txt').unlink()
        S.location(fresh).write_text(json.dumps({'schema':1,'slug':'other','base_commit':self.git('rev-parse','HEAD',site=fresh)}));attempt('wrong-slug');S.location(fresh).unlink()
        (fresh/'reading.html').write_text('Concurrent article revision');self.git('add','reading.html',site=fresh);self.git('commit','-m','New article',site=fresh)
        attempt('unmerged')
        self.git('update-ref','refs/remotes/origin/main','HEAD',site=fresh);attempt('changed-target')
        other=self.root/'other-repo';other.mkdir();self.git('init','-b','main',site=other)
        with self.assertRaisesRegex(ValueError,'different repository'):S.revision_site(B.read(self.manifest),other)
    def test_missing_upstream_is_a_controlled_diagnostic(self):
        self.assertEqual(self.call('preflight',self.manifest),0);fresh=self.fresh()
        self.git('update-ref','-d','refs/remotes/origin/main')
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--site-root',fresh,'--output',self.root/'missing-upstream/build.json','--reason','Fixture'),1)
        self.assertFalse((self.root/'missing-upstream').exists())
    def test_missing_build_history_returns_structured_failure(self):
        data=B.read(self.manifest);data['latest_build']='missing';B.write(self.manifest,data);out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(B.main(['status',str(self.manifest)]),1)
        state=json.loads(out.getvalue());self.assertEqual(state['state'],'blocked');self.assertIn('absent from build history',state['errors'][0])

    def test_status_scope_failure_explains_supported_recovery(self):
        (self.site/'unrelated.txt').write_text('Busy');out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(B.main(['status',str(self.manifest)]),1)
        state=json.loads(out.getvalue());self.assertIn('--site-root',state['next']);self.assertFalse(state['format_current'])

if __name__=='__main__':unittest.main()
