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
    def test_external_execution_is_disabled_even_with_a_client_argument(self):
        with patch.object(release_runner.subprocess,'run',side_effect=AssertionError('external execution forbidden')):
            with self.assertRaisesRegex(ValueError,'disabled'):release_runner.run({}, {}, 'unused',client='copilot')
    def test_gate_has_no_model_call_or_model_cli_permission(self):
        source=Path(gate.__file__).read_text();self.assertNotIn('release_runner.run(',source)
        workflow=(Path(gate.__file__).parent.parent/'.github/workflows/native-publication.yml').read_text()
        self.assertNotIn('copilot-requests',workflow);self.assertNotIn('@github/copilot',workflow);self.assertNotIn('evaluate.py --output',workflow)
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
        self.assertTrue(gate.runtime_only_paths(['.publication/runtime/scripture.py','.github/workflows/publication.yml','gen_facts_index.py']))
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
