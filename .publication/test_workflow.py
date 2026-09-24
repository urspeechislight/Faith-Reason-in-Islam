"""CI diagnostics and exact-contract regression reuse, with no hosted model calls."""
import contextlib,datetime,io,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import regression as R
import evaluate as E
import gate as G
import publication_status as S
import install_toolchain as I

class InstallTests(unittest.TestCase):
    def test_cold_install_has_shared_aliases_and_verifies_exact_bundle(self):
        with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(I.main(['--target',td]),0);self.assertEqual(I.main(['--target',td,'--check']),0)
            for skill in ['islamic-note','faith-reason-note']:
                alias=Path(td)/'skills'/skill/'translate.py';self.assertTrue(alias.is_file());self.assertEqual(alias.resolve(),Path(td)/'prose/translate.py')
            (Path(td)/'skills/islamic-note/translate.py').unlink();self.assertEqual(I.main(['--target',td,'--check']),1)
            self.assertEqual(I.main(['--target',td]),0);self.assertEqual(I.main(['--target',td,'--check']),0)
    def test_drift_check_stops_before_overwriting_existing_tool(self):
        with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(io.StringIO()):
            root=Path(td);self.assertEqual(I.main(['--target',td]),0)
            expected=root/'expected.json';expected.write_text(json.dumps({name:I.digest(root/name) for name in I.inventory()}))
            source=root/'prose/article_build.py';source.write_text('concurrent change')
            self.assertEqual(I.main(['--target',td,'--expected',str(expected)]),1);self.assertEqual(source.read_text(),'concurrent change')

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
    def test_cached_article_report_with_wrong_commit_is_rejected(self):
        run={'head_sha':'expected','status':'completed','run_attempt':1,'html_url':'url','conclusion':'success'}
        def gh(*args):
            if '/jobs?' in args[-1]:return {'jobs':[]}
            if '/artifacts?' in args[-1]:return {'artifacts':[{'name':'article-release-1-1'}]}
            return run
        with tempfile.TemporaryDirectory() as td,patch.object(S,'gh',side_effect=gh),contextlib.redirect_stdout(io.StringIO()):
            dest=Path(td)/'1-1/article';dest.mkdir(parents=True)
            (dest/'result.json').write_text(json.dumps({'phase':'article','status':'passed','commit':'different'}))
            self.assertEqual(S.main(['--run','1','--commit','expected','--output',td]),1)

    def test_partial_download_is_not_reused(self):
        run={'head_sha':'abc','status':'completed','run_attempt':1,'html_url':'url','conclusion':'failure'}
        def gh(*args):
            if '/jobs?' in args[-1]:return {'jobs':[]}
            if '/artifacts?' in args[-1]:return {'artifacts':[{'name':'article-release-1-1'}]}
            return run
        with tempfile.TemporaryDirectory() as td,patch.object(S,'gh',side_effect=gh),patch.object(S.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['gh'])),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(S.main(['--run','1','--commit','abc','--output',td]),1);self.assertFalse((Path(td)/'1-1/article').exists())

if __name__=='__main__':unittest.main()
