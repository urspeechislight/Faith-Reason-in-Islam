"""Regression tests for observed cache, fidelity, extraction, and approval failures."""
import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import translate as t
import review as r

class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.attempt=0
        self.job=self.root/'job.json';self.out=self.root/'out.json';self.style=self.root/'style.md'
        self.unit={'id':'u','source':'verbum','source_language':'la','mode':'plain','note':''}
        self.job.write_text(json.dumps({'blocks':[self.unit]}));self.style.write_text('Preserve meaning.')
        self.args=[str(self.job),str(self.out),'--style',str(self.style),'--parent-model','synthetic/glm-test']
    def tearDown(self):self.temp.cleanup()
    def call(self,args):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):return t.main(args)
    def prepare(self):
        self.attempt+=1;directory=self.root/f'attempt-{self.attempt}'
        code=self.call(self.args+['--prepare',str(directory)])
        requests=json.loads((directory/'manifest.json').read_text())['requests'] if not code else []
        return code,requests
    def accept(self,request,response):
        path=self.root/f'response-{self.attempt}.json';path.write_text(response)
        return self.call(self.args+['--accept',request,'--response',str(path),'--agent-id','synthetic-test-agent'])
    def run_engine(self,response='He came home.'):
        code,requests=self.prepare()
        if code:return code,0
        for request in requests:code=self.accept(request,json.dumps({'u':response}))
        return code,len(requests)
    def test_failed_translation_cannot_become_clean_on_rerun(self):
        self.assertEqual(self.run_engine('He came—home.'),(1,1))
        self.assertEqual(self.run_engine('He came—home.'),(1,1))
        self.assertEqual(json.loads(self.out.read_text()),{})
    def test_clean_cache_reused(self):
        self.assertEqual(self.run_engine(),(0,1));self.assertEqual(self.run_engine(),(0,0))
    def test_source_guidance_mode_style_model_invalidate(self):
        for field in ['source','note','mode','style','model']:
            with self.subTest(field=field):
                self.assertEqual(self.run_engine()[0],0)
                if field in self.unit:
                    self.unit[field]='elevated' if field=='mode' else self.unit[field]+' changed'
                    self.job.write_text(json.dumps({'blocks':[self.unit]}))
                elif field=='style':self.style.write_text('Changed style.')
                else:self.args[-1]='synthetic/glm-other'
                self.assertEqual(self.run_engine(),(0,1))
    def test_archived_chapter_covers_multiverse_passage(self):
        import json as _json
        chapter = _json.dumps([{"pk": 1, "verse": 4, "text": "αβ γα"}, {"pk": 2, "verse": 5, "text": "δε ζη"}])
        import evidence
        self.assertIn("αβ γα δε ζη", [q for q in evidence.archived_text(chapter)])
        note = "> [!quote]- Test 4-5, Edition\n> αβ γα δε ζη\n>\n> *ab ga de ze*\n>\n> \"Words\""
        self.assertEqual(evidence.scripture_coverage(note, evidence.archived_text(chapter)), [])

    def test_scripture_coverage_survives_combining_mark_order(self):
        decomposed = "\u05d5\u05bc\u05c1\u05dc\u05b0"  # vav+dagesh+shin-dot+hiriq, decomposed order
        composed = "\u05d5\u05bc\u05c1\u05dc\u05b0"
        note = "> [!quote]- Test verse, Testus Receptus\n> " + composed + " diber\n>\n> *walc-shel diber*\n>\n> \"God spoke\""
        archived = "prefix " + decomposed + " diber suffix"
        import evidence
        self.assertEqual(evidence.scripture_coverage(note, [archived]), [])

    def test_missing_provenance_rejected(self):
        self.out.write_text(json.dumps({'u':'He came home.'}))
        self.assertEqual(self.run_engine(),(0,1))
    def test_edited_output_rejected(self):
        self.run_engine();self.out.write_text(json.dumps({'u':'She came home.'}))
        self.assertEqual(self.run_engine(),(0,1))
    def test_request_records_inheritance_and_full_prompt(self):
        self.assertTrue(t.DEFAULT_STYLE.is_file());code,requests=self.prepare();self.assertEqual(code,0)
        request=json.loads(Path(requests[0]).read_text())
        self.assertEqual(request['parent_model'],'synthetic/glm-test');self.assertEqual(request['model_policy'],'inherit-parent')
        self.assertEqual(request['backend'],'native-subagent');self.assertIn('Preserve meaning.',request['prompt']);self.assertIn('verbum',request['prompt'])
    def test_real_negation_not_forced_into_positive(self):
        text='Some men did not agree, but others did.'
        self.assertEqual(t.check_translation(text,'u','plain'),[]);self.assertTrue(t.translation_warnings(text,'plain'))
    def test_interrupted_dispatch_does_not_leave_stale_cache(self):
        self.run_engine();self.style.write_text('Changed again.');self.prepare()
        self.assertEqual(json.loads(self.out.read_text()),{})
        self.assertEqual(self.call(self.args+['--check-only']),1)
        self.assertEqual(json.loads(t.review_path_for(self.out).read_text())['status'],'translation-incomplete')
    def test_check_only_never_starts_a_provider(self):
        self.run_engine()
        with patch.object(subprocess,'run',side_effect=AssertionError('must not launch providers')):
            self.assertEqual(self.call(self.args+['--check-only']),0)
    def test_oversized_first_unit_fails_before_dispatch(self):
        self.unit['source']='x'*6000;self.job.write_text(json.dumps({'blocks':[self.unit]}));self.args+=['--max-prompt-chars','5000']
        self.assertEqual(self.run_engine(),(2,0))
    def test_unknown_missing_nonstring_and_wrapped_response_rejected(self):
        for raw in ['{"u":"Text","extra":"Wrong"}','{}','{"u":7}','prefix {"u":"Text"}','```json\n{"u":"Text"}\n```']:
            code,requests=self.prepare();self.assertEqual(code,0)
            self.assertEqual(self.accept(requests[0],raw),1)
            self.assertEqual(json.loads(self.out.read_text()),{})
    def test_no_cli_fallback_or_provider_environment_default(self):
        with patch.dict(t.os.environ,{'OPENCODE_MODEL':'wrong/provider','OPENCODE_BIN':'/fake'}),patch.object(subprocess,'run',side_effect=AssertionError('must not launch providers')):
            self.assertEqual(self.run_engine(),(0,1))
    def test_both_entrypoints_share_engine(self):
        home=Path(t.__file__).resolve().parent.parent/'skills'
        for skill in ['islamic-note','faith-reason-note']:
            self.assertTrue((home/skill/'translate.py').is_file())
            self.assertEqual((home/skill/'translate.py').resolve(),Path(t.__file__).resolve())
            self.assertEqual((home/skill/'translate-style.md').resolve(),Path(t.__file__).resolve().parent/'translate-style.md')
    def test_request_is_bound_to_job_style_parent_model_and_prompt(self):
        for target in ['source','style','model','prompt']:
            code,requests=self.prepare();self.assertEqual(code,0)
            if target=='source':self.unit['source']+=' changed';self.job.write_text(json.dumps({'blocks':[self.unit]}))
            elif target=='style':self.style.write_text(self.style.read_text()+' changed')
            elif target=='model':self.args[-1]+='-changed'
            else:
                p=Path(requests[0]);req=json.loads(p.read_text());req['prompt']+=' extra';p.write_text(json.dumps(req))
            self.assertEqual(self.accept(requests[0],'{"u":"Text."}'),2)
    def test_raw_response_and_agent_receipt_preserved(self):
        code,requests=self.prepare();request=Path(requests[0]);raw='{"u":"First paragraph.\\n\\nSecond paragraph."}'
        self.assertEqual(self.accept(str(request),raw),0)
        receipt=json.loads(request.with_name(request.name+'.receipt.json').read_text())
        self.assertEqual(receipt['agent_id'],'synthetic-test-agent')
        self.assertEqual(request.with_name(request.name+'.response.txt').read_text(),raw)
        self.assertIn('\n\n',json.loads(self.out.read_text())['u'])
        self.assertEqual(self.accept(str(request),raw),2)
    def test_multiple_batches_require_complete_job_before_check_passes(self):
        self.job.write_text(json.dumps({'blocks':[dict(self.unit,id='one'),dict(self.unit,id='two')]}));self.args+=['--batch','1']
        code,requests=self.prepare();self.assertEqual(len(requests),2)
        self.assertEqual(self.accept(requests[0],'{"one":"One."}'),0)
        self.assertEqual(self.call(self.args+['--check-only']),1)
        self.assertEqual(self.accept(requests[1],'{"two":"Two."}'),0)
        self.assertEqual(self.call(self.args+['--check-only']),0)
    def test_legacy_provider_fingerprint_is_not_native_cache(self):
        self.run_engine();state_path=t.state_path_for(self.out);state=json.loads(state_path.read_text());state['u']['fingerprint']='legacy-opencode';state_path.write_text(json.dumps(state))
        self.assertEqual(self.call(self.args+['--check-only']),1)
    def test_missing_execution_mode_or_parent_model_blocks(self):
        for args in [self.args,self.args[:-2]+['--prepare',str(self.root/'pending')],self.args[:-1]+['inherit','--check-only']]:
            with self.assertRaises(SystemExit):self.call(args)
    def test_duplicate_keys_and_modified_output_whitespace_fail(self):
        code,requests=self.prepare()
        self.assertEqual(self.accept(requests[0],'{"u":"First.","u":"Other."}'),1)
        self.assertEqual(self.run_engine()[0],0)
        self.out.write_text(json.dumps({'u':' He came home. '}))
        self.assertEqual(self.call(self.args+['--check-only']),1)
    def test_raw_crlf_response_bytes_and_hash_preserved(self):
        code,requests=self.prepare();request=Path(requests[0]);path=self.root/'raw.json';raw=b'{\r\n"u":"He came home."\r\n}'
        path.write_bytes(raw)
        self.assertEqual(self.call(self.args+['--accept',str(request),'--response',str(path),'--agent-id','synthetic-test-agent']),0)
        self.assertEqual(request.with_name(request.name+'.response.txt').read_bytes(),raw)
        receipt=json.loads(request.with_name(request.name+'.receipt.json').read_text())
        self.assertEqual(receipt['response_sha256'],hashlib.sha256(raw).hexdigest())
    def test_failed_check_refreshes_sidecar_without_changing_output(self):
        self.run_engine();before=self.out.read_bytes()
        self.job.write_text(json.dumps({'blocks':[self.unit,dict(self.unit,id='new')]}))
        self.assertEqual(self.call(self.args+['--check-only']),1)
        sidecar=json.loads(t.review_path_for(self.out).read_text())
        self.assertEqual(sidecar['missing_ids'],['new']);self.assertEqual(sidecar['status'],'translation-incomplete')
        self.assertEqual(self.out.read_bytes(),before)
    def test_legacy_arabic_field_requires_actual_arabic_source(self):
        with self.assertRaises(ValueError):t.validate_job({'blocks':[{'id':'x','arabic':'English source'}]})
    def test_late_response_from_superseded_request_is_rejected(self):
        code,old=self.prepare();code,new=self.prepare()
        self.assertEqual(self.accept(old[0],'{"u":"Old reply."}'),2)
        self.assertEqual(self.accept(new[0],'{"u":"New reply."}'),0)
        self.assertEqual(json.loads(self.out.read_text()),{'u':'New reply.'})
    def test_source_edge_whitespace_is_not_silently_normalized(self):
        self.run_engine();self.unit['source']='\n '+self.unit['source']+' \n';self.job.write_text(json.dumps({'blocks':[self.unit]}))
        self.assertEqual(self.call(self.args+['--check-only']),1)
        self.assertEqual(t.validate_job({'blocks':[self.unit]})[0]['source'],self.unit['source'])
    def test_unverified_extra_output_key_blocks_final_check(self):
        self.run_engine();data=json.loads(self.out.read_text());data['extra']='Unverified content.';self.out.write_text(json.dumps(data))
        before=self.out.read_bytes();self.assertEqual(self.call(self.args+['--check-only']),1)
        sidecar=json.loads(t.review_path_for(self.out).read_text())
        self.assertEqual(sidecar['status'],'translation-incomplete');self.assertTrue(sidecar['errors'])
        self.assertEqual(self.out.read_bytes(),before)

