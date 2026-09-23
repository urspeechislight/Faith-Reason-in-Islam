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
        passage={'start':0,'end':12,'source':{'title':'Witness','page':1},'quote':raw[:12],'quote_sha256':evidence.sha(raw[:12]),'source_sha256':evidence.sha(raw)}
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
        fixtures=list(evaluate.fixtures());self.assertEqual(len(fixtures),3)
        for name,packet,bundle,expected in fixtures:
            self.assertEqual(bundle['artifact_sha256'],packet['artifact_sha256'])
            self.assertTrue(release_runner.review_evidence(bundle)['contexts'])
            self.assertEqual(release_runner.review_packet(packet)['candidate'],packet['candidate'])
        clean=next(row for row in fixtures if row[0]=='direct-prose')
        self.assertIn('does not assess the poets’ motives',clean[1]['candidate'])
    def test_malformed_blocked_response_cannot_pass_behavioral_test(self):
        def malformed(packet,bundle,out,client):
            out.mkdir(parents=True)
            (out/'invocation.json').write_text(json.dumps({'exit_code':0}))
            (out/'response.txt').write_text(json.dumps({'status':'blocked','open_findings':['prose:one']}))
            (out/'validation.json').write_text(json.dumps({'errors':['independent release reviewer has not cleared all findings','independent release response is stale for these council findings/dispositions']}))
            raise ValueError('invalid response')
        with tempfile.TemporaryDirectory() as directory, patch.object(sys,'argv',['evaluate','--output',directory]), patch.object(evaluate.release_runner,'run',side_effect=malformed):
            with self.assertRaisesRegex(ValueError,'Malformed rejection'):
                evaluate.main()
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
if __name__=='__main__':unittest.main()
