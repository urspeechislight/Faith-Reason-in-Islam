"""Unpublished synthetic fixtures: no historical quotation or linguistic verdict."""
import json,sys,tempfile,unittest,subprocess,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import scripture as s, handoff, translate, evidence, release_runner

HEADER='---\ncategory: commentary\n---\n\n'
def note(original='alpha',roman='alpha',english='word',caption='Synthetic scripture fixture, Latin'):
    return HEADER+f'> [!quote]- {caption}\n> {original}\n>\n> *{roman}*\n>\n> {english}\n'
def mark(word,key='1'):return f'<mark data-term="{key}">{word}</mark>'
def page(md,original='alpha',roman='alpha',english='word',lang='la'):
    receipt=handoff.prepare(md);bid=receipt['blocks'][0]['id'];caption=receipt['paragraph_layout'][bid]['caption']
    return f'<html><head><meta name="source-note-sha256" content="{receipt["source_sha256"]}"></head><body><main data-category="commentary"><blockquote class="quran-callout" data-content-role="source" data-note-block="{bid}"><p lang="{lang}">{original}</p><p class="transliteration">{roman}</p><p class="translation" lang="en">{english}</p><cite data-note-citation>{caption}</cite></blockquote></main></body></html>',receipt

class ScriptureTests(unittest.TestCase):
    def test_direct_language_jobs_and_cache_bind_language(self):
        for language,source in [('grc','α'),('he','א'),('la','verbum'),('arc','א')]:
            unit=translate.validate_job({'blocks':[{'id':'one','source':source,'source_language':language}]})[0]
            prompt=translate.build_prompt('Translate faithfully.',[unit]);self.assertIn('directly',prompt);self.assertIn('source_language',prompt)
            self.assertEqual(unit['source'],source);self.assertEqual(unit['source_language'],language);self.assertNotIn('arabic',unit)
            other=dict(unit,source_language='en')
            self.assertNotEqual(translate.fingerprint(unit,style_hash='s',model='m'),translate.fingerprint(other,style_hash='s',model='m'))
        with self.assertRaises(ValueError):translate.validate_job({'blocks':[{'id':'x','source':'x'}]})
        with self.assertRaises(ValueError):translate.validate_job({'blocks':[{'id':'x','arabic':'x','source':'x','source_language':'la'}]})
    def test_bible_language_check_covers_all_book_names(self):
        for name in ['John','Ruth','Hebrews','Ephesians','Tobit','Zephaniah']:
            md=note('\u0643\u0644\u0627\u0645','kalam','word',name+' 1:1, synthetic fixture')
            self.assertTrue(any('intermediary' in e for e in s.errors(md,'md')),name)
        with self.assertRaises(ValueError):translate.validate_job({'blocks':[{'id':'x','source':'\u0643\u0644\u0627\u0645','source_language':'grc'}]})
    def test_zero_and_one_aligned_term_round_trip(self):
        for original,roman,english in [('alpha','alpha','word'),(mark('alpha'),mark('alpha'),mark('word'))]:
            md=note(original,roman,english);html,receipt=page(md,original,roman,english)
            self.assertEqual(s.errors(md,'md'),[]);self.assertEqual(s.errors(html,'html'),[]);self.assertEqual(handoff.verify(html,receipt),[])
    def test_two_terms_can_change_order_between_languages(self):
        original=mark('alpha')+' '+mark('beta','2');english=mark('second','2')+' '+mark('first')
        md=note(original,original,english);html,receipt=page(md,original,original,english)
        self.assertEqual(s.errors(md,'md'),[]);self.assertEqual(handoff.verify(html,receipt),[])
    def test_third_term_and_extra_attributes_rejected(self):
        for bad in ['<mark data-term="3">word</mark>','<mark data-term="1" style="display:none">word</mark>']:
            self.assertTrue(s.errors(note(bad,'alpha','word'),'md'))
            html,_=page(note());self.assertTrue(s.errors(html.replace('>alpha</p>', '>'+bad+'</p>',1),'html'))
    def test_incomplete_alignment_and_phrase_emphasis_rejected(self):
        self.assertTrue(s.errors(note(mark('alpha'),'alpha',mark('word')),'md'))
        self.assertTrue(s.errors(note(mark('alpha beta'),mark('alpha'),mark('word')),'md'))
        self.assertTrue(s.errors(note(mark('alpha')+mark('beta'),mark('alpha'),mark('word')),'md'))
    def test_highlight_reassignment_or_removal_breaks_handoff(self):
        md=note(mark('alpha'),mark('alpha'),mark('word'));html,receipt=page(md,mark('alpha'),mark('alpha'),mark('word'))
        self.assertTrue(handoff.verify(html.replace(mark('word'),mark('word','2')),receipt))
        self.assertTrue(handoff.verify(html.replace(mark('word'),'word'),receipt))
    def test_mark_removal_keeps_exact_original_characters(self):
        original='ἀ γυνή';self.assertEqual(s.unmark('ἀ '+mark('γυνή')),original)
        # Synthetic Arabic fixture, not a quotation. Only checked markup is removed.
        original='\u0643\u0644\u0627\u0645';md=note(mark(original),'kalam','words',"Qur'an synthetic fixture")
        self.assertEqual(evidence.arabic_blocks(md),[original]);self.assertNotEqual(evidence.arabic_blocks(md.replace(original,original+'x')),[original])
    def test_bible_arabic_intermediary_and_missing_romanization_rejected(self):
        md=note('α\n>\n> \u0643\u0644\u0627\u0645','alpha','word','Revelation synthetic fixture')
        self.assertTrue(any('intermediary' in x for x in s.errors(md,'md')))
        md=note('α','alpha','word');html,_=page(md,'α','alpha','word','grc')
        self.assertTrue(any('transliteration' in x for x in s.errors(html.replace('<p class="transliteration">alpha</p>',''),'html')))
    def test_transliteration_requires_roman_letters(self):
        for bad in ['α','א','\u0643\u0644\u0627\u0645']:
            self.assertTrue(any('Roman' in e for e in s.errors(note('alpha',bad,'word'),'md')))
        self.assertFalse(s.errors(note('alpha','ʿāṭī','word'),'md'))
    def test_hebrew_greek_latin_do_not_need_arabic(self):
        for language,original in [('he','א'),('grc','α'),('la','alpha')]:
            md=note(original,'a','word');html,receipt=page(md,original,'a','word',language)
            self.assertFalse(s.errors(html,'html'));self.assertFalse(handoff.verify(html,receipt))
    def test_reordered_layers_nested_markup_and_orphans_rejected(self):
        md=note(mark('alpha'),mark('alpha'),mark('word'));html,receipt=page(md,mark('alpha'),mark('alpha'),mark('word'))
        self.assertTrue(s.errors(html.replace(mark('alpha'),'<mark data-term="1"><em>alpha</em></mark>',1),'html'))
        self.assertTrue(s.errors(md+'\n'+mark('orphan'),'md'))
        self.assertTrue(handoff.verify(html.replace('<main data-category="commentary">','<main data-category="commentary"><p>'+mark('orphan')+'</p>'),receipt))
        a='<p lang="la">'+mark('alpha')+'</p>';b='<p class="transliteration">'+mark('alpha')+'</p>'
        self.assertTrue(s.errors(html.replace(a+b,b+a),'html'))
        for cls in ['italic transliteration','transliteration italic']:
            self.assertTrue(s.errors('<blockquote class="hadith-callout"><p class="'+cls+'">text</p></blockquote>','html'))

    def test_archive_transport_decoding_preserves_original_words(self):
        self.assertIn('α',evidence.archived_text(json.dumps({'text':'α'},ensure_ascii=True)))
        self.assertEqual(evidence.archived_text('<p>α<span>β</span>&amp;γ</p>'),[' αβ&γ '])
        self.assertFalse(evidence.scripture_coverage(note('α','alpha','first'),evidence.archived_text(json.dumps({'text':'α'}))))
        self.assertTrue(evidence.scripture_coverage(note('β','beta','second'),evidence.archived_text(json.dumps({'text':'α'}))))

    def test_original_requires_own_archive_not_arabic_witness(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'corpus.db';con=sqlite3.connect(db)
            con.execute('CREATE TABLE pages (relpath,author,title,vol,page,raw)')
            raw='\u0643\u0644\u0627\u0645'
            con.execute('INSERT INTO pages VALUES (?,?,?,?,?,?)',('fixture','Fixture','Synthetic witness','1','1',raw));con.commit();con.close()
            entry={'id':'witness','source':dict(rowid=1,relpath='fixture',author='Fixture',title='Synthetic witness',vol='1',page='1'),
                   'source_sha256':evidence.sha(raw),'start':0,'end':len(raw),'quote':raw,'quote_sha256':evidence.sha(raw)}
            ledger={'schema':2,'passages':[entry],'dispositions':{'witness':{'use':'research-only','reason':'Synthetic comparison witness; not the original edition.'}}}
            md=note('α','alpha','first','John synthetic fixture')
            external={'id':'original','kind':'external','citation':'Synthetic Greek fixture','url':'https://example.invalid/fixture','accessed':'2026-09-23','raw':'α','raw_sha256':evidence.sha('α')}
            from test_revision_workflow import alignment
            bundle=evidence.export(db,md,ledger,[external],alignment=alignment(md))
            self.assertFalse(evidence.verify(bundle,md))
            self.assertEqual(bundle['citation_dispositions'],ledger['dispositions'])
            self.assertEqual(release_runner.review_evidence(bundle)['citation_dispositions'],ledger['dispositions'])
            with self.assertRaisesRegex(ValueError,'displayed original'):evidence.export(db,md,ledger)
            with self.assertRaisesRegex(ValueError,'displayed original'):evidence.export(db,note('β','beta','second','John synthetic fixture'),ledger,[external])
            tampered=copy.deepcopy(ledger);tampered['passages'][0]['quote']='x'
            with self.assertRaises(ValueError):evidence.export(db,md,tampered,[external])
            required=copy.deepcopy(ledger);required['dispositions']['witness']={'use':'quotation'}
            with self.assertRaisesRegex(ValueError,'missing from note'):evidence.export(db,md,required,[external])
            old=copy.deepcopy(ledger);old['schema']=1;old.pop('dispositions')
            with self.assertRaisesRegex(ValueError,'missing from note'):evidence.export(db,md,old,[external])

    def test_markup_cannot_reclassify_prose_as_scripture(self):
        self.assertTrue(s.errors('<main><p>'+mark('author claim')+'</p></main>','html'))

if __name__=='__main__':unittest.main()
