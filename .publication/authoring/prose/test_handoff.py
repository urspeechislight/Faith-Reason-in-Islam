import copy
import html
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import handoff as h

NOTE='''---
title: A Source Question
category: commentary
---
# A Source Question

Some reports suggest a qualification.

> [!note]- Source, vol. 1, p. 2
> نص المصدر
>
> The source preserves this uncertainty.

| Claim | Qualifier |
|---|---|
| An attribution | uncertain |

See [the source](https://example.invalid/source) and **its context**.
'''
def render(receipt):
    chunks=''
    for b in receipt['blocks']:
        layout=receipt.get('paragraph_layout',{}).get(b['id'])
        if layout:
            chunks+='<blockquote data-content-role="source" data-note-block="'+b['id']+'">'+''.join('<p>'+html.escape(t)+'</p>' for t in layout['paragraphs'])+'<cite data-note-citation="">'+html.escape(layout['caption'])+'</cite></blockquote>'
        else:chunks+='<section data-note-block="'+b['id']+'"><p>'+html.escape(b['text'])+'</p></section>'
    chunks=chunks.replace('the source and its context.', '<a href="https://example.invalid/source">the source</a> and its context.')
    return '<html><head><meta name="source-note-sha256" content="'+receipt['source_sha256']+'"></head><body><main data-category="commentary">'+chunks+'</main></body></html>'

