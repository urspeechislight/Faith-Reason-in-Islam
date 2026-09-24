"""Unpublished synthetic regressions for review intake and article task scope."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import article_build as B
import article_scope as S
import conversion_review as C
import evidence
import review
import review_intake as I
import review_dispatch as D
from test_article_build import ManifestTests
from test_pipeline import ReviewTests


class IntakeTests(ManifestTests):
    def setup_reviews(self):
        self.init(); self.assertEqual(self.call('preflight',self.manifest),0)
        self.assertEqual(self.call('reviews', self.manifest), 0)
        B.write(B.read(self.manifest)['paths']['evidence'],{'schema':1,'artifact_sha256':review.digest(self.source.read_text()),'sources':[{'kind':'external','id':'fixture','citation':'Synthetic witness only','url':'https://example.invalid','accessed':'2026-09-24','raw':'He went home.','raw_sha256':review.digest('He went home.')}],'claims':[]})

    def request(self, kind):
        directory=self.root/(kind+'-request')
        self.assertEqual(self.call('review-request',self.manifest,'--kind',kind,'--parent-model','fixture-parent','--output',directory),0)
        return directory/'request.json'

    def reply(self, request, record):
        path=request.parent/'actual-response.json'
        B.write(path,{'request_sha256':I.sha(B.read(request)),'status':'passed','findings':[],'record':record})
        return path

    def accept(self, request, reply, model='fixture-parent'):
        return self.call('review-accept',self.manifest,'--request',request,'--response',reply,'--agent-id','fixture-child','--model',model)

    def test_html_pending_has_no_duplicate_editorial_rows_and_capture_is_retained(self):
        self.setup_reviews();data=B.read(self.manifest);record=B.read(data['paths']['html_review'])
        self.assertEqual(record['kind'],C.KIND);self.assertEqual(record['status'],'pending')
        self.assertNotIn('blocks',record);self.assertNotIn('council',record)

    def visual_record(self, value):
        return {'binding':value['binding'],'status':'passed','assessment':'Synthetic visual fixture checks exact converted material and retained geometry without granting any source or publication approval.',
                'open_findings':[], 'checks':{k:{'status':'passed','evidence':'Synthetic test only: this specific viewport property was inspected in the retained page fixture.'} for k in C.CHECKS}}

    def test_render_intake_keeps_raw_response_and_requires_master_handoff(self):
        self.setup_reviews();request=self.request('render');reply=self.reply(request,self.visual_record(B.read(request)))
        old=Path(B.read(self.manifest)['paths']['html_review']);before=old.read_bytes()
        self.assertEqual(self.accept(request,reply),0);self.assertEqual(old.read_bytes(),before)
        data=B.read(self.manifest);record=B.read(data['paths']['html_review'])
        self.assertEqual(record['response'],reply.read_text());self.assertEqual(record['status'],'approved')
        page=Path(B.read(self.manifest)['builds'][-1]['directory'])/'article.html'
        self.assertTrue(review.verify_html(page.read_text(),B.read(data['paths']['html_baseline']),record))
        preview=B.read(page.parent/'handoff.preview.json');master=review.inspect_file(self.source)
        approved=ReviewTests().approved(master);approved['structural_validation']['status']='passed'
        preview.update(source_baseline=master,source_review=approved)
        self.assertEqual(review.verify_html(page.read_text(),B.read(data['paths']['html_baseline']),record,preview,require_release=False),[])
        for change in ('The witness arrived.', 'unmapped extra sentence'):
            bad=page.read_text().replace('</main>', '<p>'+change+'</p></main>')
            self.assertTrue(review.verify_html(bad,B.read(data['paths']['html_baseline']),record,preview,require_release=False))
        record['rendered_layout']={'changed':True}
        self.assertTrue(review.verify_html(page.read_text(),B.read(data['paths']['html_baseline']),record,preview,require_release=False))

    def test_blocked_wrong_model_stale_and_malformed_responses_never_replace_pending(self):
        self.setup_reviews();request=self.request('render');reply=self.reply(request,self.visual_record(B.read(request)))
        before=self.manifest.read_bytes()
        self.assertEqual(self.accept(request,reply,'paid-other-model'),1);self.assertEqual(self.manifest.read_bytes(),before)
        data=B.read(reply);data['record']['open_findings']=['overflow'];B.write(reply,data)
        self.assertEqual(self.accept(request,reply),1);self.assertEqual(self.manifest.read_bytes(),before)
        reply.write_text('{}');self.assertEqual(self.accept(request,reply),1)
        reply.write_text('[]');self.assertEqual(self.accept(request,reply),1)
        self.assertTrue(list((request.parent/'responses').glob('*/response.txt')))
        self.source.write_text(self.source.read_text()+'\nChanged candidate.\n')
        self.assertEqual(self.accept(request,reply),1)

    def test_request_is_repeatable_without_overwriting(self):
        self.setup_reviews();request=self.request('render');before=request.read_bytes()
        self.assertEqual(self.call('review-request',self.manifest,'--kind','render','--parent-model','fixture-parent','--output',request.parent),0)
        self.assertEqual(request.read_bytes(),before)

    def test_master_intake_rejects_unregistered_evidence_before_delegation(self):
        self.setup_reviews()
        Path(B.read(self.manifest)['paths']['evidence']).unlink()
        self.assertEqual(self.call('review-request',self.manifest,'--kind','master','--parent-model','fixture-parent','--output',self.root/'missing'),1)
        self.assertFalse((self.root/'missing').exists())

    def test_advance_native_reviews_release_and_stage_complete_one_pipeline(self):
        import sqlite3
        from test_native_release import response as release_response
        self.init();db=self.root/'sources.db';sqlite3.connect(db).close()
        ledger=self.root/'ledger.json';external=self.root/'external.json'
        B.write(ledger,{'schema':1,'passages':[]})
        B.write(external,[{'kind':'external','id':'test','citation':'Synthetic source only','url':'https://example.invalid/test','accessed':'2026-09-24','raw':'He went home.','raw_sha256':review.digest('He went home.')}])
        self.assertEqual(self.call('advance',self.manifest,'--external',external),0)
        master=ReviewTests().approved(review.inspect_file(self.source));master['reviewer']='fixture-child';master['structural_validation']['status']='passed'
        pending_path=Path(B.read(self.manifest)['paths']['review']);pending=B.read(pending_path)
        pending['council']['report']=copy.deepcopy(master['council']['report']);B.write(pending_path,pending)
        master_request=self.request('master')
        master_reply=self.reply(master_request,D.form(master))
        self.assertEqual(self.accept(master_request,master_reply),0)
        render_request=self.request('render');render_reply=self.reply(render_request,self.visual_record(B.read(render_request)))
        self.assertEqual(self.accept(render_request,render_reply),0)
        self.assertEqual(self.call('advance',self.manifest),0)
        self.assertEqual(self.call('prepare',self.manifest),0)
        release_dir=self.root/'release-request'
        self.assertEqual(self.call('release-request',self.manifest,'--parent-model','fixture-parent','--output',release_dir),0)
        final=self.root/'release-response.json';final.write_text(release_response(B.read(release_dir/'request.json')))
        self.assertEqual(self.call('release-accept',self.manifest,'--request',release_dir/'request.json','--response',final,'--agent-id','independent-fixture-final','--model','fixture-parent'),0)
        self.assertEqual(self.call('verify',self.manifest),0)
        self.assertEqual(self.call('stage',self.manifest),0)
        frozen=self.manifest.read_bytes()
        self.assertEqual(self.accept(render_request,render_reply),0)
        self.assertEqual(self.accept(master_request,master_reply),0)
        self.assertEqual(self.manifest.read_bytes(),frozen)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(B.main(['advance',str(self.manifest)]),0)
        self.assertIn('staged',out.getvalue());self.assertNotIn('approvals remain pending',out.getvalue())
        self.assertEqual((self.site/'reading.html').read_bytes(),Path(B.read(self.manifest)['ready']['paths']['html']).read_bytes())

    def test_scope_blocks_second_article_and_wrong_url(self):
        self.init();before=self.manifest.read_bytes();other=self.site/'other.html';other.write_text('fixture')
        self.assertEqual(self.call('init',self.root/'other/build.json','--source',self.source,'--site-root',self.site,'--slug','other','--operation','repair'),1)
        self.assertFalse((self.root/'other/build.json').exists())
        self.assertEqual(self.call('scope',self.manifest,'--url','https://urspeechislight.github.io/Faith-Reason-in-Islam/other.html'),1)
        self.assertEqual(self.manifest.read_bytes(),before)
        self.assertEqual(self.call('scope',self.manifest,'--url','https://urspeechislight.github.io/Faith-Reason-in-Islam/reading.html'),0)

    def test_real_git_worktree_scope_rejects_unrelated_dirty_files(self):
        import subprocess
        def git(*args):subprocess.run(['git','-C',str(self.site),*args],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        git('init');git('-c','user.name=Synthetic Test','-c','user.email=test@example.invalid','commit','--allow-empty','-m','Synthetic fixture')
        self.assertEqual(self.init(),0)
        self.assertTrue((self.site/'.git/article-task.json').is_file())
        (self.site/'unrelated.html').write_text('Different article under another task')
        self.assertEqual(self.call('preflight',self.manifest),1)
        self.assertFalse((self.manifest.parent/'builds').exists())
        self.assertEqual((self.site/'unrelated.html').read_text(),'Different article under another task')


class FindingTests(unittest.TestCase):
    def ids(self, raw):return review.council_finding_ids({'advisors':[{'role':'prose','response':raw}]})
    def test_structured_findings_do_not_multiply_quoted_historical_ids(self):
        raw=json.dumps({'findings':[{'id':'P-01','evidence':'Old FID-03 and P-20 were quoted here.'}], 'open_findings':['FID-16'], 'blocks':[{'id':'b0001','text':'Source P-22','observation':'Compare FID-19.'}]})
        self.assertEqual(self.ids(raw),{'prose:response','prose:P-01','prose:FID-16'})
    def test_declared_legacy_and_whole_response_coverage_survive(self):
        raw='## P-01: Missing qualifier\nReferences P-99 in quoted prose.\n- **FID-02** — Wrong source.\nAn unnumbered source error remains.'
        self.assertEqual(self.ids(raw),{'prose:response','prose:P-01','prose:FID-02'})
    def test_real_findings_cannot_disappear_through_empty_dispositions(self):
        report={'advisors':[{'role':'prose','response':'Unknown format still has a source error.'}]}
        report['release']={'reviewer':'child','response':json.dumps({'status':'passed','artifact_sha256':'x','council_sha256':review.council_digest(report),'assessment':'A synthetic review fixture with enough words to reach the mechanical assessment minimum here.','open_findings':[],'dispositions':[]})}
        self.assertTrue(review.release_errors(report,'x'))


class ArchiveTests(unittest.TestCase):
    def test_canonical_unicode_only_in_scripture_comparison(self):
        from test_scripture import note
        source=note('α\u0301','a','a word')
        self.assertEqual(evidence.scripture_coverage(source,['ά']),[])
        self.assertNotEqual(evidence.flat('α\u0301'),evidence.flat('ά'))
        self.assertTrue(evidence.scripture_coverage(note('ab','a b','two words'),['a\u200db']))
        self.assertTrue(evidence.scripture_coverage(note('שלום','shalom','peace'),['לום']))
    def test_chapter_decode_retains_raw_bytes_and_does_not_reorder(self):
        raw=json.dumps([{'verse':1,'text':'alpha','label':'one'},{'verse':2,'text':'beta','label':'two'}])
        before=review.digest(raw);self.assertIn('alpha beta',evidence.archived_text(raw));self.assertEqual(review.digest(raw),before)
        wrong=json.dumps([{'verse':2,'text':'beta','label':'two'},{'verse':1,'text':'alpha','label':'one'}])
        self.assertNotIn('alpha beta',evidence.archived_text(wrong))
        gap=json.dumps([{'verse':1,'text':'alpha','label':'one'},{'verse':3,'text':'beta','label':'two'}])
        self.assertNotIn('alpha beta',evidence.archived_text(gap))
        self.assertNotIn('alpha beta',evidence.archived_text(json.dumps([{'verse':1,'text':'alpha'},{'verse':3,'text':'beta'}])))

    def test_hebrew_joiners_preserve_exact_words_and_only_boundary_markers_are_excluded(self):
        import scripture_alignment as A
        original='אֱ\u200dֽלֹהִים'
        self.assertEqual(A.words(original),[original])
        self.assertEqual(A.words('שלום׃ פ מלך׃ ס'),['שלום','מלך'])
        self.assertEqual(A.words('פ ס שלום'),['פ','ס','שלום'])
        self.assertEqual(evidence.flat(original),original)

    def test_xml_words_are_decoded_without_repairing_or_dropping_variants(self):
        raw='<Tanach><v n="1"><w>שלום</w><w>מלך</w></v></Tanach>'
        self.assertIn('שלום מלך',evidence.archived_text(raw))
        variant=raw.replace('<w>מלך</w>','<q>מלך</q><k>מלכים</k>')
        self.assertEqual(evidence.archived_text(variant),[variant])

if __name__=='__main__':unittest.main()
