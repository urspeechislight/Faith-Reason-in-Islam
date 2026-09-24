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

class ReviewUpgradeTests(unittest.TestCase):
    def test_previous_version_inflight_reviews_survive_the_supported_upgrade(self):
        self.upgrade(True)

    def test_legacy_empty_council_response_survives_without_new_identity_privileges(self):
        self.upgrade(False)

    def upgrade(self,seed):
        import tarfile,sys
        root=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);old=work/'old';old.mkdir()
            archive=subprocess.check_output(['git','-C',str(root),'archive','014f1ac','.publication'])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(old,filter='data')
            subprocess.run([sys.executable,str(old/'.publication/install_toolchain.py'),'--target',str(work/'old-agents')],check=True,capture_output=True)
            subprocess.run([sys.executable,str(root/'.publication/install_toolchain.py'),'--target',str(work/'new-agents')],check=True,capture_output=True)
            script=work/'old-run.py'
            script.write_text(OLD_REVIEW_RUN)
            run=subprocess.run([sys.executable,str(script),str(work),'seed' if seed else 'empty'],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            manifest=work/'run/build.json';tool=work/'new-agents/prose/article_build.py'
            if not seed:
                response=work/'master/reply.json';original=response.read_text();forged=json.loads(original)
                actor=forged['record']['council']['report']['advisors'][0]
                actor['reviewer_identity']={'session_id':'invented','agent_id':actor['reviewer']}
                response.write_text(json.dumps(forged));before=manifest.read_bytes()
                failed=subprocess.run([sys.executable,str(tool),'review-accept',str(manifest),'--request',str(work/'master/request.json'),'--response',str(response),'--agent-id','real-fixture-child','--model','fixture-parent'],capture_output=True,text=True)
                self.assertNotEqual(failed.returncode,0);self.assertEqual(manifest.read_bytes(),before)
                response.write_text(original)
            for kind in ('master','render'):
                args=['review-accept',str(manifest),'--request',str(work/kind/'request.json'),'--response',str(work/kind/'reply.json'),'--agent-id','real-fixture-child','--model','fixture-parent']
                result=subprocess.run([sys.executable,str(tool),*args],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([sys.executable,str(tool),'prepare',str(manifest)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            before=manifest.read_bytes()
            source=work/'candidate.md';source.write_text(source.read_text()+'\nA changed claim.\n')
            failed=subprocess.run([sys.executable,str(tool),'review-accept',str(manifest),'--request',str(work/'master/request.json'),'--response',str(work/'master/reply.json'),'--agent-id','real-fixture-child','--model','fixture-parent'],capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0);self.assertEqual(manifest.read_bytes(),before)


OLD_REVIEW_RUN=r'''import sys,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'old-agents/prose'))
import article_build as B
import review,review_intake as I,conversion_review as C
from test_article_build import note
from test_pipeline import ReviewTests
source=root/'candidate.md';source.write_text(note());site=root/'site';site.mkdir()
manifest=root/'run/build.json'
def call(*args):
 code=B.main([str(x) for x in args])
 if code:raise SystemExit(code)
call('init',manifest,'--source',source,'--site-root',site,'--slug','reading','--operation','create')
call('preflight',manifest);call('reviews',manifest)
data=B.read(manifest)
B.write(data['paths']['evidence'],{'schema':1,'artifact_sha256':review.digest(source.read_text()),'sources':[{'kind':'external','id':'fixture','citation':'Synthetic witness only','url':'https://example.invalid','accessed':'2026-09-24','raw':'He went home.','raw_sha256':review.digest('He went home.')}],'claims':[]})
master=ReviewTests().approved(review.inspect_file(source));master['structural_validation']['status']='passed'
pending=B.read(data['paths']['review'])
if sys.argv[2]=='seed':pending['council']['report']=master['council']['report'];B.write(data['paths']['review'],pending)
for kind in ('master','render'):
 call('review-request',manifest,'--kind',kind,'--parent-model','fixture-parent','--output',root/kind)
 request=B.read(root/kind/'request.json')
 record=master if kind=='master' else {'binding':request['binding'],'status':'passed','assessment':'Synthetic visual fixture checks exact converted material and retained geometry without granting any source or publication approval.','open_findings':[],'checks':{k:{'status':'passed','evidence':'Synthetic test only: this specific viewport property was inspected in the retained page fixture.'} for k in C.CHECKS}}
 B.write(root/kind/'reply.json',{'request_sha256':I.sha(request),'status':'passed','findings':[],'record':record})
'''

if __name__=='__main__':unittest.main()