class ReviewTests(unittest.TestCase):
    def draft(self,source,fmt='html'):
        return dict(r.extract(source,fmt),schema=r.VERSION,artifact_sha256=r.digest(source),format=fmt)
    def approved(self,draft,base=None):
        out=r.template(draft,base or draft);out.update(status='approved',reviewer='fixture reviewer (synthetic test only)')
        for block in out['blocks']:block.update(decision='keep',function='claim',observation='Synthetic fixture only: '+block['text']+' identifies the test content; this is not a publication review.')
        out['claim_preservation']={'status':'passed','negation_quantifiers_attribution':'The test claim retains every qualifier and named actor.','source_alignment':'The synthetic fixture contains no external source claims.'}
        for key in ['source_verification','translation_fidelity','structural_validation','council']:
            out[key]={'status':'not-applicable','evidence':'Synthetic test fixture, not a publication approval record.'}
        for item in out['cue_resolutions']:
            item.update(status='legitimate',reason='Synthetic fixture checks record completeness only, never approves real prose.')
        for item in out['semantic_review'].values():
            item.update(status='passed',blocks=[b['id'] for b in draft['blocks']],evidence='Synthetic fixture checks record completeness only, never approves real prose.')
        out['council'].update(status='passed',reviewed_artifact_sha256=draft['artifact_sha256'],
            profile_sha256=r.digest((r.ROOT/'council-article.md').read_bytes()),report={
                'advisors':[{'role':role,'reviewer':'synthetic advisor '+role,
                             'reviewed_sha256':draft['artifact_sha256'],
                             'response':'Synthetic test response for schema checks, not a real independent review.'} for role in sorted(r.COUNCIL_ROLES)],
                'peer_reviews':[{'reviewer':'synthetic peer '+str(i),
                                'reviewed_sha256':draft['artifact_sha256'],
                                'response':'Synthetic peer response for schema checks, not a real independent review.'} for i in range(5)],
                'anonymization':dict(zip('ABCDE',sorted(r.COUNCIL_ROLES))),
                'synthesis':'Synthetic test synthesis for schema checks, not a real publication decision.'})
        report=out['council']['report']
        report['release']={'reviewer':'independent synthetic fixture, not a real review',
            'response':json.dumps({'status':'passed','artifact_sha256':draft['artifact_sha256'],
                'council_sha256':r.council_digest(report),'open_findings':[],
                'dispositions':[{'id':identifier,'status':'resolved','evidence':'Synthetic fixture only: this response contains no actual editorial findings or publication approval.'} for identifier in sorted(r.council_finding_ids(report))],
                'assessment':'Synthetic schema fixture exercises explicit independent release closure only and supplies no real editorial approval.'})}
        # Synthetic evidence exercises schema only; never use on a real release.
        for q in out['quote_layout_review']:
            q.update(status='passed',paragraph_boundaries='Synthetic fixture deliberately contains the specified paragraph boundaries for testing.',
                     speaker_and_quotation_boundaries='Synthetic fixture has no unresolved speaker changes for this schema test.',
                     source_completeness='Synthetic text is complete by construction and represents no historical source.')
            for cue in q['cue_resolutions']:
                cue.update(status='legitimate',reason='Synthetic test exercises required records and is not an editorial approval.')
        if draft.get('format') in ('html','htm') and draft['quotes']:
            out['rendered_layout']={'schema':r.quote_layout.VERSION,'authored_sha256':'1'*64,'artifact_sha256':draft['artifact_sha256'],'engine':'chromium',
                'viewports':[{'width':w,'authored_sha256':'1'*64,'hidden_blocks':[],'pseudo_text':[],'overflow_px':0,'screenshot_sha256':'0'*64,
                    'callouts':[{'id':q['id'],'paragraphs':[{'sha256':p['sha256'],'height':20,'visible':True,'gap_before':16,'inset_px':16,'line_ratio':1.58,'language':'en'} for p in q['paragraphs']]} for q in draft['quotes']]} for w in (1280,390)]}
        return out
    def test_hosted_preparation_defers_only_independent_release(self):
        d=self.draft('<p>A supported statement.</p>');record=self.approved(d)
        record['council']['report']['release']={}
        self.assertTrue(r.verify(d,d,record))
        self.assertFalse(r.verify(d,d,record,require_release=False))
        record['artifact_sha256']='wrong'
        self.assertTrue(r.verify(d,d,record,require_release=False))
    def test_accessible_and_social_prose_is_reviewed(self):
        text='The conclusion is a weighed reading.'
        markup='<html><head><meta property="og:description" content="'+text+'"></head><body><img alt="'+text+'" title="'+text+'" aria-label="'+text+'"></body></html>'
        blocks=r.extract(markup,'html')['blocks']
        self.assertEqual([b['text'] for b in blocks],[text]*4)
    def test_equivalent_formats_find_same_prose_cues(self):
        sentence='Al-Mashhadi closes the door that the libel tried to open.'
        for source,fmt in [('<p>'+sentence+'</p>','html'),(sentence,'md')]:
            blocks=r.extract(source,fmt)['blocks'];self.assertIn('argumentative-metaphor',r.cues(blocks[0]['text']))
    def test_quote_and_translation_protected(self):
        for source,fmt in [('<blockquote data-content-role="source"><p>One word won it.</p></blockquote><p>He came home.</p>','html'),('> [!quote]- Source\n> One word won it.\n\nHe came home.','md')]:
            out=r.extract(source,fmt);self.assertEqual(len(out['blocks']),1);self.assertFalse(r.cues(out['blocks'][0]['text']))
    def test_inline_html_cannot_hide_prose(self):
        block=r.extract('<p>One <b>word</b> won it.</p>','html')['blocks'][0]
        self.assertIn('opaque-verdict',r.cues(block['text']))
    def test_pending_review_fails(self):
        d=self.draft('<p>He came home.</p>');self.assertTrue(r.verify(d,d,r.template(d,d)))
    def test_complete_review_record_accepted(self):
        d=self.draft('<p>He came home.</p>');self.assertEqual(r.verify(d,d,self.approved(d)),[])
    def test_stale_approval_rejected(self):
        old=self.draft('<p>Most men agreed.</p>');new=self.draft('<p>All men agreed.</p>')
        self.assertTrue(r.verify(new,old,self.approved(old)))
    def test_scope_changes_are_visible_to_reviewer(self):
        old=self.draft('<p>Most men agreed.</p>');new=self.draft('<p>None agreed.</p>')
        report=r.template(new,old)
        self.assertNotEqual(report['scope_cues_before'],report['scope_cues_after'])
    def test_protected_change_rejected_even_with_fresh_review(self):
        old=self.draft('<blockquote data-content-role="source">Most men agreed.</blockquote><p>He came home.</p>')
        new=self.draft('<blockquote data-content-role="source">All men agreed.</blockquote><p>He came home.</p>')
        self.assertTrue(any('protected' in e for e in r.verify(new,old,self.approved(new,old))))
    def test_citation_link_change_rejected(self):
        old=self.draft('<p><a href="source-a">The source</a> reports it.</p>')
        new=self.draft('<p><a href="source-b">The source</a> reports it.</p>')
        self.assertTrue(any('link' in e for e in r.verify(new,old,self.approved(new,old))))
    def test_incomplete_coverage_rejected(self):
        d=self.draft('<p>He came home.</p><p>She left.</p>');report=self.approved(d);report['blocks'].pop()
        self.assertTrue(r.verify(d,d,report))
    def test_unresolved_findings_rejected(self):
        d=self.draft('<p>He came home.</p>');report=self.approved(d);report['findings']=[{'status':'open'}]
        self.assertTrue(r.verify(d,d,report))
    def test_changed_contract_invalidates_approval(self):
        d=self.draft('<p>He came home.</p>');report=self.approved(d);report['contract_sha256']='old'
        self.assertTrue(r.verify(d,d,report))
    def test_malformed_artifact_not_accepted(self):
        with self.assertRaises(ValueError):r.extract('<p>Unclosed','html')

