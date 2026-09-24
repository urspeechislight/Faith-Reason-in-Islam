"""Adversarial publication and staging checks in disposable repository copies."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import gate
import public_files
import release_state
import stage

SOURCE=Path(__file__).resolve().parent.parent

class ReleaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='publication-forward-')
        self.root=Path(self.temp.name)
        self.repo=self.root/'repository'
        subprocess.run(['git','clone','--quiet','--shared','--no-hardlinks',str(SOURCE),str(self.repo)],check=True)
        subprocess.run(['git','-C',str(self.repo),'checkout','--quiet','--detach',release_state.MIGRATION],check=True)
        shutil.copytree(SOURCE/'.publication',self.repo/'.publication',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        self.before=Path.cwd();os.chdir(self.repo)
        self.addCleanup(self.cleanup)
        self.env=patch.dict(os.environ,{},clear=True);self.env.start()
        self.addCleanup(self.env.stop)
        self.here=patch.object(gate,'HERE',self.repo/'.publication');self.here.start();self.addCleanup(self.here.stop)

    def cleanup(self):
        os.chdir(self.before);self.temp.cleanup()

    def run_gate(self,name='check'):
        out=self.root/name
        with patch.object(sys,'argv',['gate.py','--output',str(out)]),contextlib.redirect_stdout(io.StringIO()):
            status=gate.main()
        return status,json.loads((out/'result.json').read_text()),out

    def test_full_gate_holds_unpublished_pages_at_actual_deployed_bytes(self):
        status,result,out=self.run_gate()
        self.assertEqual(status,0,result)
        held=[r for r in result['results'] if r['status']=='held-unpublished-migration']
        self.assertTrue(held,'Migration fixture must include unpublished pending pages')
        for record in held:
            name=record['path']
            self.assertEqual((out/'checked-site'/name).read_bytes(),release_state.blob(release_state.DEPLOYED,name))
            self.assertNotEqual((out/'checked-site'/name).read_bytes(),Path(name).read_bytes())
        for record in result['results']:
            if record['status']=='preserved-deployed':
                self.assertEqual((out/'checked-site'/record['path']).read_bytes(),Path(record['path']).read_bytes())
        self.assertFalse(any(r['status']=='passed' for r in result['results']))
        stage.stage(out/'result.json',self.root/'release')
        actual={str(p.relative_to(self.root/'release')):public_files.digest(p.read_bytes()) for p in (self.root/'release').rglob('*') if p.is_file() and p.name!='.nojekyll'}
        self.assertEqual(actual,result['public_files'])

    def test_new_synthetic_article_passes_full_gate_and_exact_stage(self):
        self.synthetic_article(False)

    def test_verified_conversion_passes_full_gate_and_exact_stage(self):
        self.synthetic_article(True)

    def synthetic_article(self,conversion):
        """Test-only synthetic approvals exercise schemas, never a real article decision."""
        sys.path.insert(0,str(SOURCE/'.publication/authoring/prose'))
        import render_article
        import test_article_build
        import test_native_release
        import test_pipeline
        source=test_article_build.note().replace('> [!info] A witness\n> He went home.\n','')
        master=self.root/'synthetic-candidate.md';master.write_text(source)
        baseline=gate.review.inspect_file(master)
        record=test_pipeline.ReviewTests().approved(baseline)
        record['structural_validation']['status']='passed'
        receipt=gate.handoff.prepare(source,str(master));receipt.update(source_baseline=baseline,source_review=record)
        page,receipt=render_article.render(source,receipt)
        name='synthetic-release-forward.html';Path(name).write_text(page)
        evidence={'schema':1,'artifact_sha256':gate.review.digest(source),'sources':[{'kind':'external','id':'synthetic-witness','citation':'Synthetic test fixture only','url':'https://example.invalid/test-only','accessed':'2026-09-24','raw':'He went home.','raw_sha256':gate.review.digest('He went home.')}],'claims':[]}
        evidence_raw=json.dumps(evidence)+'\n'
        report=record['council']['report']
        packet=gate.native_release.packet(source,page,evidence_raw,report,'synthetic-parent-model')
        report['release']=gate.native_release.receipt(packet,test_native_release.response(packet),'synthetic-native-child','synthetic-parent-model')
        receipt['source_review']=record
        html_baseline=gate.review.inspect_file(Path(name))
        html_review=test_pipeline.ReviewTests().approved(html_baseline)
        if conversion:
            import conversion_review as C
            capture=self.root/'visual.json';gate.quote_layout.capture(Path(name).resolve(),capture)
            render=json.loads(capture.read_text());binding=C.binding(page,receipt['source_sha256'],render)
            response=json.dumps({'request_sha256':'synthetic-intake','status':'passed','findings':[], 'record':{'binding':binding,'status':'passed','open_findings':[],
                'assessment':'Synthetic fixture only checks the exact retained converted output without making any claim about real source accuracy.',
                'checks':{k:{'status':'passed','evidence':'Synthetic fixture only: this visual property is recorded for mechanical testing of the checked conversion.'} for k in C.CHECKS}}})
            html_review=dict(C.pending(page,receipt['source_sha256'],render),status='approved',reviewer='synthetic-visual-child',response=response,
                native={'agent_id':'synthetic-visual-child','model':'synthetic-parent','parent_model':'synthetic-parent','inherited':True,'request_sha256':'synthetic-intake','response_sha256':gate.review.digest(response)})

        base=Path('.prose-reviews/synthetic-release-forward')
        for suffix,value in [('.handoff.json',receipt),('.baseline.json',html_baseline),('.review.json',html_review)]:
            Path(str(base)+suffix).write_text(json.dumps(value)+'\n')
        Path(str(base)+'.evidence.json').write_text(evidence_raw)
        subprocess.run(['git','add',name,*map(str,Path('.prose-reviews').glob('synthetic-release-forward.*'))],check=True)
        status,result,out=self.run_gate()
        self.assertEqual(status,0,result)
        fresh=[r for r in result['results'] if r['status']=='passed']
        self.assertEqual([r['path'] for r in fresh],[name])
        self.assertTrue((out/'synthetic-release-forward/render.json').is_file())
        stage.stage(out/'result.json',self.root/'release')
        self.assertEqual((self.root/'release'/name).read_bytes(),page.encode())
        self.assertEqual(public_files.digest((self.root/'release'/name).read_bytes()),result['public_files'][name])

    def test_approval_history_paginates_beyond_first_hundred_runs(self):
        """An older successful publication must remain discoverable after runtime rollouts."""
        calls=[]
        def fetch(request,**kwargs):
            url=request.full_url;calls.append(url)
            if 'publication.yml/runs?' in url and 'native-publication.yml' not in url:
                return io.BytesIO(json.dumps({'workflow_runs':[]}).encode())
            if '/runs?' in url:
                if '&page=1' in url:
                    runs=[{'id':n,'conclusion':'success','event':'push','head_sha':'runtime-'+str(n),'head_branch':'main','head_repository':{'full_name':'synthetic/site'}} for n in range(1000,1100)]
                else:runs=[{'id':1,'conclusion':'success','event':'push','head_sha':'reviewed-ancestor','head_branch':'main','head_repository':{'full_name':'synthetic/site'}}]
                return io.BytesIO(json.dumps({'workflow_runs':runs}).encode())
            passed='/runs/1/jobs?' in url
            return io.BytesIO(json.dumps({'jobs':[{'conclusion':'success','steps':[{'name':'Validate exact public artifacts and obtain independent decisions','conclusion':'success' if passed else 'skipped'}]}]}).encode())
        def fake_git(*args):return b'head' if args[0]=='rev-parse' else b''
        with patch.dict(os.environ,{'GITHUB_TOKEN':'synthetic-test-only','GITHUB_REPOSITORY':'synthetic/site'}),patch.object(gate.urllib.request,'urlopen',side_effect=fetch),patch.object(gate,'git',side_effect=fake_git),patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
            self.assertEqual(gate.prior_success(),'reviewed-ancestor')
        self.assertTrue(any('per_page=100&page=2' in u for u in calls))

    def test_changed_unreviewed_candidate_cannot_use_preservation(self):
        name='alive-with-their-lord.html';Path(name).write_text(Path(name).read_text()+'<p>Unreviewed new claim.</p>')
        status,result,_=self.run_gate()
        self.assertEqual(status,1);self.assertEqual(result['status'],'blocked');self.assertEqual(result['article'],name)

    def test_tampered_legacy_registry_cannot_approve_changed_article(self):
        name='3-42-vs-39-4.html';Path(name).write_text(Path(name).read_text()+'<p>Unreviewed new claim.</p>')
        registry=Path('.publication/legacy.json');record=json.loads(registry.read_text());record['files'][name]=public_files.digest(Path(name).read_bytes());registry.write_text(json.dumps(record))
        status,result,_=self.run_gate()
        self.assertEqual(status,1);self.assertIn('legacy registry is immutable',result['error'])

    def test_changed_pending_receipt_cannot_use_migration_preservation(self):
        name='.prose-reviews/alive-with-their-lord.review.json';record=json.loads(Path(name).read_text());record['forward_test']='unreviewed receipt change';Path(name).write_text(json.dumps(record))
        status,result,_=self.run_gate()
        self.assertEqual(status,1);self.assertEqual(result['article'],'alive-with-their-lord.html')

    def test_stage_rejects_runtime_only_result(self):
        head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        path=self.root/'runtime.json';path.write_text(json.dumps({'status':'passed','mode':'runtime-only','commit':head,'input_files':public_files.snapshot()}))
        with self.assertRaisesRegex(ValueError,'full publication'):stage.stage(path,self.root/'release')
        self.assertFalse((self.root/'release').exists())

    def test_stage_rejects_changed_checked_bytes(self):
        status,result,out=self.run_gate();self.assertEqual(status,0,result)
        target=out/'checked-site/alive-with-their-lord.html';target.write_text(target.read_text()+'<p>Injected after gate.</p>')
        with self.assertRaisesRegex(ValueError,'bytes changed'):stage.stage(out/'result.json',self.root/'release')

    def test_stage_rejects_changed_working_article(self):
        status,result,out=self.run_gate();self.assertEqual(status,0,result)
        target=Path('alive-with-their-lord.html');target.write_text(target.read_text()+'<p>Edited after gate.</p>')
        with self.assertRaisesRegex(ValueError,'public bytes changed'):stage.stage(out/'result.json',self.root/'release')

    def test_stage_rejects_extra_checked_file(self):
        status,result,out=self.run_gate();self.assertEqual(status,0,result)
        (out/'checked-site/injected.html').write_text('Unreviewed')
        with self.assertRaisesRegex(ValueError,'inventory changed'):stage.stage(out/'result.json',self.root/'release')

    def test_stage_cannot_copy_bytes_changed_after_initial_validation(self):
        status,result,out=self.run_gate();self.assertEqual(status,0,result)
        target=out/'checked-site/alive-with-their-lord.html'
        real_read=Path.read_bytes;count=0
        def changing_read(path):
            nonlocal count
            data=real_read(path)
            if path==target:
                count+=1
                if count==1:path.write_bytes(data+b'<p>Concurrent unchecked mutation.</p>')
            return data
        with patch.object(Path,'read_bytes',changing_read):
            try:stage.stage(out/'result.json',self.root/'release')
            except ValueError:return
        self.assertEqual(public_files.digest((self.root/'release/alive-with-their-lord.html').read_bytes()),result['public_files']['alive-with-their-lord.html'])

if __name__=='__main__':unittest.main()