class Tests(unittest.TestCase):
    def setUp(self):self.r=h.prepare(NOTE);self.page=render(self.r)
    def test_formatting_preserves_meaning(self):
        p=self.page.replace('Some reports','<strong>Some</strong> reports')
        self.assertEqual(h.verify(p,self.r),[])
    def test_caption_can_move_to_cite(self):
        self.assertIn('<cite data-note-citation="">Source, vol. 1, p. 2</cite>',self.page)
        self.assertEqual(h.verify(self.page,self.r),[])
    def test_callout_paragraph_merge_rejected_without_word_changes(self):
        receipt=h.prepare(NOTE.replace('> The source preserves this uncertainty.',
            '> The source preserves this uncertainty.\n>\n> Another paragraph keeps the speaker separate.'))
        page=render(receipt)
        self.assertEqual(h.verify(page,receipt),[])
        broken=page.replace('uncertainty.</p><p>Another','uncertainty. Another')
        self.assertNotEqual(broken,page)
        self.assertTrue(any('paragraphs merged' in e for e in h.verify(broken,receipt)))
    def test_soft_wrapped_quote_lines_remain_one_paragraph(self):
        receipt=h.prepare(NOTE.replace('> The source preserves this uncertainty.',
            '> The source preserves\n> this uncertainty.'))
        self.assertEqual(h.verify(render(receipt),receipt),[])
        layout=next(iter(receipt['paragraph_layout'].values()))
        self.assertEqual(layout['paragraphs'][-1],'The source preserves this uncertainty.')
    def test_prose_block_cannot_become_inline(self):
        broken=self.page.replace('<section data-note-block=', '<span data-note-block=').replace('</section>','</span>')
        self.assertTrue(any('block element' in e for e in h.verify(broken,self.r)))
    def test_callout_needs_separation_from_prose(self):
        with self.assertRaisesRegex(ValueError,'blank lines'):
            h.prepare(NOTE.replace('qualification.\n\n>', 'qualification.\n>'))
    def test_legacy_v2_receipt_remains_valid(self):
        receipt=h.prepare(NOTE,schema=2)
        self.assertEqual(h.verify(render(receipt),receipt),[])

    def test_citation_link_retarget_rejected(self):self.assertTrue(h.verify(self.page.replace('https://example.invalid/source','https://example.invalid/wrong'),self.r))
    def test_canonical_wikilink_table(self):
        receipt=h.prepare(NOTE+'\n| Claim | ↗ |\n|---|---|\n| A claim | [[#Evidence|↗]] |\n')
        self.assertIn('A claim ↗',receipt['blocks'][-1]['text'])
        self.assertNotIn('#Evidence',receipt['blocks'][-1]['text'])
        self.assertIn('#Evidence',[x['target'] for x in receipt['links']])
    def test_quantifier_change_rejected(self):self.assertTrue(h.verify(self.page.replace('Some reports','All reports'),self.r))
    def test_arabic_change_rejected(self):self.assertTrue(h.verify(self.page.replace('نص المصدر','نص آخر'),self.r))
    def test_translation_change_rejected(self):self.assertTrue(h.verify(self.page.replace('preserves this uncertainty','establishes complete certainty'),self.r))
    def test_unmapped_prose_rejected(self):self.assertTrue(h.verify(self.page.replace('</main>','<p>A new conclusion.</p></main>'),self.r))
    def test_duplicate_or_reordered_rejected(self):
        changed=copy.deepcopy(self.r);changed['blocks'].reverse()
        self.assertTrue(h.verify(render(changed),self.r))
    def test_duplicated_block_rejected(self):
        changed=copy.deepcopy(self.r);changed['blocks'].append(changed['blocks'][0]);self.assertTrue(h.verify(render(changed),self.r))
    def test_swapped_citation_destinations_rejected(self):
        note=NOTE+'\n[First](https://example.invalid/one) and [Second](https://example.invalid/two).\n'
        receipt=h.prepare(note);page=render(receipt).replace('First and Second.', '<a href="https://example.invalid/two">First</a> and <a href="https://example.invalid/one">Second</a>.')
        self.assertTrue(h.verify(page,receipt))
    def test_same_label_citation_occurrences_not_interchangeable(self):
        receipt=h.prepare(NOTE+'\n[source](https://example.invalid/one) and [source](https://example.invalid/two).\n')
        page=render(receipt).replace('source and source.', '<a href="https://example.invalid/two">source</a> and <a href="https://example.invalid/one">source</a>.')
        self.assertTrue(h.verify(page,receipt))
    def test_parentheses_in_source_url(self):
        note=NOTE+'\n[Another source](https://example.invalid/Text_(Part))\n'
        receipt=h.prepare(note);page=render(receipt).replace('Another source','<a href="https://example.invalid/Text_(Part)">Another source</a>')
        self.assertEqual(h.verify(page,receipt),[])
    def test_serial_note_link_mapping(self):
        receipt=h.prepare(NOTE+'\n[[Part One|Previous]]\n');receipt['note_map']={'wiki:Part One':'part-one.html'}
        page=render(receipt).replace('Previous','<a href="part-one.html">Previous</a>')
        self.assertEqual(h.verify(page,receipt),[])
        receipt['note_map']={'wiki:Part One':'https://wrong.example/part-one.html'}
        self.assertTrue(h.verify(page,receipt))
    def test_changed_master_rejected(self):
        changed=copy.deepcopy(self.r);changed['source_markdown']=NOTE.replace('Some reports','Most reports')
        self.assertTrue(h.verify(self.page,changed))
    def test_wrong_category_rejected(self):self.assertTrue(h.verify(self.page.replace('data-category="commentary"','data-category="narration"'),self.r))
    def test_missing_block_rejected(self):
        changed=copy.deepcopy(self.r);changed['blocks'].pop();self.assertTrue(h.verify(render(changed),self.r))
    def test_authored_block_cannot_be_hidden_as_source(self):
        changed=self.page.replace('<section data-note-block="n0002"','<section data-content-role="source" data-note-block="n0002"')
        self.assertNotEqual(changed,self.page)
        self.assertTrue(any('source content roles' in e for e in h.verify(changed,self.r)))
    def test_source_role_cannot_be_omitted(self):
        self.assertTrue(any('source content roles' in e for e in h.verify(self.page.replace('data-content-role="source" ',''),self.r)))
    def test_no_silent_unsupported_markup(self):
        with self.assertRaises(ValueError):h.prepare(NOTE+'\n```python\nx = 1\n```\n')
    def test_quote_titles_table_labels_and_links_included(self):
        text=' '.join(x['text'] for x in self.r['blocks'])
        for s in ['Source, vol. 1, p. 2','نص المصدر','preserves this uncertainty','Claim Qualifier','See the source and its context.']:self.assertIn(s,text)

    def approved_source(self):
        import review
        from test_pipeline import ReviewTests
        d=ReviewTests().draft(NOTE,'md')
        self.r.update(source_baseline=d,source_review=ReviewTests().approved(d))

    def test_preservation_without_master_approval_cannot_publish(self):
        import review
        self.assertEqual(h.verify(self.page,self.r),[])
        self.assertTrue(any('no verified master approval' in x for x in review.verify_handoff(self.page,self.r)))

    def test_complete_master_approval_reusable(self):
        import review
        self.approved_source()
        self.assertEqual(review.verify_handoff(self.page,self.r),[])

    def test_blocked_master_cannot_be_laundered_through_handoff(self):
        import review,json
        self.approved_source()
        release=self.r['source_review']['council']['report']['release']
        obj=json.loads(release['response']);obj['status']='blocked';release['response']=json.dumps(obj)
        self.assertTrue(any('not cleared' in x for x in review.verify_handoff(self.page,self.r)))

    def test_wrong_master_approval_rejected(self):
        import review
        self.approved_source();self.r['source_review']['artifact_sha256']='another master'
        self.assertTrue(any('artifact_sha256 mismatch' in x for x in review.verify_handoff(self.page,self.r)))

    def test_cli_embeds_verified_master_and_rejects_failed_review(self):
        import json,subprocess,tempfile
        self.approved_source()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);note=root/'note.md';baseline=root/'baseline.json';record=root/'review.json';receipt=root/'handoff.json'
            note.write_text(NOTE);baseline.write_text(json.dumps(self.r['source_baseline']));record.write_text(json.dumps(self.r['source_review']))
            command=[sys.executable,str(Path(h.__file__)),'prepare',str(note),str(receipt),'--baseline',str(baseline),'--review',str(record)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(receipt.read_text())['source_review'],json.loads(json.dumps(self.r['source_review'])))
            receipt.unlink();self.r['source_review']['status']='pending';record.write_text(json.dumps(self.r['source_review']))
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(receipt.exists())

if __name__=='__main__':unittest.main()
