import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import gate
import evidence
import release_runner
import json
import evaluate
from unittest.mock import patch
import tempfile

class PublicationTests(unittest.TestCase):
    def test_unmarked_html_is_still_an_article(self):
        self.assertEqual(gate.article_paths(['new.html','nested/unmarked.htm','index.html','facts.html','.publication/index-template.html']),['new.html','nested/unmarked.htm'])
    def test_corpus_export_cannot_change_quote_or_full_context(self):
        raw='source words and qualifying context';note='a candidate'
        passage={'id':'S1','start':0,'end':12,'source':{'title':'Witness','page':1},'quote':raw[:12],'quote_sha256':evidence.sha(raw[:12]),'source_sha256':evidence.sha(raw)}
        bundle={'schema':1,'artifact_sha256':evidence.sha(note),'sources':[{'id':'S1','kind':'corpus','citation':{'title':'Witness','page':1},'raw':raw,'raw_sha256':evidence.sha(raw),'passage':passage}]}
        self.assertFalse(evidence.verify(bundle,note))
        changed=copy.deepcopy(bundle);changed['sources'][0]['raw']+=' altered'
        self.assertTrue(evidence.verify(changed,note))
        changed=copy.deepcopy(bundle);changed['sources'][0]['passage']['quote']='a different quotation'
        self.assertTrue(evidence.verify(changed,note))
        self.assertTrue(evidence.verify(bundle,note+' revised'))
        changed=copy.deepcopy(bundle);changed['sources'][0]['citation']['title']='Other work'
        self.assertTrue(evidence.verify(changed,note))
    def test_joined_page_slices_require_complete_ordered_bytes(self):
        quotes=['ألف باء','جيم دال']
        self.assertEqual(evidence.covered_slices('ألف باء\n\nجيم دال',quotes),{0,1})
        for bad in ['جيم دال ألف باء','ألف باء جيم','ألف باء كلام جيم دال']:
            self.assertEqual(evidence.covered_slices(bad,quotes),set())
    def test_review_context_decodes_transport_without_summarizing(self):
        raw=json.dumps([{'verse':1,'text':'نص محفوظ'}],ensure_ascii=True)
        source={'id':'one','raw':raw,'raw_sha256':evidence.sha(raw),'citation':'Test fixture'}
        bundle={'artifact_sha256':'fixture','sources':[source,dict(source,id='two')]}
        result=release_runner.review_evidence(bundle)
        self.assertEqual(len(result['sources']),2);self.assertEqual(len(result['contexts']),1)
        self.assertEqual(next(iter(result['contexts'].values()))['content'][0]['text'],'نص محفوظ')
        parser=release_runner.SourceText();parser.feed('<html><body><p>Quoted <b>words</b>.</p><p>Qualification.</p><script>not source prose</script></body></html>')
        self.assertIn('Quoted words.', ''.join(parser.parts));self.assertIn('Qualification.', ''.join(parser.parts))
        self.assertNotIn('not source prose',''.join(parser.parts))
    def test_reuse_requires_main_or_identical_same_repository_push(self):
        run={'conclusion':'success','event':'push','head_sha':'same','head_branch':'repair','head_repository':{'full_name':'owner/site'}}
        self.assertTrue(gate.eligible_prior_run(run,'same','owner/site'))
        self.assertFalse(gate.eligible_prior_run(run,'different','owner/site'))
        self.assertFalse(gate.eligible_prior_run(dict(run,event='pull_request'),'same','owner/site'))
        self.assertFalse(gate.eligible_prior_run(run,'same','other/site'))
        self.assertTrue(gate.eligible_prior_run(dict(run,head_branch='main'),'different','owner/site'))
    def test_review_projection_retains_judgments_and_changed_historical_text(self):
        text='A full source quotation long enough to be duplicated in the candidate.'
        response={'blocks':[{'text':text,'observation':'Delete the adjacent empty framing.'},{'text':'Earlier differing claim','observation':'Attribution incorrect.'}]}
        packet={'candidate':text,'report':{'followup_reviews':[{'response':json.dumps(response)}]}}
        projected=release_runner.review_packet(packet)['report']['followup_reviews'][0]['response']
        self.assertEqual(projected['blocks'][0]['observation'],'Delete the adjacent empty framing.')
        self.assertEqual(projected['blocks'][1]['text'],'Earlier differing claim')
        self.assertIn('text',json.loads(packet['report']['followup_reviews'][0]['response'])['blocks'][0])
    def test_every_actual_provider_fixture_has_valid_projection_inputs(self):
        fixtures=list(evaluate.fixtures());self.assertEqual(len(fixtures),4)
        for name,packet,bundle,expected in fixtures:
            self.assertEqual(bundle['artifact_sha256'],packet['artifact_sha256'])
            self.assertTrue(release_runner.review_evidence(bundle)['contexts'])
            self.assertEqual(release_runner.review_packet(packet)['candidate'],packet['candidate'])
        clean=next(row for row in fixtures if row[0]=='direct-prose')
        self.assertIn('does not assess the poets’ motives',clean[1]['candidate'])
    def test_schema_retry_is_bounded_and_preserves_original_responses(self):
        import subprocess
        packet={'candidate':'Eight poets wrote elegies.','report':{'advisors':[{'role':'prose','response':'No defects.'}]},'required_disposition_ids':['prose:response']}
        packet.update(artifact_sha256=gate.review.digest(packet['candidate']),council_sha256=gate.review.council_digest(packet['report']))
        bundle={'artifact_sha256':packet['artifact_sha256'],'sources':[{'raw':'Eight poets wrote elegies.','raw_sha256':gate.review.digest('Eight poets wrote elegies.')}]}
        base={'status':'passed','open_findings':[],'artifact_sha256':packet['artifact_sha256'],'council_sha256':packet['council_sha256'],'assessment':'The complete current candidate preserves the source statement without adding any unsupported inference or framing.'}
        good=dict(base,dispositions=[{'id':'prose:response','status':'resolved','evidence':'The current candidate states the source count directly and contains no additional framing or unsupported interpretation.'}])
        short=dict(base,dispositions=[{'id':'prose:response','status':'resolved','evidence':'Direct prose.'}])
        for responses,expected,calls in [([short,good],True,2),([short,short],False,2),([dict(good,status='blocked',open_findings=['new'])],False,1),([dict(good,artifact_sha256='wrong')],False,1)]:
            with self.subTest(expected=expected,calls=calls), tempfile.TemporaryDirectory() as directory:
                sequence=iter(responses)
                def invoke(command,**kwargs):
                    kwargs['stdout'].write(json.dumps(next(sequence)));return subprocess.CompletedProcess(command,0)
                out=Path(directory)/'review'
                with patch.object(release_runner.shutil,'which',return_value='/fixture/client'),patch.object(release_runner.subprocess,'run',side_effect=invoke) as model:
                    if expected:result=release_runner.run(packet,bundle,out)
                    else:
                        with self.assertRaises(ValueError):release_runner.run(packet,bundle,out)
                self.assertEqual(model.call_count,calls)
                self.assertEqual(json.loads((out/'response.txt').read_text()),responses[0])
                if expected:
                    self.assertEqual(json.loads(result['response']),good)
                    self.assertEqual(json.loads((out/'schema-retry/response.txt').read_text()),good)
                else:self.assertFalse((out/'release.json').exists())
    def test_malformed_blocked_response_cannot_pass_behavioral_test(self):
        def malformed(packet,bundle,out,client):
            out.mkdir(parents=True)
            (out/'invocation.json').write_text(json.dumps({'exit_code':0}))
            (out/'response.txt').write_text(json.dumps({'status':'blocked','open_findings':['prose:one']}))
            (out/'validation.json').write_text(json.dumps({'errors':['independent release reviewer has not cleared all findings','independent release response is stale for these council findings/dispositions']}))
            raise ValueError('invalid response')
        with tempfile.TemporaryDirectory() as directory, patch.object(sys,'argv',['evaluate','--output',directory]), patch.object(evaluate.release_runner,'run',side_effect=malformed):
            self.assertEqual(evaluate.main(),1)
            result=json.loads((Path(directory)/'result.json').read_text())
            self.assertEqual(result['status'],'blocked')
            self.assertIn('Malformed rejection',result['error'])
    def test_hosted_validator_uses_bundled_runtime_without_personal_install(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(Path,'home',return_value=Path(directory)):
            errors=gate.validate_article.check('<html><body><main data-category="commentary"><p>A source gives a date.</p></main></body></html>')
            self.assertIsInstance(errors,list)
    def test_empty_or_unlocated_evidence_blocks(self):
        self.assertTrue(evidence.verify({'schema':1,'artifact_sha256':evidence.sha('text'),'sources':[]},'text'))
    def test_metadata_is_in_the_actual_reviewer_input(self):
        source='candidate';report={};receipt={'source_markdown':source,'source_review':{'council':{'report':report}}}
        packet=gate.packet_for(receipt,'<html><head><meta name="description" content="The conclusion is a weighed reading."></head><body><main><p>Claim.</p></main></body></html>')
        self.assertIn('The conclusion is a weighed reading.',[b['text'] for b in packet['rendered_authored_blocks']])
    def test_runtime_scope_excludes_public_and_review_changes(self):
        self.assertTrue(gate.runtime_only_paths(['.publication/runtime/scripture.py','.github/workflows/publication.yml']))
        for path in ['article.html','.prose-reviews/article.review.json','style.css','.publication/legacy.json','.publication/assets.json']:
            self.assertFalse(gate.runtime_only_paths(['.publication/gate.py',path]))
        self.assertFalse(gate.runtime_only_paths([]))
    def test_runtime_run_never_supplies_article_approval(self):
        name='Validate exact public artifacts and obtain independent decisions'
        for outcome,expected in [('skipped',False),('failure',False),('success',True)]:
            self.assertEqual(gate.completed_publication_job({'jobs':[{'conclusion':'success','steps':[{'name':name,'conclusion':outcome}]}]}),expected)
        self.assertFalse(gate.completed_publication_job({'jobs':[{'conclusion':'success','steps':[{'name':'Verify runtime-only update preserves public artifacts','conclusion':'success'}]}]}))
    def test_runtime_mode_checks_working_bytes_and_manifest(self):
        import os, subprocess
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                subprocess.run(['git','init','-q'],check=True)
                subprocess.run(['git','config','user.name','Fixture'],check=True)
                subprocess.run(['git','config','user.email','fixture@example.invalid'],check=True)
                here=Path(directory)/'.publication';(here/'runtime').mkdir(parents=True)
                (here/'runtime/check.py').write_text('pass')
                (here/'runtime-manifest.json').write_text(json.dumps({'check.py':gate.review.digest(b'pass')}))
                Path('article.html').write_text('Original article bytes')
                Path('.prose-reviews').mkdir();Path('.prose-reviews/article.review.json').write_text('{}')
                (here/'gate.py').write_text('old')
                subprocess.run(['git','add','.'],check=True);subprocess.run(['git','commit','-qm','fixture'],check=True)
                base=gate.git('rev-parse','HEAD').decode().strip();(here/'gate.py').write_text('new')
                subprocess.run(['git','add','.publication/gate.py'],check=True);subprocess.run(['git','commit','-qm','runtime fixture'],check=True)
                with patch.object(gate,'HERE',here):
                    result=gate.validate_runtime_only(base)
                    self.assertEqual(result['article_approvals'],[]);self.assertEqual(result['mode'],'runtime-only')
                    Path('article.html').write_text('Changed article')
                    with self.assertRaises(ValueError):gate.validate_runtime_only(base)
                    Path('article.html').write_text('Original article bytes')
                    Path('.prose-reviews/article.review.json').write_text('{"changed":true}')
                    with self.assertRaises(ValueError):gate.validate_runtime_only(base)
                    Path('.prose-reviews/article.review.json').write_text('{}')
                    (here/'runtime/check.py').write_text('changed')
                    with self.assertRaisesRegex(ValueError,'manifest'):gate.validate_runtime_only(base)
            finally:os.chdir(previous)
    def test_successful_runtime_run_is_skipped_during_reuse(self):
        import io, os
        runs={'workflow_runs':[{'id':1,'conclusion':'success','event':'push','head_sha':'runtime','head_branch':'main','head_repository':{'full_name':'owner/site'}},
                               {'id':2,'conclusion':'success','event':'push','head_sha':'reviewed','head_branch':'main','head_repository':{'full_name':'owner/site'}}]}
        def git(*args):return b'head' if args[0]=='rev-parse' else b'changed-policy'
        def response(request,**kwargs):
            url=request.full_url
            if '/runs?' in url:return io.BytesIO(json.dumps(runs).encode())
            outcome='skipped' if '/runs/1/' in url else 'success'
            return io.BytesIO(json.dumps({'jobs':[{'conclusion':'success','steps':[{'name':'Validate exact public artifacts and obtain independent decisions','conclusion':outcome}]}]}).encode())
        with patch.dict(os.environ,{'GITHUB_TOKEN':'fixture','GITHUB_REPOSITORY':'owner/site'}), patch.object(gate.urllib.request,'urlopen',side_effect=response), patch.object(gate,'git',side_effect=git), patch.object(gate.subprocess,'run',return_value=type('Result',(),{'returncode':0})()):
            self.assertIsNone(gate.prior_success())
            self.assertEqual(gate.prior_success(allow_older_policy=True),'reviewed')
    def test_scripture_original_needs_direct_archive_and_aligned_marks(self):
        module=gate.handoff.scripture
        note='> [!quote]- John synthetic fixture\n> <mark data-term="1">α</mark>\n>\n> *<mark data-term="1">alpha</mark>*\n>\n> <mark data-term="1">first</mark>\n'
        self.assertEqual(module.errors(note,'md'),[])
        self.assertTrue(module.errors(note.replace('*<mark data-term="1">alpha</mark>*','*alpha*'),'md'))
        self.assertTrue(module.errors(note.replace('> <mark data-term="1">α</mark>','> <mark data-term="1">α</mark>\n>\n> \u0643\u0644\u0627\u0645'),'md'))
        self.assertEqual(evidence.scripture_coverage(note,['α']),[])
        self.assertTrue(evidence.scripture_coverage(note,['\u0643\u0644\u0627\u0645']))
    def test_research_only_dispositions_are_explicit_and_reach_reviewer(self):
        ledger={'schema':2,'passages':[{'id':'source'}],'dispositions':{'source':{'use':'research-only','reason':'Comparison witness; original archived separately.'}}}
        self.assertEqual(evidence.ledger_usage(ledger),ledger['dispositions'])
        with self.assertRaises(ValueError):evidence.ledger_usage(dict(ledger,schema=1))
        bad=copy.deepcopy(ledger);bad['dispositions']['source'].pop('reason')
        with self.assertRaises(ValueError):evidence.ledger_usage(bad)
        bundle={'artifact_sha256':'fixture','sources':[],'citation_ledger_schema':2,'citation_dispositions':ledger['dispositions']}
        self.assertEqual(release_runner.review_evidence(bundle)['citation_dispositions'],ledger['dispositions'])
if __name__=='__main__':unittest.main()
