import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import gate
import evidence

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
    def test_empty_or_unlocated_evidence_blocks(self):
        self.assertTrue(evidence.verify({'schema':1,'artifact_sha256':evidence.sha('text'),'sources':[]},'text'))
    def test_metadata_is_in_the_actual_reviewer_input(self):
        source='candidate';report={};receipt={'source_markdown':source,'source_review':{'council':{'report':report}}}
        packet=gate.packet_for(receipt,'<html><head><meta name="description" content="The conclusion is a weighed reading."></head><body><main><p>Claim.</p></main></body></html>')
        self.assertIn('The conclusion is a weighed reading.',[b['text'] for b in packet['rendered_authored_blocks']])
if __name__=='__main__':unittest.main()
