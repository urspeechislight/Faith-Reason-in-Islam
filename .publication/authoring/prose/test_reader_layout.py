"""Reader format round trips and hostile disclosure/label mutations."""
import copy
import re
import unittest
from pathlib import Path
import reader_layout as L
import handoff as H
import render_article as R
from test_article_build import note

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.page,self.receipt=R.render(note(),H.prepare(note()))
    def test_both_template_names_use_same_format(self):
        for name in ('tabs','flowing'):
            page,receipt=R.render(note(),H.prepare(note()),{'template':name})
            self.assertEqual(page,self.page)
            self.assertIn('data-article-format="reader-v1"',page)
            self.assertEqual(H.verify(page,receipt),[])
    def test_facts_cells_and_links_round_trip(self):
        self.assertEqual(len(L.facts(self.page)),21)
        self.assertEqual(H.verify(self.page,self.receipt),[])
        self.assertTrue(H.verify(self.page.replace('>reported</dd>','>certain</dd>',1),self.receipt))
        self.assertTrue(H.verify(self.page.replace('href="#the-evidence"','href="#facts"'),self.receipt))
    def test_fact_disclosures_cannot_hide_content(self):
        bad=[self.page.replace('data-reader-cell="1"','data-reader-cell="2"',1),
             self.page.replace('data-reader-row="1"','data-reader-row="2"',1),
             self.page.replace('<dl>','<dl>Unmapped claim',1),
             self.page.replace('<dl>','<dl><img src="hidden.png">',1),
             self.page.replace('data-reader-ui="toggle" aria-hidden="true">+','data-reader-ui="toggle" aria-hidden="true">False claim',1),
             self.page.replace('data-reader-ui="number">01','data-reader-ui="number">99',1)]
        for source in bad:
            with self.subTest(source=source[-100:]),self.assertRaises(ValueError):L.normalize(source)
    def test_shared_caption_is_visible_once_and_checked(self):
        source=note('debate').replace('> [!summary]','> [!summary] Final Verdict')
        page,receipt=R.render(source,H.prepare(source))
        self.assertIn('data-reader-caption="Final Verdict"',page)
        self.assertNotIn('<p>Final Verdict</p>',page)
        self.assertEqual(H.verify(page,receipt),[])
        normalized=L.normalize(page)
        self.assertEqual(L.normalize(normalized),normalized)
        with self.assertRaisesRegex(ValueError,'identical heading'):
            L.normalize(page.replace('data-reader-caption="Final Verdict"','data-reader-caption="Different claim"'))
    def test_generated_labels_never_exempt_authored_claims(self):
        for role in ('source','isnad','matn','chapter','contents','unknown'):
            bad=self.page.replace('The man went home.</p>',f'The man went home.</p><span data-reader-ui="{role}">Forged assertion</span>')
            with self.subTest(role=role),self.assertRaises(ValueError):L.normalize(bad)
    def test_render_requires_all_expanded_fact_cells(self):
        cells=[dict(c,visible=True) for c in L.facts(self.page)]
        record={'viewports':[{'fact_cells':cells},{'fact_cells':copy.deepcopy(cells)}]}
        self.assertEqual(L.render_errors(self.page,record),[])
        record['viewports'][1]['fact_cells'][0]['visible']=False
        self.assertTrue(L.render_errors(self.page,record))
        record['viewports'][1]['fact_cells'].pop()
        self.assertTrue(L.render_errors(self.page,record))
    def test_other_tables_stay_tables(self):
        source=note(extra='| Name | Value |\n|---|---|\n| One | Two |')
        page,_=R.render(source,H.prepare(source))
        self.assertIn('<th>Name</th>',page)
    def test_tables_carry_scroll_affordance(self):
        source=note(extra='| Name | Value |\n|---|---|\n| One | Two |')
        page,receipt=R.render(source,H.prepare(source))
        self.assertIn('<div class="table-frame"><div class="table-scroll"',page)
        self.assertEqual(H.verify(page,receipt),[])
        self.assertIn('main .table-frame.can-scroll::after',page)
        self.assertIn('@media(max-width:900px){main .table-frame:not(.scroll-known)::after{opacity:1}}',page)
        self.assertIn("querySelectorAll('main .table-frame')",page)
        self.assertIn("frame.classList.toggle('can-scroll'",page)
    def test_muted_strong_text_passes_caption_contrast(self):
        css=(Path(__file__).parent/'reader.css').read_text()
        match=re.search(r'--muted-strong:(#[0-9A-Fa-f]{6})',css)
        self.assertTrue(match)
        def luminance(color):
            channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
            channels=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in channels]
            return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]
        def ratio(fore,back):
            first,second=sorted((luminance(fore),luminance(back)),reverse=True)
            return (first+.05)/(second+.05)
        color=match.group(1)
        self.assertGreaterEqual(ratio(color,'#F3F5F7'),4.5)
        self.assertGreaterEqual(ratio(color,'#F8F1E2'),4.5)
        for selector in ('blockquote cite','.transliteration','.isnad-segment'):
            self.assertRegex(css,re.escape(selector)+r'\{[^}]*color:var\(--muted-strong\)')
    def test_table_header_passes_contrast(self):
        css=(Path(__file__).parent/'reader.css').read_text()
        rule=re.search(r'th\{[^}]*\}',css)
        self.assertTrue(rule)
        background=re.search(r'background:(#[0-9A-Fa-f]{6})',rule.group(0))
        color=re.search(r'color:(#[0-9A-Fa-f]{6})',rule.group(0))
        self.assertTrue(background and color)
        def luminance(value):
            channels=[int(value[i:i+2],16)/255 for i in (1,3,5)]
            channels=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in channels]
            return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]
        first,second=sorted((luminance(color.group(1)),luminance(background.group(1))),reverse=True)
        self.assertGreaterEqual((first+.05)/(second+.05),4.5)
    def test_contents_navigation_passes_contrast(self):
        css=(Path(__file__).parent/'reader.css').read_text()
        def luminance(value):
            channels=[int(value[i:i+2],16)/255 for i in (1,3,5)]
            channels=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in channels]
            return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]
        def ratio(fore,back):
            first,second=sorted((luminance(fore),luminance(back)),reverse=True)
            return (first+.05)/(second+.05)
        strong=re.search(r'--muted-strong:(#[0-9A-Fa-f]{6})',css).group(1)
        self.assertGreaterEqual(ratio(strong,'#F7F4EC'),4.5)
        self.assertGreaterEqual(ratio('#6F552B','#F7F4EC'),4.5)
        for selector in ('nav li a span','.mobile-contents>summary span'):
            self.assertRegex(css,re.escape(selector)+r'\{[^}]*color:var\(--muted-strong\)')
        self.assertRegex(css,r'nav li a:hover\{[^}]*color:#6F552B')
        self.assertRegex(css,r'nav li a\[aria-current=location\]\{[^}]*color:#6F552B')
    def test_original_layer_is_not_labeled_as_english_chain(self):
        source=note(extra='> [!info] Hebrew witness\n> אשה\n>\n> A narrator, from a witness:\n>\n> > He spoke.')
        page,_=R.render(source,H.prepare(source),{'languages':{'Hebrew witness':'he'}})
        self.assertNotIn('class="chain-text">אשה',page)
        self.assertIn('class="chain-text">A narrator',page)
    def test_legacy_page_is_untouched(self):
        page='<main><blockquote><p>Legacy source</p></blockquote></main>'
        self.assertEqual(L.normalize(page),page)

