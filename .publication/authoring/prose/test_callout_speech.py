"""Preserve explicit speech boundaries without spreading source callouts out."""
import copy
from pathlib import Path
import tempfile
import unittest
import callout_structure as C
import handoff as H
import quote_layout as Q
import render_article as R
from test_article_build import note

SOURCE = "> [!note] Synthetic witness\n> The compiler, from a witness, who reported the following.\n>\n> > The witness entered the room.\n> >\n> > The judge said, “Read the document aloud.”\n> >\n> > The witness asked, “Shall I read the whole document?”\n> >\n> > The narrator recorded the answer."


class SpeechTests(unittest.TestCase):
    def render(self,extra=SOURCE):
        source=note(extra=extra)
        page,receipt=R.render(source,H.prepare(source))
        return source,page,receipt

    def test_file_path_loading_needs_no_global_pythonpath(self):
        import subprocess,sys
        for module in (Q,H):
            code="import importlib.util; s=importlib.util.spec_from_file_location('isolated',"+repr(module.__file__)+"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.callout_structure.paragraphs(['> > Speech.'])[0]['depth']==1"
            result=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_text_and_hierarchy_roundtrip(self):
        source,page,receipt=self.render()
        self.assertEqual(H.verify(page,receipt),[])
        self.assertEqual(Q.extract(source,'md'),[{k:v for k,v in q.items() if k!='layout_profile'} for q in Q.extract(page,'html')])
        row=Q.extract(page,'html')[-1]
        self.assertEqual([p['quote_depth'] for p in row['paragraphs']],[0,1,1,1,1])
        self.assertEqual(page.count('data-quote-role="matn"'),1)

    def test_stripping_nesting_rejected_without_changing_words(self):
        source,page,receipt=self.render()
        page=page.replace('class="source-matn" data-quote-role="matn"','class="plain"')
        with self.assertRaisesRegex(ValueError,'invalid generated reader label'):H.verify(page,receipt)

    def test_isnad_cannot_be_indented_with_matn(self):
        source,page,receipt=self.render()
        tree=H.reader_layout.Tree(page)
        paragraph=next(n for n in tree.nodes if n.tag=='p' and 'The compiler' in n.text())
        page=page[:paragraph.start]+'<blockquote class="source-matn" data-quote-role="matn">'+page[paragraph.start:paragraph.end]+'</blockquote>'+page[paragraph.end:]
        self.assertTrue(any('hierarchy' in e for e in H.verify(page,receipt)))

    def test_legacy_speech_role_still_preserves_recorded_boundaries(self):
        source,page,receipt=self.render()
        page=page.replace('source-matn','source-speech').replace('data-quote-role="matn"','data-quote-role="speech"')
        self.assertEqual(H.verify(page,receipt),[])

    def test_narration_cannot_escape_matn_after_dialogue(self):
        source,page,receipt=self.render()
        page=page.replace('<p class="translation" lang="en">The narrator recorded the answer.</p></blockquote>','</blockquote><p class="translation" lang="en">The narrator recorded the answer.</p>')
        self.assertTrue(any('hierarchy' in e for e in H.verify(page,receipt)))

    def test_soft_wraps_and_single_extra_level(self):
        self.assertEqual(C.paragraphs(['> > One','> > speech.']),[{'text':'One speech.','depth':1}])
        for lines in (['> Narrator','> > Speech'],['> > > Speech']):
            with self.assertRaises(ValueError):C.paragraphs(lines)

    def test_long_isnad_stops_before_review(self):
        chain='3 - Ali ibn Ibrahim, from his father, from Uthman ibn Isa, from Samaah, from Abu Abd Allah, who said, "I heard him say a complete statement."'
        with self.assertRaisesRegex(ValueError,'separate the long isnad'):
            self.render('> [!note] Synthetic chain\n> '+chain)
        self.assertFalse(C.mixed_chain('The judge said, “Read it.”'))
        self.assertFalse(C.mixed_chain('The word “woman” occurs here.'))

    def test_unquoted_narrative_matn_needs_its_own_inset(self):
        chain='A transmitter, from the first, from the second, from the third, who said,'
        body='The witness entered the room and read the document.'
        with self.assertRaisesRegex(ValueError,'every matn paragraph'):
            self.render('> [!note] Fixture\n> '+chain+'\n>\n> '+body)
        source,page,receipt=self.render('> [!note] Fixture\n> '+chain+'\n>\n> > '+body)
        self.assertEqual(H.verify(page,receipt),[])
        self.assertFalse(any('isnad-matn-layout' in p['cues'] for q in Q.extract(source,'md') for p in q['paragraphs']))
        wrong=source.replace('> > '+body,'> '+body)
        self.assertTrue(any('isnad-matn-layout' in p['cues'] for q in Q.extract(wrong,'md') for p in q['paragraphs']))

    def test_rtl_speech_changes_direction_before_english(self):
        source,page,receipt=self.render('> [!note] Synthetic RTL\n> > نص المصدر\n>\n> > A translated speech.')
        self.assertIn('data-quote-role="matn" dir="rtl"',page)
        self.assertIn('data-quote-role="matn" dir="ltr"',page)
        self.assertEqual(H.verify(page,receipt),[])
        self.assertEqual(Q.extract(source,'md'),[{k:v for k,v in q.items() if k!='layout_profile'} for q in Q.extract(page,'html')])

    def test_legacy_callout_has_no_new_depth_fields(self):
        source,page,receipt=self.render('> [!note] Synthetic legacy\n> A complete statement.')
        self.assertNotIn('quote_depths',list(receipt['paragraph_layout'].values())[-1])
        self.assertNotIn('quote_depth',Q.extract(page,'html')[-1]['paragraphs'][0])
        self.assertEqual(H.verify(page,receipt),[])

    def test_nested_scripture_preserves_three_layers(self):
        source,page,receipt=self.render('> [!quote] Greek fixture\n> > γυνή\n>\n> *gyne*\n>\n> > woman')
        self.assertEqual(H.verify(page,receipt),[])
        self.assertEqual(Q.extract(source,'md'),[{k:v for k,v in q.items() if k!='layout_profile'} for q in Q.extract(page,'html')])

    def test_fact_card_counts_outer_source_only(self):
        import article_build as B
        extra='### A witness\n\n- **Source:** Synthetic witness\n- **Claim:** The witness read.\n\n'+SOURCE
        source,page,receipt=self.render(extra)
        self.assertEqual(B.validator().check(page),[])
        page=page.replace('<div class="premise-card space-y-1 mb-4"','<div class="ordinary"')
        self.assertTrue(any('fact card' in e for e in B.validator().check(page)))

    def test_source_narration_after_speech_keeps_protected_punctuation(self):
        import article_build as B
        source,page,receipt=self.render(SOURCE.replace('The narrator recorded the answer.','The narrator recorded the answer: yes.'))
        self.assertFalse(any('colon' in e for e in B.validator().check(page)))

    def test_arabic_archive_ignores_layout_markers_only(self):
        import evidence
        self.assertEqual(evidence.arabic_blocks('> [!note] Fixture\n> نص\n>\n> > المصدر'),['نص\nالمصدر'])

    def test_compact_measurement_checks(self):
        import test_pipeline
        source,page,receipt=self.render()
        quotes=Q.extract(page,'html')
        for q in quotes:q.pop('layout_profile',None)
        draft=test_pipeline.ReviewTests().draft(page)
        draft['quotes']=quotes
        record=test_pipeline.ReviewTests().approved(draft)['rendered_layout']
        for view in record['viewports']:
            for row,q in zip(view['callouts'],quotes):
                for p,item in zip(q['paragraphs'],row['paragraphs']):
                    item.update(quote_depth=p.get('quote_depth',0),speech_inset_px=13)
                    if 'quote_depth' in p:item['gap_before']=6
        self.assertEqual(Q.render_errors(quotes,record,draft['artifact_sha256']),[])
        for field,value,needle in [('speech_inset_px',0,'speech inset'),('speech_inset_px',40,'speech inset'),('gap_before',30,'too loose'),('gap_before',0,'spacing'),('quote_depth',0,'depth')]:
            changed=copy.deepcopy(record)
            changed['viewports'][1]['callouts'][-1]['paragraphs'][1][field]=value
            self.assertTrue(any(needle in e for e in Q.render_errors(quotes,changed,draft['artifact_sha256'])),field)

if __name__=='__main__':unittest.main()