class ProseGuardTests(unittest.TestCase):
    draft = ReviewTests.draft
    approved = ReviewTests.approved
    def test_authored_tables_and_unmarked_blockquotes_are_reviewed(self):
        for source,fmt in [
            ('<table><tr><td>The reasoning is stated plainly.</td></tr></table>','html'),
            ('<blockquote><p>The reasoning is stated plainly.</p></blockquote>','html'),
            ('| Claim |\n|---|\n| The reasoning is stated plainly. |','md'),
            ('> The reasoning is stated plainly.','md'),
            ('<p class="translation">The reasoning is stated plainly.</p>','html')]:
            with self.subTest(source=source):self.assertTrue(r.cue_items(r.extract(source,fmt)['blocks']))

    def test_table_prose_edit_preserves_numeric_data(self):
        a=self.draft('<table><tr><td>The record is clear: 12 reports.</td></tr></table>')
        b=self.draft('<table><tr><td>12 reports.</td></tr></table>')
        c=self.draft('<table><tr><td>13 reports.</td></tr></table>')
        self.assertEqual(a['protected_sha256'],b['protected_sha256'])
        self.assertNotEqual(a['protected_sha256'],c['protected_sha256'])
    def test_observed_article_examples_flagged(self):
        samples=[
            "Eight poets are named. Whatever the councils judged, the school's own biographical dictionary records him mourned in verse.",
            "The same entry's roll of elegists keeps the mourning on the record.",
            "The reasoning is stated plainly.",
            "His own tradition tells a fuller story.",
            "Every quotation below is cited to a Sunni source.",
            "This was no small concession.",
            "He was not a reformer but a rebel.",
            "The critic graciously concedes the date.",
        ]
        for text in samples:
            with self.subTest(text=text):self.assertTrue(r.cues(text))
    def test_sister_aaron_surviving_phrases_flagged(self):
        samples = [
            "One relay preserves the shape of the scene.",
            "The envoy's silence on the spot is the report's own detail.",
            "The kinship word was already doing lineage work before anyone thought to doubt it.",
            "If Muqatil falls, the idiom stands on the rest.",
            "Every other reading reaches the same ground by another road.",
            "The next two sections carry the argument.",
            "No one in the line stops to ask what brother means here.",
            "One speaker, two addresses, two peoples.",
        ]
        for text in samples:
            with self.subTest(text=text): self.assertTrue(r.cues(text))

    def test_shifted_observation_rejected_even_with_current_text_and_hashes(self):
        d=self.draft("<p>The men cast their pens, and Zakariyya's lot came out.</p>")
        record=self.approved(d)
        record['blocks'][0].update(function='heading',observation='Section five heading naming the Gospel evidence.')
        errors=r.verify(d,d,record)
        self.assertTrue(any('quote current block' in e for e in errors))
        self.assertTrue(any('labels body prose as a heading' in e for e in errors))

    def test_repeated_generic_observations_rejected(self):
        d=self.draft('<p>The report identifies the father.</p><p>The report identifies the mother.</p>')
        record=self.approved(d)
        for row in record['blocks']:row['observation']='The report identifies the named relationship in this passage.'
        self.assertTrue(any('reuses' in e for e in r.verify(d,d,record)))

    def test_anchored_specific_observations_pass(self):
        d=self.draft('<p>The men cast their pens.</p><h2>Guardianship</h2>')
        record=self.approved(d)
        record['blocks'][0]['observation']='"The men cast their pens" explains how the guardian was selected.'
        record['blocks'][1].update(function='heading',observation='"Guardianship" locates the section about care of Maryam.')
        self.assertEqual(r.verify(d,d,record),[])

    def test_anchor_ignores_punctuation_and_case(self):
        self.assertTrue(r.observation_anchored('The men cast their pens.', 'THE MEN CAST THEIR PENS names the action.'))
        self.assertFalse(r.observation_anchored('The men cast their pens.', 'The Gospel identifies a relative.'))

    def test_specific_attribution_and_genuine_limits_stay_clean(self):
        for text in ["Ibn Hajar names eight poets who elegized him.",
                     "The evidence does not establish an exact date.",
                     "Ibn Hajar reports that the judge imprisoned him."]:
            self.assertEqual(r.cues(text),[])
    def test_hits_cannot_be_deleted_from_receipt(self):
        d=self.draft('<p>The reasoning is stated plainly.</p>');record=self.approved(d)
        record['cue_resolutions']=[]
        self.assertTrue(any('cue resolutions' in e for e in r.verify(d,d,record)))
    def test_generic_block_approval_cannot_override_pending_hit(self):
        d=self.draft('<p>This was no small concession.</p>');record=self.approved(d)
        record['cue_resolutions'][0]['status']='pending'
        self.assertTrue(any('unresolved prose cue' in e for e in r.verify(d,d,record)))
    def test_fresh_cues_recomputed_even_if_cues_field_forged(self):
        d=self.draft('<p>The reasoning is stated plainly.</p>');record=self.approved(d)
        record['blocks'][0]['cues']=[];record['cue_resolutions'][0]['text']='harmless'
        self.assertTrue(any('actual artifact' in e for e in r.verify(d,d,record)))
    def test_unflagged_prose_still_requires_semantic_review(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['semantic_review']={}
        self.assertTrue(any('semantic review incomplete' in e for e in r.verify(d,d,record)))
    def test_council_status_without_responses_rejected(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['council']['report']={}
        self.assertTrue(any('advisor responses' in e for e in r.verify(d,d,record)))
    def test_council_cannot_be_waived(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['council']['status']='not-applicable'
        self.assertTrue(any('council must pass' in e for e in r.verify(d,d,record)))
    def test_stale_council_rejected(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['council']['reviewed_artifact_sha256']='old'
        self.assertTrue(any('different candidate' in e for e in r.verify(d,d,record)))
    def test_verified_handoff_can_reuse_master_council(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['council']['reviewed_artifact_sha256']='master'
        release=json.loads(record['council']['report']['release']['response']);release['artifact_sha256']='master'
        record['council']['report']['release']['response']=json.dumps(release)
        self.assertEqual(r.verify(d,d,record,council_source_sha256='master'),[])
        self.assertTrue(r.verify(d,d,record))
    def test_policy_change_invalidates_receipt(self):
        d=self.draft('<p>He came home.</p>');record=self.approved(d);record['policy_sha256']='old'
        self.assertTrue(any('policy_sha256 mismatch' in e for e in r.verify(d,d,record)))
    def test_authored_conclusion_blockquote_is_reviewed(self):
        d=r.extract('<blockquote class="conclusion-card"><p>The reasoning is stated plainly.</p></blockquote>','html')
        self.assertTrue(r.cue_items(d['blocks']))

class ReleaseTests(unittest.TestCase):
    draft = ReviewTests.draft
    approved = ReviewTests.approved

    def setUp(self):
        self.d=self.draft('<p>The source does not name the ruler.</p>')
        self.record=self.approved(self.d)
        self.report=self.record['council']['report']

    def edit_release(self, **changes):
        obj=json.loads(self.report['release']['response']);obj.update(changes)
        self.report['release']['response']=json.dumps(obj)

    def test_writer_pass_without_independent_response_rejected(self):
        del self.report['release']
        self.assertTrue(any('chairman approval' in x for x in r.verify(self.d,self.d,self.record)))

    def test_blocked_response_overrides_writer_pass(self):
        self.edit_release(status='blocked',open_findings=['prose:P-02'])
        self.assertTrue(any('not cleared' in x for x in r.verify(self.d,self.d,self.record)))

    def test_open_findings_cannot_coexist_with_pass(self):
        self.edit_release(open_findings=['prose:P-02'])
        self.assertTrue(r.release_errors(self.report,self.d['artifact_sha256']))

    def test_changed_council_invalidates_release(self):
        self.report['advisors'][0]['response']='P-02 remains unresolved. Delete the metanarration before publishing this article.'
        self.assertTrue(any('stale' in x for x in r.release_errors(self.report,self.d['artifact_sha256'])))

    def test_changed_artifact_invalidates_release(self):
        self.assertTrue(any('different candidate' in x for x in r.release_errors(self.report,'changed')))

    def test_release_response_must_be_actual_json(self):
        self.report['release']['response']='The chairman approved all of the retained stylistic choices for this article.'
        self.assertTrue(r.release_errors(self.report,self.d['artifact_sha256']))

    def test_observed_blocked_council_cannot_be_passed_by_chairman(self):
        # Reproduce the observed approval bypass without publishing private transcripts.
        report=copy.deepcopy(self.report);report.pop('release',None)
        report['advisors'][0]['response']='Blocking findings\nP-02: The candidate still contains an empty introduction.'
        self.record['council']['report']=report
        self.assertEqual(self.record['council']['status'],'passed')
        self.assertTrue(any('chairman approval' in x for x in r.verify(self.d,self.d,self.record)))

    def test_independent_response_must_cover_reviewer_ids(self):
        self.report['advisors'][0].update(role='prose',response='**Follow-Up Verdict: Blocking Findings**\nP-02 remains unapplied. Remove the empty introduction.')
        self.edit_release(council_sha256=r.council_digest(self.report),dispositions=[])
        errors=r.release_errors(self.report,self.d['artifact_sha256'])
        self.assertTrue(any('prose:P-02' in x for x in errors))
        self.assertTrue(any('blocking council responses' in x for x in errors))

    def test_independent_evidenced_dismissal_can_close_false_positive(self):
        self.report['advisors'][0].update(role='prose',response='P-02: delete the negation as a potential stylistic failure in the statement.')
        dispositions=[{'id':identifier,'status':'resolved','evidence':'Synthetic fixture only: unchanged panel response contains no actual unresolved editorial finding.'} for identifier in sorted(r.council_finding_ids(self.report)) if identifier!='prose:P-02']
        dispositions.append({
            'id':'prose:P-02','status':'not-a-defect',
            'evidence':'The source does not name the ruler states an evidentiary limit; deletion would reverse the claim.'})
        self.edit_release(council_sha256=r.council_digest(self.report),dispositions=dispositions)
        self.assertEqual(r.release_errors(self.report,self.d['artifact_sha256']),[])

    def test_peer_blocker_requires_its_own_disposition(self):
        self.report['peer_reviews'][0]['response']='Blocking findings\nPX-01: The opening still contains empty meta commentary; delete it before publication.'
        self.edit_release(council_sha256=r.council_digest(self.report))
        self.assertTrue(any('peer-1:PX-01' in x for x in r.release_errors(self.report,self.d['artifact_sha256'])))

    def test_followup_blocker_requires_its_own_disposition(self):
        self.report['followup_reviews']=[{'response':'Blocking findings\nFX-01: A translation still reverses the source verb and must be corrected.'}]
        self.edit_release(council_sha256=r.council_digest(self.report))
        self.assertTrue(any('followup-1:FX-01' in x for x in r.release_errors(self.report,self.d['artifact_sha256'])))

    def test_plain_numbered_advisor_id_requires_disposition(self):
        self.report['advisors'][0].update(role='prose',response='Blocking findings\nF01: Delete the announcement before the substantive answer in the opening.')
        self.edit_release(council_sha256=r.council_digest(self.report))
        self.assertTrue(any('prose:F01' in x for x in r.release_errors(self.report,self.d['artifact_sha256'])))

    def test_unnumbered_responses_cannot_be_skipped(self):
        self.report['peer_reviews'][0]['response']='The article still contains a redundant opening; remove it before release.'
        self.edit_release(council_sha256=r.council_digest(self.report),dispositions=[])
        self.assertTrue(any('peer-1:response' in x for x in r.release_errors(self.report,self.d['artifact_sha256'])))

    def test_packet_does_not_generate_an_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);draft=root/'draft.html';receipt=root/'review.json';packet=root/'packet.json'
            draft.write_text('<p>The source does not name the ruler.</p>');receipt.write_text(json.dumps(self.record))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(r.main(['release-packet',str(draft),'--review',str(receipt),'--output',str(packet)]),0)
            data=json.loads(packet.read_text())
            self.assertNotIn('release',data['report']);self.assertNotIn('status',data)
            self.assertEqual(data['candidate'],draft.read_text())

if __name__=='__main__':unittest.main()