class BrowserTests(unittest.TestCase):
    def test_navigation_facts_fonts_and_source_groups(self):
        import tempfile
        from pathlib import Path
        from playwright.sync_api import sync_playwright
        from test_callout_speech import SOURCE
        source=note(extra=SOURCE)
        page,_=R.render(source,H.prepare(source))
        with tempfile.TemporaryDirectory() as td,sync_playwright() as pw:
            path=Path(td)/'reading.html';path.write_text(page)
            browser=pw.chromium.launch()
            for width in (1280,390):
                tab=browser.new_page(viewport={'width':width,'height':900})
                tab.goto(path.as_uri());tab.evaluate('document.fonts.ready')
                self.assertFalse(tab.evaluate('document.documentElement.scrollWidth>innerWidth'))
                self.assertEqual(tab.locator('body').evaluate('(e)=>getComputedStyle(e).backgroundColor'),'rgb(253, 251, 247)')
                self.assertIn('Literata',tab.locator('h1').evaluate('(e)=>getComputedStyle(e).fontFamily'))
                self.assertEqual(tab.locator('[data-reader-back]').first.get_attribute('href'),'index.html')
                fact=tab.locator('details.evidence').first
                fact.locator('summary').click();self.assertTrue(fact.get_attribute('open') is not None)
                self.assertTrue(fact.locator('[data-reader-cell="5"]').is_visible())
                self.assertEqual(tab.locator('.source-matn p').count(),4)
                chain=tab.locator('.isnad-segment').first
                self.assertNotEqual(chain.evaluate('(e)=>getComputedStyle(e).borderBottomStyle'),'none')
                if width==390:
                    menu=tab.locator('.mobile-contents');menu.locator('summary').click()
                    menu.locator('a').last.click();self.assertIsNone(menu.get_attribute('open'))
                tab.evaluate("document.querySelector('details.evidence').open=false; document.querySelector('[data-reader-cell=\"5\"]').id='fact-detail'; location.hash='fact-detail'")
                tab.wait_for_function("document.querySelector('details.evidence').open")
                tab.evaluate("document.querySelectorAll('details').forEach(e=>e.open=false)")
                tab.emulate_media(media='print')
                self.assertTrue(tab.locator('.evidence-body').first.is_visible())
                tab.close()
            tab=browser.new_page()
            tab.route('https://reader.test/**',lambda route:route.fulfill(body=page,content_type='text/html'))
            tab.goto('https://reader.test/article',referer='https://reader.test/previous')
            self.assertEqual(tab.locator('[data-reader-back]').first.get_attribute('href'),'https://reader.test/previous')
            tab.close();tab=browser.new_page()
            tab.route('https://reader.test/**',lambda route:route.fulfill(body=page,content_type='text/html'))
            tab.goto('https://reader.test/article#%ZZ',referer='https://reader.test/article')
            self.assertEqual(tab.locator('[data-reader-back]').first.get_attribute('href'),'index.html')
            browser.close()

if __name__=='__main__':unittest.main()
