"""Regressions for routine repair without schema exploration or identity workarounds."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import article_build as B
import review
import review_dependencies as D
import review_dispatch as F
import review_identity as I
from test_review_flow import IntakeTests
from test_pipeline import ReviewTests


class IdentityTests(unittest.TestCase):
    def row(self,session,agent='agent-2'):
        return {'reviewer':agent,'reviewer_identity':I.identity(session,agent)}

    def test_equal_local_ids_in_different_sessions_are_distinct(self):
        self.assertEqual(I.distinct(self.row('current'),[self.row('historical')]),[])
        self.assertTrue(I.distinct(self.row('current'),[self.row('current')]))
        self.assertTrue(I.distinct(self.row('current'),[{'reviewer':'agent-2'}]))

    def test_origins_require_actual_matching_response_without_renaming(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=root/'invocation.json';origins=root/'origins.json'
            raw='Retained independent observation about the actual earlier candidate and its sources.'
            report={'advisors':[{'reviewer':'agent-2','response':raw}]}
            record.write_text(json.dumps({'session_id':'old-session','agent_id':'agent-2','response':raw}))
            rows=[{'group':'advisors','index':0,'session_id':'old-session','agent_id':'agent-2','transcript':str(record)}]
            origins.write_text(json.dumps(rows));bound=I.origins(report,origins)
            self.assertNotIn('reviewer_identity',report['advisors'][0])
            self.assertEqual(bound['advisors'][0]['response'],raw)
            self.assertEqual(I.distinct(self.row('new-session'),bound['advisors']),[])
            record.write_text(json.dumps({'session_id':'old-session','agent_id':'agent-2','response':'different response'}))
            with self.assertRaisesRegex(ValueError,'matching session'):I.origins(report,origins)
            rows[0]['agent_id']='invented';origins.write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError,'rename'):I.origins(report,origins)


class DependencyTests(unittest.TestCase):
    def test_render_changes_do_not_invalidate_editorial_but_prose_policy_does(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in set(sum((list(v) for v in D.GROUPS.values()),[])):(root/name).write_text(name)
            with patch.object(D,'ROOT',root):
                editorial=D.digest('editorial');render=D.digest('render')
                (root/'conversion_review.py').write_text('changed visual check')
                self.assertEqual(D.digest('editorial'),editorial);self.assertNotEqual(D.digest('render'),render)
                (root/'editorial.md').write_text('changed prose requirement')
                self.assertNotEqual(D.digest('editorial'),editorial)

    def test_legacy_compatibility_is_exact_and_unknown_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in D.GROUPS['editorial']:(root/name).write_text(name)
            with patch.object(D,'ROOT',root):
                (root/'review-policy-compat.json').write_text(json.dumps({'old':{'editorial':D.digest('editorial')}}))
                self.assertTrue(D.matches('old','editorial'));self.assertFalse(D.matches('unknown','editorial'))
                (root/'review.py').write_text('new semantic validation')
                self.assertFalse(D.matches('old','editorial'))


class ReleaseMaterialsTests(unittest.TestCase):
    def test_complete_release_form_and_materials_validate_without_schema_exploration(self):
        import native_release as N
        from test_native_release import NativeTests,response
        fixture=NativeTests();fixture.setUp();value=fixture.packet
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);text=N.reference_materials(value,root)
            self.assertLess(len(text),7000)
            self.assertEqual((root/'inputs/candidate.md').read_text(),fixture.source)
            form=json.loads((root/'inputs/response-form.json').read_text())
            self.assertEqual([r['id'] for r in form['dispositions']],value['required_disposition_ids'])
            self.assertTrue(N.response_errors(value,json.dumps(form)))
            actual=json.loads(response(value))
            form.update(status=actual['status'],assessment=actual['assessment'],dispositions=actual['dispositions'])
            self.assertEqual(N.response_errors(value,json.dumps(form)),[])
            (root/'inputs/council.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'changed'):N.reference_materials(value,root,check=True)
    def test_known_legacy_release_contract_keeps_exact_binding_and_unknown_fails(self):
        import native_release as N
        from test_native_release import NativeTests,response
        fixture=NativeTests();fixture.setUp()
        with patch.object(N,'contract_hash',return_value='old-contract'):
            old=N.packet(fixture.source,fixture.page,fixture.evidence,fixture.report,'active-parent')
            report=dict(fixture.report,release=N.receipt(old,response(old),'native-child','active-parent'))
        with tempfile.TemporaryDirectory() as temp,patch.object(N,'contract_hash',return_value='new-contract'),patch.object(N,'ROOT',Path(temp)):
            catalog=Path(temp)/'review-policy-compat.json'
            self.assertTrue(N.errors(fixture.source,fixture.page,fixture.evidence,report))
            catalog.write_text(json.dumps({'native_contracts':{'old-contract':'new-contract'}}))
            self.assertEqual(N.errors(fixture.source,fixture.page,fixture.evidence,report),[])
            self.assertTrue(N.errors(fixture.source+' Changed.',fixture.page,fixture.evidence,report))
            catalog.write_text(json.dumps({'native_contracts':{'old-contract':'unrelated-contract'}}))
            self.assertTrue(N.errors(fixture.source,fixture.page,fixture.evidence,report))



class DispatchTests(unittest.TestCase):
    setUp=IntakeTests.setUp
    tearDown=IntakeTests.tearDown
    call=IntakeTests.call
    init=IntakeTests.init
    setup_reviews=IntakeTests.setup_reviews
    request=IntakeTests.request
    reply=IntakeTests.reply
    accept=IntakeTests.accept
    visual_record=IntakeTests.visual_record

    def test_stale_master_stops_render_before_dispatch_and_status_reports_it(self):
        self.setup_reviews();data=B.read(self.manifest);path=Path(data['paths']['review']);row=B.read(path)
        row.update(status='approved',policy_sha256='stale');B.write(path,row)
        out=self.root/'blocked-render'
        self.assertEqual(self.call('review-request',self.manifest,'--kind','render','--parent-model','fixture-parent','--output',out),1)
        self.assertFalse(out.exists());self.assertEqual(self.call('review-plan',self.manifest),1)
        self.assertIn('stale',str(F.plan(B,self.manifest)['errors']))

    def test_sparse_form_keeps_all_judgments_pending_and_expands_only_machine_fields(self):
        self.setup_reviews();draft=review.inspect_file(self.source);template=review.template(draft,draft)
        sparse=F.form(template)
        self.assertNotIn('text',sparse['blocks'][0]);self.assertEqual(sparse['blocks'][0]['decision'],'pending')
        expanded=F.expand(template,sparse)
        self.assertEqual(expanded['blocks'],template['blocks'])
        self.assertTrue(review.verify(draft,draft,expanded,require_release=False))
        approved=ReviewTests().approved(draft);actual=F.expand(template,F.form(approved))
        self.assertEqual(actual['blocks'],approved['blocks'])
        altered=F.form(template);altered['council']['report']={'advisors':[{'reviewer':'invented'}]}
        with self.assertRaisesRegex(ValueError,'retained council'):F.expand(template,altered)
        sparse['blocks'][0]['text']='edited source'
        with self.assertRaisesRegex(ValueError,'immutable'):F.expand(template,sparse)
        sparse=F.form(template);sparse['blocks'].reverse()
        with self.assertRaisesRegex(ValueError,'ordered IDs'):F.expand(template,sparse)

    def test_prompt_is_bounded_and_modified_reading_assets_are_rejected(self):
        self.setup_reviews();request=self.request('render');value=B.read(request)
        prompt=(request.parent/'prompt.txt').read_text()
        self.assertLess(len(prompt),7000);self.assertNotIn(value['page'],prompt)
        self.assertEqual((request.parent/'inputs/article.html').read_text(),value['page'])
        reply=self.reply(request,self.visual_record(value))
        (request.parent/'inputs/article.html').write_text('changed reading copy')
        before=self.manifest.read_bytes()
        self.assertEqual(self.accept(request,reply),1);self.assertEqual(self.manifest.read_bytes(),before)

    def test_readiness_checks_accepted_metadata_and_actual_master_prerequisites(self):
        self.setup_reviews();request=self.request('render');reply=self.reply(request,self.visual_record(B.read(request)))
        self.assertEqual(self.accept(request,reply),0)
        data=B.read(self.manifest);path=Path(data['paths']['html_review']);row=B.read(path)
        row['native']['response_sha256']='corrupt';B.write(path,row)
        self.assertTrue(F.plan(B,self.manifest)['errors'])
        master=ReviewTests().approved(review.inspect_file(self.source));master['structural_validation']['status']='not-applicable'
        B.write(data['paths']['review'],master)
        self.assertIn('master structural_validation must pass',str(F.plan(B,self.manifest)['errors']))

    def test_valid_original_editorial_baseline_is_accepted(self):
        self.setup_reviews();data=B.read(self.manifest)
        before=self.root/'original.md';before.write_text(self.source.read_text().replace('The man went home.','The man returned home.'))
        baseline=review.inspect_file(before);draft=review.inspect_file(self.source)
        row=ReviewTests().approved(draft);row['baseline_sha256']=baseline['artifact_sha256'];row['structural_validation']['status']='passed'
        self.assertEqual(review.verify(draft,baseline,row,require_release=False),[])
        B.write(data['paths']['baseline'],baseline);B.write(data['paths']['review'],row)
        self.assertEqual(F.plan(B,self.manifest)['errors'],[])

    def test_render_fingerprint_excludes_orchestration_but_not_renderer(self):
        with patch.object(B,'runtime',return_value={'/tool/article_build.py':'changed','/tool/render_article.py':'a','/tool/quotation.css':'b','/tool/review.py':'c'}):
            self.assertNotIn('/tool/article_build.py',B.render_runtime())
            self.assertIn('/tool/render_article.py',B.render_runtime())

if __name__=='__main__':unittest.main()
