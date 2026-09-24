"""CI diagnostics and exact-contract regression reuse, with no hosted model calls."""
import contextlib,datetime,io,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import regression as R
import evaluate as E
import gate as G
import publication_status as S

class RegressionTests(unittest.TestCase):
    def run_fixture(self):
        return {'id':12,'head_sha':'abc','conclusion':'success','event':'push','head_branch':'main','head_repository':{'full_name':'owner/repo'},'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'html_url':'https://example.invalid/run'}
    def test_receipt_requires_recent_successful_main_same_repo(self):
        run=self.run_fixture();now=datetime.datetime.now(datetime.timezone.utc);self.assertTrue(R.eligible(run,'owner/repo',now))
        for changes in [{'event':'pull_request'},{'head_branch':'topic'},{'conclusion':'failure'},{'head_repository':{'full_name':'fork/repo'}},{'updated_at':(now-datetime.timedelta(hours=25)).isoformat()},{'updated_at':(now+datetime.timedelta(hours=1)).isoformat()}]:self.assertFalse(R.eligible(dict(run,**changes),'owner/repo',now))
    def receipt(self,fingerprint=None,step='success',ancestor=0,error=None):
        run=self.run_fixture()
        def api(path):
            if error:raise error
            return {'workflow_runs':[run]} if '/workflows/' in path else {'jobs':[{'conclusion':'success','steps':[{'name':R.STEP,'conclusion':step}]}]}
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'owner/repo','GITHUB_TOKEN':'synthetic','GITHUB_EVENT_NAME':'push'}),patch.object(R,'api',side_effect=api),patch.object(R,'fingerprint',side_effect=fingerprint or (lambda *a:'same')),patch.object(R.subprocess,'run',return_value=subprocess.CompletedProcess([],ancestor)):
            return R.find_receipt()
    def test_only_exact_contract_and_actual_regression_step_reuse(self):
        self.assertEqual(self.receipt()['run_id'],12)
        self.assertIsNone(self.receipt(fingerprint=lambda *a:'old' if a else 'new'))
        self.assertIsNone(self.receipt(step='skipped'));self.assertIsNone(self.receipt(ancestor=1));self.assertIsNone(self.receipt(error=OSError('outage')))
    def test_runtime_scope_never_includes_articles_or_receipts(self):
        self.assertTrue(G.runtime_only_paths(['.publication/authoring/prose/article_build.py','.publication/regression.py']))
        self.assertFalse(G.runtime_only_paths(['article.html']));self.assertFalse(G.runtime_only_paths(['.prose-reviews/article.review.json']))
    def test_regression_failures_have_typed_result_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as td,patch.object(E,'evaluate',side_effect=ValueError('malformed reviewer response')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(E.main(['--output',td]),1);result=json.loads((Path(td)/'result.json').read_text());self.assertEqual(result['phase'],'regression');self.assertEqual(result['status'],'blocked')

class StatusTests(unittest.TestCase):
    def test_wrong_commit_stops_before_artifact_download(self):
        with tempfile.TemporaryDirectory() as td,patch.object(S,'gh',return_value={'head_sha':'wrong'}),patch.object(S.subprocess,'run') as download,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(S.main(['--run','1','--commit','expected','--output',td]),1);download.assert_not_called()
    def test_named_artifacts_separate_regression_and_article(self):
        run={'head_sha':'abc','status':'completed','run_attempt':2,'html_url':'url','conclusion':'failure'}
        def gh(*args):
            path=args[-1]
            if '/jobs?' in path:return {'jobs':[{'name':'gate','steps':[{'name':'article review','conclusion':'failure'}]}]}
            if '/artifacts?' in path:return {'artifacts':[{'name':'article-release-1-2'},{'name':'reviewer-regression-1-2'},{'name':'article-release-1-1'}]}
            return run
        names=[]
        def download(args,**kwargs):
            name=args[args.index('--name')+1];names.append(name);dest=Path(args[-1]);phase='article' if name.startswith('article-') else 'regression'
            (dest/'result.json').write_text(json.dumps({'phase':phase,'status':'blocked' if phase=='article' else 'passed'}))
            return subprocess.CompletedProcess(args,0)
        with tempfile.TemporaryDirectory() as td,patch.object(S,'gh',side_effect=gh),patch.object(S.subprocess,'run',side_effect=download),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(S.main(['--run','1','--commit','abc','--output',td]),1)
            result=json.loads((Path(td)/'status.json').read_text());self.assertEqual(result['article']['result']['status'],'blocked');self.assertEqual(result['regression']['result']['status'],'passed')
            self.assertEqual(set(names),{'article-release-1-2','reviewer-regression-1-2'})
    def test_partial_download_is_not_reused(self):
        run={'head_sha':'abc','status':'completed','run_attempt':1,'html_url':'url','conclusion':'failure'}
        def gh(*args):
            if '/jobs?' in args[-1]:return {'jobs':[]}
            if '/artifacts?' in args[-1]:return {'artifacts':[{'name':'article-release-1-1'}]}
            return run
        with tempfile.TemporaryDirectory() as td,patch.object(S,'gh',side_effect=gh),patch.object(S.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['gh'])),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(S.main(['--run','1','--commit','abc','--output',td]),1);self.assertFalse((Path(td)/'1-1/article').exists())

if __name__=='__main__':unittest.main()
