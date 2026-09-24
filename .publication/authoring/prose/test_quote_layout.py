"""Tests for protected-callout review gaps observed in the deployed article."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import quote_layout as q
import review as r
import test_pipeline as fixtures

class LayoutTests(unittest.TestCase):
    def test_observed_live_wall_and_dangling_quotations(self):
        # Synthetic equivalent of the observed long paragraph and two clipped tails.
        wall='"word" "word" '+' '.join(['word']*309)+'.'
        text='<blockquote data-content-role="source"><p>'+wall+'</p><p>The witness arrived with</p><p>He spoke because</p><cite>Synthetic fixture.</cite></blockquote>'
        rows=q.extract(text,'html')
        english=[p for row in rows for p in row['paragraphs'] if p['language']!='original']
        wall=next(p for p in english if p['words']==311)
        self.assertIn('dense-paragraph',wall['cues'])
        self.assertIn('ambiguous-double-quotation-nesting',wall['cues'])
        tails=[p for p in english if 'possible-unfinished-tail' in p['cues']]
        self.assertEqual(len(tails),2)
        self.assertTrue(q.review_errors(rows,q.pending(rows)))
    def test_blank_lines_are_paragraphs_soft_wraps_are_not(self):
        rows=q.extract('> [!note]- A source\n> A speaker arrived\n> at the meeting.\n>\n> The other speaker left.\n','md')
        self.assertEqual([p['text'] for p in rows[0]['paragraphs']],['A speaker arrived at the meeting.','The other speaker left.'])
    def test_code_example_is_not_a_source_callout(self):
        self.assertEqual(q.extract('```md\n> [!note]- Example\n> Fake text.\n```','md'),[])
    def test_inline_markup_does_not_change_text_inventory(self):
        a=q.extract('<blockquote data-content-role="source"><p>A <em>real</em> statement.</p><cite>Source.</cite></blockquote>','html')
        self.assertEqual(a[0]['paragraphs'][0]['text'],'A real statement.')
        self.assertEqual(a[0]['caption'],'Source.')
    def test_structural_argument_callout_not_treated_as_quote(self):
        self.assertEqual(q.extract('<blockquote class="conclusion-card"><p>Claim.</p></blockquote>','html'),[])
    def test_quotes_stay_protected_but_require_layout_review(self):
        t=fixtures.ReviewTests();d=t.draft('<blockquote data-content-role="source"><p>The witness spoke.</p></blockquote><p>The judge listened.</p>')
        self.assertEqual(len(d['blocks']),1)
        record=t.approved(d)
        self.assertEqual(r.verify(d,d,record),[])
        record['quote_layout_review']=[]
        self.assertTrue(any('every source callout' in e for e in r.verify(d,d,record)))
    def test_density_is_a_review_trigger_not_a_word_cap(self):
        rows=q.extract('> [!note]- Source\n> '+' '.join(['word']*101),'md')
        self.assertIn('dense-paragraph',rows[0]['paragraphs'][0]['cues'])
        records=q.pending(rows);row=records[0]
        row.update(status='passed',paragraph_boundaries='Synthetic continuous definition has no separate scene or claim boundary.',speaker_and_quotation_boundaries='Synthetic statement has one speaker and no quoted dialogue inside.',source_completeness='Synthetic source starts and ends with the complete definition here.')
        row['cue_resolutions'][0].update(status='legitimate',reason='Synthetic fixture tests that density triggers review without mandatory word splitting.')
        self.assertEqual(q.review_errors(rows,records),[])
    def test_cue_cannot_be_silently_removed(self):
        rows=q.extract('> [!note]- Source\n> He wrote with','md');rec=q.pending(rows);rec[0]['cue_resolutions']=[]
        self.assertTrue(any('cues missing' in e for e in q.review_errors(rows,rec)))
    def test_changed_paragraphs_invalidate_quote_review(self):
        rows=q.extract('> [!note]- Source\n> The witness spoke.','md');rec=q.pending(rows)
        rec[0]['paragraphs'][0]['text']='A changed translation.'
        # pending creates rows referencing the paragraph data; copy actual artifact anew.
        actual=q.extract('> [!note]- Source\n> The witness spoke.','md')
        self.assertTrue(any('does not match' in e for e in q.review_errors(actual,rec)))
    def render_fixture(self):
        t=fixtures.ReviewTests();d=t.draft('<blockquote data-content-role="source"><p>First paragraph.</p><p>Second paragraph.</p></blockquote><p>Analysis.</p>')
        return d,t.approved(d)
    def test_opacity_dom_changes_and_hidden_mapping_rejected(self):
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['callouts'][0]['paragraphs'][0]['visible']=False
        self.assertTrue(any('not visibly rendered' in e for e in r.verify(d,d,rec)))
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['authored_sha256']='changed'
        self.assertTrue(any('rendered authored text differs' in e for e in r.verify(d,d,rec)))
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['hidden_blocks']=['n0001']
        self.assertTrue(any('not visibly rendered' in e for e in r.verify(d,d,rec)))
    def test_missing_browser_evidence_rejected(self):
        d,rec=self.render_fixture();rec['rendered_layout']=None
        self.assertTrue(any('measurements missing' in e for e in r.verify(d,d,rec)))
    def test_zero_margin_wall_rejected_at_either_viewport(self):
        for i in [0,1]:
            d,rec=self.render_fixture();rec['rendered_layout']['viewports'][i]['callouts'][0]['paragraphs'][1]['gap_before']=0
            self.assertTrue(any('visible paragraph spacing' in e for e in r.verify(d,d,rec)))
    def test_stale_capture_and_missing_paragraph_rejected(self):
        d,rec=self.render_fixture();rec['rendered_layout']['artifact_sha256']='old'
        self.assertTrue(any('stale' in e for e in r.verify(d,d,rec)))
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['callouts'][0]['paragraphs'].pop()
        self.assertTrue(any('coverage differs' in e for e in r.verify(d,d,rec)))
    def test_hidden_paragraph_and_mobile_overflow_rejected(self):
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['callouts'][0]['paragraphs'][0]['height']=0
        self.assertTrue(any('not visibly rendered' in e for e in r.verify(d,d,rec)))
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][1]['overflow_px']=30
        self.assertTrue(any('horizontal page overflow' in e for e in r.verify(d,d,rec)))
    def test_md_emphasis_and_literal_asterisks_match_rendered_shas(self):
        md = "> [!quote]- Test 1:1, edition\n> (باب) * (معنى) * نص\n>\n> *translit line*\n>\n> \"Translation.\"\n"
        html = "<blockquote data-content-role=source class=quran-callout><p class=rtl lang=ar>(باب) (معنى) نص</p><p class=italic transliteration>translit line</p><p class=translation>&quot;Translation.&quot;</p></blockquote>"
        a = q.extract(md, "md"); b = q.extract(html, "html")
        self.assertEqual([p["sha256"] for p in a[0]["paragraphs"]], [p["sha256"] for p in b[0]["paragraphs"]])

    def test_missing_inset_and_compressed_lines_rejected(self):
        for field,value,needle in [('inset_px',0,'inset'),('line_ratio',1.1,'line spacing'),('line_ratio',float('nan'),'line spacing')]:
            d,rec=self.render_fixture();rec['rendered_layout']['viewports'][0]['callouts'][0]['paragraphs'][0][field]=value
            self.assertTrue(any(needle in e for e in r.verify(d,d,rec)))

    def test_nan_cannot_bypass_spacing_check(self):
        d,rec=self.render_fixture();rec['rendered_layout']['viewports'][1]['callouts'][0]['paragraphs'][1]['gap_before']=float('nan')
        self.assertTrue(any('spacing' in e for e in r.verify(d,d,rec)))

if __name__=='__main__':unittest.main()
