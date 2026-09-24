"""Unpublished fixtures for the maintained renderer and immutable run manifest."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import article_build as B
import handoff as H
import render_article as R
import review


def note(category='commentary',extra='',scripture=False):
    source='''---
title: A reading
category: CATEGORY
OPPONENT---

# A reading

> [!abstract]
> One witness records a journey.

## The Facts

| Claim | Actor | Date | Place | Source | Qualifier | ↗ |
|---|---|---|---|---|---|---|
| He went home | The man | Unknown | Home | Witness | reported | [[#The Evidence|Evidence]] |
| He saw a man | The man | Unknown | Home | Witness | reported | [[#The Evidence|Evidence]] |
| He met a friend | The man | Unknown | Home | Witness | reported | [[#The Evidence|Evidence]] |

## The Evidence

The man went home.

> [!info] A witness
> He went home.

EXTRA
CLOSING
'''.replace('CATEGORY',category).replace('OPPONENT','opponent: sunni\n' if category=='debate' else '')
    closing={'debate':'## Final Verdict\n\n> [!summary]\n> The witness describes one journey.','exegesis':'## The Reading\n\nThe witness describes one journey.','narration':'## Commentary\n\n### The journey\n\nThe journey took one day.','commentary':'## The journey\n\nThe journey took one day.'}[category]
    return source.replace('EXTRA',extra).replace('CLOSING',closing)


class RendererTests(unittest.TestCase):
    def render(self,source,options=None):return R.render(source,H.prepare(source),options)
    def test_all_categories_preserve_text_and_pass_structure(self):
        for cat in ('debate','exegesis','narration','commentary'):
            with self.subTest(category=cat):
                source=note(cat);page,receipt=self.render(source)
                self.assertEqual(H.verify(page,receipt),[])
                self.assertEqual(B.validator().check(page),[])
                self.assertEqual(page,self.render(source)[0])
    def test_scripture_marks_languages_and_layers(self):
        # Synthetic strings test conversion, not source provenance or translations.
        for lang,original,caption in [('grc','γυνή','Greek fixture'),('he','אשה','Hebrew fixture'),('ar','امرأة','Arabic fixture'),('la','mulier','Latin fixture')]:
            with self.subTest(language=lang):
                source=note(extra=f'> [!quote] {caption}\n> <mark data-term="1">{original}</mark>\n>\n> *<mark data-term="1">transliterated</mark>*\n>\n> A <mark data-term="1">woman</mark>.')
                page,receipt=self.render(source,{'languages':{caption:lang}})
                self.assertEqual(H.verify(page,receipt),[]);self.assertIn('lang="'+lang+'"',page)
                self.assertEqual(page.count('<mark data-term="1">'),3)
                self.assertNotIn('Van Dyck',page)
    def test_two_terms_preserve_positions(self):
        source=note(extra='> [!quote] Greek fixture\n> <mark data-term="1">γυνή</mark> <mark data-term="2">γυνή</mark>\n>\n> *<mark data-term="1">one</mark> <mark data-term="2">two</mark>*\n>\n> <mark data-term="1">woman</mark> <mark data-term="2">wife</mark>')
        page,receipt=self.render(source);self.assertEqual(H.verify(page,receipt),[])
        self.assertTrue(H.verify(page.replace('data-term="2">wife','data-term="1">wife'),receipt))
    def test_unknown_source_language_stops(self):
        source=note(extra='> [!quote] An edition\n> mulier\n>\n> *mulier*\n>\n> woman')
        with self.assertRaisesRegex(ValueError,'actual source language'):self.render(source)
    def test_latin_report_explicit_layers(self):
        source=note(extra='> [!note] Latin report\n> Testimonium.\n>\n> A testimony.')
        options={'languages':{'Latin report':'la'}}
        with self.assertRaisesRegex(ValueError,'source_paragraphs'):self.render(source,options)
        options['source_paragraphs']={'Latin report':1};page,_=self.render(source,options)
        self.assertIn('lang="la">Testimonium.',page)
    def test_soft_wraps_and_paragraphs(self):
        source=note(extra='> [!info] Witness two\n> He went\n> home.\n>\n> He met a friend.')
        page,receipt=self.render(source);self.assertEqual(H.verify(page,receipt),[])
        self.assertIn('>He went home.</p><p',page)
    def test_fact_card_mapping_accepted_and_missing_card_still_blocks(self):
        extra='### Witness\n\n- **Source:** A witness\n- **Claim:** He went home.\n\n> [!info] A witness\n> He went home.'
        page,_=self.render(note(extra=extra));self.assertFalse([e for e in B.validator().check(page) if 'fact card' in e])
        page,_=self.render(note(extra=extra.replace('- **Source:** A witness\n- **Claim:** He went home.\n\n','')))
        self.assertTrue([e for e in B.validator().check(page) if 'fact card' in e])
    def test_links_lists_tables_preserved(self):
        extra='One **strong** word, *emphasis*, and `code`.\n\n3. [First](https://example.invalid/Text_(Part))\n4. Second\n\n| Heading | Link |\n|---|---|\n| A \\| B | [[#The Evidence|Evidence]] |'
        page,receipt=self.render(note(extra=extra));self.assertEqual(H.verify(page,receipt),[])
        self.assertIn('<ol start="3">',page);self.assertIn('A | B',page)
    def test_original_numbering_never_silently_removed(self):
        page,receipt=self.render(note(extra='> [!info] Witness\n> 12. A numbered quotation.'))
        self.assertIn('12. A numbered quotation.',page);self.assertEqual(H.verify(page,receipt),[])
    def test_unsupported_syntax_stops(self):
        for extra in ('```\ncode\n```','![image](image.png)','#### Deep heading','<div>HTML</div>','> [!custom] Caption\n> Text'):
            with self.subTest(extra=extra),self.assertRaises(ValueError):self.render(note(extra=extra))
    def test_invalid_config_and_anchors_stop(self):
        with self.assertRaisesRegex(ValueError,'unknown render'):self.render(note(),{'templat':'flowing'})
        with self.assertRaisesRegex(ValueError,'absent'):self.render(note(),{'languages':{'Missing':'la'}})
        with self.assertRaisesRegex(ValueError,'unresolved'):self.render(note(extra='[[#Missing]]'))
    def test_title_anchor_is_rendered(self):
        page,_=self.render(note(extra='Return to [[#A reading|the title]].'))
        self.assertIn('id="a-reading"',page);self.assertEqual(B.validator().check(page),[])
    def test_old_html_is_never_a_template(self):
        with tempfile.TemporaryDirectory() as td:
            site=Path(td);(site/'reading.html').write_text('POISON OLD PAGE')
            source=note();page,_=R.render(source,H.prepare(source),{},site)
            self.assertNotIn('POISON',page);self.assertIn('.reading-layout',page)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'candidate.md';self.source.write_text(note())
        self.site=self.root/'site';self.site.mkdir();self.manifest=self.root/'run.json'
    def tearDown(self):self.tmp.cleanup()
    def call(self,*args):
        with contextlib.redirect_stdout(io.StringIO()):return B.main(list(map(str,args)))
    def init(self,operation='create',extra=()):return self.call('init',self.manifest,'--source',self.source,'--site-root',self.site,'--slug','reading','--operation',operation,*extra)
    def preflight(self):
        # Unit fixture skips only the browser call; browser integration is separate.
        with patch.object(B.review,'extract',return_value={'quotes':[]}):return self.call('preflight',self.manifest)
    def test_create_repair_slug_routing(self):
        self.assertEqual(self.init('repair'),1);(self.site/'reading.html').write_text('old')
        self.assertEqual(self.init(),1);self.assertEqual(self.init('repair'),0)
        self.assertEqual((self.site/'reading.html').read_text(),'old');self.assertEqual(self.init('repair'),1)
    def test_concurrent_destination_changes_block_reuse(self):
        self.init();self.preflight();(self.site/'reading.html').write_text('another article')
        self.assertEqual(self.preflight(),1)
        self.manifest.unlink();self.assertEqual(self.init('repair'),0);self.assertEqual(self.preflight(),0)
        (self.site/'reading.html').write_text('new concurrent repair');self.assertEqual(self.preflight(),1)
    def test_malformed_map_has_clean_diagnostic(self):
        config=self.root/'config.json';B.write(config,{'note_map':[]})
        self.assertEqual(self.init(extra=('--config',config)),1);self.assertFalse(self.manifest.exists())
        self.init();data=B.read(self.manifest);data['render']['note_map']=[];B.write(self.manifest,data)
        self.assertEqual(self.preflight(),1)
    def test_preflight_never_approves_or_changes_master(self):
        self.assertEqual(self.init(),0);before=self.source.read_bytes();self.assertEqual(self.preflight(),0)
        data=B.read(self.manifest);self.assertIsNone(data['ready']);self.assertEqual(before,self.source.read_bytes())
        self.assertFalse(list(self.site.iterdir()));self.assertEqual(self.call('verify',self.manifest),1)
        self.assertEqual(self.call('prepare',self.manifest),1)
    def test_cache_and_source_edit_invalidate(self):
        self.init();self.assertEqual(self.preflight(),0);first=B.read(self.manifest)['latest_build']
        self.assertEqual(self.preflight(),0);self.assertEqual(len(B.read(self.manifest)['builds']),1)
        self.source.write_text(note(extra='A later witness arrived.'));self.assertEqual(self.call('prepare',self.manifest),1)
        self.assertEqual(self.preflight(),0);self.assertNotEqual(B.read(self.manifest)['latest_build'],first)
        self.source.write_text(note());self.assertEqual(self.preflight(),0);self.assertEqual(B.read(self.manifest)['latest_build'],first)
    def test_tampered_preview_rejected(self):
        self.init();self.preflight();data=B.read(self.manifest);directory=Path(data['builds'][0]['directory']);(directory/'article.html').write_text('changed')
        self.assertEqual(self.preflight(),1);self.assertEqual(self.call('prepare',self.manifest),1)
    def test_runtime_change_invalidates_preflight(self):
        self.init();self.preflight()
        with patch.object(B,'runtime',return_value={'changed':'runtime'}):self.assertEqual(self.call('prepare',self.manifest),1)
    def test_exact_review_paths_and_pending_approval_rejected(self):
        baseline=self.root/'actual-baseline.json';record=self.root/'actual-review.json'
        self.init(extra=('--baseline',baseline,'--review',record));self.preflight()
        draft=review.inspect_file(self.source);B.write(baseline,draft);B.write(record,{'schema':review.VERSION,'status':'pending'})
        before=record.read_bytes();self.assertEqual(self.call('prepare',self.manifest),1);self.assertEqual(record.read_bytes(),before)
        self.assertIsNone(B.read(self.manifest)['ready'])
    def test_browser_failure_is_blocked_and_retry_preserves_evidence(self):
        self.init()
        with patch.object(B.quote_layout,'capture',side_effect=RuntimeError('browser unavailable')):self.assertEqual(self.call('preflight',self.manifest),1)
        first=B.read(self.manifest)['builds'][0];saved=Path(first['preflight']).read_bytes()
        self.assertEqual(self.preflight(),0);data=B.read(self.manifest)
        self.assertEqual(len(data['builds']),2);self.assertEqual(Path(first['preflight']).read_bytes(),saved)
    def test_real_master_verifier_and_final_combined_check(self):
        from test_pipeline import ReviewTests
        fixture=ReviewTests();self.init();self.preflight();data=B.read(self.manifest)
        master=review.inspect_file(self.source);record=fixture.approved(master)
        B.write(data['paths']['baseline'],master);B.write(data['paths']['review'],record)
        self.assertEqual(self.call('prepare',self.manifest),0)
        ready=B.read(self.manifest)['ready'];html=review.inspect_file(Path(ready['paths']['html']))
        B.write(data['paths']['html_baseline'],html);B.write(data['paths']['html_review'],fixture.approved(html))
        B.write(data['paths']['evidence'],{'schema':1,'artifact_sha256':review.digest(self.source.read_text()),'sources':[{'kind':'external','id':'fixture','citation':'Synthetic witness only','url':'https://example.invalid','accessed':'2026-09-23','raw':'He went home.','raw_sha256':review.digest('He went home.')}],'claims':[]})
        from test_native_release import finish_fixture
        self.assertEqual(self.call('verify',self.manifest),1)
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(finish_fixture(B,self.manifest),0)
        ready=B.read(self.manifest)['ready']
        self.assertEqual(self.call('verify',self.manifest),0)
        # A valid HTML review cannot excuse a stale embedded master approval.
        receipt=B.read(ready['paths']['handoff']);receipt['source_review']['schema']='obsolete'
        B.write(ready['paths']['handoff'],receipt)
        self.assertEqual(self.call('verify',self.manifest),1)
    def test_blocked_then_passed_retry_is_cached(self):
        self.init()
        with patch.object(B.quote_layout,'capture',side_effect=RuntimeError('browser unavailable')):self.assertEqual(self.call('preflight',self.manifest),1)
        self.assertEqual(self.preflight(),0);self.assertEqual(self.preflight(),0)
        self.assertEqual(len(B.read(self.manifest)['builds']),2)
    def test_sibling_link_missing_invalidates_cache(self):
        self.source.write_text(note(extra='[[Other]]'));other=self.site/'other.html';other.write_text('other')
        config=self.root/'config.json';B.write(config,{'note_map':{'wiki:Other':'other.html'}})
        self.init(extra=('--config',config));self.assertEqual(self.preflight(),0);other.unlink()
        self.assertEqual(self.call('prepare',self.manifest),1)

if __name__=='__main__':unittest.main()
